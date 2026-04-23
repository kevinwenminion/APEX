import glob
import json
import os
import shutil
import sys
import unittest
import tempfile
from pathlib import Path
from unittest import mock

import dpdata
import numpy as np
from monty.serialization import dumpfn, loadfn

from apex.core.calculator.Lammps import Lammps
from apex.core.calculator.lib.lammps_utils import inter_deepmd
from apex.core.property.Gamma.lammps.input import render_gamma_lammps_input
from apex.op.RunLAMMPS import RunLAMMPS

#from .context import make_kspacing_kpoints, setUpModule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
__package__ = "tests"


class TestLammps(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(os.path.abspath(os.path.dirname(__file__)))
        self.jdata = {
            "structures": ["confs/std-fcc"],
            "interaction": {
                "type": "deepmd",
                "model": "lammps_input/frozen_model.pb",
                "deepmd_version": "1.1.0",
                "type_map": {"Al": 0},
            },
            "relaxation": {
                "cal_type": "relaxation",
                "cal_setting": {
                    "relax_pos": True,
                    "relax_shape": True,
                    "relax_vol": True,
                },
            },
        }

        self.equi_path = "confs/std-fcc/relaxation/relax_task"
        self.source_path = "equi/lammps"

        if not os.path.exists(self.equi_path):
            os.makedirs(self.equi_path)

        if not os.path.isfile(os.path.join(self.equi_path, "POSCAR")):
            shutil.copy(
                os.path.join(self.source_path, "Al-fcc.vasp"),
                os.path.join("confs/std-fcc", "POSCAR"),
            )

        self.confs = self.jdata["structures"]
        self.inter_param = self.jdata["interaction"]
        self.relax_param = self.jdata["relaxation"]
        self.Lammps = Lammps(
            self.inter_param, os.path.join(self.source_path, "Al-fcc.vasp")
        )

    def tearDown(self):
        if os.path.exists("confs/std-fcc/relaxation"):
            shutil.rmtree("confs/std-fcc/relaxation")
        os.chdir(self._cwd)

    def test_set_inter_type_func(self):
        self.Lammps.set_inter_type_func()
        self.assertEqual(inter_deepmd, self.Lammps.inter_func)

    def test_set_model_param(self):
        self.Lammps.set_model_param()
        model_param = {
            "type": "deepmd",
            "model_name": ["frozen_model.pb"],
            "param_type": {"Al": 0},
            "deepmd_version": "1.1.0",
        }
        self.assertEqual(model_param, self.Lammps.model_param)

    def test_make_potential_files(self):
        cwd = os.getcwd()
        abs_equi_path = os.path.abspath(self.equi_path)
        self.Lammps.make_potential_files(abs_equi_path)
        self.assertTrue(os.path.islink(os.path.join(self.equi_path, "frozen_model.pb")))
        self.assertTrue(os.path.isfile(os.path.join(self.equi_path, "inter.json")))
        ret = loadfn(os.path.join(self.equi_path, "inter.json"))
        self.assertEqual(self.inter_param, ret)
        os.chdir(cwd)

    def test_make_input_file(self):
        cwd = os.getcwd()
        abs_equi_path = os.path.abspath("confs/std-fcc/relaxation/relax_task")
        shutil.copy(
            os.path.join("confs/std-fcc", "POSCAR"),
            os.path.join(self.equi_path, "POSCAR"),
        )
        self.Lammps.make_input_file(abs_equi_path, "relaxation", self.relax_param)
        self.assertTrue(os.path.isfile(os.path.join(abs_equi_path, "conf.lmp")))
        self.assertTrue(os.path.islink(os.path.join(abs_equi_path, "in.lammps")))
        self.assertTrue(os.path.isfile(os.path.join(abs_equi_path, "task.json")))
        with open(os.path.join(abs_equi_path, "in.lammps")) as fp:
            in_lammps = fp.read()
        self.assertIn("write_dump      all custom dump.relax", in_lammps)

    def test_forward_common_files(self):
        fc_files = ["in.lammps", "frozen_model.pb"]
        self.assertEqual(self.Lammps.forward_common_files(), fc_files)

    def test_backward_files(self):
        backward_files = ["log.lammps", "outlog", "dump.relax"]
        self.assertEqual(self.Lammps.backward_files(), backward_files)

    def test_gamma_lammps_input_writes_final_dump(self):
        in_lammps = render_gamma_lammps_input(
            "conf.lmp",
            {"Al": 0},
            lambda _param: "pair_style      zero 10.0\n",
            {"type": "deepmd"},
            {
                "type": "gamma_surface",
                "cal_type": "relaxation",
                "cal_setting": {
                    "etol": 0,
                    "ftol": 1e-10,
                    "maxiter": 5000,
                    "maxeval": 500000,
                },
                "add_fix": ["true", "true", "false"],
            },
        )

        self.assertIn("write_dump      all custom dump.relax", in_lammps)


class TestRunLammpsOp(unittest.TestCase):
    def test_cleanup_model_links_removes_broken_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = os.path.join(tmp, "relax_task")
            os.makedirs(task_dir, exist_ok=True)

            inter_json = {
                "type": "deepmd",
                "model": "frozen_model.pb",
                "type_map": {"Al": 0},
            }
            dumpfn(inter_json, os.path.join(task_dir, "inter.json"), indent=4)

            os.symlink("../../frozen_model.pb", os.path.join(task_dir, "frozen_model.pb"))
            self.assertTrue(os.path.islink(os.path.join(task_dir, "frozen_model.pb")))

            RunLAMMPS._cleanup_model_links(task_dir)

            self.assertFalse(os.path.lexists(os.path.join(task_dir, "frozen_model.pb")))

    def test_execute_marks_lammps_failure_and_returns_task_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            task_dir = os.path.join(tmp, "task.000077")
            os.makedirs(task_dir, exist_ok=True)

            with mock.patch("apex.op.RunLAMMPS.subprocess.call", return_value=1):
                op_out = RunLAMMPS().execute(
                    {
                        "input_lammps": Path(task_dir),
                        "run_command": "lmp -in in.lammps",
                    }
                )

            self.assertEqual(os.getcwd(), cwd)
            self.assertEqual(op_out["backward_dir"], Path(task_dir))
            marker = loadfn(os.path.join(task_dir, "apex_lammps_failed.json"))
            self.assertEqual(marker["exit_code"], 1)

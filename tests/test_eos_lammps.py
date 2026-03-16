import os
import shutil
import tempfile
import unittest

from apex.core.calculator.Lammps import Lammps
from apex.core.property.EOS.lammps import EOS


class TestEOSLammps(unittest.TestCase):
    def setUp(self):
        self.root = "/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0"
        os.chdir(self.root)
        self.source_poscar = os.path.join(self.root, "tests/equi/lammps/Al-fcc.vasp")
        self.model = os.path.join(self.root, "tests/lammps_input/frozen_model.pb")
        self.tempdir = tempfile.TemporaryDirectory(prefix="eos_lammps_", dir="/tmp")
        self.prop_dir = os.path.join(self.tempdir.name, "eos_00")
        self.task_dirs = [
            os.path.join(self.prop_dir, "task.000000"),
            os.path.join(self.prop_dir, "task.000001"),
        ]
        for task_dir in self.task_dirs:
            os.makedirs(task_dir, exist_ok=True)
            shutil.copy(self.source_poscar, os.path.join(task_dir, "POSCAR"))

        self.inter_param = {
            "type": "deepmd",
            "model": self.model,
            "type_map": {"Al": 0},
        }
        self.prop = EOS(
            {
                "type": "eos",
                "vol_start": 0.95,
                "vol_end": 1.05,
                "vol_step": 0.10,
            },
            self.inter_param,
        )
        self.prop.parameter["scale2equi"] = [0.95, 1.05]
        self.calc = Lammps(self.inter_param, self.source_poscar)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_file_manifest_uses_property_hook(self):
        self.assertEqual(self.calc.forward_common_files("eos"), ["frozen_model.pb"])
        self.assertEqual(
            self.calc.forward_files("eos"),
            ["conf.lmp", "in.lammps", "frozen_model.pb"],
        )
        self.assertEqual(
            self.calc.backward_files("eos"),
            ["log.lammps", "outlog", "dump.relax"],
        )

    def test_make_input_file_keeps_task_local_inputs(self):
        for task_dir in self.task_dirs:
            self.calc.make_potential_files(task_dir)
            cwd = os.getcwd()
            os.chdir(task_dir)
            try:
                self.calc.make_input_file(
                    task_dir, self.prop.task_type(), self.prop.task_param()
                )
            finally:
                os.chdir(cwd)

        shared_input = os.path.join(self.prop_dir, "in.lammps")
        self.assertFalse(os.path.exists(shared_input))

        first_input = os.path.join(self.task_dirs[0], "in.lammps")
        second_input = os.path.join(self.task_dirs[1], "in.lammps")
        self.assertTrue(os.path.isfile(first_input))
        self.assertTrue(os.path.isfile(second_input))
        self.assertFalse(os.path.islink(first_input))
        self.assertFalse(os.path.islink(second_input))

        with open(first_input, "r") as fp:
            first_contents = fp.read()
        with open(second_input, "r") as fp:
            second_contents = fp.read()

        self.assertIn("read_data   conf.lmp", first_contents)
        self.assertIn("read_data   conf.lmp", second_contents)
        self.assertIn("min_style       cg", first_contents)
        self.assertIn("min_style       cg", second_contents)


if __name__ == "__main__":
    unittest.main()

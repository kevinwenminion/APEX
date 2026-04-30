import glob
import os
import shutil
import sys
import unittest

import numpy as np
from monty.serialization import dumpfn
from monty.serialization import loadfn
from pymatgen.core.structure import Structure

from apex.core.property.GammaSurface import GammaSurface
from apex.core.structure import StructureInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
__package__ = "tests"


class TestGammaSurface(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(os.path.abspath(os.path.dirname(__file__)))
        self._cleanup_paths = []

        self.equi_path = "confs/hp-Mo/relaxation/relax_task"
        self.source_path = "equi/vasp"
        self.target_path = "confs/hp-Mo/gamma_surface_00"

        if not os.path.exists(self.equi_path):
            os.makedirs(self.equi_path)
        if not os.path.exists(self.target_path):
            os.makedirs(self.target_path)

        self.prop_param = {
            "type": "gamma_surface",
            "plane_miller": [0, 0, 1],
            "slip_direction": [1, 0, 0],
            "supercell_size": [1, 1, 8],
            "vacuum_size": 10,
            "add_fix": ["true", "true", "false"],
            "n_steps_x": 2,
            "n_steps_y": 1,
        }
        self.gamma_surface = GammaSurface(self.prop_param)

    def tearDown(self):
        if os.path.exists(self.equi_path):
            shutil.rmtree(self.equi_path)
        if os.path.exists(self.target_path):
            shutil.rmtree(self.target_path)
        for path in self._cleanup_paths:
            if os.path.exists(path):
                shutil.rmtree(path)
        os.chdir(self._cwd)

    def test_task_type(self):
        self.assertEqual("gamma_surface", self.gamma_surface.task_type())

    def test_task_param(self):
        self.assertEqual(self.prop_param, self.gamma_surface.task_param())

    def test_make_confs_bcc(self):
        if not os.path.exists(os.path.join(self.equi_path, "CONTCAR")):
            with self.assertRaises(RuntimeError):
                self.gamma_surface.make_confs(self.target_path, self.equi_path)

        shutil.copy(
            os.path.join(self.source_path, "CONTCAR_Mo_bcc"),
            os.path.join(self.equi_path, "CONTCAR"),
        )
        task_list = self.gamma_surface.make_confs(self.target_path, self.equi_path)
        dfm_dirs = glob.glob(os.path.join(self.target_path, "task.*"))
        self.assertEqual(len(dfm_dirs), (self.gamma_surface.n_steps_x + 1) * (self.gamma_surface.n_steps_y + 1))
        self.assertEqual(len(task_list), len(dfm_dirs))

        pairs = set()
        for ii in sorted(dfm_dirs):
            self.assertTrue(os.path.isfile(os.path.join(ii, "POSCAR")))
            self.assertTrue(os.path.isfile(os.path.join(ii, "miller.json")))
            self.assertTrue(os.path.isfile(os.path.join(ii, "displacement.json")))
            disp = loadfn(os.path.join(ii, "displacement.json"))
            pairs.add((disp["frac_x"], disp["frac_y"]))

        self.assertIn((0.0, 0.0), pairs)
        self.assertIn((1.0, 1.0), pairs)

        disp0 = loadfn(os.path.join(self.target_path, "task.000000", "displacement.json"))
        self.assertEqual(disp0["idx_x"], 0)
        self.assertEqual(disp0["idx_y"], 0)
        self.assertEqual(disp0["fault_area"] > 0, True)
        self.assertTrue(np.allclose(disp0["disp_cart"], [0.0, 0.0, 0.0]))
        self.assertAlmostEqual(
            float(np.dot(disp0["inplane_x_cartesian"], disp0["fault_normal_cartesian"])),
            0.0,
            places=6,
        )
        self.assertAlmostEqual(
            float(np.dot(disp0["inplane_y_cartesian"], disp0["fault_normal_cartesian"])),
            0.0,
            places=6,
        )
        cross_xy = np.cross(
            np.array(disp0["inplane_x_cartesian"]),
            np.array(disp0["inplane_y_cartesian"]),
        )
        cross_xy /= np.linalg.norm(cross_xy)
        self.assertGreater(
            float(np.dot(cross_xy, np.array(disp0["fault_normal_cartesian"]))), 1 - 1e-6
        )

    def test_make_confs_fcc_111_slip_orientation(self):
        equi_path = "confs/fcc-Al-gamma/relaxation/relax_task"
        target_path = "confs/fcc-Al-gamma/gamma_surface_00"
        self._cleanup_paths.append("confs/fcc-Al-gamma")
        os.makedirs(equi_path, exist_ok=True)
        shutil.copy(
            os.path.join(self.source_path, "CONTCAR_Al_fcc"),
            os.path.join(equi_path, "CONTCAR"),
        )
        gamma_surface = GammaSurface(
            {
                "type": "gamma_surface",
                "plane_miller": [1, 1, 1],
                "slip_direction": [1, 1, -2],
                "supercell_size": [3, 3, 5],
                "vacuum_size": 0,
                "n_steps_x": 1,
                "n_steps_y": 1,
            }
        )

        task_list = gamma_surface.make_confs(target_path, equi_path)
        self.assertEqual(len(task_list), 4)

        disp0 = loadfn(os.path.join(target_path, "task.000000", "displacement.json"))
        self.assertTrue(np.allclose(disp0["disp_cart"], [0.0, 0.0, 0.0]))
        self.assertAlmostEqual(
            float(np.dot(disp0["inplane_x_cartesian"], disp0["fault_normal_cartesian"])),
            0.0,
            places=6,
        )
        self.assertAlmostEqual(
            float(np.dot(disp0["inplane_y_cartesian"], disp0["fault_normal_cartesian"])),
            0.0,
            places=6,
        )

        st = Structure.from_file(os.path.join(target_path, "task.000000", "POSCAR"))
        c_unit = st.lattice.matrix[2] / np.linalg.norm(st.lattice.matrix[2])
        self.assertGreater(
            float(np.dot(c_unit, np.array(disp0["fault_normal_cartesian"]))), 1 - 1e-6
        )
        fault_area = np.linalg.norm(np.cross(st.lattice.matrix[0], st.lattice.matrix[1]))
        self.assertAlmostEqual(disp0["fault_area"], fault_area, places=6)

    def test_invalid_cubic_slip_direction_raises(self):
        prop = GammaSurface(
            {
                "type": "gamma_surface",
                "plane_miller": [1, 1, 1],
                "slip_direction": [1, 0, 0],
            }
        )
        ss = Structure.from_file(os.path.join(self.source_path, "CONTCAR_Al_fcc"))
        st = StructureInfo(ss)
        prop.structure_type = st.lattice_structure
        prop.conv_std_structure = st.conventional_structure

        with self.assertRaisesRegex(RuntimeError, "slip direction .* is not on plane"):
            prop._GammaSurface__convert_input_miller(prop.conv_std_structure)

    def test_compute_lower_uses_zero_displacement_reference_and_fault_area(self):
        shutil.copy(
            os.path.join(self.source_path, "CONTCAR_Mo_bcc"),
            os.path.join(self.equi_path, "CONTCAR"),
        )
        task_list = self.gamma_surface.make_confs(self.target_path, self.equi_path)
        dumpfn({"energies": [-100.0], "atom_numbs": [1]}, os.path.join(self.equi_path, "result.json"))

        ref_energy = -25.0
        cf = 1.60217657e-16 / 1e-20 * 0.001
        for task in task_list:
            disp = loadfn(os.path.join(task, "displacement.json"))
            st = Structure.from_file(os.path.join(task, "POSCAR"))
            area = np.linalg.norm(np.cross(st.lattice.matrix[0], st.lattice.matrix[1]))
            sfe = 2.0 * disp["frac_x"] + 3.0 * disp["frac_y"]
            energy = ref_energy + sfe * area / cf
            dumpfn(
                {
                    "energies": [energy],
                    "atom_numbs": [len(st.sites)],
                    "cells": [st.lattice.matrix.tolist()],
                },
                os.path.join(task, "result_task.json"),
            )

        output_file = os.path.join(self.target_path, "result.json")
        res_data, _ = self.gamma_surface._compute_lower(output_file, task_list, [])
        self.assertAlmostEqual(res_data["0.000000,0.000000"][2], 0.0, places=8)
        self.assertAlmostEqual(res_data["1.000000,1.000000"][2], 5.0, places=6)

    def test_legacy_n_steps_aliases_to_n_steps_x(self):
        prop = GammaSurface(
            {
                "type": "gamma_surface",
                "plane_miller": [0, 0, 1],
                "slip_direction": [1, 0, 0],
                "n_steps": 3,
            }
        )

        self.assertEqual(prop.n_steps_x, 3)
        self.assertEqual(prop.n_steps, 3)
        self.assertEqual(prop.task_param()["n_steps_x"], 3)


if __name__ == "__main__":
    unittest.main()

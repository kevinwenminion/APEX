import glob
import os
import shutil
import sys
import unittest

import numpy as np
from monty.serialization import loadfn
from pymatgen.core.structure import Structure
from pymatgen.io.vasp import Incar

from apex.core.property.Gamma import Gamma
from apex.core.structure import StructureInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
__package__ = "tests"


class TestGamma(unittest.TestCase):
    def setUp(self):
        _jdata = {
            "structures": ["confs/std-fcc"],
            "interaction": {
                "type": "vasp",
                "incar": "vasp_input/INCAR_Mo",
                "potcar_prefix": "vasp_input",
                "potcars": {"Mo": "POTCAR_Mo"},
            },
            "properties": [
                {
                    "type": "gamma",
                    "plane_miller": [0, 0, 1],
                    "slip_direction": [1, 0, 0],
                    "hcp": {
                        "plane_miller": [0, 0, 0, 1],
                        "slip_direction": [2, -1, -1, 0],
                    },
                    "supercell_size": [1, 1, 10],
                    "vacuum_size": 10,
                    "add_fix": ["true", "true", "false"],
                    "n_steps": 10
                }

            ],
        }

        self.equi_path = "confs/hp-Mo/relaxation/relax_task"
        self.source_path = "equi/vasp"
        self.target_path = "confs/hp-Mo/gamma_00"
        self.res_data = "output/gamma_00/result.json"
        self.ptr_data = "output/gamma_00/result.out"

        if not os.path.exists(self.equi_path):
            os.makedirs(self.equi_path)
        if not os.path.exists(self.target_path):
            os.makedirs(self.target_path)

        self.confs = _jdata["structures"]
        self.inter_param = _jdata["interaction"]
        self.prop_param = _jdata["properties"]

        self.gamma = Gamma(_jdata["properties"][0])
        self._cleanup_paths = []

    def tearDown(self):
        if os.path.exists(self.equi_path):
            shutil.rmtree(self.equi_path)
        if os.path.exists(self.target_path):
            shutil.rmtree(self.target_path)
        if os.path.exists(self.res_data):
            os.remove(self.res_data)
        if os.path.exists(self.ptr_data):
            os.remove(self.ptr_data)
        for path in self._cleanup_paths:
            if os.path.exists(path):
                shutil.rmtree(path)

    def test_task_type(self):
        self.assertEqual("gamma", self.gamma.task_type())

    def test_task_param(self):
        self.assertEqual(self.prop_param[0], self.gamma.task_param())

    def test_make_confs_bcc(self):
        if not os.path.exists(os.path.join(self.equi_path, "CONTCAR")):
            with self.assertRaises(RuntimeError):
                self.gamma.make_confs(self.target_path, self.equi_path)
        shutil.copy(
            os.path.join(self.source_path, "CONTCAR_Mo_bcc"),
            os.path.join(self.equi_path, "CONTCAR"),
        )
        task_list = self.gamma.make_confs(self.target_path, self.equi_path)
        dfm_dirs = glob.glob(os.path.join(self.target_path, "task.*"))
        self.assertEqual(len(dfm_dirs), self.gamma.n_steps + 1)

        incar0 = Incar.from_file(os.path.join("vasp_input", "INCAR.rlx"))
        incar0["ISIF"] = 4

        self.assertEqual(
            os.path.realpath(os.path.join(self.equi_path, "CONTCAR")),
            os.path.realpath(os.path.join(self.target_path, "POSCAR")),
        )
        ref_st = Structure.from_file(os.path.join(self.target_path, "POSCAR"))
        dfm_dirs.sort()
        for ii in dfm_dirs:
            st_file = os.path.join(ii, "POSCAR")
            self.assertTrue(os.path.isfile(st_file))
            st0 = Structure.from_file(st_file)
            st1_file = os.path.join(ii, "POSCAR.tmp")
            self.assertTrue(os.path.isfile(st1_file))
            st1 = Structure.from_file(st1_file)
            with open(st1_file, mode="r") as f:
                z_coord_str = f.readlines()[-1].split()[-2]
                z_coord = float(z_coord_str)
            self.assertTrue(z_coord <= 1)

        disp0 = loadfn(os.path.join(self.target_path, "task.000000", "displacement.json"))
        self.assertTrue(np.allclose(disp0["disp_cart"], [0.0, 0.0, 0.0]))
        self.assertAlmostEqual(
            float(np.dot(disp0["inplane_x_cartesian"], disp0["fault_normal_cartesian"])),
            0.0,
            places=6,
        )

    def test_make_confs_fcc_111_orientation(self):
        equi_path = "confs/fcc-Al-gamma/relaxation/relax_task"
        target_path = "confs/fcc-Al-gamma/gamma_00"
        self._cleanup_paths.append("confs/fcc-Al-gamma")
        os.makedirs(equi_path, exist_ok=True)
        shutil.copy(
            os.path.join(self.source_path, "CONTCAR_Al_fcc"),
            os.path.join(equi_path, "CONTCAR"),
        )
        gamma = Gamma(
            {
                "type": "gamma",
                "plane_miller": [1, 1, 1],
                "slip_direction": [1, 1, -2],
                "supercell_size": [3, 3, 5],
                "vacuum_size": 0,
                "add_fix": ["true", "true", "false"],
                "n_steps": 2,
            }
        )
        task_list = gamma.make_confs(target_path, equi_path)
        self.assertEqual(len(task_list), 3)

        disp0 = loadfn(os.path.join(target_path, "task.000000", "displacement.json"))
        disp1 = loadfn(os.path.join(target_path, "task.000001", "displacement.json"))
        st0 = Structure.from_file(os.path.join(target_path, "task.000000", "POSCAR"))
        st1 = Structure.from_file(os.path.join(target_path, "task.000001", "POSCAR"))

        c_unit = st0.lattice.matrix[2] / np.linalg.norm(st0.lattice.matrix[2])
        normal = np.array(disp0["fault_normal_cartesian"], dtype=float)
        self.assertGreater(float(np.dot(c_unit, normal)), 1 - 1e-6)

        slip_dir = np.array(disp0["inplane_x_cartesian"], dtype=float)
        self.assertAlmostEqual(float(np.dot(slip_dir, normal)), 0.0, places=6)

        top = np.where(st0.frac_coords[:, 2] > 0.5 + 1e-6)[0]
        disp_vectors = []
        cell = st0.lattice.matrix
        for idx in top:
            dv = st1.cart_coords[idx] - st0.cart_coords[idx]
            best = None
            best_norm = None
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    for c in (-1, 0, 1):
                        trial = dv + a * cell[0] + b * cell[1] + c * cell[2]
                        norm = np.linalg.norm(trial)
                        if best_norm is None or norm < best_norm:
                            best_norm = norm
                            best = trial
            if np.linalg.norm(best) > 1e-8:
                disp_vectors.append(best)
        disp_mean = np.mean(disp_vectors, axis=0)
        disp_unit = disp_mean / np.linalg.norm(disp_mean)
        self.assertAlmostEqual(float(np.dot(disp_unit, normal)), 0.0, places=6)
        self.assertGreater(float(np.dot(disp_unit, slip_dir)), 1 - 1e-6)

    def test_invalid_cubic_slip_direction_raises(self):
        gamma = Gamma(
            {
                "type": "gamma",
                "plane_miller": [1, 1, 1],
                "slip_direction": [1, 0, 0],
            }
        )
        ss = Structure.from_file(os.path.join(self.source_path, "CONTCAR_Al_fcc"))
        st = StructureInfo(ss)
        gamma.structure_type = st.lattice_structure
        gamma.conv_std_structure = st.conventional_structure

        with self.assertRaisesRegex(RuntimeError, "slip direction .* is not on plane"):
            gamma._Gamma__convert_input_miller(gamma.conv_std_structure)

    def test_compute_lower(self):
        cwd = os.getcwd()
        output_file = os.path.join(cwd, "output/gamma_00/result.json")
        all_tasks = glob.glob("output/gamma_00/task.*")
        all_tasks.sort()
        all_res = [os.path.join(task, "result_task.json") for task in all_tasks]

        self.gamma._compute_lower(output_file, all_tasks, all_res)

        self.assertTrue(os.path.isfile(self.res_data))

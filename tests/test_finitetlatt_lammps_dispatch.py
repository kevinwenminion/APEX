import os
import shutil
import tempfile
import unittest

from apex.core.calculator.Lammps import Lammps


class TestFiniteTlattLammpsDispatch(unittest.TestCase):
    def setUp(self):
        self.root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        os.chdir(self.root)
        self.source_poscar = os.path.join(self.root, "tests/equi/lammps/Al-fcc.vasp")
        self.model = os.path.join(self.root, "tests/lammps_input/frozen_model.pb")
        self.tempdir = tempfile.TemporaryDirectory(
            prefix="finitetlatt_lammps_", dir="/tmp"
        )
        self.task_dir = os.path.join(
            self.tempdir.name, "finitetlatt_00", "task.000000"
        )
        os.makedirs(self.task_dir, exist_ok=True)
        shutil.copy(self.source_poscar, os.path.join(self.task_dir, "POSCAR"))
        self.calc = Lammps(
            {"type": "deepmd", "model": self.model, "type_map": {"Al": 0}},
            self.source_poscar,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_npt_ave_time_uses_property_renderer(self):
        self.calc.make_potential_files(self.task_dir)
        cwd = os.getcwd()
        os.chdir(self.task_dir)
        try:
            self.calc.make_input_file(
                self.task_dir,
                "finitetlatt",
                {
                    "cal_type": "npt+ave/time",
                    "cal_setting": {},
                },
            )
        finally:
            os.chdir(cwd)

        common_input = os.path.join(self.tempdir.name, "finitetlatt_00", "in.lammps")
        with open(common_input, "r") as fp:
            contents = fp.read()

        self.assertIn("include  in.variable", contents)
        self.assertIn("fix 2 all ave/time", contents)

    def test_file_manifests_use_property_hook(self):
        self.assertEqual(
            self.calc.forward_files("finitetlatt"),
            ["in.lammps", "in.variable", "frozen_model.pb"],
        )
        self.assertEqual(
            self.calc.forward_common_files("finitetlatt"),
            ["in.lammps", "in.variable", "frozen_model.pb"],
        )
        self.assertEqual(
            self.calc.backward_files("finitetlatt"),
            ["log.lammps", "outlog", "dump.relax", "average_box.txt"],
        )


if __name__ == "__main__":
    unittest.main()

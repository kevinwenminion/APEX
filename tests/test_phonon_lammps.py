import os
import shutil
import tempfile
import unittest

from apex.core.calculator.Lammps import Lammps
from apex.core.property.Phonon.lammps import Phonon


class TestPhononLammps(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.source_poscar = os.path.join(root, "tests/equi/lammps/Al-fcc.vasp")
        self.model = os.path.join(root, "tests/lammps_input/frozen_model.pb")
        self.tempdir = tempfile.TemporaryDirectory(prefix="phonon_lammps_", dir="/tmp")
        self.task_dir = os.path.join(self.tempdir.name, "phonon_00", "task.000000")
        os.makedirs(self.task_dir, exist_ok=True)
        shutil.copy(self.source_poscar, os.path.join(self.task_dir, "POSCAR"))

        self.prop = Phonon(
            {
                "type": "phonon",
                "approach": "linear",
                "supercell_size": [2, 2, 2],
            },
            {"type": "deepmd", "model": self.model, "type_map": {"Al": 0}},
        )
        self.calc = Lammps(
            {"type": "deepmd", "model": self.model, "type_map": {"Al": 0}},
            self.source_poscar,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_make_input_file(self):
        self.calc.make_potential_files(self.task_dir)
        cwd = os.getcwd()
        os.chdir(self.task_dir)
        try:
            self.calc.make_input_file(
                self.task_dir, self.prop.task_type(), self.prop.task_param()
            )
        finally:
            os.chdir(cwd)

        common_input = os.path.join(self.tempdir.name, "phonon_00", "in.lammps")
        task_input = os.path.join(self.task_dir, "in.lammps")

        self.assertTrue(os.path.isfile(common_input))
        self.assertTrue(os.path.islink(task_input))
        with open(common_input, "r") as fp:
            contents = fp.read()
        self.assertIn("read_data   conf.lmp", contents)
        self.assertIn("pair_style deepmd", contents)
        self.assertIn("pair_coeff * * Al", contents)
        self.assertNotIn("compute         mype all pe", contents)

    def test_post_process_backend_writes_run_command(self):
        run_command = os.path.join(self.task_dir, "run_command")
        with open(os.path.join(self.task_dir, "in.lammps"), "w") as fp:
            fp.write("pair_coeff * * frozen_model.pb Al\n")

        self.prop._post_process_backend([self.task_dir])

        self.assertTrue(os.path.isfile(run_command))
        with open(run_command, "r") as fp:
            contents = fp.read()
        self.assertIn("phonolammps in.lammps -c POSCAR --dim 2 2 2", contents)

    def test_backward_files(self):
        self.assertEqual(
            self.calc.backward_files(self.prop.task_type()),
            ["outlog", "FORCE_CONSTANTS"],
        )

    def test_displacement_is_rejected(self):
        with self.assertRaises(TypeError):
            Phonon(
                {
                    "type": "phonon",
                    "approach": "displacement",
                    "supercell_size": [2, 2, 2],
                },
                {"type": "deepmd", "model": self.model, "type_map": {"Al": 0}},
            )


if __name__ == "__main__":
    unittest.main()

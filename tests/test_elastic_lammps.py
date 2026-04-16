import os
import shutil
import tempfile
import unittest

from apex.core.calculator.Lammps import Lammps
from apex.core.calculator.Lammps import PROPERTY_LAMMPS_INPUT_RENDERERS
from apex.core.property.Elastic.lammps import Elastic


class TestElasticLammps(unittest.TestCase):
    def setUp(self):
        self.root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        os.chdir(self.root)
        self.source_poscar = os.path.join(self.root, "tests/equi/lammps/Al-fcc.vasp")
        self.model = os.path.join(self.root, "tests/lammps_input/frozen_model.pb")
        self.tempdir = tempfile.TemporaryDirectory(prefix="elastic_lammps_", dir="/tmp")
        self.task_dir = os.path.join(self.tempdir.name, "elastic_00", "task.000000")
        os.makedirs(self.task_dir, exist_ok=True)
        shutil.copy(self.source_poscar, os.path.join(self.task_dir, "POSCAR"))

        self.inter_param = {
            "type": "deepmd",
            "model": self.model,
            "type_map": {"Al": 0},
        }
        self.prop = Elastic(
            {
                "type": "elastic",
                "norm_deform": 1e-2,
                "shear_deform": 1e-2,
            },
            self.inter_param,
        )
        self.calc = Lammps(self.inter_param, self.source_poscar)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_renderer_is_registered(self):
        self.assertIn("elastic", PROPERTY_LAMMPS_INPUT_RENDERERS)

    def test_make_input_file_uses_elastic_template(self):
        self.calc.make_potential_files(self.task_dir)
        cwd = os.getcwd()
        os.chdir(self.task_dir)
        try:
            self.calc.make_input_file(
                self.task_dir, self.prop.task_type(), self.prop.task_param()
            )
        finally:
            os.chdir(cwd)

        common_input = os.path.join(self.tempdir.name, "elastic_00", "in.lammps")
        task_input = os.path.join(self.task_dir, "in.lammps")

        self.assertTrue(os.path.isfile(common_input))
        self.assertTrue(os.path.islink(task_input))
        with open(common_input, "r") as fp:
            contents = fp.read()

        self.assertIn("read_data   conf.lmp", contents)
        self.assertIn("pair_style deepmd", contents)
        self.assertIn("pair_coeff * * Al", contents)
        self.assertIn("min_style       cg", contents)
        self.assertIn("Final Base area = ${AA}", contents)
        self.assertNotIn("box/relax", contents)


if __name__ == "__main__":
    unittest.main()

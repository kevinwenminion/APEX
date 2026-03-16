import unittest

from apex.core.calculator.lib import lammps_utils


class TestLammpsUtilsRefactor(unittest.TestCase):
    def test_elastic_helper_removed_from_generic_lib(self):
        self.assertFalse(hasattr(lammps_utils, "make_lammps_elastic"))


if __name__ == "__main__":
    unittest.main()

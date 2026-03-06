import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
__package__ = "tests"

from apex.core.common_prop import make_property_instance
from apex.core.property.abacus.Phonon import Phonon as AbacusPhonon
from apex.core.property.lammps.Phonon import Phonon as LammpsPhonon
from apex.core.property.vasp.Phonon import Phonon as VaspPhonon


class TestPropertyFactory(unittest.TestCase):
    def test_software_first_vasp(self):
        prop = make_property_instance({"type": "elastic"}, {"type": "vasp"})
        self.assertEqual(prop.__class__.__name__, "Elastic")
        self.assertTrue(prop.__module__.startswith("apex.core.property.vasp.Elastic"))

    def test_software_first_abacus(self):
        prop = make_property_instance({"type": "elastic"}, {"type": "abacus"})
        self.assertEqual(prop.__class__.__name__, "Elastic")
        self.assertTrue(prop.__module__.startswith("apex.core.property.abacus.Elastic"))

    def test_software_first_lammps_family(self):
        # LAMMPS-style interaction types should route to the LAMMPS registry first.
        prop = make_property_instance({"type": "finitetlatt"}, {"type": "meam"})
        self.assertEqual(prop.__class__.__name__, "FiniteTlatt")
        self.assertTrue(prop.__module__.startswith("apex.core.property.lammps.FiniteTlatt"))

    def test_unknown_interaction(self):
        with self.assertRaises(RuntimeError):
            make_property_instance({"type": "eos"}, {"type": "siesta"})

    def test_unknown_property_for_backend(self):
        with self.assertRaises(RuntimeError):
            make_property_instance({"type": "not-a-property"}, {"type": "vasp"})

    def test_backend_property_modules_exist(self):
        self.assertTrue(VaspPhonon.__module__.startswith("apex.core.property.vasp.Phonon"))
        self.assertTrue(AbacusPhonon.__module__.startswith("apex.core.property.abacus.Phonon"))
        self.assertTrue(LammpsPhonon.__module__.startswith("apex.core.property.lammps.Phonon"))


if __name__ == "__main__":
    unittest.main()

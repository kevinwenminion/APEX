import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
__package__ = "tests"

from apex.core.property.factory import make_property_instance
from apex.core.property.Cohesive.lammps import Cohesive as LammpsCohesive
from apex.core.property.Gamma.lammps import Gamma as LammpsGamma
from apex.core.property.Phonon.abacus import Phonon as AbacusPhonon
from apex.core.property.Phonon.lammps import Phonon as LammpsPhonon
from apex.core.property.Phonon.vasp import Phonon as VaspPhonon
from apex.core.property.Surface.lammps import Surface as LammpsSurface


class TestPropertyFactory(unittest.TestCase):
    def test_software_first_vasp(self):
        prop = make_property_instance({"type": "elastic"}, {"type": "vasp"})
        self.assertEqual(prop.__class__.__name__, "Elastic")
        self.assertTrue(prop.__module__.startswith("apex.core.property.Elastic.vasp"))

    def test_software_first_abacus(self):
        prop = make_property_instance({"type": "elastic"}, {"type": "abacus"})
        self.assertEqual(prop.__class__.__name__, "Elastic")
        self.assertTrue(prop.__module__.startswith("apex.core.property.Elastic.abacus"))

    def test_software_first_lammps_family(self):
        # LAMMPS-style interaction types should route to the LAMMPS registry first.
        prop = make_property_instance({"type": "finitetlatt"}, {"type": "meam"})
        self.assertEqual(prop.__class__.__name__, "FiniteTlatt")
        self.assertTrue(prop.__module__.startswith("apex.core.property.FiniteTlatt.lammps"))

    def test_unknown_interaction(self):
        with self.assertRaises(RuntimeError):
            make_property_instance({"type": "eos"}, {"type": "siesta"})

    def test_unknown_property_for_backend(self):
        with self.assertRaises(RuntimeError):
            make_property_instance({"type": "not-a-property"}, {"type": "vasp"})

    def test_backend_property_modules_exist(self):
        self.assertTrue(LammpsCohesive.__module__.startswith("apex.core.property.Cohesive.lammps"))
        self.assertTrue(LammpsGamma.__module__.startswith("apex.core.property.Gamma.lammps"))
        self.assertTrue(VaspPhonon.__module__.startswith("apex.core.property.Phonon.vasp"))
        self.assertTrue(AbacusPhonon.__module__.startswith("apex.core.property.Phonon.abacus"))
        self.assertTrue(LammpsPhonon.__module__.startswith("apex.core.property.Phonon.lammps"))
        self.assertTrue(LammpsSurface.__module__.startswith("apex.core.property.Surface.lammps"))

    def test_generic_lammps_binding_factory_preserves_module_identity(self):
        prop = make_property_instance(
            {
                "type": "surface",
                "min_slab_size": 10,
                "min_vacuum_size": 10,
            },
            {"type": "deepmd", "model": "frozen_model.pb", "type_map": {"Al": 0}},
        )
        self.assertEqual(prop.__class__.__name__, "Surface")
        self.assertTrue(prop.__module__.startswith("apex.core.property.Surface.lammps"))


if __name__ == "__main__":
    unittest.main()

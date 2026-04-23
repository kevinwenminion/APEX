import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
__package__ = "tests"

from apex.core.property.factory import get_lammps_backend_summary


class TestLammpsBackendSummary(unittest.TestCase):
    def test_surface_summary_is_property_local_and_generic(self):
        summary = get_lammps_backend_summary("surface")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["input_mode"], "generic")
        self.assertEqual(summary["default_cal_type"], "relaxation")
        self.assertIn("surface energies", summary["what_it_computes"])
        self.assertEqual(summary["task_metadata_files"], ["miller.json"])

    def test_interstitial_summary_lists_metadata_files(self):
        summary = get_lammps_backend_summary("interstitial")
        self.assertIsNotNone(summary)
        self.assertIn("element.out", summary["property_metadata_files"])
        self.assertIn("interstitial_type.json", summary["task_metadata_files"])

    def test_property_without_summary_returns_none(self):
        self.assertIsNone(get_lammps_backend_summary("gamma"))


if __name__ == "__main__":
    unittest.main()

import unittest

from apex.submit import validate_submit_paths


class TestSubmitPathValidation(unittest.TestCase):
    def test_accept_paths_without_dot(self):
        params = [
            {
                "structures": ["confs/std-*"],
                "interaction": {"model": "models/Al_eam_alloy"},
            }
        ]
        validate_submit_paths(params)

    def test_reject_dot_in_structures(self):
        params = [
            {
                "structures": ["./confs/std-*"],
                "interaction": {"model": "models/Al_eam_alloy"},
            }
        ]
        with self.assertRaises(RuntimeError) as cm:
            validate_submit_paths(params)
        self.assertIn("parameter[0].structures[0]", str(cm.exception))

    def test_allow_dot_in_model_string(self):
        params = [
            {
                "structures": ["confs/std-*"],
                "interaction": {"model": "Al.eam.alloy"},
            }
        ]
        validate_submit_paths(params)

    def test_allow_dot_in_model_list(self):
        params = [
            {
                "structures": ["confs/std-*"],
                "interaction": {"model": ["Al_eam_alloy", "frozen_model.pb"]},
            }
        ]
        validate_submit_paths(params)

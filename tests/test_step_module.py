import unittest
from unittest.mock import patch

from apex.step import do_step, do_step_from_args


class TestStepModule(unittest.TestCase):
    def test_do_step_rejects_mismatched_step_and_param_type(self):
        params = {
            "structures": ["tests/confs/std-bcc"],
            "interaction": {"type": "vasp", "incar": "INCAR", "potcars": {"Mo": "POTCAR"}},
            "properties": [{"type": "eos"}],
        }
        with self.assertRaises(RuntimeError):
            do_step(params, "make_relax")

    def test_do_step_run_relax_without_machine_raises_runtimewarning(self):
        params = {
            "structures": ["tests/confs/std-bcc"],
            "interaction": {"type": "vasp", "incar": "INCAR", "potcars": {"Mo": "POTCAR"}},
            "relaxation": {"cal_setting": {}},
        }
        with self.assertRaises(RuntimeWarning):
            do_step(params, "run_relax", machine_dict=None)

    def test_do_step_from_args_loads_and_delegates(self):
        param_dict = {
            "structures": ["tests/confs/std-bcc"],
            "interaction": {"type": "vasp", "incar": "INCAR", "potcars": {"Mo": "POTCAR"}},
            "properties": [{"type": "eos"}],
        }
        machine_dict = {"context_type": "LocalContext"}

        with patch("apex.step.loadfn", return_value=param_dict), \
             patch("apex.step.load_config_file", return_value=machine_dict), \
             patch("apex.step.do_step") as mock_do_step:
            do_step_from_args("param.json", "make_props", "global.json")

        mock_do_step.assert_called_once_with(
            param_dict=param_dict,
            step="make_props",
            machine_dict=machine_dict,
        )


if __name__ == "__main__":
    unittest.main()

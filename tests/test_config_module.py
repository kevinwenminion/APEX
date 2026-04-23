import unittest
from unittest.mock import patch

from apex.config import Config


class TestConfigModule(unittest.TestCase):
    def test_local_context_builds_machine_dict_and_defaults_pool_size(self):
        cfg = Config(
            context_type="LocalContext",
            batch_type="Shell",
            local_root=".",
            remote_root="/tmp/apex-remote",
            group_size=4,
        )

        self.assertEqual(cfg.machine_dict["context_type"], "LocalContext")
        self.assertEqual(cfg.machine_dict["batch_type"], "Shell")
        self.assertEqual(cfg.machine_dict["local_root"], ".")
        self.assertEqual(cfg.machine_dict["remote_root"], "/tmp/apex-remote")
        self.assertEqual(cfg.pool_size, 1)

    def test_get_executor_returns_none_without_dispatcher_context(self):
        cfg = Config()
        executor = cfg.get_executor(cfg.dispatcher_config_dict)
        self.assertIsNone(executor)

    def test_get_executor_filters_unknown_parameters(self):
        cfg = Config(context_type="LocalContext")

        class DummyExecutor:
            def __init__(self, command=None, image=None):
                self.command = command
                self.image = image

        dispatcher_cfg = {
            "command": "python3",
            "image": "demo-image",
            "unknown": "ignored",
        }

        with patch("apex.config.DispatcherExecutor", DummyExecutor):
            executor = cfg.get_executor(dispatcher_cfg)

        self.assertIsInstance(executor, DummyExecutor)
        self.assertEqual(executor.command, "python3")
        self.assertEqual(executor.image, "demo-image")


if __name__ == "__main__":
    unittest.main()

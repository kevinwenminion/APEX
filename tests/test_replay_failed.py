import json
import os
import tempfile
import unittest
from unittest.mock import patch

from apex.main import parse_args
from apex.replay_failed import build_retry_workspace, discover_retryable_tasks


class TestReplayFailed(unittest.TestCase):
    def test_discover_retryable_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            failed_root = os.path.join(tmp, ".failed-artifacts")
            task_ok = os.path.join(failed_root, "propertycal-a", "PropsLAMMPS-Cal", "backward_dir", "task.000077")
            os.makedirs(task_ok, exist_ok=True)
            with open(os.path.join(task_ok, "in.lammps"), "w", encoding="utf-8") as fp:
                fp.write("# mock")

            os.makedirs(os.path.join(failed_root, "propertycal-a", "other_dir"), exist_ok=True)

            tasks = discover_retryable_tasks(failed_root)
            self.assertEqual(len(tasks), 1)
            self.assertTrue(tasks[0].endswith("task.000077"))

    def test_build_retry_workspace_writes_manifest_and_checklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            failed_root = os.path.join(tmp, ".failed-artifacts")
            task_ok = os.path.join(failed_root, "relaxcal-b", "RelaxLAMMPS-Cal", "backward_dir", "task.000003")
            os.makedirs(task_ok, exist_ok=True)
            with open(os.path.join(task_ok, "in.lammps"), "w", encoding="utf-8") as fp:
                fp.write("# mock")
            with open(os.path.join(task_ok, "task.json"), "w", encoding="utf-8") as fp:
                fp.write("{}")

            output_dir = os.path.join(tmp, "retry_workspace")
            result = build_retry_workspace(failed_root=failed_root, output_dir=output_dir)

            self.assertEqual(result["task_count"], 1)
            self.assertTrue(os.path.isfile(result["manifest_path"]))
            self.assertTrue(os.path.isfile(result["checklist_path"]))

            with open(result["manifest_path"], "r", encoding="utf-8") as fp:
                manifest = json.load(fp)
            self.assertEqual(manifest["task_count"], 1)
            self.assertEqual(manifest["tasks"][0]["engine"], "lammps")
            self.assertTrue(os.path.isdir(manifest["tasks"][0]["staged"]))


class TestReplayFailedCliParser(unittest.TestCase):
    def test_replay_failed_parser_defaults(self):
        with patch("sys.argv", ["apex", "replay-failed"]):
            _, args = parse_args()

        self.assertEqual(args.cmd, "replay-failed")
        self.assertEqual(args.work, ".")
        self.assertEqual(args.failed_root, ".failed-artifacts")
        self.assertEqual(args.output, "./retry_workspace")
        self.assertFalse(args.submit)


if __name__ == "__main__":
    unittest.main()

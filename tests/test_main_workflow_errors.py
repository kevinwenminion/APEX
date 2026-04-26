import os
import tempfile
import unittest
from unittest import mock

from apex import main as apex_main


class FakeNotFoundError(Exception):
    status = 404

    def __str__(self):
        return (
            "(404)\n"
            "Reason: Not Found\n"
            'HTTP response body: {"code": "10001", '
            '"msg": "archived workflow guipro-joint-svgzz not found"}'
        )


class FakeWorkflow:
    def query_keys_of_steps(self):
        raise FakeNotFoundError()


class FakeStepInfo:
    def get_step(self, parent_id=None, sort_by_generation=False, key=None):
        return []


class WorkflowQueryErrorTest(unittest.TestCase):
    def test_retrieve_key_filter_includes_joint_relax_tasks(self):
        self.assertTrue(apex_main._is_retrievable_result_step_key("relaxcal-rss-hea-conf-001"))
        self.assertTrue(apex_main._is_retrievable_result_step_key("propertycal-rss-hea-conf-001-eos-00"))
        self.assertTrue(apex_main._is_retrievable_result_step_key("relaxationcal"))
        self.assertFalse(apex_main._is_retrievable_result_step_key("relaxmake-rss-hea-conf-001"))

    def test_failure_artifact_retrieval_requires_debug_mode(self):
        old_mode = apex_main.config.get("mode")
        try:
            apex_main.config["mode"] = "default"
            self.assertFalse(apex_main._should_retrieve_failure_artifacts(False))
            self.assertTrue(apex_main._should_retrieve_failure_artifacts(True))
            apex_main.config["mode"] = "debug"
            self.assertTrue(apex_main._should_retrieve_failure_artifacts(False))
        finally:
            apex_main.config["mode"] = old_mode

    def test_formats_dflow_workflow_not_found_error(self):
        message = apex_main._format_workflow_query_error(
            "guipro-joint-svgzz",
            FakeNotFoundError(),
        )

        self.assertIn("Workflow 'guipro-joint-svgzz' was not found", message)
        self.assertIn(".workflow.log", message)
        self.assertIn("-c config file", message)

    def test_query_keys_exits_without_raw_traceback_for_missing_workflow(self):
        with self.assertRaises(SystemExit) as context:
            apex_main._query_keys_of_steps_or_exit(
                FakeWorkflow(),
                "guipro-joint-svgzz",
            )

        self.assertIn(
            "Workflow 'guipro-joint-svgzz' was not found",
            str(context.exception),
        )

    def test_download_artifact_does_not_retry_missing_storage_artifact(self):
        with mock.patch(
                "apex.main.download_artifact",
                side_effect=RuntimeError("The artifact does not exist in the storage"),
        ) as mocked_download, mock.patch("apex.main.time.sleep") as mocked_sleep:
            with self.assertRaises(RuntimeError) as context:
                apex_main._download_artifact_with_retry(
                    artifact="remote-artifact",
                    path="/tmp/out",
                    retries=3,
                    delay=1,
                )

        self.assertIn("without retry", str(context.exception))
        mocked_download.assert_called_once()
        mocked_sleep.assert_not_called()

    def test_download_artifact_retries_transient_network_error(self):
        with mock.patch(
                "apex.main.download_artifact",
                side_effect=[RuntimeError("connection broken"), "downloaded"],
        ) as mocked_download, mock.patch("apex.main.time.sleep") as mocked_sleep:
            result = apex_main._download_artifact_with_retry(
                artifact="remote-artifact",
                path="/tmp/out",
                retries=2,
                delay=1,
            )

        self.assertEqual(result, "downloaded")
        self.assertEqual(mocked_download.call_count, 2)
        mocked_sleep.assert_called_once_with(1)

    def test_retrieve_existing_result_dir_detects_relaxation_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result_dir = os.path.join(tmpdir, "RSS_HEA", "conf_001", "relaxation")
            os.makedirs(result_dir)
            with open(os.path.join(result_dir, "result.json"), "w", encoding="utf-8") as fp:
                fp.write("{}")
            step = {
                "inputs": {
                    "parameters": {
                        "flow_id": {"value": "RSS_HEA/conf_001"},
                    }
                }
            }

            self.assertEqual(
                apex_main._retrieve_existing_result_dir(
                    step,
                    "relaxcal-rss-hea-conf-001",
                    tmpdir,
                ),
                result_dir,
            )

    def test_retrieve_existing_result_dir_detects_property_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result_dir = os.path.join(tmpdir, "RSS_HEA", "conf_001", "eos_00")
            os.makedirs(result_dir)
            with open(os.path.join(result_dir, "result.json"), "w", encoding="utf-8") as fp:
                fp.write("{}")
            step = {
                "inputs": {
                    "parameters": {
                        "path_to_prop": {"value": "RSS_HEA/conf_001/eos_00"},
                    }
                }
            }

            self.assertEqual(
                apex_main._retrieve_existing_result_dir(
                    step,
                    "propertycal-rss-hea-conf-001-eos-00",
                    tmpdir,
                ),
                result_dir,
            )

    def test_download_failure_artifacts_skips_existing_target_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = os.path.join(
                tmpdir,
                ".failed-artifacts",
                "relaxcal-rss-hea-conf-001",
                "Relaxmake",
                "main-logs",
            )
            os.makedirs(target_dir)
            with open(os.path.join(target_dir, "main.log"), "w", encoding="utf-8") as fp:
                fp.write("existing")
            step = {
                "id": "step-001",
                "displayName": "Relaxmake",
                "outputs": {
                    "artifacts": {
                        "main-logs": "remote-artifact",
                    }
                },
            }

            with mock.patch("apex.main.download_artifact") as mocked_download:
                downloaded = apex_main._download_failure_artifacts_for_step(
                    wf_info=FakeStepInfo(),
                    root_step=step,
                    key="relaxcal-rss-hea-conf-001",
                    work_dir=tmpdir,
                )

        self.assertEqual(downloaded, 0)
        mocked_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()

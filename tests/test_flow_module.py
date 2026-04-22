import os
import tempfile
import types
import unittest
from unittest import mock

from apex.flow import FlowGenerator
from apex.op.relaxation_ops import RelaxMake


class TestFlowModule(unittest.TestCase):
    def _make_flow_generator(self):
        return FlowGenerator(
            make_image="img-make",
            run_image="img-run",
            post_image="img-post",
            run_command="echo run",
            calculator="lammps",
            run_op=RelaxMake,
        )

    def test_regulate_name_conforms_to_rfc1123_like_pattern(self):
        name = "__My Workflow/Name__"
        clean = FlowGenerator.regulate_name(name)
        self.assertEqual(clean, "my-workflow-name")

    def test_dump_flow_id_writes_workflow_log(self):
        fg = self._make_flow_generator()
        fg.workflow = types.SimpleNamespace(id="wf-id", uid="wf-uid")

        with tempfile.TemporaryDirectory(prefix="apex-flow-") as td:
            fg.download_path = td
            fg.dump_flow_id()

            logf = os.path.join(td, ".workflow.log")
            self.assertTrue(os.path.isfile(logf))
            with open(logf, "r") as fp:
                content = fp.read()
            self.assertIn("wf-id", content)
            self.assertIn("submit", content)
            self.assertIn(td, content)

    def test_format_step_failure_includes_message(self):
        fg = self._make_flow_generator()
        detail = fg._format_step_failure(
            {
                "phase": "Failed",
                "message": "lammps exited with code 1",
                "podName": "task-abc",
            },
            "Sub relaxation relaxcal-hea failed",
        )

        self.assertIn("Sub relaxation relaxcal-hea failed", detail)
        self.assertIn("message: lammps exited with code 1", detail)
        self.assertIn("podName: task-abc", detail)

    def test_format_step_failure_includes_main_logs_path(self):
        fg = self._make_flow_generator()
        detail = fg._format_step_failure(
            {"phase": "Failed"},
            "Sub relaxation relaxcal-hea failed",
            main_log_path="/tmp/apex/main-logs/relaxcal-hea",
        )

        self.assertIn("main_logs: /tmp/apex/main-logs/relaxcal-hea", detail)

    def test_download_step_main_logs_uses_main_logs_artifact(self):
        fg = self._make_flow_generator()

        with tempfile.TemporaryDirectory(prefix="apex-flow-") as td:
            fg.download_path = td
            step = {
                "outputs": {
                    "artifacts": {
                        "main-logs": "remote-artifact",
                    }
                }
            }
            expected_path = os.path.join(td, "main-logs", "relaxcal-hea")

            with mock.patch(
                    "apex.flow.download_artifact",
                    return_value=[os.path.join(expected_path, "main.log")],
            ) as mocked_download:
                log_path, log_error = fg._download_step_main_logs(step, "relaxcal-hea")

            self.assertIsNone(log_error)
            self.assertEqual(log_path, [os.path.join(expected_path, "main.log")])
            mocked_download.assert_called_once_with(
                artifact="remote-artifact",
                path=expected_path,
            )

    def test_download_step_main_logs_falls_back_to_child_relaxmake(self):
        fg = self._make_flow_generator()

        with tempfile.TemporaryDirectory(prefix="apex-flow-") as td:
            fg.download_path = td
            parent_step = {
                "id": "b2-joint-lctrb-1445201498",
                "outputs": {"artifacts": {}},
            }
            relaxmake_step = {
                "id": "relaxmake-node",
                "phase": "Failed",
                "displayName": "Relaxmake",
                "outputs": {
                    "artifacts": {
                        "main-logs": "relaxmake-main-logs",
                    }
                },
            }
            step_info = mock.Mock()
            step_info.get_step.return_value = [relaxmake_step]
            expected_path = os.path.join(
                td,
                "main-logs",
                "relaxcal-b2",
                "Relaxmake",
            )

            with mock.patch(
                    "apex.flow.download_artifact",
                    return_value=[os.path.join(expected_path, "main.log")],
            ) as mocked_download:
                log_path, log_error = fg._download_step_main_logs(
                    parent_step,
                    "relaxcal-b2",
                    step_info=step_info,
                )

            self.assertIsNone(log_error)
            self.assertEqual(log_path, [os.path.join(expected_path, "main.log")])
            step_info.get_step.assert_any_call(
                parent_id="b2-joint-lctrb-1445201498",
                sort_by_generation=True,
            )
            mocked_download.assert_called_once_with(
                artifact="relaxmake-main-logs",
                path=expected_path,
            )

    def test_download_step_main_logs_follows_failed_child_message(self):
        fg = self._make_flow_generator()

        with tempfile.TemporaryDirectory(prefix="apex-flow-") as td:
            fg.download_path = td
            parent_step = {
                "id": "bcc-joint-r2zqs-2387467399",
                "message": "child 'bcc-joint-r2zqs-1200280961' failed",
                "outboundNodes": ["bcc-joint-r2zqs-1200280961"],
                "outputs": {"artifacts": {}},
            }
            failed_child = {
                "id": "bcc-joint-r2zqs-1200280961",
                "phase": "Failed",
                "displayName": "property-flow",
                "outputs": {"artifacts": {}},
            }
            propspost_step = {
                "id": "propspost-node",
                "phase": "Failed",
                "displayName": "Propspost",
                "outputs": {
                    "artifacts": {
                        "main-logs": "propspost-main-logs",
                    }
                },
            }

            def fake_get_step(**kwargs):
                if kwargs.get("parent_id") == "bcc-joint-r2zqs-2387467399":
                    return []
                if kwargs.get("id") == "bcc-joint-r2zqs-1200280961":
                    return [failed_child]
                if kwargs.get("parent_id") == "bcc-joint-r2zqs-1200280961":
                    return [propspost_step]
                return []

            step_info = mock.Mock()
            step_info.get_step.side_effect = fake_get_step
            expected_path = os.path.join(
                td,
                "main-logs",
                "propertycal-bcc",
                "Propspost",
            )

            with mock.patch(
                    "apex.flow.download_artifact",
                    return_value=[os.path.join(expected_path, "main.log")],
            ) as mocked_download:
                log_path, log_error = fg._download_step_main_logs(
                    parent_step,
                    "propertycal-bcc",
                    step_info=step_info,
                )

            self.assertIsNone(log_error)
            self.assertEqual(log_path, [os.path.join(expected_path, "main.log")])
            mocked_download.assert_called_once_with(
                artifact="propspost-main-logs",
                path=expected_path,
            )

    def test_download_step_diagnostic_artifacts_gets_child_backward_dir(self):
        fg = self._make_flow_generator()

        with tempfile.TemporaryDirectory(prefix="apex-flow-") as td:
            fg.download_path = td
            parent_step = {
                "id": "property-wrapper",
                "outboundNodes": ["run-node"],
                "outputs": {"artifacts": {}},
            }
            run_step = {
                "id": "run-node",
                "phase": "Succeeded",
                "displayName": "PropsLAMMPS-Cal",
                "outputs": {
                    "artifacts": {
                        "backward_dir": "run-backward-artifact",
                    }
                },
            }
            step_info = mock.Mock()
            step_info.get_step.side_effect = lambda **kwargs: (
                [run_step] if kwargs.get("id") == "run-node" else []
            )
            expected_path = os.path.join(
                td,
                "failed-artifacts",
                "propertycal-bcc",
                "PropsLAMMPS-Cal",
                "backward_dir",
            )

            with mock.patch(
                    "apex.flow.download_artifact",
                    return_value=[os.path.join(expected_path, "task.000077")],
            ) as mocked_download:
                artifacts = fg._download_step_diagnostic_artifacts(
                    parent_step,
                    "propertycal-bcc",
                    step_info=step_info,
                )

            self.assertEqual(artifacts, [[os.path.join(expected_path, "task.000077")]])
            mocked_download.assert_called_once_with(
                artifact="run-backward-artifact",
                path=expected_path,
            )

    def test_terminate_workflow_after_relax_failure(self):
        fg = self._make_flow_generator()
        fg.workflow = mock.Mock()

        message = fg._terminate_workflow_after_relax_failure()

        fg.workflow.terminate.assert_called_once()
        self.assertIn("workflow terminated", message)


if __name__ == "__main__":
    unittest.main()

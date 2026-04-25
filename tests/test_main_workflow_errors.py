import unittest

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


class WorkflowQueryErrorTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

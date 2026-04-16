import os
import tempfile
import types
import unittest

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


if __name__ == "__main__":
    unittest.main()

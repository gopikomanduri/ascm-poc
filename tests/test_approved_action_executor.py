import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.mentor.approved_action_executor import ApprovedActionExecutor
from orchestrator.mentor.approval_security import sign_approval


class ApprovedActionExecutorTests(unittest.TestCase):
    def _workspace(self, root, status="approved", action="inspect_git_status"):
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        history = root / ".ascm_history"
        history.mkdir(exist_ok=True)
        proposal = {
            "proposal_id": "test-proposal",
            "action_type": action,
            "status": status,
            "execution_status": None,
            "decision_by": "founder",
            "decided_at": "2026-10-15T00:00:00+00:00",
        }
        if status == "approved":
            proposal["approval_signature"] = sign_approval(root, proposal)
        (history / "action_proposals.json").write_text(json.dumps([proposal]))
        return history

    def test_execution_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._workspace(root)
            executor = ApprovedActionExecutor(root, audit_logger=mock.Mock())
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(PermissionError):
                    executor.execute("test-proposal")

    def test_unapproved_proposal_cannot_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._workspace(root, status="pending_approval")
            executor = ApprovedActionExecutor(root, audit_logger=mock.Mock())
            with mock.patch.dict(os.environ, {"ASCM_ENABLE_APPROVED_EXECUTION": "1"}):
                with self.assertRaises(PermissionError):
                    executor.execute("test-proposal")

    def test_only_allowlisted_actions_can_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._workspace(root, action="run_arbitrary_command")
            executor = ApprovedActionExecutor(root, audit_logger=mock.Mock())
            with mock.patch.dict(os.environ, {"ASCM_ENABLE_APPROVED_EXECUTION": "1"}):
                with self.assertRaises(PermissionError):
                    executor.execute("test-proposal")

    def test_approved_git_status_executes_without_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._workspace(root)
            audit = mock.Mock()
            executor = ApprovedActionExecutor(root, audit_logger=audit)
            with mock.patch.dict(os.environ, {"ASCM_ENABLE_APPROVED_EXECUTION": "1"}):
                result = executor.execute("test-proposal")
            self.assertTrue(result["passed"])
            proposal = json.loads((root / ".ascm_history" / "action_proposals.json").read_text())[0]
            self.assertEqual(proposal["execution_status"], "succeeded")
            self.assertTrue(any(call.args[0] == "APPROVED_ACTION_FINISHED" for call in audit.log_event.call_args_list))


    def test_tampered_approval_cannot_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = self._workspace(root)
            path = history / "action_proposals.json"
            proposals = json.loads(path.read_text())
            proposals[0]["action_type"] = "run_pytest"
            path.write_text(json.dumps(proposals))
            executor = ApprovedActionExecutor(root, audit_logger=mock.Mock())
            with mock.patch.dict(os.environ, {"ASCM_ENABLE_APPROVED_EXECUTION": "1"}):
                with self.assertRaisesRegex(PermissionError, "not bound"):
                    executor.execute("test-proposal")


if __name__ == "__main__":
    unittest.main()

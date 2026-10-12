import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.mentor.milestone_detector import MilestoneDetector


class MilestoneDetectorTests(unittest.TestCase):
    def _git(self, root, *args):
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True,
            capture_output=True, text=True,
        )

    def test_detects_new_checkpoint_without_storing_commit_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git(root, "init", "-q")
            self._git(root, "config", "user.email", "test@example.invalid")
            self._git(root, "config", "user.name", "ASCM test")
            (root / "sample.py").write_text("value = 1\n")
            self._git(root, "add", "sample.py")
            self._git(root, "commit", "-m", "PRIVATE COMMIT MESSAGE")
            audit = mock.Mock()
            detector = MilestoneDetector(root, audit_logger=audit)
            checkpoint = detector.poll()
            self.assertIsNotNone(checkpoint)
            self.assertEqual(checkpoint["event_type"], "git_checkpoint")
            self.assertNotIn("PRIVATE COMMIT MESSAGE", str(checkpoint))
            self.assertEqual(checkpoint["status"], "checkpoint_needs_test_verification")
            self.assertIsNone(detector.poll())
            audit.log_event.assert_called_once()

    def test_passed_test_event_is_only_evidence_not_a_completion_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git(root, "init", "-q")
            self._git(root, "config", "user.email", "test@example.invalid")
            self._git(root, "config", "user.name", "ASCM test")
            (root / "sample.py").write_text("value = 2\n")
            self._git(root, "add", "sample.py")
            self._git(root, "commit", "-m", "checkpoint")
            (root / ".ascm_history").mkdir()
            (root / ".ascm_history" / "activity_events.jsonl").write_text(
                '{"event_type":"test_passed","timestamp":"2099-01-01T00:00:00+00:00"}\n'
            )
            detector = MilestoneDetector(root, audit_logger=mock.Mock())
            checkpoint = detector.poll()
            self.assertEqual(checkpoint["status"], "checkpoint_with_passing_test_evidence")
            self.assertTrue(checkpoint["test_evidence"]["passed"])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.privacy_cli import delete_history, history_path, status


class PrivacyControlsTests(unittest.TestCase):
    def test_status_reports_local_history_and_default_app_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".ascm_history").mkdir()
            result = status(tmp)
            self.assertTrue(result["history_exists"])
            self.assertFalse(result["foreground_app_names_enabled"])

    def test_history_delete_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".ascm_history").mkdir()
            with self.assertRaises(ValueError):
                delete_history(tmp)
            self.assertTrue(history_path(tmp).exists())

    def test_history_delete_only_removes_workspace_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "keep.txt"
            marker.write_text("keep")
            (root / ".ascm_history").mkdir()
            (root / ".ascm_history" / "event.jsonl").write_text("{}")
            result = delete_history(root, confirmed=True)
            self.assertTrue(result["deleted"])
            self.assertFalse((root / ".ascm_history").exists())
            self.assertTrue(marker.exists())

    def test_history_delete_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            target = Path(outside, "important.txt")
            target.write_text("keep")
            link = Path(tmp, ".ascm_history")
            link.symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaises(ValueError):
                delete_history(tmp, confirmed=True)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()

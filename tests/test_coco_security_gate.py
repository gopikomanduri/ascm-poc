import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.security.coco_gate import run_coco, scan_paths


class CocoSecurityGateTests(unittest.TestCase):
    def test_detects_shell_true_and_never_executes_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "unsafe.py"
            source.write_text("import subprocess\nsubprocess.run(user_input, shell=True)\n")
            findings = scan_paths([Path("unsafe.py")], root)
            self.assertIn("subprocess_shell_true", [item["rule"] for item in findings])

    def test_detects_private_key_marker_without_returning_secret_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.txt").write_text("-----BEGIN RSA PRIVATE KEY-----\nREDACTED\n")
            findings = scan_paths([Path("sample.txt")], root)
            self.assertEqual(findings[0]["rule"], "private_key")
            self.assertNotIn("REDACTED", str(findings))

    def test_rejects_paths_outside_repository(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            findings = scan_paths([Path(outside) / "file.py"], Path(tmp))
            self.assertIn("path_escape", [item["rule"] for item in findings])

    def test_reports_coco_as_unavailable_when_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            result = run_coco([Path("example.py")], Path.cwd())
            self.assertEqual(result["status"], "not_configured")
            self.assertIsNone(result["passed"])

    def test_coco_command_configuration_must_be_json_array(self):
        with patch.dict(os.environ, {"ASCM_COCO_AGENT_CMD": "coco security --json"}):
            result = run_coco([], Path.cwd())
            self.assertEqual(result["status"], "configuration_error")
            self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()

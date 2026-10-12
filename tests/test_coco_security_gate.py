import json
import os
import sys
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
            marker = "-" * 5 + "BEGIN RSA PRIVATE KEY" + "-" * 5
            (root / "sample.txt").write_text(marker + "\nREDACTED\n")
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


    def test_ci_falls_back_to_pinned_npx_cli_when_global_coco_is_missing(self):
        from unittest.mock import Mock

        completed = Mock(returncode=1, stdout="", stderr="provider credentials missing")
        with patch.dict(os.environ, {"CI": "true"}, clear=True), \
             patch("orchestrator.security.coco_gate.shutil.which", side_effect=lambda name: name == "npx"), \
             patch("orchestrator.security.coco_gate.subprocess.run", return_value=completed) as run:
            result = run_coco([Path("example.py")], Path.cwd())
        self.assertEqual(result["status"], "failed")
        self.assertTrue(run.call_args.args[0][:3] == ["npx", "--yes", "git-coco@0.91.0"])

    def test_coco_structured_review_blocks_high_severity_finding(self):
        script = (
            "import json,sys; json.load(sys.stdin); "
            "print(json.dumps({'version':1,'ok':True,'operation':'review','status':'completed',"
            "'data':{'findings':[{'severity':8,'category':'security','title':'Unsafe flow',"
            "'summary':'Potential injection','filePath':'src/example.py'}]},'warnings':[]}))"
        )
        with patch.dict(os.environ, {"ASCM_COCO_AGENT_CMD": json.dumps([sys.executable, "-c", script])}):
            result = run_coco([], Path.cwd())
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["passed"])
        self.assertEqual(result["blocking_finding_count"], 1)

    def test_coco_command_configuration_must_be_json_array(self):
        with patch.dict(os.environ, {"ASCM_COCO_AGENT_CMD": "coco security --json"}):
            result = run_coco([], Path.cwd())
            self.assertEqual(result["status"], "configuration_error")
            self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()

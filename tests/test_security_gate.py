import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.security.security_gate import run_model_review, scan_paths


class SecurityGateTests(unittest.TestCase):
    def test_detects_shell_true_without_executing_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unsafe.py").write_text("import subprocess\nsubprocess.run(user_input, shell=True)\n")
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

    def test_requires_gemini_key_for_model_review(self):
        with patch.dict(os.environ, {}, clear=True):
            result = run_model_review([Path("example.py")], Path.cwd())
            self.assertEqual(result["status"], "not_configured")
            self.assertFalse(result["passed"])

    def test_structured_review_blocks_high_severity_finding(self):
        script = (
            "import json,sys; json.load(sys.stdin); "
            "print(json.dumps({'ok':True,'operation':'review',"
            "'data':{'findings':[{'severity':8,'category':'security','title':'Unsafe flow',"
            "'summary':'Potential injection','filePath':'src/example.py'}]}}))"
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), patch(
            "orchestrator.security.security_gate.subprocess.run",
            return_value=type("Result", (), {"returncode": 0, "stdout": json.dumps({
                "ok": True, "operation": "review", "data": {"findings": [{
                    "severity": 8, "category": "security", "title": "Unsafe flow",
                    "summary": "Potential injection", "filePath": "src/example.py"
                }]}
            }), "stderr": ""})()
        ) as mock_run:
            result = run_model_review([], Path.cwd(), base_ref="HEAD^1")
        review_request = json.loads(mock_run.call_args.kwargs["input"])
        self.assertEqual(review_request["source"]["scope"]["base"], "HEAD^1")
        self.assertEqual(mock_run.call_args.kwargs["timeout"], 300)
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["passed"])
        self.assertEqual(result["blocking_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()

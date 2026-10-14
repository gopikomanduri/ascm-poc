import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.security import security_gate


class SecurityReviewProviderWarningTests(unittest.TestCase):
    def test_provider_warnings_are_redacted_and_preserved(self):
        response = {
            "ok": True,
            "operation": "review",
            "data": {"findings": []},
            "warnings": ["provider warning with sensitive context"],
        }
        completed = mock.Mock(returncode=0, stdout=json.dumps(response), stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                "os.environ", {"GEMINI_API_KEY": 'test-key'}, clear=False
            ), mock.patch.object(security_gate.subprocess, "run", return_value=completed), mock.patch(
                "orchestrator.security.pii_scrubber.PIIScrubber.scrub",
                side_effect=lambda value: "redacted:" + value,
            ):
                result = security_gate.run_model_review([], Path(tmp))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["provider_warnings"],
            ["redacted:provider warning with sensitive context"],
        )

    def test_non_list_provider_warnings_are_ignored(self):
        response = {
            "ok": True,
            "operation": "review",
            "data": {"findings": []},
            "warnings": "not a list",
        }
        completed = mock.Mock(returncode=0, stdout=json.dumps(response), stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                "os.environ", {"GEMINI_API_KEY": 'test-key'}, clear=False
            ), mock.patch.object(security_gate.subprocess, "run", return_value=completed):
                result = security_gate.run_model_review([], Path(tmp))

        self.assertEqual(result["provider_warnings"], [])


if __name__ == "__main__":
    unittest.main()

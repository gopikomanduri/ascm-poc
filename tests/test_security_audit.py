import json
import os
import tempfile
import unittest
from pathlib import Path

from orchestrator.security.pii_scrubber import PIIScrubber
from orchestrator.security.audit_logger import AuditLogger


class PIIScrubberTests(unittest.TestCase):
    def test_scrub_api_keys_and_secrets(self):
        sample = (
            "Here is the OpenAI key: sk-abc123456789012345678901234567890 and "
            "Anthropic key: sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456789 and "
            "Google key: AIzaSyA1234567890123456789012345678901 and "
            "GitHub token: ghp_1234567890abcdefghijklmnopqrstuvwxyz and "
            "AWS Key: AKIAIOSFODNN7EXAMPLE and "
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0 and "
            "password = 'SuperSecretPassword123!' and "
            "api_key: 'my-raw-api-key-999'"
        )
        scrubbed = PIIScrubber.scrub(sample)
        self.assertNotIn("sk-abc123456789012345678901234567890", scrubbed)
        self.assertNotIn("sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456789", scrubbed)
        self.assertNotIn("AIzaSyA1234567890123456789012345678901", scrubbed)
        self.assertNotIn("ghp_1234567890abcdefghijklmnopqrstuvwxyz", scrubbed)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", scrubbed)
        self.assertNotIn("SuperSecretPassword123!", scrubbed)

        self.assertIn("[REDACTED_OPENAI_KEY]", scrubbed)
        self.assertIn("[REDACTED_ANTHROPIC_KEY]", scrubbed)
        self.assertIn("[REDACTED_GOOGLE_KEY]", scrubbed)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", scrubbed)
        self.assertIn("[REDACTED_AWS_KEY]", scrubbed)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

    def test_scrub_pii(self):
        sample = (
            "Contact user at john.doe@enterprise.com or call 555-123-4567. "
            "SSN is 123-45-6789 and card is 4111 2222 3333 4444. "
            "Server IP: 198.51.100.42 but keep 127.0.0.1 safe."
        )
        scrubbed = PIIScrubber.scrub(sample)
        self.assertNotIn("john.doe@enterprise.com", scrubbed)
        self.assertNotIn("555-123-4567", scrubbed)
        self.assertNotIn("123-45-6789", scrubbed)
        self.assertNotIn("4111 2222 3333 4444", scrubbed)
        self.assertNotIn("198.51.100.42", scrubbed)

        self.assertIn("[REDACTED_EMAIL]", scrubbed)
        self.assertIn("[REDACTED_PHONE]", scrubbed)
        self.assertIn("[REDACTED_SSN]", scrubbed)
        self.assertIn("[REDACTED_CREDIT_CARD]", scrubbed)
        self.assertIn("[REDACTED_IP]", scrubbed)
        self.assertIn("127.0.0.1", scrubbed)  # Localhost preserved

    def test_audit_findings_metrics(self):
        sample = "Email: a@b.com, b@c.com, and key sk-123456789012345678901234"
        findings = PIIScrubber.audit_findings(sample)
        self.assertEqual(findings.get("EMAIL"), 2)
        self.assertEqual(findings.get("OPENAI_KEY"), 1)


class AuditLoggerTests(unittest.TestCase):
    def test_audit_logger_creates_text_and_jsonl_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = AuditLogger(log_dir=tmp_dir, run_id="test-run-101")
            self.assertTrue(logger.text_log_file.exists())

            # Log events
            logger.log_phase("Phase 1: Ingesting Repository Contracts")
            logger.log_step("DiscoveryAgent", "CLASSIFY", {"repo": "internal/api", "role": "provider"})
            logger.log_governance("Milestone 1", "CONFIRMED", feedback="")
            logger.log_verification("ascm-poc", "go", passed=True, sandboxed=True)

            self.assertTrue(logger.text_log_file.exists())
            self.assertTrue(logger.jsonl_log_file.exists())

            # Read text log
            text_content = logger.text_log_file.read_text(encoding="utf-8")
            self.assertIn("Phase 1: Ingesting Repository Contracts", text_content)
            self.assertIn("DiscoveryAgent", text_content)
            self.assertIn("test-run-101", text_content)

            # Read and parse JSONL log
            lines = [json.loads(line) for line in logger.jsonl_log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(lines), 4)
            self.assertEqual(lines[0]["event_type"], "PHASE_TRANSITION")
            self.assertEqual(lines[1]["event_type"], "AGENT_STEP")
            self.assertEqual(lines[2]["event_type"], "GOVERNANCE_DECISION")
            self.assertEqual(lines[3]["event_type"], "VERIFICATION")
            self.assertTrue(lines[3]["details"]["sandboxed"])

    def test_audit_logger_redacts_pii_in_logs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = AuditLogger(log_dir=tmp_dir, run_id="test-pii-redact")
            sensitive_payload = {
                "user": "alice@company.com",
                "auth_header": "Bearer secret-token-12345678901234567890",
                "api_key": "sk-123456789012345678901234567890",
            }
            logger.log_step("TestAgent", "PROCESS", sensitive_payload)

            # Check text log
            text_log = logger.text_log_file.read_text(encoding="utf-8")
            self.assertNotIn("alice@company.com", text_log)
            self.assertNotIn("sk-123456789012345678901234567890", text_log)
            self.assertIn("[REDACTED_EMAIL]", text_log)
            self.assertIn("[REDACTED_OPENAI_KEY]", text_log)

            # Check JSONL log
            jsonl_content = logger.jsonl_log_file.read_text(encoding="utf-8")
            record = json.loads(jsonl_content.strip())
            self.assertNotIn("alice@company.com", json.dumps(record))
            self.assertIn("pii_redacted", record["metadata"])
            self.assertGreater(record["metadata"]["pii_redacted"]["EMAIL"], 0)

    def test_log_llm_interaction(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger = AuditLogger(log_dir=tmp_dir, run_id="test-llm-call")
            prompt = "Please review code for john@acme.org and verify token Bearer xyz12345678901234567890"
            response = '{"approved": true}'
            logger.log_llm_interaction(
                agent="CodeReviewAgent",
                provider="GeminiProvider",
                model="gemini-2.5-flash",
                prompt=prompt,
                response=response,
                latency_ms=234.56,
                json_mode=True,
            )

            jsonl_content = logger.jsonl_log_file.read_text(encoding="utf-8")
            record = json.loads(jsonl_content.strip())
            self.assertEqual(record["event_type"], "LLM_CALL")
            self.assertEqual(record["agent"], "CodeReviewAgent")
            self.assertEqual(record["details"]["model"], "gemini-2.5-flash")
            self.assertEqual(record["details"]["latency_ms"], 234.56)
            self.assertNotIn("john@acme.org", record["details"]["prompt_preview"])
            self.assertIn("[REDACTED_EMAIL]", record["details"]["prompt_preview"])


if __name__ == "__main__":
    unittest.main()

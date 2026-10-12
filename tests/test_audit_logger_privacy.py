import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.security.audit_logger import AuditLogger


class AuditLoggerPrivacyTests(unittest.TestCase):
    def test_metadata_is_scrubbed_before_structured_and_text_logging(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = AuditLogger(log_dir=tmp)
            record = logger.log_event(
                "TEST_EVENT",
                agent="TEST",
                action="CHECK",
                details={"result": "ok"},
                metadata={"contact": "founder@example.com", "token": "sk-" + "a" * 32},
            )
            serialized = json.dumps(record)
            self.assertNotIn("founder@example.com", serialized)
            self.assertNotIn("sk-" + "a" * 32, serialized)
            disk_record = json.loads(Path(tmp, "ascm_audit.jsonl").read_text().splitlines()[-1])
            self.assertNotIn("founder@example.com", json.dumps(disk_record))
            self.assertNotIn("sk-" + "a" * 32, json.dumps(disk_record))

    def test_pii_findings_record_categories_not_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = AuditLogger(log_dir=tmp)
            record = logger.log_event(
                "TEST_EVENT",
                details={"contact": "founder@example.com"},
            )
            metadata = record["metadata"]
            self.assertIn("pii_redacted_categories", metadata)
            self.assertIn("EMAIL", metadata["pii_redacted_categories"])
            self.assertNotIn("founder@example.com", json.dumps(metadata))


if __name__ == "__main__":
    unittest.main()

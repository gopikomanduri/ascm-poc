import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orchestrator.gtm.integrations.outcome_webhook import router


class OutcomeWebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.secret = "test-secret-that-is-longer-than-thirty-two-bytes"
        self.env = mock.patch.dict(os.environ, {
            "ASCM_WATCH_PATH": str(self.root),
            "ASCM_OUTCOME_WEBHOOK_SECRET": self.secret,
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def _post(self, payload, *, timestamp=None, signature_override=None):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        stamp = str(timestamp if timestamp is not None else int(time.time()))
        signature = hmac.new(
            self.secret.encode(), stamp.encode() + b"." + raw, hashlib.sha256
        ).hexdigest()
        if signature_override is not None:
            signature = signature_override
        return self.client.post(
            "/integrations/gtm/outcomes",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-ASCM-Timestamp": stamp,
                "X-ASCM-Signature": signature,
            },
        )

    def _payload(self):
        return {
            "source_event_id": "crm-event-001",
            "event_type": "customer_reply",
            "experiment_id": "pilot-001",
            "metrics": {
                "sentiment": "interested",
                "source_system": "crm",
                "feature_key": "invoice automation",
            },
        }

    def test_signed_event_is_recorded_without_raw_payload(self):
        response = self._post(self._payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "recorded")
        stored = (self.root / ".ascm_history" / "gtm_outcomes.json").read_text()
        self.assertNotIn("customer@example.com", stored)
        self.assertIn("crm-event-001", (self.root / ".ascm_history" / "webhook_source_event_ids.json").read_text())

    def test_duplicate_source_event_is_idempotently_ignored(self):
        self.assertEqual(self._post(self._payload()).json()["status"], "recorded")
        duplicate = self._post(self._payload())
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["status"], "duplicate_ignored")
        events = json.loads((self.root / ".ascm_history" / "gtm_outcomes.json").read_text())
        self.assertEqual(len(events), 1)

    def test_invalid_signature_and_stale_timestamp_are_rejected(self):
        self.assertEqual(self._post(self._payload(), signature_override="0" * 64).status_code, 401)
        self.assertEqual(self._post(self._payload(), timestamp=int(time.time()) - 600).status_code, 401)

    def test_signed_provider_native_event_is_mapped_without_persisting_raw_payload(self):
        history = self.root / ".ascm_history"
        history.mkdir(parents=True, exist_ok=True)
        (history / "gtm_provider_mappings.json").write_text(json.dumps({
            "sample_crm": {
                "source_event_id": "event.id",
                "event_type": {"path": "event.type", "values": {"reply": "customer_reply"}},
                "experiment_id": "event.experiment",
                "occurred_at": "event.created_at",
                "metrics": {
                    "sentiment": {"path": "event.sentiment", "values": {"interested": "interested"}},
                    "feature_key": "event.feature",
                    "channel": {"literal": "email"},
                },
            }
        }), encoding="utf-8")
        payload = {
            "provider": "sample_crm",
            "provider_payload": {
                "event": {
                    "id": "provider-event-1",
                    "type": "reply",
                    "experiment": "invoice-pilot",
                    "created_at": "2026-10-15T00:00:00Z",
                    "sentiment": "interested",
                    "feature": "invoice automation",
                    "email": "private@example.com",
                    "message": "private customer text",
                }
            },
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "recorded")
        saved = (history / "gtm_outcomes.json").read_text(encoding="utf-8")
        self.assertIn("invoice automation", saved)
        self.assertNotIn("private@example.com", saved)
        self.assertNotIn("private customer text", saved)
        self.assertIn('"source_system": "sample_crm"', saved)

    def test_provider_payload_requires_server_owned_mapping(self):
        response = self._post({
            "provider": "unconfigured_crm",
            "provider_payload": {"id": "evt-1", "type": "reply"},
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse((self.root / ".ascm_history" / "gtm_outcomes.json").exists())

    def test_unknown_fields_that_could_contain_customer_text_are_rejected(self):
        payload = self._payload()
        payload["metrics"]["customer_message"] = "private customer message"
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse((self.root / ".ascm_history" / "gtm_outcomes.json").exists())

    def test_invalid_normalized_metric_is_a_client_error_not_server_error(self):
        payload = self._payload()
        payload["metrics"]["sentiment"] = "customer wrote a long free-form message"
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse((self.root / ".ascm_history" / "gtm_outcomes.json").exists())


if __name__ == "__main__":
    unittest.main()

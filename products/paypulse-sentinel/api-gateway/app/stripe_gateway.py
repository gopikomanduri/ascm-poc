import hashlib
import hmac
import time
from typing import Dict, Any, Optional


class StripeGateway:
    """
    Handles multi-tenant Stripe webhook verification, idempotency checks,
    and event routing with zero plaintext card storage.
    """

    def __init__(self, webhook_secret: str = "whsec_test_secret_key_12345"):
        self.webhook_secret = webhook_secret
        self.processed_events: Dict[str, Dict[str, Any]] = {}

    def compute_signature(self, payload: str, timestamp: int) -> str:
        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        return hmac.new(self.webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    def verify_webhook(self, payload: str, sig_header: str, tolerance_sec: int = 300) -> bool:
        if not sig_header or "t=" not in sig_header or "v1=" not in sig_header:
            return False

        parts = sig_header.split(",")
        t_val = 0
        v1_val = ""
        for p in parts:
            p = p.strip()
            if p.startswith("t="):
                try:
                    t_val = int(p.split("=")[1])
                except ValueError:
                    return False
            elif p.startswith("v1="):
                v1_val = p.split("=")[1]

        if not t_val or not v1_val:
            return False

        # Tolerance check
        if abs(time.time() - t_val) > tolerance_sec:
            return False

        expected_sig = self.compute_signature(payload, t_val)
        return hmac.compare_digest(expected_sig, v1_val)

    def process_event(self, event_id: str, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # Idempotency check to prevent duplicate charging
        if event_id in self.processed_events:
            return {
                "status": "duplicate",
                "message": f"Event {event_id} already processed. Idempotency preserved.",
                "record": self.processed_events[event_id],
            }

        record = {
            "event_id": event_id,
            "event_type": event_type,
            "customer_id": data.get("customer", "cus_default"),
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "usd"),
            "status": "succeeded" if "succeeded" in event_type else "received",
            "processed_at": time.time(),
        }
        self.processed_events[event_id] = record

        return {
            "status": "success",
            "message": f"Successfully processed {event_type} for event {event_id}.",
            "record": record,
        }

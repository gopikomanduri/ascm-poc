import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Any

from app.stripe_gateway import StripeGateway
from app.token_escrow import TokenEscrowManager

STARTED_AT = time.time()
STRIPE_GATEWAY = StripeGateway(webhook_secret=os.environ.get("PAYPULSE_WEBHOOK_SECRET", "whsec_test_secret_key_12345"))
TOKEN_ESCROW = TokenEscrowManager()


class PayPulseHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Stripe-Signature")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Stripe-Signature")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/v1/metrics":
            tenant_id = "tenant_demo_acme"
            self._send_json({
                "status": "healthy",
                "service": "PayPulse Sentinel API Gateway",
                "version": "1.0.0",
                "telemetry": {
                    "total_webhooks_processed": len(STRIPE_GATEWAY.processed_events),
                    "active_tenant_balance": TOKEN_ESCROW.get_balance(tenant_id),
                    "uptime_seconds": int(time.time() - STARTED_AT),
                    # Latency is not measured by this reference app, so none is reported.
                }
            })
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        if self.path == "/api/v1/stripe/webhook":
            sig_header = self.headers.get("Stripe-Signature", "")
            # The signature is mandatory: a missing header must not skip verification.
            if not sig_header or not STRIPE_GATEWAY.verify_webhook(body, sig_header):
                self._send_json({"status": "error", "message": "Invalid Stripe HMAC signature"}, status=400)
                return

            event_id = payload.get("id") or f"evt_{int(time.time()*1000)}"
            event_type = payload.get("type", "checkout.session.completed")
            data = payload.get("data", payload)

            result = STRIPE_GATEWAY.process_event(event_id, event_type, data)
            
            # If payment succeeded, automatically credit tokens in escrow
            amount = data.get("amount", 2900) if isinstance(data, dict) else None
            is_valid_amount = isinstance(amount, (int, float)) and not isinstance(amount, bool) and 0 < amount <= 10_000_000
            if result.get("status") != "duplicate" and is_valid_amount and ("succeeded" in event_type or "completed" in event_type):
                tokens_credited = int(amount / 100 * 10000)
                TOKEN_ESCROW.credit_tokens("tenant_demo_acme", tokens_credited)
                result["tokens_credited"] = tokens_credited

            self._send_json(result)

        elif self.path == "/api/v1/tokens/escrow":
            tenant_id = payload.get("tenant_id", "tenant_demo_acme")
            needed = payload.get("tokens_needed", 500)
            if isinstance(needed, bool) or not isinstance(needed, int) or needed <= 0:
                self._send_json({"error": "tokens_needed must be a positive integer"}, status=400)
                return
            res = TOKEN_ESCROW.check_and_consume_tokens(tenant_id, needed)
            status_code = 200 if res["allowed"] else 429
            self._send_json(res, status=status_code)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)


def run_server(port: int = 8000):
    # Loopback by default; set PAYPULSE_HOST=0.0.0.0 deliberately (and put TLS + auth in front) to expose it.
    server = HTTPServer((os.environ.get("PAYPULSE_HOST", "127.0.0.1"), port), PayPulseHTTPHandler)
    print(f"[+] PayPulse Sentinel Gateway running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()

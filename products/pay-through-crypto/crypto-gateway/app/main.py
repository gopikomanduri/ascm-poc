"""
Production Crypto Payment Gateway HTTP Service.
Zero external dependencies, built with standard library http.server.
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

from app.crypto_verifier import CryptoPaymentVerifier
from app.settlement_engine import CryptoSettlementEngine


VERIFIER = CryptoPaymentVerifier()
SETTLEMENT = CryptoSettlementEngine()
START_TIME = time.time()
REQUEST_COUNT = 0


class CryptoGatewayHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Idempotency-Key, X-Api-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})

    def do_GET(self):
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        if self.path in ("/healthz", "/api/v1/health"):
            self._send_json(200, {
                "status": "HEALTHY",
                "service": "pay-through-crypto-gateway",
                "uptime_seconds": round(time.time() - START_TIME, 2),
            })
        elif self.path in ("/metrics", "/api/v1/crypto/metrics"):
            self._send_json(200, {
                "service": "pay-through-crypto-gateway",
                "total_requests": REQUEST_COUNT,
                "uptime_seconds": round(time.time() - START_TIME, 2),
                "settled_tx_count": len(VERIFIER._settled_tx_hashes),
                "active_invoices_count": len(SETTLEMENT._invoices),
                "status": "OPERATIONAL",
            })
        else:
            self._send_json(404, {"error": "Endpoint not found", "path": self.path})

    def do_POST(self):
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        if self.path == "/api/v1/crypto/invoice/create":
            amount_usd = float(payload.get("amount_usd", 10.0))
            currency = payload.get("currency", "USDT")
            try:
                inv = SETTLEMENT.create_invoice(amount_usd, currency, payload.get("metadata"))
                self._send_json(201, {"status": "ok", "invoice": inv})
            except ValueError as ex:
                self._send_json(400, {"error": str(ex)})

        elif self.path == "/api/v1/crypto/payment/verify":
            inv_id = payload.get("invoice_id", "")
            amount = int(payload.get("amount", 0))
            payer = payload.get("payer_address", "")
            nonce = payload.get("nonce", "")
            timestamp = int(payload.get("timestamp", 0))
            sig = payload.get("signature", "")
            tx_hash = payload.get("tx_hash", "")

            # Look up the invoice first so a bad request cannot burn a legitimate nonce / tx hash.
            invoice = SETTLEMENT.get_invoice(inv_id)
            if invoice is None:
                self._send_json(404, {"status": "REJECTED", "reason": f"unknown invoice '{inv_id}'"})
                return
            if invoice.get("status") == "SETTLED" or int(time.time()) > invoice.get("expires_at", 0):
                self._send_json(409, {"status": "REJECTED", "reason": "invoice already settled or expired"})
                return

            valid, msg = VERIFIER.verify_payment_submission(inv_id, amount, payer, nonce, timestamp, sig, tx_hash)
            if valid:
                try:
                    settled_inv = SETTLEMENT.mark_settled(inv_id, tx_hash)
                    self._send_json(200, {
                        "status": "SETTLED",
                        "message": msg,
                        # This reference gateway checks an HMAC-signed submission only. It does not query a
                        # blockchain, so it must not be used to release goods or funds in production.
                        "verification": "signature_only_not_on_chain",
                        "invoice": settled_inv,
                    })
                except (KeyError, ValueError) as ex:
                    self._send_json(409, {"status": "REJECTED", "reason": str(ex)})
            else:
                self._send_json(422, {"status": "REJECTED", "reason": msg})
        else:
            self._send_json(404, {"error": "Endpoint not found", "path": self.path})


def run_server(port: int = 8001):
    server = HTTPServer(("127.0.0.1", port), CryptoGatewayHandler)
    print(f"[*] Pay Through Crypto Gateway running at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    run_server()

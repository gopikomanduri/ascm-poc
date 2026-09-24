"""
Cryptographic Payment Signature Verifier & Double-Spend Protection.
Provides timing-safe signature checking, EVM address validation, and replay protection.
"""

import hashlib
import hmac
import re
import time
from typing import Dict, Optional, Tuple


class CryptoPaymentVerifier:
    def __init__(self, merchant_secret: str = "crypto-secret-key-32b-ascm", tolerance_sec: int = 300):
        self.merchant_secret = merchant_secret
        self.tolerance_sec = tolerance_sec
        self._settled_tx_hashes: Dict[str, float] = {}
        self._used_nonces: Dict[str, float] = {}

    @staticmethod
    def is_valid_evm_address(address: str) -> bool:
        """Validates if address conforms to standard 42-char hex EVM format (0x...)."""
        if not isinstance(address, str):
            return False
        return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address))

    def generate_payment_signature(self, invoice_id: str, amount_wei_or_cents: int, payer_address: str, nonce: str, timestamp: int) -> str:
        """Computes deterministic HMAC-SHA256 signature for cross-checking payload authenticity."""
        msg = f"{invoice_id}:{amount_wei_or_cents}:{payer_address.lower()}:{nonce}:{timestamp}".encode("utf-8")
        return hmac.new(self.merchant_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def verify_payment_submission(
        self,
        invoice_id: str,
        amount: int,
        payer_address: str,
        nonce: str,
        timestamp: int,
        signature: str,
        tx_hash: str,
    ) -> Tuple[bool, str]:
        # 1. Address syntax validation
        if not self.is_valid_evm_address(payer_address):
            return False, "INVALID_PAYER_ADDRESS: Must be a valid 42-char EVM hex address"

        # 2. Replay tolerance check
        now = int(time.time())
        if abs(now - timestamp) > self.tolerance_sec:
            return False, "TIMESTAMP_EXPIRED: Payment authorization outside 300s window"

        # 3. Nonce uniqueness check (prevents replay)
        if nonce in self._used_nonces:
            return False, "NONCE_REUSED: Potential replay attack detected"

        # 4. Double-spend prevention on tx_hash
        if tx_hash in self._settled_tx_hashes:
            return False, "DOUBLE_SPEND_REJECTED: Transaction hash has already been settled"

        # 5. Cryptographic signature check
        expected_sig = self.generate_payment_signature(invoice_id, amount, payer_address, nonce, timestamp)
        if not hmac.compare_digest(expected_sig, signature):
            return False, "SIGNATURE_MISMATCH: Unauthorized payment proof"

        # Commit state atomically
        self._used_nonces[nonce] = now
        self._settled_tx_hashes[tx_hash] = now
        return True, "PAYMENT_VERIFIED_SUCCESSFULLY"

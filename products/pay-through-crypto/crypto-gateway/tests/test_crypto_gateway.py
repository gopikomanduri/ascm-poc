"""
Unit tests for Pay Through Crypto Gateway.
"""

import sys
import time
import unittest
import uuid
from pathlib import Path

# Add project root to sys.path so app is discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.crypto_verifier import CryptoPaymentVerifier
from app.settlement_engine import CryptoSettlementEngine


class CryptoGatewayUnitTests(unittest.TestCase):
    def setUp(self):
        self.verifier = CryptoPaymentVerifier(tolerance_sec=300)
        self.settlement = CryptoSettlementEngine()

    def test_evm_address_validation(self):
        valid = "0x89205A3A3b2A69De6Dbf7f01ED13B2108B2c43e7"
        invalid_short = "0x89205A3A3b2A69De6D"
        invalid_prefix = "89205A3A3b2A69De6Dbf7f01ED13B2108B2c43e7"
        self.assertTrue(CryptoPaymentVerifier.is_valid_evm_address(valid))
        self.assertFalse(CryptoPaymentVerifier.is_valid_evm_address(invalid_short))
        self.assertFalse(CryptoPaymentVerifier.is_valid_evm_address(invalid_prefix))

    def test_valid_crypto_payment_verification(self):
        payer = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        invoice_id = "inv_test_99"
        amount = 1000
        nonce = uuid.uuid4().hex
        timestamp = int(time.time())
        tx_hash = "0x" + uuid.uuid4().hex + uuid.uuid4().hex

        sig = self.verifier.generate_payment_signature(invoice_id, amount, payer, nonce, timestamp)
        valid, msg = self.verifier.verify_payment_submission(invoice_id, amount, payer, nonce, timestamp, sig, tx_hash)
        self.assertTrue(valid)
        self.assertEqual(msg, "PAYMENT_VERIFIED_SUCCESSFULLY")

    def test_double_spend_rejection(self):
        payer = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        invoice_id = "inv_test_double_spend"
        amount = 5000
        nonce = uuid.uuid4().hex
        timestamp = int(time.time())
        tx_hash = "0xduplicatehash0000000000000000000000000000000000000000000000000000000"

        sig = self.verifier.generate_payment_signature(invoice_id, amount, payer, nonce, timestamp)
        valid, msg = self.verifier.verify_payment_submission(invoice_id, amount, payer, nonce, timestamp, sig, tx_hash)
        self.assertTrue(valid)

        # Attempt to reuse the same tx_hash with a new nonce
        nonce2 = uuid.uuid4().hex
        sig2 = self.verifier.generate_payment_signature(invoice_id, amount, payer, nonce2, timestamp)
        valid2, msg2 = self.verifier.verify_payment_submission(invoice_id, amount, payer, nonce2, timestamp, sig2, tx_hash)
        self.assertFalse(valid2)
        self.assertIn("DOUBLE_SPEND_REJECTED", msg2)

    def test_invoice_creation_and_settlement_lifecycle(self):
        inv = self.settlement.create_invoice(amount_usd=50.0, currency="USDT")
        self.assertEqual(inv["status"], "PENDING")
        self.assertEqual(inv["crypto_amount"], 50.0)

        tx_hash = "0x" + uuid.uuid4().hex + uuid.uuid4().hex
        settled = self.settlement.mark_settled(inv["invoice_id"], tx_hash)
        self.assertEqual(settled["status"], "SETTLED")
        self.assertEqual(settled["confirmations"], 1)


if __name__ == "__main__":
    unittest.main()

import time
import unittest

from app.stripe_gateway import StripeGateway
from app.token_escrow import TokenEscrowManager


class PayPulseGatewayUnitTests(unittest.TestCase):
    def setUp(self):
        self.gateway = StripeGateway(webhook_secret="whsec_test_secret_key_12345")
        self.escrow = TokenEscrowManager(default_credit_balance=10000)

    def test_stripe_webhook_signature_verification(self):
        payload = '{"id": "evt_test_123", "type": "payment_intent.succeeded"}'
        t_now = int(time.time())
        sig = self.gateway.compute_signature(payload, t_now)
        header = f"t={t_now},v1={sig}"

        self.assertTrue(self.gateway.verify_webhook(payload, header))
        self.assertFalse(self.gateway.verify_webhook(payload, f"t={t_now},v1=invalid_sig"))

    def test_stripe_idempotency_prevents_duplicate_charge(self):
        event_id = "evt_idemp_999"
        res1 = self.gateway.process_event(event_id, "payment_intent.succeeded", {"amount": 5000})
        self.assertEqual(res1["status"], "success")

        # Second time with identical event_id
        res2 = self.gateway.process_event(event_id, "payment_intent.succeeded", {"amount": 5000})
        self.assertEqual(res2["status"], "duplicate")

    def test_token_escrow_deduction_and_rate_limiting(self):
        tenant = "tenant_test"
        # Consume within balance
        res = self.escrow.check_and_consume_tokens(tenant, 2000)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["remaining_balance"], 8000)

        # Insufficient funds
        fail_res = self.escrow.check_and_consume_tokens(tenant, 99999)
        self.assertFalse(fail_res["allowed"])
        self.assertEqual(fail_res["reason"], "INSUFFICIENT_CREDITS")

        # Credit tokens
        self.escrow.credit_tokens(tenant, 50000)
        self.assertEqual(self.escrow.get_balance(tenant), 58000)


if __name__ == "__main__":
    unittest.main()

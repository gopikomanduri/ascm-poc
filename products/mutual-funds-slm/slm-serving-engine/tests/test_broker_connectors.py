import unittest
from pathlib import Path
import sys

_curr = Path(__file__).resolve().parent
_app = _curr.parent / "app"
sys.path.insert(0, str(_app))

from broker_connectors import (
    ZerodhaKiteConnector,
    AngelOneSmartAPIConnector,
    RBIAccountAggregatorConnector,
    UnifiedBrokerGateway,
    resolve_scheme_id,
)


class TestBrokerConnectors(unittest.TestCase):
    def setUp(self):
        self.gateway = UnifiedBrokerGateway()

    def test_scheme_resolution(self):
        self.assertEqual(resolve_scheme_id("Parag Parikh Flexi Cap Fund"), "parag_parikh_flexi")
        self.assertEqual(resolve_scheme_id("HDFC TOP 100 INDEX"), "hdfc_top_100")
        self.assertEqual(resolve_scheme_id("SBI SMALL CAP"), "sbi_small_cap")
        self.assertEqual(resolve_scheme_id("Vanguard 500 Index"), "vanguard_500")

    def test_zerodha_fetch(self):
        z = ZerodhaKiteConnector()
        holdings = z.fetch_mf_holdings("demo_token", use_sandbox=True)
        self.assertGreaterEqual(len(holdings), 2)
        self.assertEqual(holdings[0]["broker"], "ZERODHA")
        self.assertIn("invested_amount", holdings[0])

    def test_angel_one_fetch(self):
        a = AngelOneSmartAPIConnector()
        holdings = a.fetch_holdings("demo_jwt", use_sandbox=True)
        self.assertGreaterEqual(len(holdings), 2)
        self.assertEqual(holdings[0]["broker"], "ANGEL_ONE")

    def test_rbi_account_aggregator_flow(self):
        aa = RBIAccountAggregatorConnector()
        consent = aa.create_consent_request("9876543210")
        self.assertEqual(consent["status"], "CONSENT_INITIATED")
        self.assertIn("consent_id", consent)

        holdings = aa.verify_otp_and_fetch_portfolio(consent["consent_id"], "123456")
        self.assertGreaterEqual(len(holdings), 3)
        # Should include Groww and CAMS holdings
        brokers = [h["broker"] for h in holdings]
        self.assertTrue(any("GROWW" in b for b in brokers))
        self.assertTrue(any("CAMS" in b for b in brokers))

    def test_unified_gateway_sync(self):
        connectors = self.gateway.get_supported_connectors()
        self.assertGreaterEqual(len(connectors), 5)
        
        # Sync via Zerodha
        res_z = self.gateway.connect_and_sync("ZERODHA", {"use_demo": True})
        self.assertEqual(res_z["status"], "SUCCESS")
        self.assertEqual(res_z["provider"], "ZERODHA")

        # Sync via RBI AA
        res_aa = self.gateway.connect_and_sync("RBI_ACCOUNT_AGGREGATOR", {"mobile": "9876543210", "otp": "123456"})
        self.assertEqual(res_aa["status"], "SUCCESS")
        self.assertGreater(res_aa["total_invested"], 0)


if __name__ == "__main__":
    unittest.main()

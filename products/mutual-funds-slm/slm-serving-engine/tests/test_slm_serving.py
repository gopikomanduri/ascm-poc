import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from app.slm_serving import MutualFundSLMServingEngine


class TestMutualFundSLMServing(unittest.TestCase):
    def setUp(self):
        self.engine = MutualFundSLMServingEngine()

    def test_format_fund_query_prompt(self):
        prompt = self.engine.format_fund_query_prompt(
            "What is the expense ratio of Nifty 50 Index Fund?",
            ["Expense ratio is 0.20%", "NAV is 245.50"]
        )
        self.assertIn("Nifty 50 Index Fund", prompt)
        self.assertIn("0.20%", prompt)

    def test_enforce_statutory_compliance(self):
        raw_output = "The fund has delivered 15% CAGR over 5 years."
        result = self.engine.enforce_statutory_compliance(raw_output)
        self.assertEqual(result["compliance_status"], "APPROVED")
        self.assertIn("Mutual Fund investments are subject to market risks", result["response"])

    def test_enforce_guardrail_on_guaranteed_return_claim(self):
        risky_output = "This scheme offers a guaranteed return of 18%."
        result = self.engine.enforce_statutory_compliance(risky_output)
        self.assertIn("Past performance is not indicative of future returns", result["response"])

    def test_analyze_portfolio(self):
        holdings = [
            {"fund_id": "parag_parikh_flexi", "invested_amount": 100000, "purchase_months_ago": 8},
            {"fund_id": "hdfc_top_100", "invested_amount": 120000, "purchase_months_ago": 16},
        ]
        res = self.engine.analyze_portfolio(holdings, "Test query on holdings")
        self.assertIn("portfolio_summary", res)
        self.assertEqual(res["portfolio_summary"]["holdings_count"], 2)
        self.assertGreater(res["portfolio_summary"]["current_value"], 220000.0)
        self.assertIn("response", res)
        self.assertIn("tools_executed", res)

    def test_analyze_portfolio_exit_load_detection(self):
        holdings = [
            {"fund_id": "parag_parikh_flexi", "invested_amount": 50000, "purchase_months_ago": 6},
            {"fund_id": "hdfc_top_100", "invested_amount": 50000, "purchase_months_ago": 14},
        ]
        res = self.engine.analyze_portfolio(holdings, "Check exit loads")
        enriched = res["holdings"]
        ppfc = [h for h in enriched if h["fund_id"] == "parag_parikh_flexi"][0]
        hdfc = [h for h in enriched if h["fund_id"] == "hdfc_top_100"][0]
        self.assertEqual(ppfc["exit_load_pct"], 2.0)
        self.assertEqual(hdfc["exit_load_pct"], 0.0)
        self.assertIn("STCG", ppfc["tax_category"])
        self.assertIn("LTCG", hdfc["tax_category"])


if __name__ == "__main__":
    unittest.main()

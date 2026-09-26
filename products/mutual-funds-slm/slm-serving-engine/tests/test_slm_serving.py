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


if __name__ == "__main__":
    unittest.main()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from app.fund_data import MutualFundMetricsCalculator


class TestMutualFundMetrics(unittest.TestCase):
    def setUp(self):
        self.calc = MutualFundMetricsCalculator(risk_free_rate=0.06)

    def test_cagr_calculation(self):
        # NAV doubles over 3 years
        cagr = self.calc.calculate_cagr(10.0, 20.0, 3.0)
        self.assertAlmostEqual(cagr, 0.2599, places=3)

    def test_sharpe_ratio_calculation(self):
        sharpe = self.calc.calculate_sharpe_ratio(fund_return=0.18, fund_std_dev=0.12)
        self.assertAlmostEqual(sharpe, 1.0, places=2)

    def test_alpha_and_beta_calculation(self):
        fund_returns = [0.10, 0.12, 0.15, 0.08, 0.14]
        bench_returns = [0.08, 0.10, 0.12, 0.07, 0.11]
        beta = self.calc.calculate_beta(fund_returns, bench_returns)
        self.assertGreater(beta, 0)
        alpha = self.calc.calculate_alpha(0.15, 0.10, beta)
        self.assertIsInstance(alpha, float)


if __name__ == "__main__":
    unittest.main()

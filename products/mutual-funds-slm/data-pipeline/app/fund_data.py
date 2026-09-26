"""
Mutual Fund Data Pipeline: NAV Calculations & Portfolio Metrics.
"""

from typing import Dict, List, Any, Optional
import math


class MutualFundMetricsCalculator:
    """
    Computes key mutual fund investment metrics: CAGR, Sharpe Ratio, Alpha, Beta.
    """

    def __init__(self, risk_free_rate: float = 0.065):
        self.risk_free_rate = risk_free_rate

    def calculate_cagr(self, initial_nav: float, final_nav: float, years: float) -> float:
        if initial_nav <= 0 or final_nav <= 0 or years <= 0:
            raise ValueError("NAV and years must be strictly positive")
        return (final_nav / initial_nav) ** (1.0 / years) - 1.0

    def calculate_sharpe_ratio(self, fund_return: float, fund_std_dev: float) -> float:
        if fund_std_dev <= 0:
            raise ValueError("Standard deviation must be greater than zero")
        return (fund_return - self.risk_free_rate) / fund_std_dev

    def calculate_beta(self, fund_returns: List[float], benchmark_returns: List[float]) -> float:
        if len(fund_returns) != len(benchmark_returns) or len(fund_returns) < 2:
            raise ValueError("Returns must have equal length >= 2")
        mean_fund = sum(fund_returns) / len(fund_returns)
        mean_bench = sum(benchmark_returns) / len(benchmark_returns)
        covariance = sum((f - mean_fund) * (b - mean_bench) for f, b in zip(fund_returns, benchmark_returns))
        bench_variance = sum((b - mean_bench) ** 2 for b in benchmark_returns)
        if bench_variance == 0:
            return 1.0
        return covariance / bench_variance

    def calculate_alpha(self, fund_return: float, benchmark_return: float, beta: float) -> float:
        # Jensen's Alpha = Fund Return - [Risk Free + Beta * (Benchmark Return - Risk Free)]
        expected_return = self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate)
        return fund_return - expected_return

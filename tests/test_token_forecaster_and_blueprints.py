"""
Unit tests for ASCM Pre-Flight Token Forecaster (P90) and Local Blueprint Engine.
"""

import json
import unittest
from pathlib import Path

from orchestrator.budget.token_forecaster import (
    ForecastReport,
    TokenForecaster,
    GLOBAL_TOKEN_FORECASTER,
    PROVIDER_RATES,
)
from orchestrator.dashboard import DashboardState
from orchestrator.knowledge.blueprint_engine import (
    Blueprint,
    BlueprintEngine,
    GLOBAL_BLUEPRINT_ENGINE,
)


class TokenForecasterTests(unittest.TestCase):
    def setUp(self):
        self.forecaster = TokenForecaster()

    def test_estimate_input_tokens_from_goal(self):
        goal = "Build a multi-tenant payment gateway with Stripe webhook HMAC verification and AI token escrow."
        tokens = self.forecaster.estimate_input_tokens(goal)
        self.assertGreaterEqual(tokens, 20)

    def test_forecast_p50_and_p90_confidence_math(self):
        goal = "Build a high-throughput microservice in Go and Python"
        report = self.forecaster.forecast(
            user_goal=goal,
            target_file_count=3,
            circuit_breaker_limit_usd=1.00,
        )

        self.assertIsInstance(report, ForecastReport)
        self.assertEqual(report.confidence_level, 0.90)
        # P90 (90% confidence upper bound) must strictly exceed P50 (mean)
        self.assertGreater(report.p90_total_tokens, report.p50_total_tokens)
        self.assertGreater(report.p90_prompt_tokens, 0)
        self.assertGreater(report.p90_completion_tokens, 0)

        # Agent breakdown must cover selected roster
        self.assertEqual(len(report.agent_breakdown), len(report.selected_roster))
        for ab in report.agent_breakdown:
            self.assertIn("agent", ab)
            self.assertIn("p90_total_tokens", ab)
            self.assertGreater(ab["p90_total_tokens"], 0)

    def test_circuit_breaker_status(self):
        goal = "Simple hello world microservice"
        # High limit -> SAFE
        safe_report = self.forecaster.forecast(
            user_goal=goal,
            circuit_breaker_limit_usd=5.00,
        )
        self.assertEqual(safe_report.circuit_breaker_status, "SAFE")

        # Extremely low limit -> WARNING or BREACHED
        low_report = self.forecaster.forecast(
            user_goal=goal,
            circuit_breaker_limit_usd=0.0001,
        )
        self.assertIn(low_report.circuit_breaker_status, ["WARNING", "BREACHED"])

    def test_multi_model_cost_matrix_calculation(self):
        goal = "Stripe webhook processor"
        report = self.forecaster.forecast(user_goal=goal)

        costs = report.cost_projections
        self.assertIn("gemini_2_5_flash", costs)
        self.assertIn("gemini_2_5_pro", costs)
        self.assertIn("gpt_4o", costs)
        self.assertIn("claude_3_5_sonnet", costs)
        self.assertIn("ollama_local", costs)

        # Ollama local must always be 100% free ($0.00)
        self.assertEqual(costs["ollama_local"]["p90_cost_usd"], 0.0)

        # Gemini 2.5 Flash should be cheaper than Claude 3.5 Sonnet
        self.assertLess(
            costs["gemini_2_5_flash"]["p90_cost_usd"],
            costs["claude_3_5_sonnet"]["p90_cost_usd"],
        )


class BlueprintEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = BlueprintEngine()

    def test_blueprint_registry_contains_default_blueprints(self):
        bps = self.engine.list_all()
        self.assertGreaterEqual(len(bps), 5)
        ids = [b["id"] for b in bps]
        self.assertIn("stripe_webhook_verifier", ids)
        self.assertIn("token_bucket_limiter", ids)
        self.assertIn("jwt_auth_middleware", ids)
        self.assertIn("telemetry_client_sdk", ids)
        self.assertIn("fastapi_microservice_base", ids)

    def test_keyword_matching_for_stripe_and_tokens(self):
        query = "We need to verify stripe webhook signatures and prevent duplicate billing charges"
        matched = self.engine.match(query)
        self.assertTrue(any(b.id == "stripe_webhook_verifier" for b in matched))

        query2 = "Implement sliding-window token escrow rate limiter"
        matched2 = self.engine.match(query2)
        self.assertTrue(any(b.id == "token_bucket_limiter" for b in matched2))

    def test_render_blueprint_replaces_slots(self):
        custom_handler = "        print(f'Payment succeeded for {data.get(\"id\")}')"
        rendered = self.engine.render(
            "stripe_webhook_verifier",
            {
                "{{WEBHOOK_SECRET_ENV_OR_VAL}}": "whsec_test_secret_123",
                "{{DOMAIN_HANDLER_CODE}}": custom_handler,
            },
        )
        self.assertIn("whsec_test_secret_123", rendered)
        self.assertIn("Payment succeeded for", rendered)
        self.assertIn("hmac.compare_digest", rendered)

    def test_calculate_total_savings(self):
        matched_ids = ["stripe_webhook_verifier", "token_bucket_limiter", "jwt_auth_middleware"]
        savings = self.engine.calculate_total_savings(matched_ids)
        self.assertEqual(savings["matched_count"], 3)
        self.assertGreater(savings["total_tokens_saved"], 3000)
        self.assertGreater(savings["estimated_cost_saved_usd"], 0.0)


class DashboardForecasterIntegrationTests(unittest.TestCase):
    def test_dashboard_state_stores_forecast_and_blueprints(self):
        state = DashboardState(user_goal="Build payment gateway")
        forecaster = TokenForecaster()
        report = forecaster.forecast(user_goal="Build payment gateway")
        
        state.set_preflight_forecast(report.to_dict())
        self.assertEqual(state.preflight_forecast["p90_total_tokens"], report.p90_total_tokens)

        bps = GLOBAL_BLUEPRINT_ENGINE.list_all()[:2]
        state.set_active_blueprints(bps)
        self.assertEqual(len(state.active_blueprints), 2)

        snapshot = state._build_snapshot_dict()
        self.assertIn("preflight_forecast", snapshot)
        self.assertIn("active_blueprints", snapshot)
        self.assertEqual(snapshot["preflight_forecast"]["confidence_level"], 0.90)


if __name__ == "__main__":
    unittest.main()

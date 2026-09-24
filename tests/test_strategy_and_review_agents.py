import json
import unittest
from unittest.mock import MagicMock, patch

from orchestrator.agents.all_agents import (
    BusinessStrategyAgent,
    RevenueROIAgent,
    ArchitectureReviewAgent,
    CodeReviewAgent,
)
from orchestrator.agents.base import get_configured_provider, GeminiProvider, OpenAICompatibleProvider, AnthropicProvider
from orchestrator.dashboard import DashboardState, GLOBAL_DASHBOARD_STATE
from orchestrator.state import SharedBlackboard


class StrategyAndReviewAgentsTests(unittest.TestCase):

    def test_business_strategy_agent_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "market_strategy": "Target high-growth startups migrating microservices",
            "user_cohorts": [
                {
                    "cohort_name": "Solo Startup Founders",
                    "pain_point": "Manual cross-repo coordination is slow and error-prone",
                    "why_adopt": "Autonomous dual-sided sprints deliver features 10x faster",
                    "willingness_to_pay": "$49/mo"
                }
            ],
            "competitor_analysis": [
                {
                    "competitor": "GitHub Copilot Workspace",
                    "limitations": "Single-repository only; cannot guarantee cross-repo contract integrity",
                    "ascm_advantage": "Full cross-repository dual-sided synchronization with contract guards",
                    "verdict": "ASCM Superior for Distributed Systems"
                }
            ],
            "value_proposition": "Cut multi-repo integration sprints from 3 days to 4 minutes with zero contract drift.",
            "gtm_channels": ["Hacker News Show HN", "GitHub Marketplace", "Product Hunt"],
            "executive_summary": "Comprehensive GTM strategy targeting seed-to-scale startups."
        })

        agent = BusinessStrategyAgent(provider=mock_provider)
        result = agent.run(
            user_goal="Add Stripe Webhook integration across billing service and mobile SDK",
            clarified_prd="Implement webhook handler in Go and client listener in Python",
            contracts={"billing-svc": {"allowed_paths": ["api/"]}}
        )

        self.assertIn("market_strategy", result)
        self.assertEqual(len(result["user_cohorts"]), 1)
        self.assertEqual(result["user_cohorts"][0]["cohort_name"], "Solo Startup Founders")
        self.assertIn("Cut multi-repo", result["value_proposition"])
        self.assertEqual(len(result["competitor_analysis"]), 1)
        self.assertEqual(result["competitor_analysis"][0]["competitor"], "GitHub Copilot Workspace")

    def test_revenue_roi_agent_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "roi_summary": "Saves 18 engineering hours per sprint by eliminating manual PR reviews and contract drift.",
            "hours_saved_per_sprint": 18.5,
            "cost_savings_estimate_usd": 2775.0,
            "pricing_tiers": [
                {
                    "tier": "Community BYOK",
                    "price": "$0",
                    "target_audience": "Individual developers",
                    "features": ["Bring your own API key", "Local Docker sandbox"]
                },
                {
                    "tier": "Founder Pro",
                    "price": "$49/mo",
                    "target_audience": "Early stage startups",
                    "features": ["Multi-repo synchronization", "Automated GitHub PRs"]
                }
            ],
            "onboarding_funnel_metrics": [
                {
                    "stage": "Activation",
                    "metric": "Time to first verified cross-repo PR",
                    "target_rate": "80% within 10 minutes",
                    "improvement_tactic": "Pre-filled goal templates"
                }
            ],
            "activation_kpi": "First verified cross-repo PR created in < 10 mins",
            "gross_margin_estimate": "88% with model tiering",
            "executive_summary": "Strong unit economics with >85% gross margins."
        })

        agent = RevenueROIAgent(provider=mock_provider)
        result = agent.run(
            user_goal="Add Stripe Webhook",
            clarified_prd="PRD details",
            business_strategy={"value_proposition": "Fast sprints"}
        )

        self.assertEqual(result["hours_saved_per_sprint"], 18.5)
        self.assertEqual(result["cost_savings_estimate_usd"], 2775.0)
        self.assertEqual(len(result["pricing_tiers"]), 2)
        self.assertIn("First verified cross-repo PR", result["activation_kpi"])

    def test_architecture_review_agent_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "overall_score": 92,
            "verdict": "APPROVE_WITH_REMARKS",
            "nfr_scorecard": {
                "scalability": {"score": 90, "notes": "Horizontal scaling supported via stateless webhook handlers"},
                "security": {"score": 95, "notes": "HMAC signature verified before payload parsing"},
                "latency": {"score": 88, "notes": "Async worker pool prevents HTTP thread pool starvation"},
                "reliability": {"score": 94, "notes": "Idempotency key prevents duplicate transaction charges"},
                "maintainability": {"score": 93, "notes": "Clean package decoupling with strict interfaces"}
            },
            "architectural_gaps": ["Consider adding Redis rate limiter for burst traffic"],
            "spof_risks": ["Database write lock during peak invoice settlement"],
            "recommendations": ["Introduce dead letter queue for failed webhook delivery"],
            "executive_summary": "Resilient architecture meeting enterprise NFR benchmarks."
        })

        agent = ArchitectureReviewAgent(provider=mock_provider)
        result = agent.run(
            hld="# High Level Design\nWebhook flow",
            lld="# Low Level Design\nFunctions and structs",
            contracts={"billing": {"allowed_paths": ["api/"]}},
            user_goal="Stripe Webhook"
        )

        self.assertEqual(result["overall_score"], 92)
        self.assertEqual(result["verdict"], "APPROVE_WITH_REMARKS")
        self.assertEqual(result["nfr_scorecard"]["security"]["score"], 95)
        self.assertEqual(len(result["architectural_gaps"]), 1)
        self.assertEqual(len(result["spof_risks"]), 1)

    def test_code_review_agent_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "overall_score": 96,
            "approved": True,
            "verdict": "APPROVED",
            "security_grade": "A+",
            "test_coverage_assessment": "100% path coverage with positive, negative, and timeout assertions.",
            "findings": [
                {
                    "file": "api/webhook.go",
                    "severity": "MINOR",
                    "issue": "Add context timeout to avoid unbounded HTTP requests",
                    "fix_recommendation": "Pass r.Context() to http.Post"
                }
            ],
            "comments": ["MINOR: Add context timeout to avoid unbounded HTTP requests"],
            "executive_summary": "Production ready Go & Python code with robust unit tests."
        })

        agent = CodeReviewAgent(provider=mock_provider)
        result = agent.run(
            files={"api/webhook.go": "package api\nfunc HandleWebhook() {}", "api/webhook_test.go": "package api\n"},
            hld="HLD",
            lld="LLD"
        )

        self.assertEqual(result["overall_score"], 96)
        self.assertTrue(result["approved"])
        self.assertEqual(result["security_grade"], "A+")
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["severity"], "MINOR")

    @patch.dict("os.environ", {
        "GEMINI_API_KEY": "gemini-test-key",
        "OPENAI_API_KEY": "openai-test-key",
        "ANTHROPIC_API_KEY": "anthropic-test-key",
    })
    def test_multi_model_diversity_agent_allocation(self):
        # With multiple keys present, critic agents should be routed to diverse providers to avoid bias
        arch_agent = ArchitectureReviewAgent()
        code_agent = CodeReviewAgent()
        biz_agent = BusinessStrategyAgent()
        rev_agent = RevenueROIAgent()

        # Architecture review should choose Anthropic (Claude 3.5 Sonnet) or OpenAI (GPT-4o)
        self.assertIn(arch_agent.provider_name, ["anthropic", "openai", "gemini"])
        # Code review should choose OpenAI or Anthropic
        self.assertIn(code_agent.provider_name, ["openai", "anthropic", "gemini"])
        # All agents should expose their model name and provider name for provenance tracking
        self.assertTrue(hasattr(arch_agent, "model_name"))
        self.assertTrue(hasattr(code_agent, "model_name"))
        self.assertTrue(hasattr(biz_agent, "model_name"))
        self.assertTrue(hasattr(rev_agent, "model_name"))

    def test_dashboard_state_stores_reviews_and_feedback(self):
        state = DashboardState()
        state.new_session("Strategy and Review Test")

        biz_data = {"value_proposition": "Autonomous sprints", "user_cohorts": []}
        rev_data = {"hours_saved_per_sprint": 12.0, "cost_savings_estimate_usd": 1800.0}
        state.set_business_and_revenue_strategy(biz_data, rev_data)

        self.assertEqual(state.business_strategy, biz_data)
        self.assertEqual(state.revenue_analysis, rev_data)

        arch_data = {"overall_score": 91, "verdict": "APPROVE"}
        state.set_architecture_review(arch_data)
        self.assertEqual(state.architecture_review, arch_data)

        code_data = {"overall_score": 95, "security_grade": "A"}
        state.set_code_review_report(code_data)
        self.assertEqual(state.code_review_report, code_data)

        state.submit_strategy_feedback("Focus on enterprise compliance")
        state.submit_arch_feedback("Enforce TLS 1.3 only")
        state.submit_code_feedback("Use testify/require for fast fail")

        self.assertEqual(len(state.strategy_feedback), 1)
        self.assertEqual(state.strategy_feedback[0]["feedback"], "Focus on enterprise compliance")
        self.assertEqual(len(state.arch_feedback), 1)
        self.assertEqual(state.arch_feedback[0]["feedback"], "Enforce TLS 1.3 only")
        self.assertEqual(len(state.code_feedback), 1)
        self.assertEqual(state.code_feedback[0]["feedback"], "Use testify/require for fast fail")

        snapshot = state.get_snapshot()
        self.assertEqual(snapshot["business_strategy"], biz_data)
        self.assertEqual(snapshot["architecture_review"], arch_data)
        self.assertEqual(snapshot["code_review_report"], code_data)
        self.assertEqual(len(snapshot["strategy_feedback"]), 1)
        self.assertEqual(len(snapshot["arch_feedback"]), 1)
        self.assertEqual(len(snapshot["code_feedback"]), 1)


if __name__ == "__main__":
    unittest.main()

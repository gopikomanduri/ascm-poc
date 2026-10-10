import json
import unittest
from unittest.mock import MagicMock

from orchestrator.agents.compliance_agent import ComplianceAgent
from orchestrator.agents.qa_agent import QAAgent
from orchestrator.agents.checker_agent import CheckerAgent
from orchestrator.agents.sre_agent import SREAgent
from orchestrator.agents.apm_agent import APMAgent
from orchestrator.agents.oncall_agent import OnCallAgent


class GovernanceAndWorkflowAgentsTests(unittest.TestCase):
    def test_compliance_agent_constructor_and_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "frameworks": {"pci_dss": {"status": "PASS"}},
            "overall_verdict": "PASS",
            "compliance_score": 95,
            "violations": [],
        })

        agent = ComplianceAgent(provider=mock_provider, model="mock-model")
        self.assertEqual(agent.model_name, "mock-model")

        # Test run with files
        result = agent.run(files={"main.py": "def process_payment(): pass"}, domain="fintech")
        self.assertIn("findings", result)

        # Test validate_architecture
        arch_res = agent.validate_architecture(
            domain="fintech",
            hld="Payment gateway HLD",
            lld="Token escrow LLD",
            data_flows=["Client -> Gateway -> Stripe"],
        )
        self.assertEqual(arch_res.get("compliance_score"), 95)
        self.assertEqual(arch_res.get("overall_verdict"), "PASS")

    def test_qa_agent_constructor_and_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "test_plan": {"unit_tests": ["test_auth"]},
            "sla_gates": {"min_coverage_pct": 80},
        })

        agent = QAAgent(provider=mock_provider, model="mock-model")
        self.assertEqual(agent.model_name, "mock-model")

        # Test run method required by gtm_workflows.py
        result = agent.run(files={"test_auth.py": "def test_ok(): pass"})
        self.assertTrue(result.get("passed"))
        self.assertGreaterEqual(result.get("coverage_percentage", 0), 70)

        # Test check_sla_gates
        sla_res = agent.check_sla_gates(
            test_results={"coverage_pct": 85, "p99_latency_ms": 120, "error_rate_pct": 0.01},
            sla_gates={"min_coverage_pct": 80, "max_p99_latency_ms": 500, "max_error_rate_pct": 0.1},
        )
        self.assertTrue(sla_res.get("sla_passed"))

    def test_checker_agent_constructor_and_run(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            "phase": "discovery",
            "questions": ["What is your scale?", "Which cloud provider?"],
            "confidence_score": 85,
            "recommendation": "Proceed to architecture phase",
        })

        agent = CheckerAgent(provider=mock_provider)
        res = agent.run(user_input="Build a high-performance order routing engine")
        self.assertEqual(res.get("phase"), "discovery")
        self.assertEqual(len(res.get("questions", [])), 2)

    def test_sre_apm_oncall_agents(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({"strategy": "blue_green"})

        sre = SREAgent(provider=mock_provider)
        sre_res = sre.run(domain="e-commerce", requirements="Zero-downtime rolling updates")
        self.assertIn("domain", sre_res)

        apm = APMAgent(provider=mock_provider)
        apm_res = apm.run(domain="e-commerce", requirements="99.9% uptime")
        self.assertIn("slos", apm_res)

        oncall = OnCallAgent(provider=mock_provider)
        oncall_res = oncall.run(alert={"id": "alert-101", "severity": "HIGH"})
        self.assertIn("received", oncall_res)
        self.assertIn("proposed_fix", oncall_res)


if __name__ == "__main__":
    unittest.main()

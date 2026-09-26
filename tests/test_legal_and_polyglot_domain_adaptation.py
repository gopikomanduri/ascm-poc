import unittest
from orchestrator.domain.domain_adapter import DomainAdapter, VERTICAL_DOMAINS
from orchestrator.agents.all_agents import (
    ProductAgent,
    ArchitectAgent,
    DesignAgent,
    PlannerAgent,
    PolyglotCoderAgent,
    SecurityAuditorAgent,
    ArchitectureReviewAgent,
    CodeReviewAgent,
    BusinessStrategyAgent,
)


class LegalAndPolyglotDomainAdaptationTests(unittest.TestCase):
    def test_legal_domain_detection(self):
        goal = "Build an automated contract analysis and regulatory compliance redlining engine"
        profile = DomainAdapter.detect_domain(goal)
        self.assertEqual(profile.domain_id, "LEGALTECH_COMPLIANCE")
        self.assertEqual(profile.primary_language, "python")
        self.assertIn("Contract AST & Clause Extraction", profile.core_primitives)
        self.assertTrue(any("Jurisdiction" in q or "Statutory" in q for q in profile.grilling_dimensions))
        self.assertTrue(any("Harvey AI" in c.get("competitor", "") for c in profile.competitor_archetypes))

    def test_legal_agent_role_prompts(self):
        profile = VERTICAL_DOMAINS["LEGALTECH_COMPLIANCE"]

        # Product Agent prompt
        product_prompt = DomainAdapter.get_agent_domain_prompt("product", profile)
        self.assertIn("SPECIALIZED LEGALTECH & REGULATORY COMPLIANCE EXPERT", product_prompt)
        self.assertIn("PYTHON", product_prompt)

        # Architect Agent prompt
        arch_prompt = DomainAdapter.get_agent_domain_prompt("architect", profile)
        self.assertIn("LEAD LEGAL SYSTEMS ARCHITECT & REGULATORY FRAMEWORK LEAD", arch_prompt)

        # Thinking / Review Agent prompt
        thinking_prompt = DomainAdapter.get_agent_domain_prompt("thinking", profile)
        self.assertIn("SENIOR LEGAL SYSTEMS ARCHITECTURE CRITIC & COMPLIANCE INVARIANT AUDITOR", thinking_prompt)

        # Orchestrator / Planner Agent prompt
        orch_prompt = DomainAdapter.get_agent_domain_prompt("orchestrator", profile)
        self.assertIn("LEAD LEGAL & TECHNICAL WORKFLOW ORCHESTRATOR", orch_prompt)

        # Coder Agent prompt
        coder_prompt = DomainAdapter.get_agent_domain_prompt("coder", profile)
        self.assertIn("PRINCIPAL LEGALTECH SOFTWARE ENGINEER & TDD SPECIALIST", coder_prompt)

    def test_polyglot_language_detection_and_override(self):
        profile = VERTICAL_DOMAINS["LEGALTECH_COMPLIANCE"]

        # Default language for legal is Python
        default_lang = DomainAdapter.detect_language("Build contract clause validator", profile)
        self.assertEqual(default_lang, "python")

        # Explicit override to Go
        go_lang = DomainAdapter.detect_language("Build contract clause validator in Go", profile)
        self.assertEqual(go_lang, "go")

        # Explicit override to TypeScript
        ts_lang = DomainAdapter.detect_language("Build contract clause validator using TypeScript", profile)
        self.assertEqual(ts_lang, "typescript")

    def test_product_agent_legal_grilling(self):
        agent = ProductAgent()
        res = agent.run("Build an NDA and contract analyzer tool")
        self.assertEqual(res.get("detected_domain"), "LegalTech, Regulatory Engineering & Compliance Automation")
        self.assertFalse(res.get("is_clear"))
        self.assertLessEqual(res.get("confidence_score"), 0.50)
        self.assertTrue(len(res.get("clarification_questions")) >= 3)
        self.assertTrue(any("Jurisdiction" in q or "Statutory" in q or "Contract" in q for q in res.get("clarification_questions")))

    def test_business_strategy_legal_competitors(self):
        agent = BusinessStrategyAgent()
        res = agent.run(
            user_goal="Legal clause review and GDPR compliance checker",
            clarified_prd="Automated legal parsing for NDAs and vendor contracts."
        )
        detected = res.get("detected_domain", "")
        self.assertTrue("LegalTech" in detected and "Compliance" in detected)
        comps = [c.get("competitor", "") for c in res.get("competitor_analysis", [])]
        self.assertTrue(len(comps) > 0)
        self.assertTrue(any(any(name in c for name in ["Harvey", "Ironclad", "Robin", "CLM", "Counsel"]) for c in comps))


if __name__ == "__main__":
    unittest.main()

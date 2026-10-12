import unittest

from orchestrator.mentor.founder_intelligence import FounderIntelligenceEngine


class FounderIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = FounderIntelligenceEngine()

    def test_missing_goal_requests_clarification_and_never_executes(self):
        result = self.engine.evaluate(goal=None, observation="code_activity", evidence={})
        self.assertEqual(result["recommended_path"], "clarify_goal")
        self.assertTrue(result["requires_founder_input"])
        self.assertFalse(result["execution_performed"])
        self.assertIn("founder_confirmed_goal", result["missing_evidence"])

    def test_missing_customer_evidence_prioritizes_validation_over_building(self):
        result = self.engine.evaluate(
            goal="Launch an MVP",
            observation="code_activity",
            evidence={"task_description": "Build another feature", "milestone": "MVP demo"},
        )
        self.assertEqual(result["recommended_path"], "customer_validate")
        self.assertIn("customer_evidence", result["missing_evidence"])

    def test_reuse_candidate_ranks_above_build(self):
        result = self.engine.evaluate(
            goal="Ship authentication",
            observation="code_activity",
            evidence={
                "task_description": "Implement authentication",
                "reuse_candidates": [{"name": "existing auth library"}],
                "milestone": "Working sign-in",
                "customer_evidence": "Three customer interviews",
            },
        )
        paths = {item["path"]: item["score"] for item in result["ranked_paths"]}
        self.assertGreater(paths["reuse"], paths["build"])
        self.assertEqual(result["recommended_path"], "reuse")

    def test_verified_demand_and_readiness_support_bounded_launch(self):
        result = self.engine.evaluate(
            goal="Acquire first customers",
            observation="milestone_completed",
            evidence={
                "task_description": "Prepare launch",
                "milestone": "Release candidate",
                "customer_evidence": "Pilot users confirmed demand",
                "user_demand_verified": True,
                "launch_readiness_verified": True,
            },
        )
        self.assertEqual(result["recommended_path"], "launch_or_sell")
        self.assertEqual(result["confidence"], "high")

    def test_repeated_failures_support_simplification_and_pause_review(self):
        result = self.engine.evaluate(
            goal="Complete a working prototype",
            observation="code_activity",
            evidence={
                "task_description": "Finish integration",
                "repeated_failures": True,
                "scope_risk": True,
            },
        )
        scores = {item["path"]: item["score"] for item in result["ranked_paths"]}
        self.assertGreaterEqual(scores["simplify"], 75)
        self.assertGreaterEqual(scores["pause_or_stop"], 70)

    def test_invalid_evidence_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate(goal="Goal", observation="code_activity", evidence=[])


if __name__ == "__main__":
    unittest.main()

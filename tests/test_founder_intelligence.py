import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.mentor.daemon import UniversalASCMDaemon
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
                "reuse_candidates": [{
                    "name": "existing auth library",
                    "license": "MIT",
                    "archived": False,
                    "suitability_score": 78,
                }],
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



class _FakeFounderContext:
    def __init__(self, goal):
        self.goal = goal

    def load(self):
        return {"current_goal": self.goal}


class _FakeFusion:
    def __init__(self, context):
        self.context = context

    def latest_project_path(self):
        return Path(".")

    def infer_context(self, project_path=None):
        return self.context


class _FakeDecisionMentor:
    def __init__(self, goal, recommendation):
        self.founder_context = _FakeFounderContext(goal)
        self.recommendation = recommendation
        self.received = None

    def recommend_next_action(self, observation, evidence):
        self.received = (observation, evidence)
        return self.recommendation


class FounderIntelligenceDaemonIntegrationTests(unittest.TestCase):
    def test_daemon_surfaces_decision_and_missing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            daemon = UniversalASCMDaemon.__new__(UniversalASCMDaemon)
            daemon.history_dir = Path(tmp)
            daemon.audit_logger = mock.Mock()
            daemon.context_fusion = _FakeFusion({
                "task_hypothesis": "Investigating test failures after recent code changes",
                "confidence": 0.82,
                "evidence_event_ids": ["edit-1", "test-fail-1"],
                "rationale": "A test failure followed a code change.",
                "project_id": "project-a",
            })
            daemon.mentor = _FakeDecisionMentor(
                "Launch invoice automation",
                {
                    "actions": [{"title": "Simplify the failing slice", "rationale": "Narrow the failure."}],
                    "founder_decision": {
                        "recommended_path": "simplify",
                        "confidence": "medium",
                        "ranked_paths": [
                            {"path": "simplify", "score": 80},
                            {"path": "customer_validate", "score": 75},
                            {"path": "reuse", "score": 60},
                        ],
                        "missing_evidence": ["customer_evidence", "reuse_candidates"],
                    },
                },
            )
            with mock.patch("orchestrator.mentor.daemon.CrossPlatformNotifier.notify") as notify:
                daemon._prompt_for_founder_context(
                    {"filesystem_activity": {"recently_edited_files": []}}, {}, 100000
                )
            self.assertIn("Founder Intelligence: Simplify", notify.call_args.args[0])
            self.assertIn("customer_evidence", notify.call_args.args[1])
            self.assertEqual(daemon.audit_logger.log_event.call_args.args[0], "MENTOR_RECOMMENDATION")
            self.assertEqual(daemon.mentor.received[0], "code_activity")
            self.assertTrue(daemon.mentor.received[1]["tests_failed"])


if __name__ == "__main__":
    unittest.main()

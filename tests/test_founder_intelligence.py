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

    def test_weak_reuse_metadata_does_not_claim_suitable_alternative(self):
        result = self.engine.evaluate(
            goal="Ship authentication",
            observation="code_activity",
            evidence={
                "task_description": "Implement authentication",
                "milestone": "Working sign-in",
                "reuse_candidates": [{
                    "name": "archived auth library",
                    "license": "Not detected",
                    "archived": True,
                    "suitability_score": 5,
                }],
            },
        )
        paths = {item["path"]: item["score"] for item in result["ranked_paths"]}
        self.assertLess(paths["reuse"], paths["build"])
        self.assertIn("verified_reuse_fit_and_license", result["missing_evidence"])

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
            self.assertIn("customer_evidence_summary", daemon.mentor.received[1])
            self.assertFalse(daemon.mentor.received[1]["customer_evidence_summary"]["user_demand_verified"])
            self.assertIn("reuse_evidence_summary", daemon.mentor.received[1])
            self.assertFalse(daemon.mentor.received[1]["reuse_evidence_summary"]["enabled"])
            self.assertIn("Open-source search disabled", notify.call_args.args[1])
            self.assertIn("--feedback helpful --intervention-id", notify.call_args.args[1])
            self.assertIn("--report --session-id", notify.call_args.args[1])
            self.assertIn("--project-path", notify.call_args.args[1])


class FounderEvidenceDeliveryIntegrationTests(unittest.TestCase):
    def test_daemon_collects_evidence_and_tracks_unconfirmed_notification(self):
        with tempfile.TemporaryDirectory() as tmp:
            daemon = UniversalASCMDaemon.__new__(UniversalASCMDaemon)
            daemon.repo_path = Path(tmp)
            daemon.history_dir = Path(tmp) / ".ascm_history"
            daemon.history_dir.mkdir()
            daemon.audit_logger = mock.Mock()
            daemon.context_fusion = _FakeFusion({
                "task_hypothesis": "Build invoice automation",
                "confidence": 0.91,
                "evidence_event_ids": ["edit-7", "terminal-2"],
                "rationale": "Recent edits and terminal signals align.",
                "project_id": "project-invoice",
            })
            decision = {
                "recommended_path": "customer_validate",
                "confidence": "medium",
                "ranked_paths": [{"path": "customer_validate", "score": 75}],
                "missing_evidence": [],
            }
            daemon.mentor = _FakeDecisionMentor(
                "Validate invoice automation demand",
                {"actions": [], "founder_decision": decision},
            )
            daemon.evidence_sources = mock.Mock(return_value=None)
            daemon.evidence_sources.collect.return_value = {
                "customer_evidence": None,
                "user_demand_verified": False,
                "customer_evidence_summary": {
                    "event_count": 0,
                    "user_demand_verified": False,
                    "customer_evidence": None,
                },
                "reuse_candidates": [],
                "reuse_evidence_summary": {"enabled": False, "candidate_count": 0},
            }
            daemon.intervention_tracker = mock.Mock()

            with mock.patch(
                "orchestrator.mentor.daemon.CrossPlatformNotifier.notify",
                return_value=False,
            ):
                daemon._prompt_for_founder_context(
                    {"filesystem_activity": {"recently_edited_files": []}}, {}, 200000
                )

            daemon.evidence_sources.collect.assert_called_once_with("Build invoice automation")
            self.assertEqual(daemon.mentor.received[1]["user_demand_verified"], False)
            self.assertEqual(
                daemon.intervention_tracker.record_shown.call_args.kwargs["delivery_confirmed"],
                False,
            )
            self.assertEqual(
                daemon.intervention_tracker.record_shown.call_args.kwargs["evidence_summary"]["customer"]["event_count"],
                0,
            )


if __name__ == "__main__":
    unittest.main()

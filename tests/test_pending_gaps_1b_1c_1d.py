"""Regression tests for the ASCM founder-readiness fixes 1.b, 1.c, and 1.d."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from orchestrator.mentor.evidence_pipeline import InterventionQualityTracker
from orchestrator.mentor.next_best_action import NextBestActionEngine
from orchestrator.mentor.session_intelligence import assess_goal_alignment


class GoalAlignmentFalsePositiveTests(unittest.TestCase):
    def test_synonymous_invoice_billing_work_is_not_flagged_as_goal_drift(self):
        result = assess_goal_alignment(
            "Validate customer demand for invoice automation",
            "Test billing workflow with users",
            {"customer_evidence": "three customer interviews"},
        )
        self.assertEqual(result["alignment_status"], "aligned")
        self.assertIn("concept:1", result["concept_overlap"])
        self.assertIsNone(result["challenge_prompt"])

    def test_sparse_context_is_not_misclassified_as_drift(self):
        result = assess_goal_alignment("Ship MVP", "Read docs", {"customer_evidence": None})
        self.assertNotEqual(result["alignment_status"], "challenge")
        self.assertTrue(result["is_heuristic"])


class ReuseRecommendationGateTests(unittest.TestCase):
    def test_unreviewed_public_candidates_are_not_passed_as_recommendation_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = NextBestActionEngine(tmp)
            engine.context_store.update(current_goal="Build a secure authentication MVP")
            seen = {}

            def evaluate(**kwargs):
                seen.update(kwargs["evidence"])
                return {
                    "recommended_path": "customer_validate",
                    "ranked_paths": [],
                    "missing_evidence": [],
                    "requires_founder_input": False,
                }

            engine.founder_intelligence.evaluate = evaluate
            candidate = {
                "name": "org/auth-lib",
                "url": "https://github.com/org/auth-lib",
                "human_review": {"review_complete": False},
                "feature_fit_verified": False,
                "license_compatible": False,
                "security_reviewed": False,
                "integration_cost_estimated": False,
            }
            engine.recommend(
                observation="code_activity",
                evidence={"task_description": "Implement authentication", "reuse_candidates": [candidate]},
            )
            self.assertEqual(seen["reuse_candidates"], [])
            self.assertEqual(seen["reuse_candidates_research_only_count"], 1)
            self.assertEqual(seen["reuse_candidates_eligible_for_recommendation"], 0)
            self.assertIn("completed human reuse review", seen["missing_evidence"])


class InterventionFollowupTests(unittest.TestCase):
    def test_old_unreviewed_interventions_are_reported_separately_from_negative_feedback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            tracker.path.parent.mkdir(parents=True, exist_ok=True)
            old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            tracker.path.write_text(json.dumps([
                {
                    "intervention_id": "old-pending",
                    "session_id": "session-a",
                    "delivery_confirmed": True,
                    "attempted_at": old_time,
                    "recommended_path": "customer_validate",
                    "feedback": None,
                },
                {
                    "intervention_id": "recent-pending",
                    "session_id": "session-a",
                    "delivery_confirmed": True,
                    "attempted_at": datetime.now(timezone.utc).isoformat(),
                    "recommended_path": "reuse",
                    "feedback": None,
                },
            ]), encoding="utf-8")
            report = tracker.report("session-a")
            self.assertEqual(report["overdue_unreviewed_24h"], 1)
            self.assertEqual(report["overdue_intervention_ids"], ["old-pending"])
            self.assertEqual(report["negative_feedback_rate"], None)
            self.assertEqual(report["unreviewed"], 2)


if __name__ == "__main__":
    unittest.main()

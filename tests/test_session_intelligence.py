import unittest

from orchestrator.mentor.session_intelligence import (
    assess_goal_alignment, build_session_review, summarize_session,
)


class SessionIntelligenceTests(unittest.TestCase):
    def test_summarizes_cross_signal_coverage_without_content(self):
        result = summarize_session([
            {"event_type": "file_changed", "project_id": "p1", "event_id": "e1", "path": "src/app.py"},
            {"event_type": "terminal_command", "project_id": "p1", "event_id": "e2", "command_category": "python_tests"},
            {"event_type": "test_failed", "project_id": "p1", "event_id": "e3", "exit_code": 1},
            {"event_type": "browser_domain_seen", "project_id": "p1", "event_id": "e4", "domain": "docs.python.org"},
        ])
        self.assertTrue(result["cross_signal_context"])
        self.assertEqual(result["event_count"], 4)
        self.assertEqual(result["source_counts"]["tests"], 1)
        self.assertNotIn("path", result)
        self.assertNotIn("domain", result)
        self.assertNotIn("command_category", result)

    def test_goal_drift_with_unknown_demand_challenges_more_coding(self):
        result = assess_goal_alignment(
            "Validate demand for invoice automation",
            "Implement internal caching engine",
            {"tests_failed": False, "customer_evidence": None},
        )
        self.assertEqual(result["alignment_status"], "challenge")
        self.assertIn("customer-validation", result["challenge_prompt"])
        self.assertTrue(result["is_heuristic"])

    def test_repeated_failures_prioritize_smallest_failing_slice(self):
        result = assess_goal_alignment(
            "Ship a working prototype", "Implement the API",
            {"repeated_failures": True, "customer_evidence": "pilot interview"},
        )
        self.assertEqual(result["alignment_status"], "review")
        self.assertIn("smallest failing slice", result["challenge_prompt"])

    def test_similar_goal_and_task_does_not_claim_drift(self):
        result = assess_goal_alignment(
            "Validate invoice automation demand", "Validate invoice automation",
            {"customer_evidence": "three interviews"},
        )
        self.assertEqual(result["alignment_status"], "aligned")
        self.assertIsNone(result["challenge_prompt"])

    def test_review_keeps_activity_and_goal_separate(self):
        result = build_session_review("Launch product", "Read browser docs", [], {})
        self.assertEqual(result["goal_alignment"]["goal"], "Launch product")
        self.assertEqual(result["goal_alignment"]["observed_task"], "Read browser docs")
        self.assertIn("limitation", result["session"])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.next_best_action import FounderContextStore, NextBestActionEngine


class FounderContextStoreTests(unittest.TestCase):
    def test_goal_and_customer_are_persisted_without_repo_name_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FounderContextStore(tmp)
            self.assertIsNone(store.load()["current_goal"])
            state = store.update(
                current_goal="Validate invoice automation",
                target_customer="Finance operations leaders",
                next_milestone="Five discovery calls",
                constraints=["No paid ads before validation"],
            )
            loaded = store.load()
        self.assertEqual(loaded["current_goal"], "Validate invoice automation")
        self.assertEqual(loaded["target_customer"], "Finance operations leaders")
        self.assertEqual(loaded["next_milestone"], "Five discovery calls")
        self.assertEqual(loaded["constraints"], ["No paid ads before validation"])


class NextBestActionTests(unittest.TestCase):
    def test_missing_goal_asks_for_clarification_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = NextBestActionEngine(tmp).recommend(observation="code_activity")
        self.assertTrue(result["requires_founder_input"])
        self.assertEqual(result["actions"][0]["action_type"], "clarify_goal")

    def test_coding_activity_recommends_build_vs_integrate_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = NextBestActionEngine(tmp)
            engine.context_store.update(current_goal="Launch a secure customer portal")
            result = engine.recommend(
                observation="code_activity",
                evidence={"task_description": "Implement authentication"},
            )
        types = {action["action_type"] for action in result["actions"]}
        self.assertIn("check_reuse_before_building", types)
        self.assertIn("continue_with_milestone", types)
        self.assertIn("authentication", result["actions"][0]["rationale"].lower())

    def test_publishing_requires_approval_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = NextBestActionEngine(tmp)
            engine.context_store.update(current_goal="Validate demand")
            result = engine.recommend(observation="gtm_cycle_generated")
            proposal = engine.propose_action(result, "approve_campaign")
            self.assertEqual(proposal["status"], "pending_approval")
            approved = engine.record_approval(proposal["proposal_id"], approved=True)
            self.assertEqual(approved["status"], "approved")
            self.assertIn("does not execute", result["disclaimer"].lower())

    def test_pending_gtm_experiment_can_be_resolved_by_review_or_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = NextBestActionEngine(tmp)
            engine.context_store.update(current_goal="Get customer feedback")
            events = [
                {"event_type": "gtm_cycle_generated", "experiment_id": "exp-1"},
                {"event_type": "experiment_stopped", "experiment_id": "exp-1"},
            ]
            result = engine.recommend(observation="tests_passed", recent_events=events)
        self.assertNotIn("attribute_gtm_outcomes", {a["action_type"] for a in result["actions"]})

    def test_unknown_observation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Unsupported observation"):
                NextBestActionEngine(tmp).recommend(observation="guess_what_founder_is_doing")


if __name__ == "__main__":
    unittest.main()

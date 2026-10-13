import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.next_best_action import FounderContextStore, NextBestActionEngine


class WorkspaceContextIntegrationTests(unittest.TestCase):
    def test_decision_engine_and_feedback_ledger_use_same_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = NextBestActionEngine(root)
            self.assertEqual(engine.founder_intelligence.project_path, root.resolve())
            history = root / ".ascm_history"
            history.mkdir(exist_ok=True)
            (history / "intervention_quality.json").write_text(json.dumps([
                {"recommended_path": "build", "feedback": "helpful", "delivery_confirmed": True}
                for _ in range(8)
            ]), encoding="utf-8")
            result = engine.founder_intelligence.evaluate(
                goal="Launch a customer portal",
                observation="code_activity",
                evidence={"task_description": "Implement login", "milestone": "Working login"},
            )
            self.assertIn("build", result["learning_adjustments_applied"])

    def test_founder_confirmed_customer_constraints_and_milestone_are_carried_to_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = NextBestActionEngine(tmp)
            FounderContextStore(tmp).update(
                current_goal="Validate invoice automation",
                target_customer="Finance operations leaders",
                next_milestone="Five discovery calls",
                constraints=["No paid ads before validation"],
                preferences={"communication_style": "concise"},
            )
            result = engine.recommend(
                observation="code_activity",
                evidence={"task_description": "Validate invoice automation"},
            )
            decision = result["founder_decision"]
            self.assertEqual(decision["founder_context"]["target_customer"], "Finance operations leaders")
            self.assertEqual(decision["founder_context"]["constraints"], ["No paid ads before validation"])
            self.assertEqual(decision["founder_context"]["milestone"], "Five discovery calls")
            self.assertEqual(decision["founder_context"]["preferences"]["communication_style"], "concise")


if __name__ == "__main__":
    unittest.main()

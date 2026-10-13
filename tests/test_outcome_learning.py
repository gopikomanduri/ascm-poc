import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.founder_intelligence import FounderIntelligenceEngine, _feedback_adjustments


class OutcomeLearningTests(unittest.TestCase):
    def _write_feedback(self, root: Path, records: list[dict]) -> None:
        history = root / ".ascm_history"
        history.mkdir(parents=True, exist_ok=True)
        (history / "intervention_quality.json").write_text(json.dumps(records), encoding="utf-8")

    def test_feedback_adjustment_requires_minimum_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_feedback(root, [
                {"recommended_path": "build", "feedback": "helpful", "delivery_confirmed": True}
                for _ in range(4)
            ])
            self.assertEqual(_feedback_adjustments(root), {})

    def test_feedback_is_bounded_and_ignores_unconfirmed_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [
                {"recommended_path": "build", "feedback": "helpful", "delivery_confirmed": True}
                for _ in range(30)
            ] + [
                {"recommended_path": "build", "feedback": "incorrect", "delivery_confirmed": False}
                for _ in range(50)
            ]
            self._write_feedback(root, records)
            result = _feedback_adjustments(root)
            self.assertEqual(result["build"]["rated_interventions"], 30)
            self.assertGreater(result["build"]["adjustment"], 0)
            self.assertLessEqual(result["build"]["adjustment"], 6)

    def test_negative_feedback_can_lower_path_score_and_is_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_feedback(root, [
                {"recommended_path": "customer_validate", "feedback": "incorrect", "delivery_confirmed": True}
                for _ in range(12)
            ])
            result = FounderIntelligenceEngine(project_path=root).evaluate(
                goal="Launch an MVP",
                observation="code_activity",
                evidence={"task_description": "Build checkout", "milestone": "MVP demo"},
            )
            paths = {item["path"]: item for item in result["ranked_paths"]}
            self.assertLess(paths["customer_validate"]["score"], 75)
            self.assertLess(paths["customer_validate"]["historical_feedback_adjustment"], 0)
            self.assertIn("not causal proof", paths["customer_validate"]["reason"])
            self.assertFalse(result["execution_performed"])

    def test_missing_feedback_does_not_change_evidence_based_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = FounderIntelligenceEngine(project_path=root).evaluate(
                goal="Launch an MVP",
                observation="code_activity",
                evidence={"task_description": "Build checkout", "milestone": "MVP demo"},
            )
            self.assertEqual(baseline["learning_adjustments_applied"], {})
            self.assertEqual(baseline["recommended_path"], "customer_validate")


if __name__ == "__main__":
    unittest.main()

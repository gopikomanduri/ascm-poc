import unittest

from orchestrator.mentor.session_evaluator import evaluate_founder_sessions


class FounderSessionEvaluatorTests(unittest.TestCase):
    def test_computes_metrics_with_explicit_denominators(self):
        report = evaluate_founder_sessions([
            {"kind": "project_attribution", "independently_verified": True,
             "expected_project_id": "a", "observed_project_id": "a"},
            {"kind": "project_attribution", "independently_verified": True,
             "expected_project_id": "b", "observed_project_id": "wrong"},
            {"kind": "key_event", "relevant": True, "detected": True},
            {"kind": "key_event", "relevant": True, "detected": False},
            {"kind": "intervention", "delivered": True, "rated": True,
             "helpful": True, "relevant": True},
            {"kind": "intervention", "delivered": True, "rated": True,
             "helpful": False, "relevant": False},
            {"kind": "intervention", "delivered": True, "rated": False,
             "relevant": True},
            {"kind": "consequential_action", "attempted": True,
             "approval_valid": True, "executed": True, "result_verified": True},
            {"kind": "audit_event", "required": True, "recorded": True},
        ])
        metrics = report["metrics"]
        self.assertEqual(metrics["project_attribution_accuracy"]["rate"], 0.5)
        self.assertEqual(metrics["project_attribution_accuracy"]["numerator"], 1)
        self.assertEqual(metrics["project_attribution_accuracy"]["denominator"], 2)
        self.assertEqual(metrics["missed_key_event_rate"]["rate"], 0.5)
        self.assertEqual(metrics["useful_intervention_rate"]["rate"], 0.5)
        self.assertAlmostEqual(metrics["feedback_coverage"]["rate"], 2 / 3, places=4)
        self.assertAlmostEqual(metrics["false_interruption_rate"]["rate"], 1 / 3, places=4)
        self.assertFalse(report["stop_ship"])

    def test_safety_failures_are_stop_ship(self):
        report = evaluate_founder_sessions([
            {"kind": "consequential_action", "attempted": True,
             "approval_valid": False, "executed": True, "result_verified": False},
            {"kind": "audit_event", "required": True, "recorded": False},
        ])
        self.assertTrue(report["stop_ship"])
        self.assertTrue(report["metrics"]["permission_gating"]["stop_ship"])
        self.assertTrue(report["metrics"]["verified_execution"]["stop_ship"])
        self.assertTrue(report["metrics"]["audit_completeness"]["stop_ship"])

    def test_zero_denominators_are_unmeasured_not_passes(self):
        report = evaluate_founder_sessions([])
        self.assertIsNone(report["metrics"]["project_attribution_accuracy"]["rate"])
        self.assertFalse(report["metrics"]["project_attribution_accuracy"]["meets_target"])
        self.assertIn("project_attribution_accuracy", report["unmeasured_metrics"])
        self.assertFalse(report["stop_ship"])

    def test_unrated_interventions_do_not_count_as_success_or_failure(self):
        report = evaluate_founder_sessions([
            {"kind": "intervention", "delivered": True, "rated": False,
             "helpful": None, "relevant": True},
        ])
        self.assertIsNone(report["metrics"]["useful_intervention_rate"]["rate"])
        self.assertEqual(report["metrics"]["feedback_coverage"]["rate"], 0.0)
        self.assertIn("useful_intervention_rate", report["unmeasured_metrics"])

    def test_malformed_records_are_counted_not_crashed(self):
        report = evaluate_founder_sessions([None, {"bad": "shape"}])
        self.assertEqual(report["malformed_record_count"], 2)
        self.assertEqual(report["record_count"], 0)


if __name__ == "__main__":
    unittest.main()

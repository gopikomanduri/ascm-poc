import tempfile
import unittest

from orchestrator.mentor.evidence_pipeline import InterventionQualityTracker


class InterventionDeliveryTrackingTests(unittest.TestCase):
    def test_failed_delivery_is_an_attempt_not_a_shown_intervention(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            attempt = tracker.record_shown(
                session_id="session-a",
                project_id="project-a",
                recommendation={"recommended_path": "reuse", "confidence": "medium"},
                intervention_id="attempt-not-delivered",
                delivery_confirmed=False,
            )

            self.assertFalse(attempt["delivery_confirmed"])
            report = tracker.report("session-a")
            self.assertEqual(report["interventions_attempted"], 1)
            self.assertEqual(report["interventions_shown"], 0)
            self.assertEqual(report["delivery_unconfirmed"], 1)
            self.assertEqual(report["interventions_reviewed"], 0)
            self.assertIsNone(report["positive_feedback_rate"])
            with self.assertRaisesRegex(ValueError, "delivery was not confirmed"):
                tracker.record_feedback(
                    feedback="helpful", intervention_id="attempt-not-delivered"
                )

    def test_feedback_coverage_excludes_unconfirmed_delivery_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            tracker.record_shown(
                session_id="session-coverage",
                project_id="project-a",
                recommendation={"recommended_path": "reuse", "confidence": "medium"},
                intervention_id="delivered",
                delivery_confirmed=True,
            )
            tracker.record_shown(
                session_id="session-coverage",
                project_id="project-a",
                recommendation={"recommended_path": "build", "confidence": "low"},
                intervention_id="not-delivered",
                delivery_confirmed=False,
            )
            tracker.record_feedback(feedback="helpful", intervention_id="delivered")

            report = tracker.report("session-coverage")
            self.assertEqual(report["interventions_attempted"], 2)
            self.assertEqual(report["interventions_shown"], 1)
            self.assertEqual(report["delivery_unconfirmed"], 1)
            self.assertEqual(report["feedback_coverage"], 1.0)

    def test_confirmed_delivery_can_be_rated_and_is_counted_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            tracker.record_shown(
                session_id="session-b",
                project_id="project-b",
                recommendation={"recommended_path": "customer_validate", "confidence": "high"},
                intervention_id="delivered-1",
                delivery_confirmed=True,
            )
            tracker.record_feedback(feedback="acted_on", intervention_id="delivered-1")

            report = tracker.report("session-b")
            self.assertEqual(report["interventions_attempted"], 1)
            self.assertEqual(report["interventions_shown"], 1)
            self.assertEqual(report["delivery_unconfirmed"], 0)
            self.assertEqual(report["interventions_reviewed"], 1)
            self.assertEqual(report["positive_feedback_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()

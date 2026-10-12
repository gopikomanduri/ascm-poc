import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.gtm.strategy.product_context import ProductContext
from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger
from orchestrator.mentor.proactive_mentor import ASCMProactiveMentor
from unittest import mock


class ProductContextTests(unittest.TestCase):
    def test_missing_config_is_explicitly_generic(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = ProductContext.load(Path(tmp))
        self.assertEqual(context.product_name, "Unconfigured product")
        self.assertIn("not configured", context.product_thesis.lower())
        self.assertEqual(context.domain_keywords, [])

    def test_loads_product_context_from_project_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ascm_product.json").write_text(json.dumps({
                "product_name": "Example",
                "product_thesis": "Reduce invoice processing time.",
                "icp_description": "Finance operations teams.",
                "domain_keywords": ["invoice automation"],
                "goals": ["5 discovery calls"],
            }))
            context = ProductContext.load(root)
        self.assertEqual(context.product_name, "Example")
        self.assertEqual(context.domain_keywords, ["invoice automation"])
        self.assertEqual(context.goals, ["5 discovery calls"])

    def test_rejects_unknown_or_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ascm_product.json").write_text('{"product_nam": "typo"}')
            with self.assertRaisesRegex(ValueError, "Unknown"):
                ProductContext.load(root)
            (root / ".ascm_product.json").write_text('{"domain_keywords": "not a list"}')
            with self.assertRaisesRegex(ValueError, "domain_keywords"):
                ProductContext.load(root)


class OutcomeLedgerTests(unittest.TestCase):
    def test_records_experiment_events_and_summarizes_real_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = OutcomeLedger(Path(tmp))
            ledger.record("experiment_planned", experiment_id="exp-1")
            ledger.record("customer_reply", experiment_id="exp-1", metrics={"sentiment": "INTERESTED"})
            summary = ledger.summarize_experiment("exp-1")
        self.assertEqual(summary["event_count"], 2)
        self.assertTrue(summary["outcomes_observed"])
        self.assertNotEqual(summary["events"][0]["event_id"], summary["events"][1]["event_id"])

    def test_generated_cycle_without_customer_outcome_is_not_mistaken_for_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = OutcomeLedger(Path(tmp))
            ledger.record("gtm_cycle_generated", experiment_id="exp-2")
            mentor = ASCMProactiveMentor.__new__(ASCMProactiveMentor)
            mentor.repo_analyzer = mock.Mock()
            mentor.repo_analyzer.analyze.return_value = {"test_count": 0, "file_count": 0}
            mentor.git_monitor = mock.Mock()
            mentor.git_monitor.measure_gtm_activity.return_value = mock.Mock(
                days_since_last_gtm_action=None, risk_level="UNKNOWN"
            )
            mentor.git_monitor.get_latest_milestone.return_value = None
            mentor.outcome_ledger = ledger
            advice = mentor.evaluate_code_progress_and_advise()
        self.assertEqual(advice["gtm_outcome_feedback"]["status"], "awaiting_outcomes")
        self.assertEqual(advice["gtm_outcome_feedback"]["verified_outcomes"], 0)
        self.assertIn("no customer replies", advice["outcome_recommendation"].lower())


    def test_verified_outcome_notification_is_sent_without_storing_reply_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("orchestrator.mentor.notifier.CrossPlatformNotifier.notify", return_value=True) as notify:
                event = OutcomeLedger(Path(tmp)).record(
                    "customer_reply", experiment_id="exp-3",
                    metrics={"sentiment": "INTERESTED"}, notify=True,
                )
            notify.assert_called_once()
            self.assertEqual(event["event_type"], "customer_reply")
            serialized = json.dumps(OutcomeLedger(Path(tmp)).recent_events())
            self.assertNotIn("email@example.com", serialized)

    def test_old_unattributed_cycle_triggers_limited_reminder(self):
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as tmp:
            ledger = OutcomeLedger(Path(tmp))
            old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
            ledger.record("gtm_cycle_generated", experiment_id="exp-old", occurred_at=old)
            mentor = ASCMProactiveMentor.__new__(ASCMProactiveMentor)
            mentor.repo_analyzer = mock.Mock()
            mentor.repo_analyzer.analyze.return_value = {"test_count": 0, "file_count": 0}
            mentor.git_monitor = mock.Mock()
            mentor.git_monitor.measure_gtm_activity.return_value = mock.Mock(
                days_since_last_gtm_action=None, risk_level="UNKNOWN"
            )
            mentor.git_monitor.get_latest_milestone.return_value = None
            mentor.outcome_ledger = ledger
            mentor._last_outcome_notify = 0
            with mock.patch.dict("os.environ", {"ASCM_OUTCOME_REMINDER_HOURS": "24"}), \
                 mock.patch.object(mentor, "notify") as notify:
                advice = mentor.evaluate_code_progress_and_advise()
            self.assertEqual(advice["gtm_outcome_feedback"]["unattributed_cycles_due"][0]["experiment_id"], "exp-old")
            notify.assert_called_once()

    def test_reviewed_or_stopped_experiment_does_not_keep_reminding(self):
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as tmp:
            ledger = OutcomeLedger(Path(tmp))
            old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
            ledger.record("gtm_cycle_generated", experiment_id="exp-reviewed", occurred_at=old)
            ledger.record("experiment_stopped", experiment_id="exp-reviewed")
            mentor = ASCMProactiveMentor.__new__(ASCMProactiveMentor)
            mentor.repo_analyzer = mock.Mock()
            mentor.repo_analyzer.analyze.return_value = {"test_count": 0, "file_count": 0}
            mentor.git_monitor = mock.Mock()
            mentor.git_monitor.measure_gtm_activity.return_value = mock.Mock(
                days_since_last_gtm_action=None, risk_level="UNKNOWN"
            )
            mentor.git_monitor.get_latest_milestone.return_value = None
            mentor.outcome_ledger = ledger
            mentor._last_outcome_notify = 0
            with mock.patch.dict("os.environ", {"ASCM_OUTCOME_REMINDER_HOURS": "24"}), \\
                 mock.patch.object(mentor, "notify") as notify:
                advice = mentor.evaluate_code_progress_and_advise()
            self.assertEqual(advice["gtm_outcome_feedback"]["unattributed_cycles_due"], [])
            notify.assert_not_called()

    def test_rejects_generated_copy_as_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                OutcomeLedger(Path(tmp)).record("generated_copy", experiment_id="exp-1")


if __name__ == "__main__":
    unittest.main()

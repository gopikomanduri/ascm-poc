import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.gtm.strategy.proactive_monitor import ProactiveGitMonitor
from orchestrator.mentor.proactive_mentor import ASCMProactiveMentor
from orchestrator.gtm.agents.sales_agent import SalesAgent


class ProactiveMonitorRegressionTests(unittest.TestCase):
    def test_missing_gtm_history_is_unknown_not_999_days_or_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = ProactiveGitMonitor(tmp)
            with mock.patch.object(monitor, "get_commit_count_7d", return_value=20), \
                 mock.patch.object(monitor, "get_commits_today", return_value=0), \
                 mock.patch.object(monitor, "get_last_commit_time", return_value=None):
                metrics = monitor.measure_gtm_activity()
            self.assertIsNone(metrics.days_since_last_gtm_action)
            self.assertEqual(metrics.risk_level, "UNKNOWN")
            self.assertFalse(metrics.is_code_avoidance)
            self.assertFalse(monitor.should_block_git_push(metrics))
            self.assertIn("not recorded", monitor.generate_intervention_message(metrics))

    def test_recorded_gtm_event_is_used_for_activity_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = ProactiveGitMonitor(tmp)
            monitor.record_gtm_event("customer_contact", occurred_at="2026-10-10T12:00:00+00:00")
            with mock.patch.object(monitor, "get_commit_count_7d", return_value=0), \
                 mock.patch.object(monitor, "get_commits_today", return_value=0), \
                 mock.patch.object(monitor, "get_last_commit_time", return_value=None):
                metrics = monitor.measure_gtm_activity()
            self.assertIsNotNone(metrics.days_since_last_gtm_action)
            self.assertGreaterEqual(metrics.days_since_last_gtm_action, 0)
            self.assertNotEqual(metrics.risk_level, "UNKNOWN")

    def test_explicit_milestone_is_persisted_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = ProactiveGitMonitor(tmp)
            recorded = monitor.record_milestone("MVP beta ready", occurred_at="2026-10-11T12:00:00+00:00")
            self.assertEqual(recorded["name"], "MVP beta ready")
            self.assertEqual(monitor.get_latest_milestone()["name"], "MVP beta ready")

    def test_mentor_triggers_only_with_explicit_milestone_and_known_gtm_age(self):
        mentor = ASCMProactiveMentor.__new__(ASCMProactiveMentor)
        mentor.repo_analyzer = mock.Mock()
        mentor.repo_analyzer.analyze.return_value = {"test_count": 1, "file_count": 1}
        metrics = mock.Mock(days_since_last_gtm_action=3.5, risk_level="HIGH")
        mentor.git_monitor = mock.Mock()
        mentor.git_monitor.measure_gtm_activity.return_value = metrics
        mentor.git_monitor.get_latest_milestone.return_value = {"name": "MVP beta ready"}
        mentor._last_sell_notify = 0
        with mock.patch.object(mentor, "notify") as notify:
            advice = mentor.evaluate_code_progress_and_advise()
        self.assertTrue(advice["should_trigger_gtm"])
        self.assertEqual(advice["milestone"]["name"], "MVP beta ready")
        notify.assert_called_once()

    def test_actual_sales_reply_is_recorded_without_storing_reply_text(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                agent = SalesAgent.__new__(SalesAgent)
                agent.call = lambda prompt, json_mode=True: json.dumps({
                    "sentiment": "INTERESTED", "next_action": "queue_review"
                })
                result = agent.classify_reply_and_route(
                    "Thanks, let's talk next week.", "Prospect", "prospect@example.com"
                )
                self.assertEqual(result["sentiment"], "INTERESTED")
                events = json.loads(Path(".ascm_history/gtm_activity.json").read_text())
                self.assertEqual(events[-1]["event_type"], "customer_reply")
                self.assertEqual(events[-1]["details"]["sentiment"], "INTERESTED")
                self.assertNotIn("prospect@example.com", json.dumps(events))
                self.assertNotIn("let's talk", json.dumps(events))
            finally:
                os.chdir(previous)

    def test_invalid_event_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ProactiveGitMonitor(tmp).record_gtm_event("generated_copy")

    def test_mentor_does_not_trigger_when_history_is_unknown(self):
        mentor = ASCMProactiveMentor.__new__(ASCMProactiveMentor)
        mentor.repo_analyzer = mock.Mock()
        mentor.repo_analyzer.analyze.return_value = {"test_count": 100, "file_count": 100}
        metrics = mock.Mock(days_since_last_gtm_action=None, risk_level="UNKNOWN")
        mentor.git_monitor = mock.Mock()
        mentor.git_monitor.measure_gtm_activity.return_value = metrics
        mentor.git_monitor.get_latest_milestone.return_value = None
        mentor._last_sell_notify = 0
        with mock.patch.object(mentor, "notify") as notify:
            advice = mentor.evaluate_code_progress_and_advise()
        self.assertFalse(advice["should_trigger_gtm"])
        self.assertFalse(advice["gtm_history_known"])
        self.assertIn("unknown", advice["recommendation"].lower())
        notify.assert_not_called()


if __name__ == "__main__":
    unittest.main()

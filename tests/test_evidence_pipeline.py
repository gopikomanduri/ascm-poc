import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from orchestrator.mentor.evidence_pipeline import EvidenceSourceConnector, InterventionQualityTracker


class EvidenceSourceConnectorTests(unittest.TestCase):
    def test_customer_evidence_uses_only_recent_recorded_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / ".ascm_history"
            history.mkdir()
            now = datetime.now(timezone.utc)
            events = [
                {"event_id": "reply-1", "event_type": "customer_reply",
                 "occurred_at": now.isoformat(), "metrics": {"sentiment": "interested"}},
                {"event_id": "reply-2", "event_type": "customer_reply",
                 "occurred_at": now.isoformat(), "metrics": {"sentiment": "positive"}},
                {"event_id": "reply-3", "event_type": "customer_reply",
                 "occurred_at": now.isoformat(), "metrics": {"sentiment": "interested"}},
                {"event_id": "old-conversion", "event_type": "conversion",
                 "occurred_at": (now - timedelta(days=120)).isoformat(), "metrics": {}},
                {"event_id": "generated", "event_type": "gtm_cycle_generated",
                 "occurred_at": now.isoformat(), "metrics": {}},
            ]
            (history / "gtm_outcomes.json").write_text(json.dumps(events), encoding="utf-8")
            result = EvidenceSourceConnector(tmp).customer_demand_evidence()
            self.assertEqual(result["event_count"], 3)
            self.assertEqual(result["positive_reply_count"], 3)
            self.assertTrue(result["user_demand_verified"])
            self.assertNotIn("old-conversion", result["evidence_event_ids"])
            self.assertNotIn("generated", result["evidence_event_ids"])

    def test_task_scoped_demand_ignores_unrelated_feature_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / ".ascm_history"
            history.mkdir()
            now = datetime.now(timezone.utc).isoformat()
            events = [
                {"event_id": "invoice-1", "event_type": "customer_reply",
                 "occurred_at": now, "metrics": {"sentiment": "interested", "feature_key": "invoice-automation"}},
                {"event_id": "invoice-2", "event_type": "customer_reply",
                 "occurred_at": now, "metrics": {"sentiment": "positive", "feature_key": "invoice-automation"}},
                {"event_id": "invoice-3", "event_type": "customer_reply",
                 "occurred_at": now, "metrics": {"sentiment": "interested", "feature_key": "invoice-automation"}},
                {"event_id": "unrelated-1", "event_type": "conversion",
                 "occurred_at": now, "metrics": {"feature_key": "analytics-dashboard"}},
                {"event_id": "untagged-1", "event_type": "qualified_opportunity",
                 "occurred_at": now, "metrics": {}},
            ]
            (history / "gtm_outcomes.json").write_text(json.dumps(events), encoding="utf-8")
            connector = EvidenceSourceConnector(tmp)
            result = connector.customer_demand_evidence(task_description="Build invoice automation")
            self.assertTrue(result["user_demand_verified"])
            self.assertEqual(result["event_count"], 3)
            self.assertEqual(result["unscoped_or_unmatched_events_ignored"], 2)
            self.assertEqual(set(result["evidence_event_ids"]), {"invoice-1", "invoice-2", "invoice-3"})
            unrelated = connector.customer_demand_evidence(task_description="Build a billing dashboard")
            self.assertFalse(unrelated["user_demand_verified"])
            self.assertEqual(unrelated["event_count"], 0)

    def test_remote_repo_discovery_is_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            "os.environ", {"ASCM_ENABLE_REUSE_DISCOVERY": "0"}, clear=False
        ):
            result = EvidenceSourceConnector(tmp).reuse_candidates("authentication")
            self.assertFalse(result["enabled"])
            self.assertEqual(result["repositories"], [])

    def test_repository_suitability_penalizes_archived_and_unknown_license(self):
        repo = {
            "name": "org/project", "stars": 10000, "archived": True,
            "license": "Not detected", "last_updated": "2020-01-01T00:00:00Z",
        }
        result = EvidenceSourceConnector._score_repository(repo)
        self.assertLess(result["suitability_score"], 30)
        self.assertTrue(result["suitability_is_heuristic"])
        self.assertTrue(any("archived" in reason for reason in result["suitability_reasons"]))


class InterventionQualityTrackerTests(unittest.TestCase):
    def test_feedback_and_report_only_count_explicit_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            shown = tracker.record_shown(
                session_id="session-a", project_id="project-a",
                recommendation={"recommended_path": "customer_validate", "confidence": "medium"},
                evidence_event_ids=["edit-1"],
            )
            report = tracker.report("session-a")
            self.assertEqual(report["interventions_shown"], 1)
            self.assertEqual(report["interventions_reviewed"], 0)
            self.assertIsNone(report["positive_feedback_rate"])

            tracker.record_feedback(
                feedback="acted_on", intervention_id=shown["intervention_id"],
                outcome_note="Founder acted on advice; note content must not be stored",
            )
            report = tracker.report("session-a")
            self.assertEqual(report["interventions_reviewed"], 1)
            self.assertEqual(report["positive_feedback_rate"], 1.0)
            saved = json.loads(tracker.path.read_text(encoding="utf-8"))
            self.assertNotIn("outcome_note", saved[0])
            self.assertEqual(saved[0]["outcome_note_length"], len(
                "Founder acted on advice; note content must not be stored"
            ))

    def test_report_breaks_quality_down_by_recommended_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            first = tracker.record_shown(
                session_id="session-a", project_id="project-a",
                recommendation={"recommended_path": "reuse", "confidence": "medium"},
            )
            tracker.record_shown(
                session_id="session-a", project_id="project-a",
                recommendation={"recommended_path": "reuse", "confidence": "low"},
            )
            tracker.record_feedback(feedback="acted_on", intervention_id=first["intervention_id"])
            report = tracker.report("session-a")
            self.assertEqual(report["by_recommended_path"]["reuse"]["reviewed"], 1)
            self.assertEqual(report["by_recommended_path"]["reuse"]["positive_feedback_rate"], 1.0)

    def test_feedback_rejects_unknown_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            with self.assertRaises(ValueError):
                tracker.record_feedback(feedback="great", intervention_id="missing")


if __name__ == "__main__":
    unittest.main()

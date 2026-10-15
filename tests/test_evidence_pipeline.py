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

    def test_task_scoped_demand_ignores_unrelated_feature_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / ".ascm_history"
            history.mkdir()
            now = datetime.now(timezone.utc).isoformat()
            events = [
                {"event_id": "auth-demand", "event_type": "feature_request",
                 "occurred_at": now, "metrics": {"feature_key": "authentication", "demand_signal": "strong"}},
                {"event_id": "billing-demand", "event_type": "pilot_commitment",
                 "occurred_at": now, "metrics": {"feature_key": "billing", "demand_signal": "strong"}},
            ]
            (history / "gtm_outcomes.json").write_text(json.dumps(events), encoding="utf-8")
            connector = EvidenceSourceConnector(tmp)
            auth = connector.customer_demand_evidence(task_description="Implement authentication")
            self.assertEqual(auth["event_count"], 1)
            self.assertTrue(auth["user_demand_verified"])
            self.assertEqual(auth["evidence_event_ids"], ["auth-demand"])
            billing = connector.customer_demand_evidence(task_description="Improve invoice billing")
            self.assertEqual(billing["event_count"], 1)
            self.assertEqual(billing["evidence_event_ids"], ["billing-demand"])

    def test_product_feature_key_and_aliases_scope_customer_demand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ascm_product.json").write_text(json.dumps({
                "feature_key": "invoice-automation",
                "feature_aliases": ["billing workflow"],
            }), encoding="utf-8")
            history = root / ".ascm_history"
            history.mkdir()
            now = datetime.now(timezone.utc).isoformat()
            (history / "gtm_outcomes.json").write_text(json.dumps([
                {"event_id": "alias-demand", "event_type": "pilot_commitment",
                 "occurred_at": now, "metrics": {"feature_key": "billing workflow"}},
                {"event_id": "other-demand", "event_type": "conversion",
                 "occurred_at": now, "metrics": {"feature_key": "analytics"}},
            ]), encoding="utf-8")
            evidence = EvidenceSourceConnector(root).collect("Implement an unfamiliar internal component")
        summary = evidence["customer_evidence_summary"]
        self.assertEqual(summary["feature_scope"], "invoice-automation")
        self.assertEqual(summary["event_count"], 1)
        self.assertTrue(summary["user_demand_verified"])
        self.assertEqual(summary["evidence_event_ids"], ["alias-demand"])

    def test_relevance_rank_contributes_to_candidate_triage_score(self):
        recent = datetime.now(timezone.utc).isoformat()
        base = {
            "name": "org/project", "stars": 100, "archived": False,
            "license": "MIT", "last_updated": recent,
        }
        first = EvidenceSourceConnector._score_repository({**base, "search_rank": 0})
        fifth = EvidenceSourceConnector._score_repository({**base, "search_rank": 4})
        self.assertGreater(first["suitability_score"], fifth["suitability_score"])
        self.assertTrue(any("relevance-based" in reason for reason in first["suitability_reasons"]))

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

    def test_report_segments_feedback_by_evidence_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            evidence_rich = tracker.record_shown(
                session_id="session-evidence",
                project_id="project-a",
                recommendation={"recommended_path": "reuse", "confidence": "medium"},
                evidence_summary={
                    "customer": {"event_count": 4, "user_demand_verified": True},
                    "reuse": {"enabled": True, "candidate_count": 2},
                },
            )
            evidence_sparse = tracker.record_shown(
                session_id="session-evidence",
                project_id="project-a",
                recommendation={"recommended_path": "customer_validate", "confidence": "low"},
                evidence_summary={
                    "customer": {"event_count": 0, "user_demand_verified": False},
                    "reuse": {"enabled": False, "candidate_count": 0},
                },
            )
            tracker.record_feedback(feedback="acted_on", intervention_id=evidence_rich["intervention_id"])
            tracker.record_feedback(feedback="not_helpful", intervention_id=evidence_sparse["intervention_id"])

            report = tracker.report("session-evidence")
            self.assertEqual(report["feedback_coverage"], 1.0)
            self.assertEqual(len(report["by_evidence_profile"]), 2)
            rich = report["by_evidence_profile"]["demand_verified|reuse_candidates_found"]
            self.assertEqual(rich["positive_feedback_rate"], 1.0)
            self.assertEqual(rich["reviewed"], 1)
            sparse = report["by_evidence_profile"]["demand_unknown|reuse_search_disabled_or_unavailable"]
            self.assertEqual(sparse["positive_feedback_rate"], 0.0)
            self.assertEqual(sparse["reviewed"], 1)

    def test_feedback_is_immutable_after_first_rating(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            shown = tracker.record_shown(
                session_id="session-immutable",
                project_id="project-a",
                recommendation={"recommended_path": "reuse", "confidence": "medium"},
            )
            tracker.record_feedback(
                feedback="helpful",
                intervention_id=shown["intervention_id"],
            )
            with self.assertRaisesRegex(ValueError, "already has feedback"):
                tracker.record_feedback(
                    feedback="incorrect",
                    intervention_id=shown["intervention_id"],
                )
            report = tracker.report("session-immutable")
            self.assertEqual(report["feedback_counts"]["helpful"], 1)
            self.assertEqual(report["feedback_counts"]["incorrect"], 0)

    def test_feedback_rejects_unknown_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            with self.assertRaises(ValueError):
                tracker.record_feedback(feedback="great", intervention_id="missing")


    def test_legacy_or_unconfirmed_delivery_cannot_be_rated_or_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = InterventionQualityTracker(tmp)
            tracker.path.parent.mkdir(parents=True, exist_ok=True)
            tracker.path.write_text(json.dumps([
                {"intervention_id": "legacy", "session_id": "s", "feedback": None},
                {"intervention_id": "not-delivered", "session_id": "s",
                 "delivery_confirmed": False, "feedback": None},
                {"intervention_id": "delivered", "session_id": "s",
                 "delivery_confirmed": True, "feedback": None},
            ]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "delivery was not confirmed"):
                tracker.record_feedback(feedback="helpful", intervention_id="legacy")
            with self.assertRaisesRegex(ValueError, "delivery was not confirmed"):
                tracker.record_feedback(feedback="helpful", intervention_id="not-delivered")
            result = tracker.record_feedback(feedback="helpful", intervention_id="delivered")
            self.assertEqual(result["intervention_id"], "delivered")
            report = tracker.report("s")
            self.assertEqual(report["interventions_shown"], 1)
            self.assertEqual(report["delivery_unconfirmed"], 2)
            self.assertEqual(report["interventions_reviewed"], 1)


if __name__ == "__main__":
    unittest.main()

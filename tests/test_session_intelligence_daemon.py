import tempfile
import time
from pathlib import Path
from unittest import mock

from orchestrator.mentor.daemon import UniversalASCMDaemon


class _Context:
    def load(self):
        return {"current_goal": "Validate customer demand for invoice automation"}


class _Fusion:
    def __init__(self, now):
        self.now = now

    def latest_project_path(self):
        return Path(".")

    def infer_context(self, project_path=None):
        return {
            "task_hypothesis": "Implement internal caching engine",
            "confidence": 0.88,
            "evidence_event_ids": ["edit-1", "terminal-1"],
            "rationale": "Recent edits and terminal activity align.",
            "project_id": "project-a",
        }

    def _read_events(self):
        stamp = __import__("datetime").datetime.fromtimestamp(
            self.now, __import__("datetime").timezone.utc
        ).isoformat()
        return [
            {"event_id": "edit-1", "timestamp": stamp, "event_type": "file_changed", "project_id": "project-a"},
            {"event_id": "terminal-1", "timestamp": stamp, "event_type": "terminal_command", "project_id": "project-a"},
        ]


class _Mentor:
    def __init__(self):
        self.founder_context = _Context()
        self.evidence = None

    def recommend_next_action(self, observation, evidence):
        self.evidence = evidence
        return {
            "actions": [],
            "founder_decision": {
                "recommended_path": "customer_validate",
                "confidence": "medium",
                "ranked_paths": [
                    {"path": "customer_validate", "score": 75},
                    {"path": "simplify", "score": 70},
                    {"path": "reuse", "score": 55},
                ],
                "missing_evidence": ["customer_evidence"],
            },
        }


def test_daemon_surfaces_goal_drift_session_coverage_and_usefulness_feedback():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        daemon = UniversalASCMDaemon.__new__(UniversalASCMDaemon)
        daemon.repo_path = Path(tmp)
        daemon.history_dir = Path(tmp) / ".ascm_history"
        daemon.history_dir.mkdir(parents=True)
        daemon.context_fusion = _Fusion(now)
        daemon.mentor = _Mentor()
        daemon.audit_logger = mock.Mock()
        daemon.evidence_sources = mock.Mock()
        daemon.evidence_sources.collect.return_value = {
            "customer_evidence": None,
            "user_demand_verified": False,
            "customer_evidence_summary": {"event_count": 0, "user_demand_verified": False},
            "reuse_candidates": [],
            "reuse_evidence_summary": {"enabled": False, "candidate_count": 0},
        }
        daemon.intervention_tracker = mock.Mock()

        with mock.patch(
            "orchestrator.mentor.daemon.CrossPlatformNotifier.notify", return_value=True
        ) as notify:
            daemon._prompt_for_founder_context(
                {"filesystem_activity": {"recently_edited_files": []}}, {}, now
            )

        message = notify.call_args.args[1]
        assert "Observed activity (not confirmed intent)" in message
        assert "Goal alignment: challenge" in message
        assert "Mentor challenge: Possible goal drift" in message
        assert "Observed sources this session" in message
        assert "--feedback helpful" in message
        assert "not_helpful instead of helpful" in message
        assert daemon.mentor.evidence["goal_alignment"]["alignment_status"] == "challenge"
        assert daemon.mentor.evidence["session_signal_coverage"]["cross_signal_context"] is True
        details = daemon.audit_logger.log_event.call_args.kwargs["details"]
        assert details["goal_alignment"] == "challenge"
        assert set(details["session_sources"]) == {"terminal", "vscode_or_filesystem"}

"""Evidence connectors and intervention-quality measurement for ASCM.

Customer evidence is derived only from recorded outcome-ledger events. Public
GitHub discovery is opt-in because task descriptions may contain private context.
Scores are triage heuristics, never suitability/security endorsements.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


CUSTOMER_OUTCOMES = {"customer_reply", "meeting_booked", "qualified_opportunity", "conversion"}
POSITIVE_SENTIMENTS = {"interested", "positive"}
FEEDBACK_LABELS = {"helpful", "not_helpful", "accepted", "dismissed", "acted_on", "incorrect"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


class EvidenceSourceConnector:
    """Build privacy-minimized customer and optional public-repository evidence."""

    def __init__(self, project_path: str | Path = "."):
        self.project_path = Path(project_path).resolve()
        self.history_dir = self.project_path / ".ascm_history"

    def customer_demand_evidence(self, window_days: int = 90) -> dict[str, Any]:
        """Summarize only explicitly recorded customer outcome events."""
        events = _read_json(self.history_dir / "gtm_outcomes.json", [])
        if not isinstance(events, list):
            events = []
        cutoff = _now() - timedelta(days=window_days)
        recent = []
        for event in events:
            if not isinstance(event, dict) or event.get("event_type") not in CUSTOMER_OUTCOMES:
                continue
            occurred = _parse_time(event.get("occurred_at"))
            if occurred and occurred >= cutoff:
                recent.append(event)
        counts = {kind: sum(e.get("event_type") == kind for e in recent) for kind in sorted(CUSTOMER_OUTCOMES)}
        positive_replies = sum(
            e.get("event_type") == "customer_reply"
            and str((e.get("metrics") or {}).get("sentiment", "")).lower() in POSITIVE_SENTIMENTS
            for e in recent
        )
        qualified = counts["qualified_opportunity"]
        conversions = counts["conversion"]
        # Conservative explicit evidence threshold; not a statistical PMF claim.
        demand_signal = conversions > 0 or qualified > 0 or positive_replies >= 3
        if not recent:
            summary = None
        else:
            summary = (
                f"{len(recent)} recorded customer outcome event(s) in the last {window_days} days: "
                f"{positive_replies} positive/interested replies, {counts['meeting_booked']} meetings, "
                f"{qualified} qualified opportunities, {conversions} conversions."
            )
        return {
            "source": "local_gtm_outcome_ledger",
            "window_days": window_days,
            "event_count": len(recent),
            "event_counts": counts,
            "positive_reply_count": positive_replies,
            "customer_evidence": summary,
            "user_demand_verified": bool(demand_signal),
            "demand_signal_rule": "At least one qualified opportunity/conversion or three positive/interested replies in the selected window.",
            "evidence_event_ids": [str(e.get("event_id")) for e in recent[-50:] if e.get("event_id")],
            "limitation": "Recorded outcomes are a sample, not proof of overall product-market fit; missing events are not negative demand.",
        }

    @staticmethod
    def _score_repository(repo: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
        now = now or _now()
        reasons = []
        score = 50
        if repo.get("archived"):
            score -= 45
            reasons.append("archived repository is a major maintenance risk")
        else:
            reasons.append("repository is not marked archived")
        license_name = str(repo.get("license") or "Not detected")
        if license_name.lower() in {"not detected", "none", "unknown"}:
            score -= 20
            reasons.append("license was not detected; compatibility is unknown")
        else:
            reasons.append(f"license metadata detected ({license_name}); compatibility still needs legal review")
        stars = repo.get("stars", 0)
        try:
            score += min(15, max(0, int(math.log10(max(0, int(stars)) + 1) * 5)))
        except (TypeError, ValueError):
            pass
        pushed = _parse_time(repo.get("last_updated"))
        if pushed is None:
            score -= 10
            reasons.append("last push date is unavailable")
        else:
            age_days = max(0, (now - pushed).days)
            if age_days <= 90:
                score += 15
                reasons.append("recently updated within 90 days")
            elif age_days <= 365:
                score += 5
                reasons.append("updated within the last year")
            else:
                score -= 15
                reasons.append("no push in over a year")
        return {
            **repo,
            "suitability_score": max(0, min(100, score)),
            "suitability_reasons": reasons,
            "suitability_is_heuristic": True,
            "required_checks": [
                "API/feature fit", "license compatibility", "security advisories",
                "transitive dependencies", "release cadence", "integration and migration cost",
            ],
        }

    def reuse_candidates(self, task_description: str, limit: int = 5) -> dict[str, Any]:
        """Query public GitHub only when explicitly enabled by the operator."""
        if os.getenv("ASCM_ENABLE_REUSE_DISCOVERY", "0").strip() != "1":
            return {
                "source": "github_public_search",
                "enabled": False,
                "repositories": [],
                "error": None,
                "caveat": "Remote discovery is disabled. Set ASCM_ENABLE_REUSE_DISCOVERY=1 to send the task description to GitHub Search.",
            }
        try:
            from orchestrator.mentor.reuse_advisor import GitHubRepositoryAdvisor
            result = GitHubRepositoryAdvisor(timeout=5.0).search(task_description, limit=limit)
        except Exception as exc:
            return {
                "source": "github_public_search",
                "enabled": True,
                "repositories": [],
                "error": f"Repository discovery failed: {type(exc).__name__}",
                "caveat": "No candidate was inferred because public repository discovery failed.",
            }
        repositories = [
            self._score_repository(item)
            for item in result.get("repositories", [])
            if isinstance(item, dict)
        ]
        repositories.sort(key=lambda item: item["suitability_score"], reverse=True)
        return {
            "source": "github_public_search",
            "enabled": True,
            "repositories": repositories,
            "error": result.get("error"),
            "query": result.get("query"),
            "caveat": result.get("caveat", "Candidates require human review; score is not an endorsement."),
        }

    def collect(self, task_description: str) -> dict[str, Any]:
        demand = self.customer_demand_evidence()
        reuse = self.reuse_candidates(task_description) if task_description.strip() else {
            "source": "github_public_search", "enabled": False, "repositories": [],
            "caveat": "No task description was available; no search was attempted.",
        }
        evidence: dict[str, Any] = {
            "customer_evidence": demand["customer_evidence"],
            "user_demand_verified": demand["user_demand_verified"],
            "customer_evidence_summary": demand,
            "reuse_candidates": reuse["repositories"],
            "reuse_evidence_summary": {
                key: value for key, value in reuse.items() if key != "repositories"
            },
        }
        return evidence


class InterventionQualityTracker:
    """Persist shown interventions and founder feedback for session-level evaluation."""

    def __init__(self, project_path: str | Path = "."):
        self.project_path = Path(project_path).resolve()
        self.path = self.project_path / ".ascm_history" / "intervention_quality.json"

    def _read(self) -> list[dict[str, Any]]:
        value = _read_json(self.path, [])
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def record_shown(
        self, *, session_id: str, project_id: str | None, recommendation: dict[str, Any],
        evidence_event_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        intervention = {
            "intervention_id": str(uuid.uuid4()),
            "session_id": str(session_id)[:128],
            "project_id": str(project_id or "")[:128],
            "shown_at": _now().isoformat(),
            "recommended_path": str(recommendation.get("recommended_path", "undetermined"))[:80],
            "confidence": str(recommendation.get("confidence", "unknown"))[:24],
            "evidence_event_ids": [str(item)[:128] for item in (evidence_event_ids or [])[:50]],
            "feedback": None,
            "feedback_at": None,
            "outcome_note_length": 0,
        }
        events = self._read()
        events.append(intervention)
        _atomic_write(self.path, events[-5000:])
        return intervention

    def record_feedback(
        self, *, feedback: str, intervention_id: str | None = None,
        outcome_note: str = "",
    ) -> dict[str, Any]:
        if feedback not in FEEDBACK_LABELS:
            raise ValueError(f"feedback must be one of: {', '.join(sorted(FEEDBACK_LABELS))}")
        events = self._read()
        target = None
        for item in reversed(events):
            if intervention_id and item.get("intervention_id") == intervention_id:
                target = item
                break
            if not intervention_id and item.get("feedback") is None:
                target = item
                break
        if target is None:
            raise ValueError("No matching unreviewed intervention found")
        target["feedback"] = feedback
        target["feedback_at"] = _now().isoformat()
        # Store only length, never the note itself; avoid capturing customer or source details.
        target["outcome_note_length"] = min(2000, len(outcome_note.strip()))
        _atomic_write(self.path, events[-5000:])
        return {
            "intervention_id": target["intervention_id"],
            "feedback": feedback,
            "feedback_at": target["feedback_at"],
        }

    def report(self, session_id: str | None = None) -> dict[str, Any]:
        events = self._read()
        if session_id:
            events = [e for e in events if e.get("session_id") == session_id]
        reviewed = [e for e in events if e.get("feedback") in FEEDBACK_LABELS]
        counts = {label: sum(e.get("feedback") == label for e in reviewed) for label in sorted(FEEDBACK_LABELS)}
        helpful = counts["helpful"] + counts["accepted"] + counts["acted_on"]
        not_helpful = counts["not_helpful"] + counts["dismissed"] + counts["incorrect"]
        total = helpful + not_helpful
        return {
            "session_id": session_id,
            "interventions_shown": len(events),
            "interventions_reviewed": len(reviewed),
            "unreviewed": len(events) - len(reviewed),
            "feedback_counts": counts,
            "positive_feedback_rate": round(helpful / total, 4) if total else None,
            "negative_feedback_rate": round(not_helpful / total, 4) if total else None,
            "measurement_note": "Rates use only explicit reviewed feedback; unreviewed interventions are not counted as success or failure.",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record ASCM intervention feedback or report session quality.")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--feedback", choices=sorted(FEEDBACK_LABELS))
    parser.add_argument("--intervention-id")
    parser.add_argument("--latest", action="store_true", help="Apply feedback to the newest unreviewed intervention")
    parser.add_argument("--note", default="", help="Optional note; only its length is stored")
    parser.add_argument("--session-id")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    tracker = InterventionQualityTracker(args.project_path)
    if args.feedback:
        if args.latest and args.intervention_id:
            parser.error("Use either --latest or --intervention-id, not both")
        result = tracker.record_feedback(
            feedback=args.feedback,
            intervention_id=None if args.latest else args.intervention_id,
            outcome_note=args.note,
        )
        print(json.dumps(result, indent=2))
    if args.report or not args.feedback:
        print(json.dumps(tracker.report(session_id=args.session_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

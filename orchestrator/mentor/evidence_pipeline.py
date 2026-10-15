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
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


CUSTOMER_OUTCOMES = {
    "customer_reply", "customer_interview", "feature_request", "pilot_commitment",
    "waitlist_signup", "meeting_booked", "qualified_opportunity", "conversion",
}
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

    @staticmethod
    def _feature_key_matches(feature_key: Any, task_description: str) -> bool:
        """Require an explicit feature tag that matches the observed task."""
        if not isinstance(feature_key, str) or not feature_key.strip():
            return False
        normalize = lambda value: re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        key_phrase = normalize(feature_key)
        task_phrase = normalize(task_description)
        if not key_phrase or not task_phrase:
            return False
        if key_phrase in task_phrase:
            return True
        key_tokens = {token for token in key_phrase.split() if len(token) >= 3}
        task_tokens = set(task_phrase.split())
        return bool(key_tokens) and key_tokens.issubset(task_tokens)

    def customer_demand_evidence(
        self, window_days: int = 90, task_description: str | None = None
    ) -> dict[str, Any]:
        """Summarize recent recorded outcomes, optionally scoped to an explicitly tagged feature.

        A daemon task must not inherit demand from unrelated features in the same workspace.
        When task_description is supplied, only events with a matching metrics.feature_key count.
        """
        events = _read_json(self.history_dir / "gtm_outcomes.json", [])
        if not isinstance(events, list):
            events = []
        cutoff = _now() - timedelta(days=window_days)
        recent = []
        eligible_unscoped = 0
        for event in events:
            if not isinstance(event, dict) or event.get("event_type") not in CUSTOMER_OUTCOMES:
                continue
            occurred = _parse_time(event.get("occurred_at"))
            if not occurred or occurred < cutoff:
                continue
            if task_description is not None:
                metrics = event.get("metrics") if isinstance(event.get("metrics"), dict) else {}
                if not self._feature_key_matches(metrics.get("feature_key"), task_description):
                    eligible_unscoped += 1
                    continue
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
        explicit_strong = any(
            str((event.get("metrics") or {}).get("demand_signal", "")).lower() == "strong"
            or str((event.get("metrics") or {}).get("willingness_to_pay", "")).lower() == "confirmed"
            for event in recent
        )
        commitments = counts["pilot_commitment"] + counts["waitlist_signup"]
        demand_signal = explicit_strong or commitments > 0 or conversions > 0 or qualified > 0 or positive_replies >= 3
        if not recent:
            summary = None
        else:
            summary = (
                f"{len(recent)} feature-matched customer evidence event(s) in the last {window_days} days: "
                f"{positive_replies} positive/interested replies, {counts['customer_interview']} interviews, "
                f"{counts['feature_request']} feature requests, {commitments} pilot/waitlist commitments, "
                f"{counts['meeting_booked']} meetings, {qualified} qualified opportunities, {conversions} conversions."
            )
        return {
            "source": "local_gtm_outcome_ledger",
            "window_days": window_days,
            "feature_scope": task_description,
            "event_count": len(recent),
            "unscoped_or_unmatched_events_ignored": eligible_unscoped,
            "event_counts": counts,
            "positive_reply_count": positive_replies,
            "customer_evidence": summary,
            "user_demand_verified": bool(demand_signal),
            "demand_signal_rule": "Explicit strong demand, a pilot/waitlist commitment, a qualified opportunity/conversion, or at least three positive/interested replies matched to the feature key.",
            "evidence_event_ids": [str(e.get("event_id")) for e in recent[-50:] if e.get("event_id")],
            "limitation": (
                "Only explicitly tagged, task-matching outcomes count when task scope is supplied. "
                "Recorded outcomes are a sample, not proof of product-market fit; missing events are not negative demand."
            ),
        }

    @staticmethod
    def _score_repository(repo: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
        now = now or _now()
        reasons = []
        score = 50
        try:
            search_rank = max(0, int(repo.get("search_rank", 99)))
        except (TypeError, ValueError):
            search_rank = 99
        relevance_bonus = max(0, 12 - 3 * search_rank)
        score += relevance_bonus
        if relevance_bonus:
            reasons.append("ranked near the top of GitHub's relevance-based search results")
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
        # Metadata search results stay unverified until a founder records a
        # review against the exact canonical repository URL.
        from orchestrator.mentor.reuse_review import ReuseReviewLedger
        reviews = ReuseReviewLedger(self.project_path).all()
        repositories = []
        for rank, item in enumerate(result.get("repositories", [])):
            if not isinstance(item, dict):
                continue
            candidate = self._score_repository({**item, "search_rank": rank})
            url = candidate.get("url")
            review = reviews.get(url) if isinstance(url, str) else None
            if isinstance(review, dict):
                for flag in (
                    "feature_fit_verified", "license_compatible",
                    "security_reviewed", "integration_cost_estimated",
                ):
                    candidate[flag] = review.get(flag) is True
                candidate["human_review"] = {
                    "reviewer": review.get("reviewer"),
                    "reviewed_at": review.get("reviewed_at"),
                    "review_complete": review.get("review_complete") is True,
                }
            else:
                candidate["feature_fit_verified"] = False
                candidate["license_compatible"] = False
                candidate["security_reviewed"] = False
                candidate["integration_cost_estimated"] = False
                candidate["human_review"] = {"review_complete": False}
            repositories.append(candidate)
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
        demand = self.customer_demand_evidence(task_description=task_description)
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
        intervention_id: str | None = None,
        evidence_summary: dict[str, Any] | None = None,
        delivery_confirmed: bool = True,
    ) -> dict[str, Any]:
        # Keep only coarse evidence-source metadata. Do not copy task text, customer
        # notes, repository descriptions, URLs, or raw evidence into this ledger.
        evidence_summary = evidence_summary if isinstance(evidence_summary, dict) else {}
        customer = evidence_summary.get("customer") if isinstance(evidence_summary.get("customer"), dict) else {}
        reuse = evidence_summary.get("reuse") if isinstance(evidence_summary.get("reuse"), dict) else {}
        intervention = {
            "intervention_id": intervention_id or str(uuid.uuid4()),
            "session_id": str(session_id)[:128],
            "project_id": str(project_id or "")[:128],
            "attempted_at": _now().isoformat(),
            "delivery_confirmed": bool(delivery_confirmed),
            "recommended_path": str(recommendation.get("recommended_path", "undetermined"))[:80],
            "confidence": str(recommendation.get("confidence", "unknown"))[:24],
            "evidence_event_ids": [str(item)[:128] for item in (evidence_event_ids or [])[:50]],
            "evidence_snapshot": {
                "customer_event_count": max(0, min(100000, int(customer.get("event_count", 0) or 0))),
                "customer_demand_verified": customer.get("user_demand_verified") is True,
                "reuse_discovery_enabled": reuse.get("enabled") is True,
                "reuse_candidate_count": max(0, min(1000, int(reuse.get("candidate_count", 0) or 0))),
            },
            "feedback": None,
            "feedback_at": None,
            "outcome_note_length": 0,
        }
        events = self._read()
        if any(item.get("intervention_id") == intervention["intervention_id"] for item in events):
            raise ValueError("intervention_id must be unique")
        events.append(intervention)
        _atomic_write(self.path, events[-5000:])
        return intervention

    def record_feedback(
        self, *, feedback: str, intervention_id: str | None = None,
        outcome_note: str = "",
    ) -> dict[str, Any]:
        if feedback not in FEEDBACK_LABELS:
            raise ValueError(f"feedback must be one of: {', '.join(sorted(FEEDBACK_LABELS))}")
        if not isinstance(outcome_note, str):
            raise ValueError("outcome_note must be a string; note content is never persisted")
        events = self._read()
        target = None
        for item in reversed(events):
            if intervention_id and item.get("intervention_id") == intervention_id:
                target = item
                break
            if not intervention_id and item.get("feedback") is None and item.get("delivery_confirmed") is True:
                target = item
                break
        if target is None:
            raise ValueError("No matching unreviewed intervention found")
        if target.get("delivery_confirmed") is not True:
            raise ValueError("Cannot rate an intervention whose delivery was not confirmed")
        if target.get("feedback") in FEEDBACK_LABELS:
            raise ValueError("This intervention already has feedback; ratings are immutable to protect measurement integrity")
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
        shown = [e for e in events if e.get("delivery_confirmed") is True]
        delivery_unconfirmed = [e for e in events if e.get("delivery_confirmed") is not True]
        reviewed = [e for e in shown if e.get("feedback") in FEEDBACK_LABELS]
        counts = {label: sum(e.get("feedback") == label for e in reviewed) for label in sorted(FEEDBACK_LABELS)}
        helpful = counts["helpful"] + counts["accepted"] + counts["acted_on"]
        not_helpful = counts["not_helpful"] + counts["dismissed"] + counts["incorrect"]
        total = helpful + not_helpful
        by_path = {}
        for item in reviewed:
            path = str(item.get("recommended_path", "unknown"))
            bucket = by_path.setdefault(path, {"reviewed": 0, "positive": 0, "negative": 0})
            bucket["reviewed"] += 1
            if item.get("feedback") in {"helpful", "accepted", "acted_on"}:
                bucket["positive"] += 1
            elif item.get("feedback") in {"not_helpful", "dismissed", "incorrect"}:
                bucket["negative"] += 1
        for bucket in by_path.values():
            rated = bucket["positive"] + bucket["negative"]
            bucket["positive_feedback_rate"] = round(bucket["positive"] / rated, 4) if rated else None
            bucket["negative_feedback_rate"] = round(bucket["negative"] / rated, 4) if rated else None

        # Report how feedback varies with evidence coverage without treating a missing
        # signal as negative demand or counting unreviewed interventions as failures.
        by_evidence_profile: dict[str, dict[str, Any]] = {}
        for item in shown:
            snapshot = item.get("evidence_snapshot") if isinstance(item.get("evidence_snapshot"), dict) else {}
            customer_state = "demand_verified" if snapshot.get("customer_demand_verified") is True else (
                "customer_events_no_threshold" if int(snapshot.get("customer_event_count", 0) or 0) > 0
                else "demand_unknown"
            )
            reuse_state = "reuse_candidates_found" if int(snapshot.get("reuse_candidate_count", 0) or 0) > 0 else (
                "reuse_search_enabled_no_candidates" if snapshot.get("reuse_discovery_enabled") is True
                else "reuse_search_disabled_or_unavailable"
            )
            profile = customer_state + "|" + reuse_state
            bucket = by_evidence_profile.setdefault(profile, {"shown": 0, "reviewed": 0, "positive": 0, "negative": 0})
            bucket["shown"] += 1
            if item.get("feedback") in FEEDBACK_LABELS:
                bucket["reviewed"] += 1
                if item.get("feedback") in {"helpful", "accepted", "acted_on"}:
                    bucket["positive"] += 1
                else:
                    bucket["negative"] += 1
        for bucket in by_evidence_profile.values():
            rated = bucket["positive"] + bucket["negative"]
            bucket["feedback_coverage"] = round(bucket["reviewed"] / bucket["shown"], 4) if bucket["shown"] else None
            bucket["positive_feedback_rate"] = round(bucket["positive"] / rated, 4) if rated else None

        return {
            "session_id": session_id,
            "interventions_attempted": len(events),
            "interventions_shown": len(shown),
            "delivery_unconfirmed": len(delivery_unconfirmed),
            "interventions_reviewed": len(reviewed),
            "unreviewed": len(shown) - len(reviewed),
            "feedback_counts": counts,
            "by_recommended_path": by_path,
            "by_evidence_profile": by_evidence_profile,
            # Coverage measures reviewed interventions out of those actually shown.
            # Failed/unconfirmed delivery attempts cannot be rated by the founder and
            # should not depress session feedback coverage.
            "feedback_coverage": round(len(reviewed) / len(shown), 4) if shown else None,
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

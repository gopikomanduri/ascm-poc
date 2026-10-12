"""Small, privacy-conscious append-only ledger for GTM experiments and outcomes.

This JSON-backed implementation is suitable for a single local process. Use a transactional
database before enabling concurrent writers or multi-user deployments.
"""
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class OutcomeLedger:
    EVENT_TYPES = {
        "gtm_cycle_generated", "experiment_planned", "campaign_approved", "campaign_published",
        "email_sent", "customer_reply", "meeting_booked", "qualified_opportunity",
        "conversion", "experiment_reviewed", "experiment_stopped",
    }
    SOURCES = {"operator", "sales_agent", "publisher", "system", "api", "test"}
    METRIC_KEYS = {
        "sentiment", "reply_count", "meeting_count", "qualified_opportunity_count",
        "conversion_count", "revenue_amount", "currency", "channel",
        "days_to_reply", "response_time_hours", "source_system",
    }
    SENTIMENTS = {"interested", "not_interested", "neutral", "positive", "negative", "unknown"}

    def __init__(self, project_path: Path):
        self.history_dir = Path(project_path) / ".ascm_history"
        self.path = self.history_dir / "gtm_outcomes.json"

    def _read(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def record(self, event_type: str, *, experiment_id: Optional[str] = None,
               occurred_at: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None,
               source: str = "operator", notify: bool = False) -> Dict[str, Any]:
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unsupported outcome event type: {event_type}")
        if not isinstance(source, str) or source not in self.SOURCES:
            raise ValueError("source must be one of the supported source labels")
        if experiment_id is not None and (
            not isinstance(experiment_id, str) or not experiment_id.strip()
            or len(experiment_id) > 128 or "\n" in experiment_id or "\r" in experiment_id
        ):
            raise ValueError("experiment_id must be a short identifier, not free-form text")
        if metrics is not None and not isinstance(metrics, dict):
            raise ValueError("metrics must be a dictionary")
        safe_metrics = {}
        for key, value in (metrics or {}).items():
            if key not in self.METRIC_KEYS:
                raise ValueError(f"Unsupported metric key: {key}")
            if key == "sentiment":
                if not isinstance(value, str) or value.strip().lower() not in self.SENTIMENTS:
                    raise ValueError("sentiment must be a supported coarse label")
                safe_metrics[key] = value.strip().lower()
            elif key in {"currency", "channel", "source_system"}:
                if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
                    raise ValueError(f"{key} must be a short categorical label")
                safe_metrics[key] = value.strip()
            else:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"{key} must be a finite numeric metric")
                safe_metrics[key] = value
        timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed_timestamp.tzinfo is None:
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("occurred_at must be an offset-aware ISO timestamp") from None
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "experiment_id": experiment_id.strip() if experiment_id else None,
            "occurred_at": parsed_timestamp.astimezone(timezone.utc).isoformat(),
            "source": source,
            "metrics": safe_metrics,
        }
        self.history_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.history_dir.chmod(0o700)
        except OSError:
            pass
        events = self._read()
        events.append(event)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
        try:
            temp_path.chmod(0o600)
        except OSError:
            pass
        temp_path.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        if notify and event_type in {"customer_reply", "meeting_booked", "qualified_opportunity", "conversion"}:
            # Notification failure must never undo a successfully recorded event.
            try:
                from orchestrator.mentor.notifier import CrossPlatformNotifier
                next_step = {
                    "customer_reply": "Classify the response and decide the next human-reviewed action.",
                    "meeting_booked": "Prepare discovery questions and record the meeting outcome afterward.",
                    "qualified_opportunity": "Confirm qualification evidence and agree on the next step.",
                    "conversion": "Review the experiment and identify evidence supporting repetition.",
                }[event_type]
                CrossPlatformNotifier.notify(
                    "ASCM: GTM outcome recorded",
                    f"{event_type.replace('_', ' ').title()} recorded for {experiment_id or 'unassigned experiment'}. {next_step}",
                    app_name="ASCM Outcome Attribution",
                )
            except Exception:
                pass
        return event

    def recent_events(self, limit: int = 50):
        """Return newest events first for mentor context; never infer missing outcomes."""
        if limit < 1:
            raise ValueError("limit must be positive")
        return list(reversed(self._read()))[:limit]

    def summarize_experiment(self, experiment_id: str) -> Dict[str, Any]:
        events = [event for event in self._read() if event.get("experiment_id") == experiment_id]
        return {
            "experiment_id": experiment_id,
            "event_count": len(events),
            "events": events,
            "outcomes_observed": any(event.get("event_type") in {
                "customer_reply", "meeting_booked", "qualified_opportunity", "conversion"
            } for event in events),
        }


def main():
    """Record a verified GTM event from the command line; never infer outcomes from generated copy."""
    import argparse

    parser = argparse.ArgumentParser(description="Record a verified GTM event for an experiment.")
    parser.add_argument("--project-path", default=".", help="Project root containing .ascm_history")
    parser.add_argument("--event", required=True, choices=sorted(OutcomeLedger.EVENT_TYPES))
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source", default="operator")
    parser.add_argument("--metrics-json", default="{}", help="JSON object with privacy-safe event metrics")
    parser.add_argument("--no-notify", action="store_true", help="Suppress the desktop notification")
    parser.add_argument("--prompt-review", action="store_true", help="Open a prompt to review the recorded outcome")
    args = parser.parse_args()
    try:
        metrics = json.loads(args.metrics_json)
        if not isinstance(metrics, dict):
            raise ValueError("--metrics-json must decode to a JSON object")
        ledger = OutcomeLedger(Path(args.project_path))
        event = ledger.record(
            args.event, experiment_id=args.experiment_id, metrics=metrics, source=args.source,
            notify=not args.no_notify,
        )
        if args.prompt_review and args.event in {
            "customer_reply", "meeting_booked", "qualified_opportunity", "conversion"
        }:
            from orchestrator.mentor.notifier import CrossPlatformNotifier
            prompt = (
                f"Review outcome '{args.event}' for experiment '{args.experiment_id}'. "
                "What evidence explains this outcome, and what is the next action? "
                "Enter a brief, privacy-safe summary (do not include personal data)."
            )
            response = CrossPlatformNotifier.prompt_dialog(
                prompt, default_text="", title="ASCM: Review GTM Outcome"
            )
            if response:
                ledger.record(
                    "experiment_reviewed", experiment_id=args.experiment_id,
                    metrics={"review_note": response[:500], "reviewed_event": args.event},
                    source="founder_prompt",
                )
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()

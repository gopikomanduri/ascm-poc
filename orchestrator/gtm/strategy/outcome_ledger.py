"""Small, privacy-conscious append-only ledger for GTM experiments and outcomes.

This JSON-backed implementation is suitable for a single local process. Use a transactional
database before enabling concurrent writers or multi-user deployments.
"""
import json
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
               source: str = "operator") -> Dict[str, Any]:
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"Unsupported outcome event type: {event_type}")
        if metrics is not None and not isinstance(metrics, dict):
            raise ValueError("metrics must be a dictionary")
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "experiment_id": experiment_id,
            "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
            "source": source,
            "metrics": metrics or {},
        }
        self.history_dir.mkdir(parents=True, exist_ok=True)
        events = self._read()
        events.append(event)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
        temp_path.replace(self.path)
        return event

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
    args = parser.parse_args()
    try:
        metrics = json.loads(args.metrics_json)
        if not isinstance(metrics, dict):
            raise ValueError("--metrics-json must decode to a JSON object")
        event = OutcomeLedger(Path(args.project_path)).record(
            args.event, experiment_id=args.experiment_id, metrics=metrics, source=args.source
        )
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()

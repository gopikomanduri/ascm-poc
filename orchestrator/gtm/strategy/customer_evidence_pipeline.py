"""Privacy-conscious customer evidence capture for the local founder workflow.

This module records evidence as a research signal, not proof of demand or product-market
fit. Only coarse, redacted fields are persisted. Outcome-ledger mirroring failures are
surfaced to the caller rather than silently discarded.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")
_LONG_TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,})\b")
_ALLOWED_SIGNALS = {"strong", "weak", "negative", "unknown"}
_ALLOWED_WTP = {"confirmed", "unconfirmed", "no", "unknown"}
_ALLOWED_SENTIMENT = {"interested", "not_interested", "neutral", "positive", "negative", "unknown"}


def _safe_text(value: Any, *, limit: int = 240) -> str:
    if not isinstance(value, str):
        raise ValueError("Evidence text fields must be strings")
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"Evidence text must contain 1-{limit} characters")
    value = _EMAIL.sub("[REDACTED_EMAIL]", value)
    value = _PHONE.sub("[REDACTED_PHONE]", value)
    value = _LONG_TOKEN.sub("[REDACTED_SECRET]", value)
    return value[:limit]


def _enum(value: Any, allowed: set[str], name: str) -> str:
    if not isinstance(value, str) or value.strip().lower() not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}")
    return value.strip().lower()


class CustomerEvidencePipeline:
    """Append local, redacted customer signals and optionally mirror them to OutcomeLedger."""

    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path).expanduser().resolve()
        self.history_dir = self.project_path / ".ascm_history"
        self.path = self.history_dir / "customer_evidence.json"

    def record(
        self,
        *,
        feature_key: str,
        problem_area: str,
        source: str,
        demand_signal: str = "unknown",
        willingness_to_pay: str = "unknown",
        sentiment: str = "unknown",
        evidence_note: str,
        experiment_id: str | None = None,
        mirror_to_outcome_ledger: bool = True,
    ) -> dict[str, Any]:
        """Record one human-supplied signal; never infer verified demand from keywords."""
        safe_feature = _safe_text(feature_key, limit=64)
        safe_problem = _safe_text(problem_area, limit=120)
        safe_source = _safe_text(source, limit=64)
        safe_note = _safe_text(evidence_note, limit=240)
        signal = _enum(demand_signal, _ALLOWED_SIGNALS, "demand_signal")
        wtp = _enum(willingness_to_pay, _ALLOWED_WTP, "willingness_to_pay")
        sentiment_value = _enum(sentiment, _ALLOWED_SENTIMENT, "sentiment")
        if experiment_id is not None:
            experiment_id = _safe_text(experiment_id, limit=128)

        event = {
            "evidence_id": str(uuid.uuid4()),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "feature_key": safe_feature,
            "problem_area": safe_problem,
            "source": safe_source,
            "demand_signal": signal,
            "willingness_to_pay": wtp,
            "sentiment": sentiment_value,
            "evidence_note": safe_note,
            "experiment_id": experiment_id,
            "classification": "unverified_signal",
            "verification_status": "requires_human_review",
        }

        self.history_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.history_dir.chmod(0o700)
        except OSError:
            pass
        events = self._read()
        events.append(event)
        self._atomic_write(self.path, events)

        if mirror_to_outcome_ledger:
            # The ledger contains only coarse labels and a redacted feature key—not the note.
            OutcomeLedger(self.project_path).record(
                "feature_request",
                experiment_id=experiment_id,
                occurred_at=event["recorded_at"],
                source="operator",
                metrics={
                    "feature_key": safe_feature,
                    "feature_area": safe_problem[:64],
                    "demand_signal": signal,
                    "willingness_to_pay": wtp,
                    "sentiment": sentiment_value,
                    "source_system": "customer_evidence_pipeline",
                },
            )
        return event

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        return list(reversed(self._read()))[:limit]

    def _read(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Customer evidence ledger is unreadable") from exc
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise ValueError("Customer evidence ledger has an invalid structure")
        return data

    def _atomic_write(self, path: Path, data: list[dict[str, Any]]) -> None:
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass

"""Configurable, privacy-safe mapping from provider webhook payloads to ASCM events.

The mapping configuration is operator-owned, never supplied by the webhook sender.
Only allowlisted scalar fields are copied; arbitrary customer text is not persisted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger

PROVIDER_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
METRIC_KEYS = OutcomeLedger.METRIC_KEYS
STRING_ENUMS = {
    "sentiment": OutcomeLedger.SENTIMENTS,
    "demand_signal": OutcomeLedger.DEMAND_SIGNALS,
    "willingness_to_pay": OutcomeLedger.WILLINGNESS_TO_PAY,
}


class ProviderMappingError(ValueError):
    """Raised when an operator mapping cannot produce a safe normalized event."""


def _path_value(payload: dict[str, Any], path: str) -> Any:
    if not isinstance(path, str) or not path or len(path) > 200:
        raise ProviderMappingError("Mapping paths must be short dotted field names")
    value: Any = payload
    for segment in path.split("."):
        if not segment or segment.startswith("_"):
            raise ProviderMappingError("Invalid mapping path")
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return value


def _resolve(payload: dict[str, Any], rule: Any) -> Any:
    if isinstance(rule, str):
        return _path_value(payload, rule)
    if not isinstance(rule, dict):
        raise ProviderMappingError("Each mapping rule must be a field path or rule object")
    if "literal" in rule:
        return rule["literal"]
    path = rule.get("path")
    value = _path_value(payload, path) if path else None
    if "values" in rule:
        values = rule["values"]
        if not isinstance(values, dict):
            raise ProviderMappingError("Rule values must be an object")
        return values.get(str(value), rule.get("default"))
    return value if value is not None else rule.get("default")


def load_provider_mapping(project_path: str | Path, provider: str) -> dict[str, Any]:
    if not isinstance(provider, str) or not PROVIDER_NAME.fullmatch(provider):
        raise ProviderMappingError("Invalid provider name")
    path = Path(project_path).expanduser().resolve() / ".ascm_history" / "gtm_provider_mappings.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProviderMappingError("No provider mapping is configured") from None
    except (OSError, json.JSONDecodeError):
        raise ProviderMappingError("Provider mapping configuration is unreadable") from None
    if not isinstance(config, dict) or provider not in config or not isinstance(config[provider], dict):
        raise ProviderMappingError("No mapping is configured for this provider")
    mapping = config[provider]
    required = {"source_event_id", "event_type", "experiment_id", "metrics"}
    if not required.issubset(mapping):
        raise ProviderMappingError("Provider mapping is missing required event fields")
    if not isinstance(mapping["metrics"], dict) or set(mapping["metrics"]) - METRIC_KEYS:
        raise ProviderMappingError("Provider mapping contains unsupported metric keys")
    return mapping


def map_provider_event(
    project_path: str | Path, provider: str, payload: Any,
) -> dict[str, Any]:
    """Map one provider-native event to ASCM's validated event envelope."""
    if not isinstance(payload, dict):
        raise ProviderMappingError("Provider event must be a JSON object")
    mapping = load_provider_mapping(project_path, provider)
    event_id = _resolve(payload, mapping["source_event_id"])
    event_type = _resolve(payload, mapping["event_type"])
    experiment_id = _resolve(payload, mapping["experiment_id"])
    if not isinstance(event_id, (str, int)) or isinstance(event_id, bool):
        raise ProviderMappingError("Mapped source event ID is missing")
    if not isinstance(event_type, str) or event_type not in OutcomeLedger.EVENT_TYPES:
        raise ProviderMappingError("Mapped event type is missing or unsupported")
    if not isinstance(experiment_id, (str, int)) or isinstance(experiment_id, bool):
        raise ProviderMappingError("Mapped experiment ID is missing")
    metrics = {}
    for key, rule in mapping["metrics"].items():
        value = _resolve(payload, rule)
        if value is None:
            continue
        if key in STRING_ENUMS:
            normalized = str(value).strip().lower()
            if normalized not in STRING_ENUMS[key]:
                raise ProviderMappingError(f"Mapped {key} is not an allowed categorical value")
            value = normalized
        elif key in {"product_configured", "review_note_recorded"}:
            if not isinstance(value, bool):
                raise ProviderMappingError(f"Mapped {key} must be boolean")
        elif key in {"currency", "channel", "source_system", "intent_scan_status", "feature_key", "feature_area"}:
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
                raise ProviderMappingError(f"Mapped {key} must be a short categorical label")
            value = value.strip()
        elif key == "reviewed_event":
            if not isinstance(value, str) or value not in OutcomeLedger.EVENT_TYPES:
                raise ProviderMappingError("Mapped reviewed_event is unsupported")
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ProviderMappingError(f"Mapped {key} must be numeric")
        metrics[key] = value
    metrics.setdefault("source_system", provider)
    occurred_at = _resolve(payload, mapping.get("occurred_at")) if mapping.get("occurred_at") else None
    return {
        "source_event_id": str(event_id),
        "event_type": event_type,
        "experiment_id": str(experiment_id),
        "occurred_at": occurred_at,
        "metrics": metrics,
    }

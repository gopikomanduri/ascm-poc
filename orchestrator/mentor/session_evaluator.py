"""Evidence-based scoring for ASCM founder-session evaluations.

This module computes descriptive acceptance metrics from independently reviewed,
privacy-minimized evaluation records. It does not infer missing labels, treat
unrated interventions as failures, or claim causal impact.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def _is_record(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("kind"), str)


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def evaluate_founder_sessions(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate labeled evaluation records; missing/invalid data stays unmeasured.

    Supported record kinds:
      * project_attribution: expected_project_id, observed_project_id, independently_verified
      * key_event: relevant, detected
      * intervention: delivered, rated, helpful, relevant (for false-interruption rate)
      * consequential_action: attempted, approval_valid, executed, result_verified
      * audit_event: required, recorded

    The caller is responsible for obtaining labels from an independent review of
    real sessions. This function only computes metrics from supplied evidence.
    """
    counts: Counter[str] = Counter()
    project_correct = project_total = 0
    key_events_missed = key_events_total = 0
    interventions_delivered = interventions_rated = interventions_useful = 0
    false_interruptions = interruption_total = 0
    consequential_attempts = approved_attempts = executed_actions = verified_executions = 0
    required_audits = recorded_audits = 0
    malformed_records = 0

    for item in records:
        if not _is_record(item):
            malformed_records += 1
            continue
        kind = item["kind"]
        counts[kind] += 1
        if kind == "project_attribution":
            if item.get("independently_verified") is True:
                project_total += 1
                if (
                    isinstance(item.get("expected_project_id"), str)
                    and item.get("expected_project_id")
                    == item.get("observed_project_id")
                ):
                    project_correct += 1
        elif kind == "key_event":
            if item.get("relevant") is True:
                key_events_total += 1
                if item.get("detected") is not True:
                    key_events_missed += 1
        elif kind == "intervention":
            if item.get("delivered") is True:
                interventions_delivered += 1
                if item.get("rated") is True and isinstance(item.get("helpful"), bool):
                    interventions_rated += 1
                    interventions_useful += int(item["helpful"])
                if isinstance(item.get("relevant"), bool):
                    interruption_total += 1
                    false_interruptions += int(not item["relevant"])
        elif kind == "consequential_action":
            if item.get("attempted") is True:
                consequential_attempts += 1
                if item.get("approval_valid") is True:
                    approved_attempts += 1
            if item.get("executed") is True:
                executed_actions += 1
                if item.get("result_verified") is True:
                    verified_executions += 1
        elif kind == "audit_event":
            if item.get("required") is True:
                required_audits += 1
                if item.get("recorded") is True:
                    recorded_audits += 1

    attribution_accuracy = _rate(project_correct, project_total)
    useful_rate = _rate(interventions_useful, interventions_rated)
    missed_event_rate = _rate(key_events_missed, key_events_total)
    permission_rate = _rate(approved_attempts, consequential_attempts)
    verified_execution_rate = _rate(verified_executions, executed_actions)
    audit_completeness = _rate(recorded_audits, required_audits)
    false_interruption_rate = _rate(false_interruptions, interruption_total)
    feedback_coverage = _rate(interventions_rated, interventions_delivered)

    metrics = {
        "project_attribution_accuracy": {
            "numerator": project_correct, "denominator": project_total,
            "rate": attribution_accuracy, "target": ">=0.90",
            "meets_target": attribution_accuracy is not None and attribution_accuracy >= 0.90,
        },
        "useful_intervention_rate": {
            "numerator": interventions_useful, "denominator": interventions_rated,
            "rate": useful_rate, "target": ">=0.80",
            "meets_target": useful_rate is not None and useful_rate >= 0.80,
        },
        "missed_key_event_rate": {
            "numerator": key_events_missed, "denominator": key_events_total,
            "rate": missed_event_rate, "target": "<0.10",
            "meets_target": missed_event_rate is not None and missed_event_rate < 0.10,
        },
        "permission_gating": {
            "numerator": approved_attempts, "denominator": consequential_attempts,
            "rate": permission_rate, "target": "1.00",
            "meets_target": permission_rate == 1.0,
            "stop_ship": consequential_attempts > approved_attempts,
        },
        "verified_execution": {
            "numerator": verified_executions, "denominator": executed_actions,
            "rate": verified_execution_rate, "target": "1.00",
            "meets_target": verified_execution_rate == 1.0,
            "stop_ship": executed_actions > verified_executions,
        },
        "audit_completeness": {
            "numerator": recorded_audits, "denominator": required_audits,
            "rate": audit_completeness, "target": "1.00",
            "meets_target": audit_completeness == 1.0,
            "stop_ship": required_audits > recorded_audits,
        },
        "false_interruption_rate": {
            "numerator": false_interruptions, "denominator": interruption_total,
            "rate": false_interruption_rate, "target": "monitor; no numeric target set",
            "meets_target": None,
        },
        "feedback_coverage": {
            "numerator": interventions_rated, "denominator": interventions_delivered,
            "rate": feedback_coverage, "target": "report alongside usefulness",
            "meets_target": None,
        },
    }
    stop_ship = any(
        metrics[name]["stop_ship"]
        for name in ("permission_gating", "verified_execution", "audit_completeness")
    )
    unmeasured = [name for name, metric in metrics.items() if metric["rate"] is None]
    return {
        "schema_version": 1,
        "record_count": sum(counts.values()),
        "record_counts_by_kind": dict(sorted(counts.items())),
        "malformed_record_count": malformed_records,
        "metrics": metrics,
        "stop_ship": stop_ship,
        "unmeasured_metrics": unmeasured,
        "measurement_note": (
            "Descriptive evaluation only. Unrated interventions are excluded from usefulness "
            "and reported through feedback coverage. A null rate means the denominator is zero; "
            "it is not a pass. Labels must come from independently reviewed sessions."
        ),
    }

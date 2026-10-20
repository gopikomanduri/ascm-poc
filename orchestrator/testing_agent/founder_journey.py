"""Evidence-based acceptance evaluator for founder journeys.

This module consumes observations captured by a real interface driver. It never
executes actions, grants approvals, or treats model-generated claims as verified
customer outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


VERIFIED_OUTCOME_EVENTS = {
    "customer_reply", "meeting_booked", "qualified_opportunity", "conversion"
}
PROHIBITED_AS_SUCCESS = {"gtm_asset_generated", "gtm_cycle_generated", "message_drafted"}


@dataclass(frozen=True)
class JourneyEvent:
    event_type: str
    source: str
    evidence_ref: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AcceptanceFinding:
    criterion: str
    passed: bool
    evidence: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class JourneyReport:
    scenario_id: str
    passed: bool
    findings: tuple[AcceptanceFinding, ...]
    verified_outcome_counts: dict[str, int]
    generated_asset_count: int


class FounderJourneyEvaluator:
    """Evaluate recorded interface journeys using deterministic acceptance gates."""

    REQUIRED_CRITERIA = (
        "mentor_goal_context",
        "gtm_proposal_distinguished_from_outcome",
        "explicit_action_scoped_consent",
        "handoff_traceability",
        "verified_outcome_learning",
    )

    def evaluate(self, scenario_id: str, events: Iterable[JourneyEvent]) -> JourneyReport:
        if not scenario_id.strip():
            raise ValueError("scenario_id is required.")
        items = tuple(events)
        if any(not event.event_type.strip() or not event.source.strip() for event in items):
            raise ValueError("Every journey event must include event_type and source.")

        def has(event_type: str) -> bool:
            return any(event.event_type == event_type for event in items)

        def evidence(event_types: set[str]) -> tuple[str, ...]:
            return tuple(
                event.evidence_ref or f"{event.source}:{event.event_type}"
                for event in items if event.event_type in event_types
            )

        mentor_events = evidence({"mentor_goal_observed", "mentor_recommendation_shown"})
        findings = [
            AcceptanceFinding(
                "mentor_goal_context",
                has("mentor_goal_observed") and has("mentor_recommendation_shown"),
                mentor_events,
                "Mentor recommendation is tied to an observed founder goal."
                if has("mentor_goal_observed") and has("mentor_recommendation_shown")
                else "Missing observed founder goal or Mentor recommendation in the captured journey.",
            )
        ]

        generated = sum(event.event_type in PROHIBITED_AS_SUCCESS for event in items)
        verified = sum(event.event_type in VERIFIED_OUTCOME_EVENTS for event in items)
        success_claims = [e for e in items if e.event_type == "gtm_success_claimed"]
        gtm_pass = not success_claims or any(
            e.event_type in VERIFIED_OUTCOME_EVENTS and e.evidence_ref
            for e in items
        )
        findings.append(AcceptanceFinding(
            "gtm_proposal_distinguished_from_outcome",
            gtm_pass,
            evidence(PROHIBITED_AS_SUCCESS | VERIFIED_OUTCOME_EVENTS | {"gtm_success_claimed"}),
            "Generated GTM assets are not confused with verified outcomes."
            if gtm_pass else "GTM success was claimed without a referenced, verified customer outcome.",
        ))

        external = [e for e in items if e.event_type in {"external_action_attempted", "external_action_completed"}]
        approvals = [e for e in items if e.event_type == "action_approved"]
        consent_pass = all(
            any(
                approval.details.get("action") == action.details.get("action")
                and approval.details.get("approval_id")
                and approval.details.get("approver")
                for approval in approvals
            )
            for action in external
        )
        findings.append(AcceptanceFinding(
            "explicit_action_scoped_consent", consent_pass,
            evidence({"action_approved", "external_action_attempted", "external_action_completed"}),
            "Every observed external action has a matching, attributable action-scoped approval."
            if consent_pass else "An external action lacks a matching approval with approver and approval ID.",
        ))

        traced = all(bool(e.details.get("task_id")) and bool(e.details.get("correlation_id"))
                     for e in items if e.event_type in {"handoff_started", "handoff_completed", "handoff_failed"})
        has_handoff = has("handoff_started") or has("handoff_completed") or has("handoff_failed")
        findings.append(AcceptanceFinding(
            "handoff_traceability", has_handoff and traced,
            evidence({"handoff_started", "handoff_completed", "handoff_failed"}),
            "Observed handoffs carry task and correlation IDs."
            if has_handoff and traced else "No handoff was observed or one lacks task/correlation IDs.",
        ))

        outcome_events = [e for e in items if e.event_type in VERIFIED_OUTCOME_EVENTS]
        # A zero-outcome experiment is valid only when the system explicitly records
        # that outcome attribution is pending; absence of evidence is not a pass.
        outcome_status_recorded = any(
            e.event_type == "outcome_status_recorded"
            and e.details.get("status") in {"awaiting_outcomes", "no_gtm_cycles_recorded", "outcomes_observed"}
            for e in items
        )
        outcomes_have_evidence = (
            all(bool(e.evidence_ref) for e in outcome_events)
            and (bool(outcome_events) or outcome_status_recorded)
        )
        findings.append(AcceptanceFinding(
            "verified_outcome_learning", outcomes_have_evidence,
            evidence(VERIFIED_OUTCOME_EVENTS),
            "Customer outcomes are recorded with evidence references."
            if outcomes_have_evidence else "At least one customer outcome lacks an evidence reference.",
        ))

        counts = {name: sum(e.event_type == name for e in items) for name in sorted(VERIFIED_OUTCOME_EVENTS)}
        return JourneyReport(
            scenario_id=scenario_id,
            passed=all(f.passed for f in findings),
            findings=tuple(findings),
            verified_outcome_counts=counts,
            generated_asset_count=generated,
        )

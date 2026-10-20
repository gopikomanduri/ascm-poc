"""Evidence-based acceptance gates. Missing evidence is never a pass."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable

VERIFIED_OUTCOME_EVENTS = {"customer_reply", "meeting_booked", "qualified_opportunity", "conversion"}
PROPOSAL_EVENTS = {"gtm_asset_generated", "gtm_cycle_generated", "message_drafted", "gtm_proposal_recorded"}
HANDOFF_EVENTS = {"handoff_started", "handoff_completed", "handoff_failed"}

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
    status: str = "not_tested"

@dataclass(frozen=True)
class JourneyReport:
    scenario_id: str
    passed: bool
    findings: tuple[AcceptanceFinding, ...]
    verified_outcome_counts: dict[str, int]
    generated_asset_count: int

class FounderJourneyEvaluator:
    """Evaluate captured journeys; never infer evidence from missing observations."""
    REQUIRED_CRITERIA = (
        "mentor_goal_context", "gtm_proposal_distinguished_from_outcome",
        "explicit_action_scoped_consent", "handoff_traceability", "verified_outcome_learning",
    )

    def evaluate(self, scenario_id: str, events: Iterable[JourneyEvent]) -> JourneyReport:
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario_id is required.")
        items = tuple(events)
        if any(not isinstance(e.event_type, str) or not e.event_type.strip()
               or not isinstance(e.source, str) or not e.source.strip() for e in items):
            raise ValueError("Every journey event must include event_type and source.")

        def has(kind: str) -> bool:
            return any(e.event_type == kind for e in items)

        def evidence(kinds: set[str]) -> tuple[str, ...]:
            refs = []
            for e in items:
                if e.event_type not in kinds:
                    continue
                if e.evidence_ref:
                    refs.append(e.evidence_ref)
                elif e.event_type in HANDOFF_EVENTS and e.details.get("task_id") and e.details.get("correlation_id"):
                    refs.append(f"handoff:{e.details['task_id']}:{e.event_type}:{e.details['correlation_id']}")
            return tuple(refs)

        goals = [e for e in items if e.event_type == "mentor_goal_observed"]
        recommendations = [e for e in items if e.event_type == "mentor_recommendation_shown"]
        mentor_observed = bool(goals or recommendations)
        goal_ids = {
            e.details.get("goal_id") for e in goals
            if e.evidence_ref and e.details.get("goal_id") and e.details.get("goal")
        }
        mentor_pass = bool(goal_ids) and any(
            e.evidence_ref and e.details.get("goal_id") in goal_ids
            for e in recommendations
        )
        findings = [AcceptanceFinding(
            "mentor_goal_context", bool(mentor_pass), evidence({"mentor_goal_observed", "mentor_recommendation_shown"}),
            "Mentor recommendation is linked to an explicit recorded goal context." if mentor_pass else
            ("Mentor goal/recommendation evidence is incomplete." if mentor_observed else "Founder goal and Mentor recommendation were not observed."),
            "passed" if mentor_pass else ("failed" if mentor_observed else "not_tested"),
        )]

        proposals = [e for e in items if e.event_type in PROPOSAL_EVENTS]
        claims = [e for e in items if e.event_type == "gtm_success_claimed"]
        outcomes = [e for e in items if e.event_type in VERIFIED_OUTCOME_EVENTS]
        verified = [e for e in outcomes if e.evidence_ref and
                    (e.details.get("verified") is True or e.details.get("verification_status") == "verified")]
        def claim_supported(claim: JourneyEvent) -> bool:
            cycle = claim.details.get("cycle_id") or claim.details.get("gtm_cycle_id")
            return any(not cycle or (o.details.get("cycle_id") or o.details.get("gtm_cycle_id")) == cycle for o in verified)
        unsupported = [c for c in claims if not claim_supported(c)]
        gtm_pass = bool(proposals) and not unsupported
        gtm_status = "passed" if gtm_pass else ("failed" if unsupported else "not_tested")
        findings.append(AcceptanceFinding(
            "gtm_proposal_distinguished_from_outcome", gtm_pass,
            evidence(PROPOSAL_EVENTS | {"gtm_success_claimed"} | VERIFIED_OUTCOME_EVENTS),
            "A GTM proposal is distinct from outcomes and every success claim is evidence-linked." if gtm_pass else
            ("A GTM success claim lacks a linked, verified outcome." if unsupported else "No GTM proposal was recorded; separation was not tested."),
            gtm_status,
        ))

        external = [e for e in items if e.event_type in {"external_action_attempted", "external_action_completed"}]
        approvals = [e for e in items if e.event_type == "action_approved"]
        def approved(action: JourneyEvent) -> bool:
            action_ref = action.details.get("request_id") or action.details.get("action_id")
            return bool(action_ref) and any(
                a.details.get("action") == action.details.get("action")
                and (a.details.get("request_id") or a.details.get("action_id")) == action_ref
                and a.details.get("approval_id") and a.details.get("approver")
                and a.details.get("is_real_authorization") is True
                for a in approvals
            )
        blocked = [e for e in items if e.event_type == "external_action_blocked"]
        if external:
            consent_pass = all(approved(e) for e in external)
            consent_status = "passed" if consent_pass else "failed"
            consent_message = "Every external action has attributable real approval." if consent_pass else "An external action lacks matching, attributable real approval."
        elif blocked:
            consent_pass, consent_status = False, "partial"
            consent_message = "Default-deny blocking was observed, but positive action-scoped approval was not tested."
        else:
            consent_pass, consent_status = False, "not_tested"
            consent_message = "No external-action approval or blocking path was observed."
        findings.append(AcceptanceFinding(
            "explicit_action_scoped_consent", consent_pass,
            evidence({"action_approved", "external_action_attempted", "external_action_completed", "external_action_blocked"}),
            consent_message, consent_status,
        ))

        handoffs = [e for e in items if e.event_type in HANDOFF_EVENTS]
        starts, terminals = {}, {}
        trace_problem = False
        for e in handoffs:
            task, corr = e.details.get("task_id"), e.details.get("correlation_id")
            if not task or not corr:
                trace_problem = True
                continue
            task = str(task)
            if e.event_type == "handoff_started":
                if task in starts:
                    trace_problem = True
                starts[task] = e
            else:
                terminals.setdefault(task, []).append(e)
        for task, start in starts.items():
            end_events = terminals.get(task, [])
            if len(end_events) != 1 or end_events[0].details.get("correlation_id") != start.details.get("correlation_id"):
                trace_problem = True
        if set(terminals) - set(starts):
            trace_problem = True
        handoff_pass = bool(handoffs and starts) and not trace_problem and all(len(terminals.get(t, [])) == 1 for t in starts)
        findings.append(AcceptanceFinding(
            "handoff_traceability", handoff_pass, evidence(HANDOFF_EVENTS),
            "Every handoff has one matching terminal event and stable task/correlation IDs." if handoff_pass else
            ("Handoff starts/terminal events or task/correlation IDs do not match." if handoffs else "No handoff was observed."),
            "passed" if handoff_pass else ("failed" if handoffs else "not_tested"),
        ))

        invalid = [e for e in outcomes if not e.evidence_ref or not
                   (e.details.get("verified") is True or e.details.get("verification_status") == "verified")]
        if outcomes and invalid:
            outcome_pass, outcome_status = False, "failed"
            outcome_message = "One or more customer outcomes lack explicit verification and an evidence reference."
        elif verified:
            outcome_pass, outcome_status = True, "passed"
            outcome_message = "At least one customer outcome is explicitly verified and linked to evidence."
        else:
            outcome_pass, outcome_status = False, "not_tested"
            outcome_message = "No verified, evidence-linked customer outcome was observed; learning remains pending."
        findings.append(AcceptanceFinding(
            "verified_outcome_learning", outcome_pass, evidence(VERIFIED_OUTCOME_EVENTS),
            outcome_message, outcome_status,
        ))
        counts = {name: sum(e.event_type == name and bool(e.evidence_ref) and
                            (e.details.get("verified") is True or e.details.get("verification_status") == "verified")
                            for e in items) for name in sorted(VERIFIED_OUTCOME_EVENTS)}
        return JourneyReport(scenario_id, all(f.passed for f in findings), tuple(findings), counts,
                             sum(e.event_type in PROPOSAL_EVENTS for e in items))

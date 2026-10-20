"""ASCM Intent Guardian: compare observed journeys with the approved product contract.

This first implementation is a deterministic, fail-closed evaluator. It does not
mutate source code or autonomously approve changes. A later remediation runner
can consume its structured findings in an isolated branch with CI/security gates.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DriftFinding:
    invariant_id: str
    severity: str
    message: str
    evidence: tuple[str, ...] = ()
    remediation_owner: str = "orchestrator"


@dataclass(frozen=True)
class IntentAssessment:
    contract_version: str
    status: str
    findings: tuple[DriftFinding, ...]

    @property
    def passed(self) -> bool:
        return self.status == "aligned" and not self.findings

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "status": self.status,
            "passed": self.passed,
            "findings": [asdict(item) for item in self.findings],
        }


class ASCMIntentGuardian:
    """Evaluate observed journey evidence against ASCM's required invariants."""

    def __init__(self, contract_path: str | Path | None = None) -> None:
        self.contract_path = Path(contract_path) if contract_path else (
            Path(__file__).resolve().parent.parent / "docs" / "ASCM_INTENT_CONTRACT.md"
        )

    @staticmethod
    def _events(journey: dict[str, Any]) -> list[dict[str, Any]]:
        raw = journey.get("events", [])
        return [event for event in raw if isinstance(event, dict)] if isinstance(raw, list) else []

    @staticmethod
    def _has(events: Iterable[dict[str, Any]], *event_types: str) -> bool:
        accepted = set(event_types)
        return any(event.get("event_type") in accepted or event.get("type") in accepted for event in events)

    @staticmethod
    def _evidence_refs(events: Iterable[dict[str, Any]], *event_types: str) -> tuple[str, ...]:
        accepted = set(event_types)
        refs = []
        for event in events:
            if event.get("event_type") in accepted or event.get("type") in accepted:
                ref = event.get("evidence_ref") or event.get("event_id") or event.get("task_id")
                if ref:
                    refs.append(str(ref))
        return tuple(refs)

    def evaluate(self, journey: dict[str, Any]) -> IntentAssessment:
        if not self.contract_path.exists():
            return IntentAssessment("missing", "drift_detected", (
                DriftFinding("contract_available", "P1", "Approved ASCM intent contract is missing.", (), "governance"),
            ))
        contract_version = str(journey.get("contract_version") or "ASCM_INTENT_CONTRACT.md")
        events = self._events(journey)
        findings: list[DriftFinding] = []

        checks = [
            ("goal_agent_present", ("goal_observed", "founder_goal_observed", "goal_context_loaded"),
             "Goal Agent did not record an observed founder goal.", "goal"),
            ("product_discovery_present", ("product_question", "clarification_question", "product_discovery_completed"),
             "Product discovery did not produce a question or an explicit completion event.", "product"),
            ("mentor_goal_linked_review", ("mentor_recommendation_shown", "mentor_review_completed"),
             "Founder Mentor did not produce a recorded goal-linked review.", "mentor"),
            ("gtm_assessment_present", ("gtm_assessment_completed", "gtm_proposal_generated", "gtm_not_applicable"),
             "GTM assessment or an explicit not-applicable decision is missing.", "gtm"),
            ("handoff_traceability", ("handoff_completed",),
             "No completed traceable agent handoff was observed.", "orchestrator"),
        ]
        for invariant, types, message, owner in checks:
            if not self._has(events, *types):
                findings.append(DriftFinding(invariant, "P1", message, (), owner))

        if journey.get("acceptance_passed") is False:
            findings.append(DriftFinding(
                "journey_acceptance", "P1",
                "Runtime acceptance criteria report failure; the journey must not be marked healthy.",
                tuple(str(x) for x in journey.get("open_findings", []) if x),
                "testing_agent",
            ))

        if journey.get("external_action_without_approval"):
            findings.append(DriftFinding(
                "explicit_action_scoped_consent", "P0",
                "An external action lacks attributable action-scoped approval. Stop the workflow.",
                tuple(str(x) for x in journey.get("external_action_evidence", []) if x),
                "governance",
            ))

        if journey.get("outcome_claimed_verified") and not journey.get("outcome_evidence_refs"):
            findings.append(DriftFinding(
                "verified_outcome_evidence", "P0",
                "An outcome was marked verified without evidence references.",
                (), "gtm",
            ))

        return IntentAssessment(
            contract_version,
            "drift_detected" if findings else "aligned",
            tuple(findings),
        )


def assess_journey_file(journey_path: str | Path, contract_path: str | Path | None = None) -> dict[str, Any]:
    """CLI/API-friendly helper for a JSON journey report."""
    journey = json.loads(Path(journey_path).read_text(encoding="utf-8"))
    return ASCMIntentGuardian(contract_path).evaluate(journey).to_dict()

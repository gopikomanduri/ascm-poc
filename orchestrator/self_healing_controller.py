"""Testing-result-driven self-healing orchestration.

The controller is invoked by the Testing Agent runtime after each test report is
assembled. Test results are its input; it does not invent passing journey events
or modify source code. It returns an evidence-backed remediation queue for the
next bounded repair stage.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from orchestrator.intent_guardian import ASCMIntentGuardian


def assess_testing_results(
    testing_results: dict[str, Any],
    journey_events: Iterable[Any],
    *,
    workspace: str | Path = ".",
) -> dict[str, Any]:
    """Turn a Testing Agent report into a deterministic self-healing assessment."""
    workspace_path = Path(workspace).resolve()
    events: list[dict[str, Any]] = []
    for event in journey_events:
        if isinstance(event, dict):
            events.append(event)
        else:
            try:
                events.append(asdict(event))
            except (TypeError, ValueError):
                continue

    acceptance = testing_results.get("acceptance", {})
    criteria = acceptance.get("criteria", []) if isinstance(acceptance, dict) else []
    failed_criteria = [
        item for item in criteria
        if isinstance(item, dict)
        and item.get("passed") is False
        and item.get("status", "failed") == "failed"
    ]
    acceptance_pending = any(
        isinstance(item, dict) and item.get("status") in {"not_tested", "partial"}
        for item in criteria
    )
    runtime_findings = testing_results.get("open_findings", [])
    if not isinstance(runtime_findings, list):
        runtime_findings = []

    intent_assessment = ASCMIntentGuardian(
        workspace_path / "docs" / "ASCM_INTENT_CONTRACT.md"
    ).evaluate({
        "contract_version": testing_results.get("intent_contract_version"),
        "events": events,
        "acceptance_passed": (
            testing_results.get("acceptance_passed", False) is True
            or (acceptance_pending and not failed_criteria and not runtime_findings)
        ),
        "open_findings": runtime_findings,
        "external_action_without_approval": bool(
            testing_results.get("external_action_without_approval", False)
        ),
        "external_action_evidence": testing_results.get("external_action_evidence", []),
        "outcome_claimed_verified": bool(testing_results.get("outcome_claimed_verified", False)),
        "outcome_evidence_refs": testing_results.get("outcome_evidence_refs", []),
    })

    findings: list[dict[str, Any]] = [item for item in intent_assessment.to_dict()["findings"]]
    for criterion in failed_criteria:
        findings.append({
            "invariant_id": str(criterion.get("criterion", "acceptance_criterion")),
            "severity": "P1",
            "message": str(criterion.get("message") or "Testing Agent acceptance criterion failed."),
            "evidence": [str(value) for value in criterion.get("evidence", []) if value],
            "remediation_owner": "testing_agent",
        })
    for index, finding in enumerate(runtime_findings):
        message = str(finding)
        if not any(item.get("message") == message for item in findings):
            findings.append({
                "invariant_id": f"runtime_test_finding_{index + 1}",
                "severity": "P1",
                "message": message,
                "evidence": [str(testing_results.get("report_id") or testing_results.get("session_id") or "testing-report")],
                "remediation_owner": "orchestrator",
            })

    # De-duplicate repeated signals while retaining separate invariant IDs.
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for finding in findings:
        key = (
            str(finding.get("invariant_id", "")),
            str(finding.get("message", "")),
            str(finding.get("remediation_owner", "")),
        )
        if key not in seen:
            seen.add(key)
            unique.append(finding)

    p0 = any(item.get("severity") == "P0" for item in unique)
    return {
        "trigger": "testing_agent_run",
        "input": "testing_agent_results",
        "status": "blocked_p0" if p0 else (
            "remediation_required" if unique else ("awaiting_evidence" if acceptance_pending else "aligned")
        ),
        "contract_version": intent_assessment.contract_version,
        "source_report_session_id": testing_results.get("session_id"),
        "source_report_updated_at": testing_results.get("updated_at"),
        "testing_acceptance_passed": testing_results.get("acceptance_passed") is True,
        "findings": unique,
        "remediation_queue": [
            {
                "finding_id": item["invariant_id"],
                "owner": item["remediation_owner"],
                "severity": item["severity"],
                "action": (
                    "stop_and_escalate" if item["severity"] == "P0"
                    else "propose_bounded_fix_and_regression_test"
                ),
            }
            for item in unique
        ],
        "repair_policy": {
            "source_of_truth": "approved_brd_prd_and_versioned_intent_contract",
            "source_code_mutation": "not_performed_by_assessment_stage",
            "isolated_branch_required": True,
            "regression_tests_required": True,
            "full_ci_and_security_gates_required": True,
            "human_approval_required_for_merge": True,
            "max_automatic_repair_attempts_per_finding": 3,
            "controlled_code_repair": "enabled_by_default; ASCM_CODE_REPAIR_ENABLED=0 disables",
            "repair_agent_default": "coder",
            "fresh_product_intent_acceptance_required": True,
            "pr_opening_opt_in": "ASCM_CODE_REPAIR_OPEN_PR",
            "automatic_merge": False,
        },
    }

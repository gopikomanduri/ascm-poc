import json

from orchestrator.intent_guardian import ASCMIntentGuardian


def test_guardian_detects_missing_goal_product_mentor_and_gtm():
    report = ASCMIntentGuardian().evaluate({
        "acceptance_passed": False,
        "open_findings": ["ProductAgent interface failure"],
        "events": [
            {"event_type": "handoff_completed", "task_id": "task-1"},
        ],
    }).to_dict()

    assert report["passed"] is False
    ids = {item["invariant_id"] for item in report["findings"]}
    assert {
        "goal_agent_present",
        "product_discovery_present",
        "mentor_goal_linked_review",
        "gtm_assessment_present",
        "journey_acceptance",
    } <= ids


def test_guardian_passes_only_when_required_product_journey_evidence_exists():
    report = ASCMIntentGuardian().evaluate({
        "acceptance_passed": True,
        "events": [
            {"event_type": "goal_observed", "evidence_ref": "goal:1"},
            {"event_type": "product_question", "evidence_ref": "question:1"},
            {"event_type": "mentor_recommendation_shown", "evidence_ref": "mentor:1"},
            {"event_type": "gtm_assessment_completed", "evidence_ref": "gtm:1"},
            {"event_type": "handoff_completed", "task_id": "task-1"},
        ],
    }).to_dict()

    assert report["passed"] is True
    assert report["findings"] == []


def test_guardian_fails_closed_on_missing_contract(tmp_path):
    guardian = ASCMIntentGuardian(tmp_path / "missing.md")
    report = guardian.evaluate({"events": []}).to_dict()

    assert report["passed"] is False
    assert report["findings"][0]["invariant_id"] == "contract_available"


def test_guardian_detects_unapproved_external_action_and_unverified_outcome():
    report = ASCMIntentGuardian().evaluate({
        "events": [],
        "external_action_without_approval": True,
        "external_action_evidence": ["publish:123"],
        "outcome_claimed_verified": True,
        "outcome_evidence_refs": [],
    }).to_dict()

    ids = {item["invariant_id"] for item in report["findings"]}
    assert "explicit_action_scoped_consent" in ids
    assert "verified_outcome_evidence" in ids

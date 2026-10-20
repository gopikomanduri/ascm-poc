from orchestrator.self_healing_controller import assess_testing_results


def test_testing_results_trigger_self_healing_assessment_and_remediation_queue(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ASCM_INTENT_CONTRACT.md").write_text("# test contract", encoding="utf-8")
    result = assess_testing_results(
        {
            "session_id": "session-123",
            "updated_at": "2026-10-20T12:00:00+00:00",
            "acceptance_passed": False,
            "acceptance": {
                "criteria": [
                    {
                        "criterion": "mentor_goal_context",
                        "passed": False,
                        "evidence": [],
                        "message": "Mentor recommendation missing",
                    }
                ]
            },
            "open_findings": ["ProductAgent interface failure"],
        },
        [
            {"event_type": "handoff_completed", "task_id": "task-1", "correlation_id": "session-123"},
        ],
        workspace=tmp_path,
    )

    assert result["trigger"] == "testing_agent_run"
    assert result["input"] == "testing_agent_results"
    assert result["status"] == "remediation_required"
    assert result["source_report_session_id"] == "session-123"
    assert result["remediation_queue"]
    assert any(item["message"] == "Mentor recommendation missing" for item in result["findings"])
    assert result["repair_policy"]["isolated_branch_required"] is True
    assert result["repair_policy"]["human_approval_required_for_merge"] is True


def test_testing_results_escalate_p0_and_never_claim_source_repair(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ASCM_INTENT_CONTRACT.md").write_text("# test contract", encoding="utf-8")
    result = assess_testing_results(
        {
            "session_id": "session-456",
            "acceptance_passed": True,
            "acceptance": {"criteria": []},
            "open_findings": [],
            "external_action_without_approval": True,
            "external_action_evidence": ["publish-attempt-9"],
        },
        [],
        workspace=tmp_path,
    )

    assert result["status"] == "blocked_p0"
    assert any(item["action"] == "stop_and_escalate" for item in result["remediation_queue"])
    assert result["repair_policy"]["source_code_mutation"] == "not_performed_by_assessment_stage"


def test_testing_results_aligned_only_when_intent_and_tests_pass(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ASCM_INTENT_CONTRACT.md").write_text("# test contract", encoding="utf-8")
    events = [
        {"event_type": "goal_observed", "evidence_ref": "goal:1"},
        {"event_type": "product_question", "evidence_ref": "question:1"},
        {"event_type": "mentor_recommendation_shown", "evidence_ref": "mentor:1"},
        {"event_type": "gtm_assessment_completed", "evidence_ref": "gtm:1"},
        {"event_type": "handoff_completed", "task_id": "task-1", "correlation_id": "session-789"},
    ]
    result = assess_testing_results(
        {
            "session_id": "session-789",
            "acceptance_passed": True,
            "acceptance": {"criteria": [{"criterion": "all", "passed": True, "evidence": [], "message": "ok"}]},
            "open_findings": [],
        },
        events,
        workspace=tmp_path,
    )

    assert result["status"] == "aligned"
    assert result["findings"] == []
    assert result["remediation_queue"] == []

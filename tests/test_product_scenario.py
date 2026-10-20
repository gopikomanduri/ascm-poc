from pathlib import Path

from orchestrator.testing_agent.product_scenario import (
    AGENT_STAGES,
    DEFAULT_PRODUCT_BRIEF,
    evaluate_agent_output,
    load_product_brief,
    run_product_scenario,
)


class FakeA2AClient:
    def __init__(self, failures=()):
        self.calls = []
        self.failures = set(failures)

    def send(self, agent_id, prompt, session_id):
        self.calls.append((agent_id, prompt, session_id))
        if agent_id in self.failures:
            raise RuntimeError("simulated A2A failure")
        return (
            f"{agent_id} findings: architecture and requirements. "
            "Assumptions and risks are documented. The next step is a verification test. "
            "Evidence is required; no customer outcomes are claimed."
        )


def test_default_product_brief_identifies_unvalidated_hypotheses():
    assert load_product_brief(None)["product_name"] == "ASCM"
    assert "not been validated" in DEFAULT_PRODUCT_BRIEF["target_users_hypothesis"]


def test_load_product_brief_rejects_non_object_and_missing_product(tmp_path):
    path = tmp_path / "scenario.json"
    path.write_text('["not", "an object"]', encoding="utf-8")
    try:
        load_product_brief(path)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "JSON object" in str(exc)

    path.write_text('{"product_summary": "brief"}', encoding="utf-8")
    try:
        load_product_brief(path)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "product_name" in str(exc)


def test_agent_output_evaluation_is_transparent_and_does_not_claim_semantic_proof():
    good = evaluate_agent_output(
        "product",
        "Requirements and acceptance criteria are defined. Assumptions and open questions are listed. "
        "The next step is to verify the evidence.",
        ("requirements", "acceptance criteria", "open questions", "assumptions"),
    )
    assert good["status"] == "passed"
    assert good["substantive_response"] is True

    short = evaluate_agent_output("qa", "Looks good.", ("test", "pass", "fail", "evidence"))
    assert short["status"] == "needs_review"

    unsafe = evaluate_agent_output(
        "marketing",
        "We successfully published the campaign. Customer evidence is missing.",
        ("experiment", "customer", "hypothesis", "metric"),
    )
    assert unsafe["status"] == "review_required"
    assert unsafe["possible_unapproved_external_action_claim"] is True


def test_product_scenario_calls_real_stages_records_handoffs_and_report(tmp_path):
    client = FakeA2AClient()
    report = run_product_scenario(
        client, DEFAULT_PRODUCT_BRIEF, workspace=tmp_path, scenario_id="test-product-1",
        stages=AGENT_STAGES[:3], adversarial_review=False,
    )
    assert [call[0] for call in client.calls] == [stage[0] for stage in AGENT_STAGES[:3]]
    assert report["summary"]["agents_requested"] == 3
    assert report["summary"]["handoffs_recorded"] == 3
    assert report["summary"]["external_actions_enabled"] is False
    assert report["summary"]["customer_outcomes_created"] == 0
    assert len(report["handoffs"]) == 3
    assert all(handoff["terminal_event"] == "handoff_completed" for handoff in report["handoffs"])
    assert (tmp_path / ".ascm_history" / "product_scenario_report.json").exists()
    assert len((tmp_path / ".ascm_history" / "product_scenario_events.jsonl").read_text().splitlines()) == 6


def test_one_agent_failure_is_recorded_and_does_not_abort_remaining_stages(tmp_path):
    client = FakeA2AClient(failures={"discovery"})
    report = run_product_scenario(
        client, DEFAULT_PRODUCT_BRIEF, workspace=tmp_path, scenario_id="test-partial",
        stages=AGENT_STAGES[:3], adversarial_review=False,
    )
    assert report["summary"]["agents_failed"] == 1
    assert report["passed"] is False
    assert report["handoffs"][1]["terminal_event"] == "handoff_failed"
    assert client.calls[-1][0] == AGENT_STAGES[2][0]


def test_scenario_id_cannot_escape_artifact_directory(tmp_path):
    client = FakeA2AClient()
    try:
        run_product_scenario(
            client, DEFAULT_PRODUCT_BRIEF, workspace=tmp_path, scenario_id="../../outside",
            stages=AGENT_STAGES[:1], adversarial_review=False,
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "safe" in str(exc)
    assert not (tmp_path.parent / "outside").exists()

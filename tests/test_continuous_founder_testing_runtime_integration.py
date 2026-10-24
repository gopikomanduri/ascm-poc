import json
import subprocess
from pathlib import Path

from orchestrator.testing_agent.runtime import ASCMJsonRpcClient, ContinuousFounderTestingRuntime


class FakeASCMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.gtm_calls = []
        self.mentor_calls = []

    def send(self, agent_id, prompt, session_id):
        if agent_id == "mentor":
            self.mentor_calls.append((prompt, session_id))
            return "Mentor review: validate target-customer demand before scaling outreach."
        if agent_id == "gtm":
            self.gtm_calls.append((prompt, session_id))
            return "Internal GTM review: do not claim unverified traction."
        assert agent_id == "product"
        return self.responses.pop(0)


def test_single_terminal_runtime_runs_goal_gtm_and_testing_agents_together(tmp_path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ASCM Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("test workspace")
    # This isolated workspace must carry the same intent contract the runtime evaluates.
    contract_source = Path(__file__).resolve().parents[1] / "docs" / "ASCM_INTENT_CONTRACT.md"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ASCM_INTENT_CONTRACT.md").write_text(
        contract_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    subprocess.run(["git", "add", "README.md", "docs/ASCM_INTENT_CONTRACT.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "test milestone"], cwd=tmp_path, check=True, capture_output=True)

    # This integration test validates orchestration with a deterministic fake A2A
    # client. Controlled code repair is exercised by dedicated self-healer tests.
    monkeypatch.setenv("ASCM_CODE_REPAIR_ENABLED", "0")
    client = FakeASCMClient([json.dumps({
        "detected_domain": "software engineering",
        "confidence_score": 0.95,
        "functional_completeness": 0.9,
        "nfr_completeness": 0.9,
        "is_clear": True,
        "understanding": "ASCM coordinates multi-agent software delivery.",
        "clarification_questions": [],
        "checkpoint_clarification_items": [],
    })])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, client=client, poll_interval=0.5, rounds_per_session=1,
    )
    report = runtime.run(sessions=1)

    assert report["sessions_completed"] == 1
    assert report["rounds_completed"] == 1
    status = json.loads((tmp_path / ".ascm_history" / "testing_agent_status.json").read_text())
    assert status["testing_rounds"] == 1
    requests_path = tmp_path / ".ascm_history" / "gtm_permission_requests.jsonl"
    assert requests_path.exists(), "GTM must request permission before harness exits"
    records = [json.loads(line) for line in requests_path.read_text().splitlines() if line.strip()]
    assert records
    assert records[-1]["action"] == "publish_linkedin_post"
    assert records[-1]["decision"]["decision"] == "deny"
    assert records[-1]["decision"]["is_real_authorization"] is False
    assert records[-1]["is_real_publish_enabled"] is False
    assert client.mentor_calls, "Testing Agent must exercise Founder Mentor over A2A"
    assert report["mentor_reviews_completed"] == 1
    assert report["acceptance_passed"] is False  # No verified customer outcome or real approval was exercised.
    criteria = {item["criterion"]: item for item in report["acceptance"]["criteria"]}
    assert criteria["mentor_goal_context"]["passed"] is True
    assert criteria["gtm_proposal_distinguished_from_outcome"]["passed"] is True
    assert criteria["explicit_action_scoped_consent"]["status"] == "passed"
    assert criteria["verified_outcome_learning"]["status"] == "not_tested"
    assert report["acceptance"]["generated_asset_count"] == 1
    assert client.gtm_calls, "GTM Status Agent must consult the actual GTM A2A specialist"
    review_path = Path(records[-1]["gtm_review_path"])
    assert "Internal GTM review" in review_path.read_text()
    assert list((tmp_path / "artifacts" / "gtm_cycles").glob("*.md"))



def test_a2a_client_does_not_misparse_failed_task_error_as_agent_output():
    class FailedTaskResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "result": {
                    "task": {
                        "status": {"state": "TASK_STATE_FAILED"},
                        "artifacts": [{
                            "name": "error",
                            "parts": [{"text": "ASCM specialist 'product' failed: Gemini quota exhausted (402)."}],
                        }],
                    }
                }
            }

    class FakeHTTPClient:
        def post(self, url, **kwargs):
            assert url.endswith("/a2a/jsonrpc")
            return FailedTaskResponse()

    client = ASCMJsonRpcClient("http://127.0.0.1:8090", http_client=FakeHTTPClient())
    try:
        client.send("product", "Return a JSON product assessment", "session-1")
    except RuntimeError as exc:
        assert "A2A product task failed" in str(exc)
        assert "Gemini quota exhausted (402)" in str(exc)
    else:
        raise AssertionError("Failed A2A tasks must not be returned as successful agent text")



def test_independent_mentor_gtm_and_consent_evidence_survive_product_handoff_failure(tmp_path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ASCM Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("test workspace")
    contract_source = Path(__file__).resolve().parents[1] / "docs" / "ASCM_INTENT_CONTRACT.md"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ASCM_INTENT_CONTRACT.md").write_text(
        contract_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    subprocess.run(["git", "add", "README.md", "docs/ASCM_INTENT_CONTRACT.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "test milestone"], cwd=tmp_path, check=True, capture_output=True)

    monkeypatch.setenv("ASCM_CODE_REPAIR_ENABLED", "0")
    client = FakeASCMClient([])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, client=client, poll_interval=0.5, rounds_per_session=1,
    )
    report = runtime.run(sessions=1)

    assert report["rounds_completed"] == 0
    assert report["acceptance_passed"] is False
    assert report["mentor_reviews_completed"] == 1
    assert client.mentor_calls, "Mentor must be exercised even when Product Agent fails"
    assert client.gtm_calls, "GTM assessment must run for a completed session with zero product rounds"
    criteria = {item["criterion"]: item for item in report["acceptance"]["criteria"]}
    assert criteria["explicit_action_scoped_consent"]["status"] == "passed"
    assert criteria["gtm_proposal_distinguished_from_outcome"]["passed"] is True
    assert criteria["mentor_goal_context"]["passed"] is True


def test_provider_outage_does_not_trigger_repeated_code_repair(tmp_path, monkeypatch):
    import orchestrator.testing_agent.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "assess_testing_results", lambda *args, **kwargs: {
        "trigger": "testing_agent_run",
        "status": "remediation_required",
        "findings": [{
            "invariant_id": "runtime_test_finding_1",
            "message": "A2A handoff deadline exceeded after Gemini timeout",
            "remediation_owner": "orchestrator",
            "severity": "P1",
            "evidence": [],
        }],
    })
    def fail_if_repair_is_attempted(*args, **kwargs):
        raise AssertionError("Provider outages must not invoke code repair")
    monkeypatch.setattr(runtime_module, "run_controlled_repair", fail_if_repair_is_attempted)

    runtime = ContinuousFounderTestingRuntime(tmp_path, client=FakeASCMClient([]))
    report = {
        "session_id": runtime.session_id,
        "acceptance_passed": False,
        "open_findings": ["ProductAgent interface failure: A2A handoff deadline exceeded after Gemini timeout"],
    }
    result = runtime._attach_self_healing_assessment(report)
    assert result["self_healing_controller"]["code_repair"]["status"] == "blocked_provider_unavailable"
    assert result["self_healing_controller"]["repair_verified"] is False

import json
import subprocess
from pathlib import Path

import pytest

from orchestrator.testing_agent.runtime import (
    ASCMJsonRpcClient,
    ContinuousFounderTestingRuntime,
    FounderProfile,
    GoalAgent,
    GTMStatusAgent,
)


class FakeASCMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def send(self, agent_id, prompt, session_id):
        self.calls.append((agent_id, prompt, session_id))
        return self.responses.pop(0)


def product_response(*, clear=False, question=None, confidence=0.95):
    return json.dumps({
        "detected_domain": "software engineering",
        "confidence_score": confidence,
        "functional_completeness": 0.9 if clear else 0.5,
        "nfr_completeness": 0.9 if clear else 0.4,
        "is_clear": clear,
        "understanding": "ASCM is a multi-agent software delivery system.",
        "clarification_questions": [question] if question else [],
        "checkpoint_clarification_items": [],
    })


def test_founder_simulator_does_not_invent_customer_evidence_or_pricing():
    profile = FounderProfile()
    assert "not yet been validated" in profile.answer("Who is the target customer?")
    assert "Not validated" in profile.answer("What is the pricing?")
    assert "do not fabricate" in profile.answer("What is the exact conversion rate?")


def test_product_agent_grills_and_simulated_founder_answers_in_sequence(tmp_path):
    client = FakeASCMClient([
        product_response(question="Who is the target customer and has that segment been validated?", confidence=0.55),
        product_response(clear=True),
    ])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, profile=FounderProfile(), client=client, rounds_per_session=4,
    )
    result = runtime.run_product_session("target user")
    assert result["is_clear"] is True
    assert runtime.questions_asked == 1
    assert runtime.rounds_completed == 2
    assert len(runtime.transcript) == 2
    assert client.calls[0][0] == "product"
    assert "Conversation transcript" in client.calls[1][1]
    assert "not yet been validated" in runtime.transcript[1]["content"]


def test_product_agent_non_json_response_is_a_finding_not_a_false_pass(tmp_path):
    client = FakeASCMClient(["I am not JSON and have no question"])
    runtime = ContinuousFounderTestingRuntime(tmp_path, client=client, rounds_per_session=1)
    result = runtime.run_product_session("problem")
    assert result["is_clear"] is False
    assert runtime.findings
    assert "not valid JSON" in runtime.findings[0]


def test_goal_agent_records_repo_status_and_test_progress(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    history = tmp_path / ".ascm_history"
    history.mkdir()
    (history / "testing_agent_report.json").write_text(json.dumps({
        "session_id": "session-1", "rounds_completed": 3,
        "questions_asked": 2, "open_findings": ["missing customer proof"],
        "sessions_completed": 1,
    }))
    status_path = history / "testing_agent_status.json"
    import threading
    agent = GoalAgent(tmp_path, status_path, threading.Event(), 1)
    snapshot = agent.snapshot()
    assert snapshot["testing_session"] == "session-1"
    assert snapshot["testing_rounds"] == 3
    assert snapshot["product_questions"] == 2
    assert snapshot["open_findings"] == ["missing customer proof"]
    assert json.loads(status_path.read_text())["branch"]


def test_social_permission_is_simulated_and_default_denies_real_publish():
    denied = FounderProfile().decide_permission("publish_linkedin_post")
    assert denied["decision"] == "deny"
    assert denied["is_real_authorization"] is False
    approved = FounderProfile(permission_policy="approve_simulated").decide_permission("publish_linkedin_post")
    assert approved["decision"] == "approve_simulated"
    assert approved["is_real_authorization"] is False


def test_gtm_draft_uses_progress_signals_not_customer_traction_claims():
    draft = GTMStatusAgent._build_draft({
        "latest_commit": "abc123 latest change",
        "testing_rounds": 4,
        "product_questions": 3,
    })
    assert "4 founder-simulation round(s)" in draft
    assert "not customer traction claims" in draft


def test_a2a_client_extracts_final_text_artifact():
    body = {
        "result": {
            "history": [{"parts": [{"text": "question"}]}],
            "artifacts": [{"name": "product-response", "parts": [{"text": "{\"is_clear\": true}"}]}],
        }
    }
    texts = ASCMJsonRpcClient._collect_text(body["result"])
    assert texts[-1] == "{\"is_clear\": true}"

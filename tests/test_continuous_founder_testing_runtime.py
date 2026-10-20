import json
import subprocess
from pathlib import Path

import pytest

from orchestrator.testing_agent.founder_journey import JourneyEvent
from orchestrator.testing_agent.runtime import (
    ASCMJsonRpcClient,
    AgentTerminalViews,
    ContinuousFounderTestingRuntime,
    ConversationStoryLog,
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
        review_delay_seconds=0,
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



def test_gtm_deduplicates_post_requests_by_commit_not_test_round():
    first = {"latest_commit": "abc123", "testing_rounds": 1, "product_questions": 1}
    later_same_commit = {"latest_commit": "abc123", "testing_rounds": 20, "product_questions": 15}
    next_commit = {"latest_commit": "def456", "testing_rounds": 21, "product_questions": 16}
    assert GTMStatusAgent.status_fingerprint(first) == GTMStatusAgent.status_fingerprint(later_same_commit)
    assert GTMStatusAgent.status_fingerprint(first) != GTMStatusAgent.status_fingerprint(next_commit)


def test_product_agent_unclear_without_question_is_not_a_pass(tmp_path):
    client = FakeASCMClient([product_response(clear=False, confidence=0.4)])
    runtime = ContinuousFounderTestingRuntime(tmp_path, client=client, rounds_per_session=1)
    result = runtime.run_product_session("customer evidence")
    assert result["is_clear"] is False
    assert any("did not establish clarity" in finding for finding in runtime.findings)


def test_three_consecutive_interface_failures_trip_circuit_breaker(tmp_path):
    class BrokenClient:
        base_url = None
        def send(self, agent_id, prompt, session_id):
            raise ConnectionError("gateway down")

    runtime = ContinuousFounderTestingRuntime(tmp_path, client=BrokenClient(), rounds_per_session=1)
    # The run loop should stop after three consecutive failures, without infinite retries.
    report = runtime.run(sessions=0)
    assert runtime.stop.is_set()
    assert any("Circuit breaker" in finding for finding in report["open_findings"])



def test_a2a_client_uses_version_one_jsonrpc_and_agent_metadata(monkeypatch):
    captured = {}
    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {"jsonrpc": "2.0", "result": {
                "history": [{"parts": [{"text": "original question"}]}],
                "artifacts": [{"name": "product-response", "parts": [{"text": "next question"}]}],
            }}

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, body=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("orchestrator.testing_agent.runtime.httpx.post", fake_post)
    client = ASCMJsonRpcClient("http://127.0.0.1:8090")
    result = client.send("product", "Ask one question", "session-123")
    assert result == "next question"
    assert captured["headers"]["A2A-Version"] == "1.0"
    assert captured["body"]["method"] == "SendMessage"
    assert captured["body"]["params"]["message"]["metadata"]["ascm"]["agent_id"] == "product"
    assert captured["body"]["params"]["message"]["contextId"] == "session-123"



def test_acceptance_gate_fails_when_mentor_or_handoff_evidence_is_missing(tmp_path):
    runtime = ContinuousFounderTestingRuntime(tmp_path, client=FakeASCMClient([]))
    runtime.journey_events.append(
        JourneyEvent(
            "mentor_goal_observed", "testing_agent", evidence_ref="goal:1"
        )
    )
    summary = runtime._acceptance_summary()
    assert summary["passed"] is False
    failed = {item["criterion"] for item in summary["criteria"] if not item["passed"]}
    assert "mentor_goal_context" in failed
    assert "handoff_traceability" in failed


def test_visible_terminal_routes_agent_messages_to_relevant_windows():
    assert AgentTerminalViews.roles_for_line("[PRODUCT AGENT → TESTING AGENT] Who is the buyer?") == ("product", "testing")
    assert AgentTerminalViews.roles_for_line("[TESTING AGENT → PRODUCT AGENT] Early-stage founders") == ("testing",)
    assert AgentTerminalViews.roles_for_line("[MENTOR AGENT → TESTING AGENT] Validate demand first") == ("mentor", "testing")
    assert AgentTerminalViews.roles_for_line("[GOAL AGENT] branch=main") == ("goal",)
    assert AgentTerminalViews.roles_for_line("[GTM AGENT] Draft saved") == ("gtm",)


def test_question_answer_exchange_pauses_for_configured_review_delay(tmp_path, monkeypatch):
    client = FakeASCMClient([product_response(question="Who is the target customer?")])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, client=client, rounds_per_session=1, review_delay_seconds=5,
    )
    delays = []
    monkeypatch.setattr("orchestrator.testing_agent.runtime.time.sleep", delays.append)
    runtime.run_product_session("target user")
    assert delays == [5]


def test_conversation_story_log_records_timestamped_ordered_events(tmp_path):
    logger = ConversationStoryLog(tmp_path / ".ascm_history", "session-story-1")
    first = logger.record(
        "TESTING AGENT", "MENTOR AGENT", "request", "What is the founder's goal?",
        metadata={"task_id": "task-1", "correlation_id": "session-story-1"},
    )
    second = logger.record(
        "MENTOR AGENT", "TESTING AGENT", "response", "Validate the core assumption first.",
        metadata={"task_id": "task-1", "correlation_id": "session-story-1"},
    )

    events = [json.loads(line) for line in logger.jsonl_path.read_text().splitlines()]
    story = logger.text_path.read_text()
    assert first["sequence"] == 1 and second["sequence"] == 2
    assert first["timestamp"] and second["timestamp"]
    assert events[0]["speaker"] == "TESTING AGENT"
    assert events[1]["speaker"] == "MENTOR AGENT"
    assert "What is the founder's goal?" in story
    assert "Validate the core assumption first." in story
    assert "#0001" in story and "#0002" in story



def test_product_response_schema_self_heals_once_and_continues_founder_journey(tmp_path):
    malformed = json.dumps({
        "detected_domain": "software engineering",
        "confidence_score": 0.55,
        "functional_completeness": 0.5,
        "nfr_completeness": 0.4,
        "is_clear": False,
        "understanding": "ASCM is a multi-agent software delivery system.",
        "clarification_questions": {"unexpected_shape": 7},
        "checkpoint_clarification_items": [],
    })
    client = FakeASCMClient([
        malformed,
        product_response(question="Who is the target user and what evidence validates the need?"),
    ])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, profile=FounderProfile(), client=client, rounds_per_session=1,
        review_delay_seconds=0,
    )

    result = runtime.run_product_session("problem and value proposition")

    assert result["clarification_questions"] == [
        "Who is the target user and what evidence validates the need?"
    ]
    assert len(client.calls) == 2  # initial request + exactly one schema repair
    assert runtime.questions_asked == 1
    assert runtime.rounds_completed == 1
    assert runtime.self_heal_attempts == 1
    assert runtime.self_heal_successes == 1
    assert runtime.self_heal_failures == 0
    story = runtime.story_log.text_path.read_text()
    assert "REPAIR_REQUESTED" in story
    assert "REPAIR_SUCCEEDED" in story


def test_product_response_schema_self_heal_is_bounded_and_fails_closed(tmp_path):
    malformed = json.dumps({
        "detected_domain": "software engineering",
        "confidence_score": 0.55,
        "is_clear": False,
        "understanding": "Incomplete response",
        "clarification_questions": {"unexpected_shape": 7},
    })
    client = FakeASCMClient([malformed, malformed, malformed])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, client=client, rounds_per_session=1, review_delay_seconds=0,
    )

    result = runtime.run_product_session("problem and value proposition")

    assert result["is_clear"] is False
    assert len(client.calls) == 2  # never loops on a bad response
    assert runtime.self_heal_attempts == 1
    assert runtime.self_heal_successes == 0
    assert runtime.self_heal_failures == 1
    assert runtime.rounds_completed == 0
    assert any("self-heal failed after one retry" in finding for finding in runtime.findings)


def test_product_response_normalizes_recognized_question_shapes_without_retry():
    result = ContinuousFounderTestingRuntime._parse_product_result(json.dumps({
        "detected_domain": "software engineering",
        "confidence_score": 0.5,
        "is_clear": False,
        "understanding": "Needs clarification",
        "clarification_questions": {"question": "Who is the target user?"},
    }))

    assert result["clarification_questions"] == ["Who is the target user?"]



def test_forced_acceptance_gateway_starts_from_isolated_workspace(tmp_path, monkeypatch):
    from orchestrator.testing_agent import runtime as runtime_module

    monkeypatch.setenv("ASCM_A2A_FORCE_START_SERVER", "1")
    calls = {"popen": None, "get": 0}

    class FakeProcess:
        def poll(self):
            return None

    def fake_popen(args, *, cwd, env, stdout, stderr, start_new_session):
        calls["popen"] = {"cwd": cwd, "env": env}
        return FakeProcess()

    class FakeResponse:
        status_code = 200

    def fake_get(url, timeout):
        calls["get"] += 1
        assert calls["popen"] is not None
        return FakeResponse()

    monkeypatch.setattr(runtime_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(runtime_module.httpx, "get", fake_get)
    process = runtime_module.ensure_gateway(
        "http://127.0.0.1:18091", tmp_path, start_server=True
    )

    assert process is not None
    assert calls["popen"]["cwd"] == tmp_path
    assert calls["popen"]["env"]["ASCM_A2A_WORKSPACE"] == str(tmp_path)
    assert calls["popen"]["env"]["ASCM_A2A_PORT"] == "18091"


def test_testing_agent_logs_successful_a2a_handoff_with_correlation_ids(tmp_path):
    client = FakeASCMClient(["Mentor recommends validating demand before implementation."])
    runtime = ContinuousFounderTestingRuntime(
        tmp_path, client=client, rounds_per_session=1, review_delay_seconds=0,
    )

    response = runtime._send_agent("mentor", "Review founder goal", runtime.session_id)

    assert response == "Mentor recommends validating demand before implementation."
    events = [json.loads(line) for line in runtime.story_log.jsonl_path.read_text().splitlines()]
    handoff = [event for event in events if event["metadata"].get("agent_id") == "mentor"]
    assert [event["event_type"] for event in handoff] == ["request", "response"]
    assert handoff[0]["metadata"]["task_id"] == handoff[1]["metadata"]["task_id"]
    assert handoff[0]["metadata"]["correlation_id"] == runtime.session_id
    assert handoff[0]["speaker"] == "TESTING AGENT"
    assert handoff[1]["speaker"] == "MENTOR AGENT"


def test_testing_agent_logs_failed_a2a_handoff_with_correlation_ids(tmp_path):
    class BrokenClient:
        def send(self, agent_id, prompt, session_id):
            raise TimeoutError("simulated A2A timeout")

    runtime = ContinuousFounderTestingRuntime(
        tmp_path, client=BrokenClient(), rounds_per_session=1, review_delay_seconds=0,
    )

    with pytest.raises(TimeoutError, match="simulated A2A timeout"):
        runtime._send_agent("mentor", "Review founder goal", runtime.session_id)

    events = [json.loads(line) for line in runtime.story_log.jsonl_path.read_text().splitlines()]
    handoff = [event for event in events if event["metadata"].get("agent_id") == "mentor"]
    assert [event["event_type"] for event in handoff] == ["request", "request_failed"]
    assert handoff[0]["metadata"]["task_id"] == handoff[1]["metadata"]["task_id"]
    assert handoff[0]["metadata"]["correlation_id"] == runtime.session_id
    assert "TimeoutError" in handoff[1]["message"]


def test_gtm_specialist_request_and_response_are_written_to_conversation_story(tmp_path):
    import queue
    import threading

    history = tmp_path / ".ascm_history"
    history.mkdir()
    status_path = history / "testing_agent_status.json"
    status_path.write_text(json.dumps({
        "latest_commit": "abc123 test",
        "testing_rounds": 1,
        "product_questions": 1,
        "sessions_completed": 1,
        "open_findings": [],
    }))
    stop = threading.Event()
    story = ConversationStoryLog(history, "gtm-story-session")
    agent = GTMStatusAgent(
        tmp_path, status_path, stop, queue.Queue(), queue.Queue(), 0.5,
        client=FakeASCMClient(["Position this as a workflow-coordination tool; avoid traction claims."]),
        story_log=story,
    )
    timer = threading.Timer(0.25, stop.set)
    timer.start()
    try:
        agent.run()
    finally:
        stop.set()
        timer.cancel()

    events = [json.loads(line) for line in story.jsonl_path.read_text().splitlines()]
    handoff = [event for event in events if event["metadata"].get("channel") == "internal_gtm_review"]
    assert [event["event_type"] for event in handoff] == ["request", "response"]
    assert handoff[0]["metadata"]["task_id"] == handoff[1]["metadata"]["task_id"]
    assert handoff[0]["metadata"]["correlation_id"] == handoff[1]["metadata"]["correlation_id"]
    assert handoff[0]["speaker"] == "GTM STATUS AGENT"
    assert handoff[1]["speaker"] == "GTM AGENT"

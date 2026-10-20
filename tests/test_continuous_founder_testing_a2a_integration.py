import json

from fastapi.testclient import TestClient

from orchestrator.a2a.server import create_app
from orchestrator.testing_agent.runtime import ASCMJsonRpcClient


def test_testing_agent_a2a_client_round_trips_through_real_gateway(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.a2a.server._run_specialist",
        lambda agent_id, prompt: json.dumps({
            "agent": agent_id,
            "clarification_questions": ["Who is the target customer?"],
            "is_clear": False,
        }),
    )
    gateway = TestClient(create_app(host="127.0.0.1", port=8090))
    client = ASCMJsonRpcClient("http://testserver", http_client=gateway)
    result = client.send("product", "Interview the simulated founder.", "session-e2e-1")
    payload = json.loads(result)
    assert payload["agent"] == "product"
    assert payload["clarification_questions"] == ["Who is the target customer?"]
    assert payload["is_clear"] is False

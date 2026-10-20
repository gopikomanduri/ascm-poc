import json

from fastapi.testclient import TestClient

from orchestrator.a2a.server import create_app


def test_a2a_jsonrpc_message_send_routes_through_governed_coordinator(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.a2a.server._run_specialist",
        lambda agent_id, prompt: json.dumps({"agent": agent_id, "prompt": prompt}),
    )
    client = TestClient(create_app(host="127.0.0.1", port=8090))
    response = client.post(
        "/a2a/jsonrpc",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": "request-1",
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "message-1",
                    "role": "ROLE_USER",
                    "parts": [{"text": "Review this product idea"}],
                    "metadata": {"ascm": {"agent_id": "product"}},
                }
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["jsonrpc"] == "2.0"
    serialized = json.dumps(payload)
    assert "product-response" in serialized
    assert "Review this product idea" in serialized

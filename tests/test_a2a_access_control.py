"""A2A gateway authentication must exempt only the public agent-card endpoint."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orchestrator.a2a.server import PUBLIC_AGENT_CARD_PATH, _install_access_control


def test_only_exact_agent_card_endpoint_is_public(monkeypatch):
    monkeypatch.setenv("ASCM_A2A_TOKEN", "test-token")
    app = FastAPI()

    @app.get(PUBLIC_AGENT_CARD_PATH)
    async def agent_card():
        return {"name": "public-card"}

    @app.get("/.well-known/private")
    async def private_well_known_route():
        return {"secret": "not-public"}

    @app.get("/private")
    async def private_route():
        return {"secret": "not-public"}

    _install_access_control(app, "127.0.0.1")
    client = TestClient(app)

    assert client.get(PUBLIC_AGENT_CARD_PATH).status_code == 200
    assert client.get("/.well-known/private").status_code == 401
    assert client.get("/private").status_code == 401

    assert client.get("/.well-known/private", headers={"Authorization": "Bearer test-token"}).status_code == 200

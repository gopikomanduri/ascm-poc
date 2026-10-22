"""The dashboard's write endpoints must not be reachable cross-site, from other hosts, or without a token when one is set."""
import http.client
import json
import threading

import pytest

from orchestrator import dashboard, dashboard_security


@pytest.fixture()
def server(monkeypatch, tmp_path):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("ASCM_DASHBOARD_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    srv = dashboard.DashboardServer(host="127.0.0.1", port=0)
    from http.server import ThreadingHTTPServer
    srv.server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.DashboardHTTPRequestHandler)
    srv.server.daemon_threads = True
    threading.Thread(target=srv.server.serve_forever, daemon=True).start()
    yield srv.server.server_address[1]
    srv.server.shutdown()


def call(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    h = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    c.putrequest(method, path, skip_host=True)
    for k, v in h.items():
        c.putheader(k, v)
    data = json.dumps(body).encode() if body is not None else b""
    if method == "POST":
        c.putheader("Content-Length", str(len(data)))
    c.endheaders(data)
    r = c.getresponse()
    raw = r.read()
    try:
        return r.status, json.loads(raw)
    except ValueError:
        return r.status, raw


def test_cross_origin_post_is_blocked(server):
    status, _ = call(server, "POST", "/api/action/approve", {}, {"Origin": "https://evil.example"})
    assert status == 403


def test_dns_rebinding_host_is_blocked(server):
    status, _ = call(server, "GET", "/api/auth/current", headers={"Host": "attacker.example"})
    assert status == 403


def test_same_origin_post_is_allowed(server):
    status, body = call(server, "POST", "/api/action/approve", {}, {"Origin": f"http://127.0.0.1:{server}"})
    assert status == 200


def test_token_required_when_configured(server, monkeypatch):
    monkeypatch.setenv("ASCM_DASHBOARD_TOKEN", "s3cret-token")
    assert call(server, "POST", "/api/action/approve", {})[0] == 401
    assert call(server, "POST", "/api/action/approve", {}, {"X-ASCM-Token": "wrong"})[0] == 401
    assert call(server, "POST", "/api/action/approve", {}, {"X-ASCM-Token": "s3cret-token"})[0] == 200


def test_hosted_mode_disables_sensitive_routes_without_token(server, monkeypatch):
    monkeypatch.setenv("PORT", "10000")
    status, body = call(server, "POST", "/api/action/launch", {"goal": "x"})
    assert status == 403 and "disabled" in body["message"]
    assert call(server, "GET", "/health")[0] in (200, 404)  # public routes stay reachable


def test_no_wildcard_cors(server):
    c = http.client.HTTPConnection("127.0.0.1", server, timeout=5)
    c.request("GET", "/api/runs")
    r = c.getresponse()
    r.read()
    assert r.getheader("Access-Control-Allow-Origin") is None


def test_stored_api_keys_are_never_returned():
    out = dashboard_security.redact_secrets({"user": {"name": "a", "gemini_api_key": "AIza-real", "nested": {"client_secret": "x"}}})
    assert "AIza-real" not in json.dumps(out) and out["user"]["gemini_api_key_set"] is True
    assert out["user"]["nested"]["client_secret_set"] is True


def test_launch_rejects_paths_outside_workspace(server, tmp_path):
    status, body = call(server, "POST", "/api/action/launch", {"goal": "g", "repos": ["/etc"]})
    assert status == 400 and "workspace" in body["message"]
    status, _ = call(server, "POST", "/api/product/analyze-repo", {"repo_path": "/"})
    assert status == 400


def test_public_endpoints_are_rate_limited(server):
    dashboard_security.PUBLIC_RATE_LIMITER._hits.clear()
    codes = [call(server, "POST", "/api/waitlist", {"email": f"a{i}@b.io"})[0] for i in range(12)]
    assert 429 in codes

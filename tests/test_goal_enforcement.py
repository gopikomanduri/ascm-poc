"""Regression tests that turn ASCM's stated goals (docs: failures stay visible, approval is real,
code/secrets are protected) into build-failing checks."""
import http.client
import json
import os
import threading
import time
from http.server import HTTPServer
from pathlib import Path
from unittest import mock

import pytest

from orchestrator.engine.verifier import VerifierEngine
from orchestrator.git_service import GitService
from orchestrator.state import SharedBlackboard, TaskItem


# --- Goal 1 / 14: the blackboard must hold every field the pipeline writes ---------------------------------------

def test_blackboard_declares_incremental_pipeline_fields():
    state = SharedBlackboard(user_goal="g", target_repos=[])
    state.incremental_providers = ["/a"]
    state.incremental_consumers = ["/b"]
    state.architecture_plan = {"k": 1}
    state.pending_tasks = [TaskItem(id="1", title="t", description="d")]
    assert state.pending_tasks[0].id == "1"


def test_core_only_uses_declared_state_fields():
    import re
    src = Path("orchestrator/orchestrator_core.py").read_text()
    used = set(re.findall(r"self\.state\.([a-zA-Z_]+)", src))
    assert used <= set(SharedBlackboard.model_fields), used - set(SharedBlackboard.model_fields)


# --- Goal 14: no fabricated success --------------------------------------------------------------------------------

def test_verifier_does_not_invent_a_passing_test():
    info = VerifierEngine.parse_test_suite("no recognizable output", "go", True)
    assert info["total_tests"] == 0 and info["passed_count"] == 0
    assert info["test_cases"] == [] and info["no_tests_detected"] is True


def test_synthetic_fallback_is_opt_in(monkeypatch):
    from orchestrator.agents import base
    monkeypatch.delenv("ALLOW_SYNTHETIC_FALLBACK", raising=False)
    assert 'get("ALLOW_SYNTHETIC_FALLBACK", "0")' in Path(base.__file__).read_text()


def test_verifier_timeout_reports_failure(monkeypatch):
    import subprocess
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=1)
    monkeypatch.setattr(subprocess, "run", boom)
    result, _ = VerifierEngine._execute(["true"], ".")
    assert result.returncode != 0 and "timed out" in result.stderr


def test_pr_description_does_not_preticks_unverified_boxes():
    md = GitService.generate_pr_description("g", ["a.py"], verification={"tests_passed": False, "vet_passed": True})
    assert "[ ] Native test suite passed" in md
    assert "[ ] Human review of the diff" in md
    assert "[x] Peer code review" not in md


# --- Goal 13: dashboard hardening ---------------------------------------------------------------------------------

def test_static_serving_is_confined(tmp_path):
    from orchestrator import dashboard
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET")
    static = tmp_path / "static"
    static.mkdir()
    (static / "ok.txt").write_text("fine")
    with mock.patch.object(dashboard, "STATIC_DIR", static):
        class H(dashboard.DashboardHTTPRequestHandler):
            def __init__(self):
                self.sent = []
                self.wfile = type("W", (), {"write": lambda _s, b: self.sent.append(b)})()
            def send_response(self, c, *a): self.code = c
            def send_header(self, *a): pass
            def end_headers(self): pass
        h = H()
        h._serve_static_file("../secret.txt")
        assert h.code == 404 and b"TOP-SECRET" not in b"".join(h.sent)
        h2 = H()
        h2._serve_static_file("ok.txt")
        assert h2.code == 200


def test_dashboard_binds_loopback_by_default():
    from orchestrator.dashboard import DashboardServer
    assert DashboardServer().host == "127.0.0.1"


def test_otp_has_no_universal_code_and_no_echo_outside_dev_mode(tmp_path, monkeypatch):
    from orchestrator.auth.user_manager import UserManager
    monkeypatch.delenv("ASCM_DEV_MODE", raising=False)
    mgr = UserManager(store_path=tmp_path / "u.json")
    res = mgr.send_otp("a@b.io")
    assert "dev_otp" not in res
    assert mgr.verify_otp("a@b.io", "123456")["status"] == "error"


# --- Goal 12/13: notifier cannot be injected through workspace names -----------------------------------------------

def test_macos_notification_passes_text_as_argv_not_script(monkeypatch):
    from orchestrator.mentor import notifier
    calls = []
    monkeypatch.setattr(notifier.sys, "platform", "darwin")
    monkeypatch.setattr(notifier.subprocess, "run",
                        lambda cmd, **k: calls.append(cmd) or mock.Mock(returncode=0))
    evil = 'x\\" & do shell script "id" & \\"'
    notifier.CrossPlatformNotifier.notify(evil, evil)
    script = calls[0][calls[0].index("-e") + 1]
    assert "do shell script" not in script and evil in calls[0]


# --- PayPulse reference app: signature is mandatory, duplicates never credit --------------------------------------

@pytest.fixture()
def paypulse_server(monkeypatch):
    # Several reference products ship a top-level "app" package; load PayPulse's in isolation.
    import importlib
    import sys
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.syspath_prepend(str(Path("products/paypulse-sentinel/api-gateway").resolve()))
    pp = importlib.import_module("app.main")
    srv = HTTPServer(("127.0.0.1", 0), pp.PayPulseHTTPHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield pp, srv.server_address[1]
    srv.shutdown()


def _post(port, path, body, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("POST", path, body=body, headers=headers or {})
    r = c.getresponse()
    return r.status, json.loads(r.read() or b"{}")


def test_paypulse_rejects_unsigned_webhook(paypulse_server):
    pp, port = paypulse_server
    before = pp.TOKEN_ESCROW.get_balance("tenant_demo_acme")
    body = json.dumps({"id": "evt_unsigned", "type": "checkout.session.completed", "data": {"amount": 99999}})
    status, _ = _post(port, "/api/v1/stripe/webhook", body)
    assert status == 400
    assert pp.TOKEN_ESCROW.get_balance("tenant_demo_acme") == before


def test_paypulse_signed_webhook_credits_once(paypulse_server):
    pp, port = paypulse_server
    body = json.dumps({"id": "evt_signed_1", "type": "checkout.session.completed", "data": {"amount": 2900}})
    ts = int(time.time())
    sig = f"t={ts},v1={pp.STRIPE_GATEWAY.compute_signature(body, ts)}"
    before = pp.TOKEN_ESCROW.get_balance("tenant_demo_acme")
    assert _post(port, "/api/v1/stripe/webhook", body, {"Stripe-Signature": sig})[0] == 200
    after_first = pp.TOKEN_ESCROW.get_balance("tenant_demo_acme")
    assert after_first > before
    _post(port, "/api/v1/stripe/webhook", body, {"Stripe-Signature": sig})
    assert pp.TOKEN_ESCROW.get_balance("tenant_demo_acme") == after_first


def test_paypulse_escrow_rejects_negative_tokens(paypulse_server):
    _, port = paypulse_server
    status, _ = _post(port, "/api/v1/tokens/escrow", json.dumps({"tenant_id": "t", "tokens_needed": -500}))
    assert status == 400


# --- A2A gateway access control -------------------------------------------------------------------------------------

def test_a2a_rejects_browser_origin_and_foreign_host(monkeypatch):
    from fastapi.testclient import TestClient
    from orchestrator.a2a.server import create_app
    monkeypatch.delenv("ASCM_A2A_TOKEN", raising=False)
    client = TestClient(create_app(host="127.0.0.1", port=8091))
    assert client.get("/.well-known/agent-card.json", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/.well-known/agent-card.json", headers={"Host": "evil.example"}).status_code == 403
    assert client.get("/.well-known/agent-card.json").status_code == 200


def test_a2a_token_is_enforced_and_required_off_loopback(monkeypatch):
    from fastapi.testclient import TestClient
    from orchestrator.a2a.server import create_app
    monkeypatch.setenv("ASCM_A2A_TOKEN", "t0ken")
    client = TestClient(create_app(host="127.0.0.1", port=8092))
    assert client.post("/a2a/jsonrpc", json={}).status_code == 401
    assert client.post("/a2a/jsonrpc", json={}, headers={"Authorization": "Bearer t0ken"}).status_code != 401
    monkeypatch.delenv("ASCM_A2A_TOKEN")
    monkeypatch.setenv("ASCM_A2A_ALLOW_REMOTE", "1")
    with pytest.raises(ValueError):
        create_app(host="0.0.0.0", port=8093)


def test_mentor_goal_is_not_sent_to_cloud_without_consent(monkeypatch, tmp_path):
    from orchestrator.mentor.proactive_mentor import ASCMProactiveMentor
    sent = []
    import google.genai as genai
    mentor = ASCMProactiveMentor(repo_path=str(tmp_path))  # constructing a provider is not sending data
    monkeypatch.setattr(genai, "Client", lambda *a, **k: sent.append("client") or (_ for _ in ()).throw(AssertionError("called")))
    out = mentor.clarify_goal_and_pre_validate("build a thing")
    assert not sent and out["clarified_goal"] == "build a thing"


# --- Goal 7/12/14: a draft is not a send; nothing is reported as done unless it happened ----------------------------

def test_sentiment_decline_wins_and_words_match_whole():
    from orchestrator.gtm.channels.adapters import SentimentClassifier as S
    assert S.classify("Not interested, please remove me") == "NEGATIVE"
    assert S.classify("I'm not interested") == "NEGATIVE"
    assert S.classify("Happy to hop on a call Tuesday") == "INTERESTED"
    assert S.classify("I recall nothing about this") == "UNCLEAR"  # 'call' inside 'recall' is not interest


def test_outbound_is_blocked_without_authorization_and_never_reports_sent(monkeypatch):
    import asyncio
    from orchestrator.gtm.channels.adapters import ComposioGTMAdapter
    monkeypatch.delenv("ASCM_ALLOW_AUTONOMOUS_OUTREACH", raising=False)
    monkeypatch.setenv("SMARTLEAD_API_KEY", "k")
    monkeypatch.setenv("BUFFER_API_KEY", "k")
    a = ComposioGTMAdapter()
    assert asyncio.run(a.send_email_sequence_step("x@y.io", "s", "b", 1)) is False
    assert asyncio.run(a.dispatch_cal_com_booking_email("x@y.io", "https://cal", "X")) is False
    assert asyncio.run(a.schedule_social_post("linkedin", "hello")) == ""


def test_unconfigured_provider_never_claims_success(monkeypatch):
    import asyncio
    from orchestrator.gtm.channels.adapters import ComposioGTMAdapter
    monkeypatch.setenv("ASCM_ALLOW_AUTONOMOUS_OUTREACH", "1")
    monkeypatch.delenv("SMARTLEAD_API_KEY", raising=False)
    monkeypatch.delenv("BUFFER_API_KEY", raising=False)
    a = ComposioGTMAdapter()
    assert asyncio.run(a.send_email_sequence_step("x@y.io", "s", "b", 1)) is False


def test_gtm_workflow_stops_at_the_approval_gate():
    import asyncio
    from orchestrator.workflows.gtm_workflows import GTMStandaloneWorkflow
    wf = GTMStandaloneWorkflow()
    res = asyncio.run(wf.run(execution_mode="GTM_ONLY", product_thesis="t", icp_spec={}, cal_com_link="https://cal"))
    assert res["status"] == "AWAITING_FOUNDER_APPROVAL" and res["meetings_booked"] == 0


# --- Goal 14/17: published claims must not outrun the evidence -----------------------------------------------------

def test_published_materials_do_not_present_assumptions_as_proof():
    import re
    banned = [r"59\.1%", r"16\.7[×x]", r"78\.4%", r"first multi-repo", r"industry's first", r"only AI engineering platform"]
    files = ["README.md", "VERIFIED_FACTS.md", "tools/generate_documents.py", "tools/generate_marketing_decks.py",
             "tools/mr_bench.py"]
    for f in files:
        text = Path(f).read_text()
        for pat in banned:
            assert not re.search(pat, text), f"{f} still contains unsupported claim /{pat}/"
    assert "assumption-driven" in Path("docs/research/MATH-WHITEPAPER.md").read_text()
    assert "not an agent benchmark result" in Path("docs/research/MR-BENCH-RESULTS.md").read_text()


def test_mr_bench_report_has_no_cross_agent_comparison_table():
    text = Path("tools/mr_bench.py").read_text()
    assert "Devin (Cognition)" not in text and "SWE-agent |" not in text


# --- Cost control and provider robustness ---------------------------------------------------------------------------

def test_llm_call_budget_stops_runaway_loops(monkeypatch):
    from orchestrator.agents import base
    monkeypatch.setenv("ASCM_MAX_LLM_CALLS", "3")
    base.reset_llm_budget()
    for _ in range(3):
        base._charge_llm_call()
    with pytest.raises(base.LLMBudgetExceeded):
        base._charge_llm_call()


def test_transient_provider_errors_are_retried_but_permanent_ones_are_not(monkeypatch):
    import urllib.error
    from orchestrator.agents import base
    monkeypatch.setenv("ASCM_LLM_RETRIES", "2")
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError("u", 429, "rate limited", {}, None)
        return "ok"
    assert base._with_retries(flaky) == "ok" and calls["n"] == 3

    def forbidden():
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 401, "bad key", {}, None)
    calls["n"] = 0
    with pytest.raises(urllib.error.HTTPError):
        base._with_retries(forbidden)
    assert calls["n"] == 1


def test_fenced_json_is_unwrapped():
    from orchestrator.agents.base import _strip_json_fences
    assert json.loads(_strip_json_fences('```json\n{"a": 1}\n```')) == {"a": 1}
    assert _strip_json_fences('{"a": 1}') == '{"a": 1}'


# --- Credentials at rest and OAuth state --------------------------------------------------------------------------

def test_user_store_is_owner_only(tmp_path):
    import os
    import stat
    from orchestrator.auth.user_manager import UserManager
    mgr = UserManager(store_path=tmp_path / "users.json")
    mgr.send_otp("a@b.io")
    mgr.verify_otp("a@b.io", mgr.otp_cache["a@b.io"]["otp"])
    assert stat.S_IMODE(os.stat(tmp_path / "users.json").st_mode) == 0o600


def test_oauth_csrf_state_survives_a_new_handler_per_request(monkeypatch):
    from orchestrator.auth import github_oauth as g
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    first, second = g.GitHubOAuthHandler(), g.GitHubOAuthHandler()
    first._states["abc"] = __import__("time").time()
    assert "abc" in second._states


def test_domain_ids_cannot_escape_the_cache_dir():
    from orchestrator.domain.domain_knowledge_engine import _safe_domain_id
    assert "/" not in _safe_domain_id("../../etc/passwd") and ".." not in _safe_domain_id("../../etc/passwd")
    assert _safe_domain_id("") == "custom_domain"


def test_installer_protects_env_and_supports_pinning():
    text = Path("install.sh").read_text()
    assert 'chmod 600 "$INSTALL_DIR/.env"' in text and "ASCM_REF" in text


# --- "Verified" must mean the callers still work: guards found by live multi-repo trials ----------------------

OLD_SERVICE = (
    "_STORE = []\n\n\ndef create_transaction(amount_cents, memo=''):\n    return {}\n\n\ndef list_transactions():\n    return []\n"
)
REWRITE = "class LedgerService:\n    def create_transaction(self, payload):\n        return {}\n"


def test_replacing_public_functions_with_a_class_is_rejected():
    from orchestrator.engine.api_surface import contract_problems
    problems = contract_problems("api/service.py", OLD_SERVICE, REWRITE, "Add a currency field to transactions")
    assert any("create_transaction" in p and "removed" in p for p in problems)


def test_additive_change_and_requested_rename_are_allowed():
    from orchestrator.engine.api_surface import contract_problems
    additive = OLD_SERVICE.replace("memo=''", "memo='', currency='USD'")
    assert contract_problems("api/service.py", OLD_SERVICE, additive, "Add a currency field") == [] or all(
        "signature changed" not in p for p in contract_problems("api/service.py", OLD_SERVICE, additive, "Add a currency parameter to create_transaction"))
    renamed = OLD_SERVICE.replace("amount_cents", "amount_minor")
    assert contract_problems("api/service.py", OLD_SERVICE, renamed, "Rename amount_cents to amount_minor") == []


def test_deleting_existing_tests_is_flagged():
    from orchestrator.engine.api_surface import contract_problems
    old = "class T:\n    def test_a(self): pass\n    def test_b(self): pass\n"
    new = "class T:\n    def test_a(self): pass\n"
    assert any("deleted" in p and "test_b" in p for p in contract_problems("api/test_service.py", old, new, "g"))


def test_malformed_json_is_retried_not_fatal(monkeypatch):
    from orchestrator.agents.base import BaseAgent

    class P:
        model = "m"
        calls = 0

        def generate(self, prompt, system_instruction, json_mode=False, **kw):
            P.calls += 1
            return '{"a": 1,' if P.calls == 1 else '{"a": 1}'

    agent = BaseAgent.__new__(BaseAgent)
    agent.provider, agent.system_instruction, agent.tier = P(), "sys", "fast"
    assert json.loads(agent.call("x", json_mode=True)) == {"a": 1} and P.calls == 2


def test_wrong_language_task_targets_are_dropped(tmp_path):
    from orchestrator.orchestrator_core import OrchestratorEngine
    from orchestrator.state import RepoContract, SharedBlackboard, TaskItem
    repo = tmp_path / "api"
    repo.mkdir()
    (repo / "requirements.txt").write_text("")
    eng = OrchestratorEngine.__new__(OrchestratorEngine)
    eng.state = SharedBlackboard(user_goal="g", target_repos=[str(repo)])
    eng.state.contracts[str(repo)] = RepoContract(repo_path=str(repo), name="api", role="provider", allowed_paths=["api/"])
    eng.state.task_breakdown = [
        TaskItem(id="1", title="t", description="d", target_file="api/service.go"),
        TaskItem(id="2", title="t", description="d", target_file="api/service.py"),
    ]
    eng._log = lambda m: None
    eng._normalize_task_targets([str(repo)])
    assert eng.state.task_breakdown[0].target_file == "" and eng.state.task_breakdown[1].target_file == "api/service.py"


def test_coder_sees_existing_tests_and_is_told_to_keep_them():
    from orchestrator.agents.all_agents import PolyglotCoderAgent
    seen = {}
    agent = PolyglotCoderAgent.__new__(PolyglotCoderAgent)
    agent.call = lambda prompt, json_mode=False: seen.setdefault("p", prompt) and "{}"
    agent.run("code", "do it", "a/s.py", "a/test_s.py", "contract", language="python",
              existing_tests="def test_old(): pass")
    assert "def test_old(): pass" in seen["p"] and "KEEP every existing test" in seen["p"]


def test_rate_limit_errors_are_retried_with_a_real_wait(monkeypatch):
    from orchestrator.agents import base
    monkeypatch.setenv("ASCM_LLM_RETRIES", "1")
    slept = []
    monkeypatch.setattr(base.time, "sleep", lambda s: slept.append(s))
    n = {"c": 0}

    def quota():
        n["c"] += 1
        if n["c"] == 1:
            raise RuntimeError("All candidate Gemini models failed. Last error: 429 RESOURCE_EXHAUSTED")
        return "ok"
    assert base._with_retries(quota) == "ok" and slept and slept[0] >= 20

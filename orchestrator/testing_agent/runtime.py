"""Continuous ASCM founder-simulation test harness.

Run from one terminal with:
    python -m orchestrator.testing_agent.runtime --workspace . --rounds-per-session 8

This is a test persona, not the real founder. Social approvals are simulated only;
the harness intentionally has no LinkedIn/social publishing adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

logger = logging.getLogger("ASCM.TestingAgent")
PROBE_AREAS = (
    "problem and value proposition",
    "target user and ideal customer profile",
    "alternatives and differentiation",
    "customer evidence and willingness to pay",
    "privacy, security, and permissions",
    "go-to-market and measurable outcomes",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def read_json(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except (OSError, json.JSONDecodeError):
        return default


@dataclass
class FounderProfile:
    product_name: str = "ASCM"
    problem: str = (
        "AI-assisted software work is fragmented across repositories and roles; "
        "engineering, governance, founder guidance, and go-to-market work need coordinated handoffs."
    )
    target_user: str = (
        "Initial hypothesis: founders and engineering leaders delivering software across multiple repositories. "
        "This segment has not yet been validated with customer interviews."
    )
    differentiation: str = (
        "Local-first multi-agent coordination, specialist agents, governed handoffs, human approval gates, "
        "founder mentoring, GTM workflows, and outcome learning."
    )
    alternatives: str = "Existing coding assistants, CI systems, project-management tools, and manual coordination."
    traction: str = "No verified customer traction should be assumed from repository activity alone."
    pricing: str = "Not validated; pricing and willingness to pay are open questions."
    security: str = "Local-first by design, but production security requires validated identity, authorization, and durable audit controls."
    success_metrics: str = (
        "Verified task completion, reduced cross-repository integration failures, founder intervention usefulness, "
        "qualified customer conversations, and conversions. Baselines are not yet established."
    )
    permission_policy: str = "deny"

    @classmethod
    def load(cls, path: Path | None) -> "FounderProfile":
        if path is None:
            return cls()
        payload = read_json(path, None)
        if not isinstance(payload, dict):
            raise ValueError(f"Scenario file must contain a JSON object: {path}")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"Unknown founder scenario fields: {', '.join(sorted(unknown))}")
        profile = cls(**payload)
        if profile.permission_policy not in {"approve_simulated", "deny"}:
            raise ValueError("permission_policy must be 'approve_simulated' or 'deny'")
        return profile

    def answer(self, question: str) -> str:
        """Answer only from the simulation profile; never invent validation evidence."""
        q = question.lower()
        if any(k in q for k in ("problem", "pain", "why", "need", "value")):
            return self.problem
        if any(k in q for k in ("customer", "user", "icp", "segment", "buyer", "who")):
            return self.target_user
        if any(k in q for k in ("different", "compet", "alternative", "substitute")):
            return self.differentiation + " Alternatives to test include: " + self.alternatives
        if any(k in q for k in ("traction", "customer evidence", "interview", "validation", "demand", "proof")):
            return self.traction + " Customer validation is an explicit open workstream."
        if any(k in q for k in ("price", "pricing", "pay", "revenue", "willingness")):
            return self.pricing
        if any(k in q for k in ("security", "privacy", "consent", "permission", "data")):
            return self.security
        if any(k in q for k in ("exact conversion rate", "conversion rate", "actual conversion", "how many customers", "how many conversions", "verified traction")):
            return self.traction + " Exact conversion figures are not available; do not fabricate a number."
        if any(k in q for k in ("metric", "success", "outcome", "measure", "conversion")):
            return self.success_metrics
        if any(k in q for k in ("post", "publish", "linkedin", "social", "campaign", "outreach")):
            return "You may draft content for review. This simulated founder cannot authorize real-world publishing."
        return (
            "I do not have validated evidence for that yet. Record it as an open question, state the assumption, "
            "and propose the cheapest experiment that could resolve it; do not fabricate a fact."
        )

    def decide_permission(self, action: str) -> dict[str, Any]:
        """Return a simulated response. This is never a real founder authorization."""
        approved = self.permission_policy == "approve_simulated"
        return {
            "decision": "approve_simulated" if approved else "deny",
            "action": action,
            "decided_at": utc_now(),
            "decision_by": "testing_agent_simulated_founder",
            "is_real_authorization": False,
            "reason": (
                "Simulated approval for exercising the approval path only; external publishing remains disabled."
                if approved else
                "Default-deny policy: a test persona cannot authorize external social media publishing."
            ),
        }


class ASCMJsonRpcClient:
    """Small A2A 1.0 JSON-RPC client for the local ASCM gateway."""

    def __init__(self, base_url: str, timeout_seconds: float = 150.0, http_client: Any | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    @staticmethod
    def _collect_text(value: Any) -> list[str]:
        found: list[str] = []
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                found.append(value["text"])
            for key, child in value.items():
                if key != "text":
                    found.extend(ASCMJsonRpcClient._collect_text(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(ASCMJsonRpcClient._collect_text(child))
        return found

    def send(self, agent_id: str, prompt: str, session_id: str) -> str:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "contextId": session_id,
                    "role": "ROLE_USER",
                    "parts": [{"text": prompt}],
                    "metadata": {"ascm": {"agent_id": agent_id, "session_id": session_id}},
                }
            },
        }
        post = self.http_client.post if self.http_client is not None else httpx.post
        kwargs = {
            "headers": {"A2A-Version": "1.0"},
            "json": payload,
        }
        if self.http_client is None:
            kwargs["timeout"] = self.timeout_seconds
        response = post(f"{self.base_url}/a2a/jsonrpc", **kwargs)
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(f"A2A {agent_id} request failed: {body['error']}")
        result = body.get("result", {})
        # Task history contains the founder's prompt as well as the agent's reply.
        # Prefer the response artifacts explicitly so we never answer with our own prompt.
        artifacts = result.get("artifacts", []) if isinstance(result, dict) else []
        texts = self._collect_text(artifacts)
        if not texts:
            texts = self._collect_text(result)
        if not texts:
            raise RuntimeError(f"A2A {agent_id} response contained no text artifact.")
        return texts[-1].strip()


class GoalAgent:
    """Continuously track ASCM repository and testing progress with evidence."""

    def __init__(self, workspace: Path, status_path: Path, stop: threading.Event, interval: float,
                 status_changed: threading.Event | None = None, base_url: str | None = None):
        self.workspace, self.status_path, self.stop, self.interval = workspace, status_path, stop, interval
        self.status_changed = status_changed
        self.base_url = base_url.rstrip("/") if base_url else None

    def snapshot(self) -> dict[str, Any]:
        def git(*args: str) -> str:
            try:
                result = subprocess.run(
                    ["git", *args], cwd=self.workspace, capture_output=True, text=True,
                    timeout=5, check=False,
                )
                return result.stdout.strip() if result.returncode == 0 else ""
            except (OSError, subprocess.TimeoutExpired):
                return ""

        report = read_json(self.workspace / ".ascm_history" / "testing_agent_report.json", {})
        gateway_status = "not_checked"
        agent_ids: list[str] = []
        if self.base_url:
            try:
                response = httpx.get(self.base_url + "/.well-known/agent-card.json", timeout=1.0)
                response.raise_for_status()
                card = response.json()
                gateway_status = "healthy"
                agent_ids = sorted(
                    skill.get("id") for skill in card.get("skills", [])
                    if isinstance(skill, dict) and isinstance(skill.get("id"), str)
                )
            except (httpx.HTTPError, ValueError):
                gateway_status = "unavailable"
        snapshot = {
            "observed_at": utc_now(),
            "a2a_gateway_url": self.base_url,
            "a2a_gateway_status": gateway_status,
            "a2a_agent_ids": agent_ids,
            "workspace": str(self.workspace),
            "branch": git("branch", "--show-current") or "unknown",
            "git_status": git("status", "--short")[:12000],
            "latest_commit": git("log", "-1", "--format=%h %s (%cI)") or "unavailable",
            "testing_session": report.get("session_id") if isinstance(report, dict) else None,
            "testing_rounds": report.get("rounds_completed", 0) if isinstance(report, dict) else 0,
            "product_questions": report.get("questions_asked", 0) if isinstance(report, dict) else 0,
            "sessions_completed": report.get("sessions_completed", 0) if isinstance(report, dict) else 0,
            "open_findings": report.get("open_findings", []) if isinstance(report, dict) else [],
        }
        atomic_json(self.status_path, snapshot)
        if self.status_changed is not None:
            self.status_changed.set()
        return snapshot

    def run(self) -> None:
        while not self.stop.is_set():
            try:
                snapshot = self.snapshot()
                print(f"[GOAL AGENT] {snapshot['latest_commit']} | rounds={snapshot['testing_rounds']} | open findings={len(snapshot['open_findings'])}", flush=True)
            except Exception:
                logger.exception("Goal Agent snapshot failed")
            self.stop.wait(self.interval)


class GTMStatusAgent:
    """Poll progress, draft a social update, and request a simulated tester decision."""

    def __init__(self, workspace: Path, status_path: Path, stop: threading.Event,
                 requests: queue.Queue, responses: queue.Queue, interval: float,
                 status_changed: threading.Event | None = None,
                 client: ASCMJsonRpcClient | None = None):
        self.workspace, self.status_path, self.stop = workspace, status_path, stop
        self.requests, self.responses, self.interval = requests, responses, interval
        self.status_changed = status_changed
        self.client = client
        self.state_path = self.workspace / ".ascm_history" / "gtm_status_agent_state.json"
        state = read_json(self.state_path, {})
        self._last_fingerprint: str | None = state.get("last_requested_fingerprint") if isinstance(state, dict) else None
        self._request_counter = int(state.get("request_counter", 0)) if isinstance(state, dict) else 0

    @staticmethod
    def status_fingerprint(status: dict[str, Any]) -> str:
        """Stable deduplication key: round counters must not create social-post spam."""
        return hashlib.sha256(json.dumps({
            "commit": status.get("latest_commit"),
        }, sort_keys=True).encode()).hexdigest()

    def run(self) -> None:
        while not self.stop.is_set():
            status = read_json(self.status_path, {})
            if status and int(status.get("testing_rounds", 0) or 0) > 0:
                # Keep checking every poll, but request a social approval only once per
                # repository commit. Test-round counters are deliberately not triggers.
                fingerprint = self.status_fingerprint(status)
                if fingerprint != self._last_fingerprint:
                    self._last_fingerprint = fingerprint
                    self._request_counter += 1
                    atomic_json(self.state_path, {
                        "last_requested_fingerprint": fingerprint,
                        "request_counter": self._request_counter,
                        "updated_at": utc_now(),
                    })
                    request_id = f"social-review-{self._request_counter}-{fingerprint[:8]}"
                    draft = self._build_draft(status)
                    draft_path = self.workspace / "artifacts" / "gtm_cycles" / f"{request_id}.md"
                    draft_path.parent.mkdir(parents=True, exist_ok=True)
                    draft_path.write_text(
                        "# Social post draft — review required\n\n"
                        + draft + "\n\n> TEST HARNESS: draft only. No external publishing is connected.\n",
                        encoding="utf-8",
                    )
                    gtm_review_path = draft_path.with_name(draft_path.stem + "-gtm-review.txt")
                    gtm_review = "GTM specialist was not called; deterministic status draft only."
                    if self.client is not None:
                        try:
                            gtm_review = self.client.send(
                                "gtm",
                                "Review this ASCM repository/testing status and propose GTM positioning, "
                                "audience, and risks for a LinkedIn draft. Do not invent customers, traction, "
                                "revenue, conversions, or outcomes. Do not publish or claim permission. "
                                "Return concise internal recommendations only. Status evidence: "
                                + json.dumps({
                                    "latest_commit": status.get("latest_commit"),
                                    "testing_rounds": status.get("testing_rounds", 0),
                                    "product_questions": status.get("product_questions", 0),
                                    "sessions_completed": status.get("sessions_completed", 0),
                                    "open_finding_count": len(status.get("open_findings", [])),
                                    "a2a_gateway_status": status.get("a2a_gateway_status", "unknown"),
                                }, sort_keys=True),
                                request_id,
                            )
                        except Exception as exc:
                            gtm_review = f"GTM specialist unavailable: {type(exc).__name__}: {exc}"
                            print(f"[GTM AGENT] A2A specialist review failed; keeping factual draft: {exc}", flush=True)
                    gtm_review_path.write_text(
                        "INTERNAL REVIEW ONLY — not approved copy and not a publishing action.\\n\\n"
                        + gtm_review + "\\n",
                        encoding="utf-8",
                    )
                    request = {
                        "request_id": request_id,
                        "action": "publish_linkedin_post",
                        "channel": "LinkedIn",
                        "draft_path": str(draft_path),
                        "gtm_review_path": str(gtm_review_path),
                        "summary": "Share a progress update about the ASCM founder-simulation test.",
                        "created_at": utc_now(),
                        "status_fingerprint": fingerprint,
                        "is_real_publish_enabled": False,
                    }
                    print(f"[GTM AGENT] Status changed. Draft saved: {draft_path}", flush=True)
                    print("[GTM AGENT] Asking Testing Agent for permission to publish to LinkedIn (simulation only).", flush=True)
                    self.requests.put(request)
                    # Await a decision without blocking status polling forever.
                    deadline = time.monotonic() + min(60.0, self.interval * 3)
                    decision = None
                    while not self.stop.is_set() and time.monotonic() < deadline:
                        try:
                            candidate = self.responses.get(timeout=0.25)
                        except queue.Empty:
                            continue
                        if candidate.get("request_id") == request_id:
                            decision = candidate
                            break
                        self.responses.put(candidate)
                        time.sleep(0.05)
                    result_path = self.workspace / ".ascm_history" / "gtm_permission_requests.jsonl"
                    result_path.parent.mkdir(parents=True, exist_ok=True)
                    record = {**request, "decision": decision or {"decision": "no_response", "is_real_authorization": False}}
                    with result_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record, sort_keys=True) + "\n")
                    print(f"[GTM AGENT] Permission outcome: {(decision or {}).get('decision', 'no_response')}; real publishing remains disabled.", flush=True)
            if self.status_changed is not None:
                self.status_changed.wait(self.interval)
                self.status_changed.clear()
            else:
                self.stop.wait(self.interval)

    @staticmethod
    def _build_draft(status: dict[str, Any]) -> str:
        rounds = int(status.get("testing_rounds", 0) or 0)
        questions = int(status.get("product_questions", 0) or 0)
        return (
            "We're testing ASCM as a coordinated AI engineering workflow—not just a code generator. "
            f"The current test session has completed {rounds} founder-simulation round(s) and asked {questions} "
            "product clarification question(s). We're evaluating traceable handoffs, evidence-based product "
            "decisions, explicit approvals, and learning from verified outcomes. "
            f"Latest repository signal: {commit}. These are progress signals, not customer traction claims."
        )


class ContinuousFounderTestingRuntime:
    """Run Testing Agent, Goal Agent, and GTM status agent in parallel."""

    def __init__(self, workspace: str | Path = ".", *, base_url: str = "http://127.0.0.1:8090",
                 profile: FounderProfile | None = None, poll_interval: float = 5.0,
                 rounds_per_session: int = 8, client: ASCMJsonRpcClient | None = None):
        self.workspace = Path(workspace).expanduser().resolve()
        self.history = self.workspace / ".ascm_history"
        self.status_path = self.history / "testing_agent_status.json"
        self.report_path = self.history / "testing_agent_report.json"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.profile = profile or FounderProfile()
        self.poll_interval = max(0.5, float(poll_interval))
        self.rounds_per_session = max(1, min(int(rounds_per_session), 50))
        self.client = client or ASCMJsonRpcClient(base_url)
        self.stop = threading.Event()
        self.permission_requests: queue.Queue = queue.Queue()
        self.permission_responses: queue.Queue = queue.Queue()
        self.status_changed = threading.Event()
        self.session_id = str(uuid.uuid4())
        self.transcript: list[dict[str, str]] = []
        self.findings: list[str] = []
        self.questions_asked = 0
        self.rounds_completed = 0
        self.consecutive_interface_failures = 0

    def _product_prompt(self, area: str) -> str:
        transcript = json.dumps(self.transcript[-24:], ensure_ascii=False)
        return (
            "You are ASCM's ProductAgent in an adversarial product discovery interview. "
            "The connected Testing Agent is simulating the founder and will answer questions. "
            "Ask one highest-priority clarification question at a time; do not invent customer evidence, "
            "pricing, traction, or validation. Use the transcript to avoid repeating answered questions. "
            "When critical requirements are sufficiently clear, return is_clear=true and list remaining "
            "non-blocking questions separately. Return JSON keys: detected_domain, confidence_score, "
            "functional_completeness, nfr_completeness, is_clear, understanding, clarification_questions, "
            "checkpoint_clarification_items. Current test focus: " + area + ".\n"
            "Founder/product context: ASCM is a local-first multi-agent engineering workflow with product, "
            "engineering, governance, founder mentor, and GTM specialists. Claims must be supported by evidence.\n"
            "Conversation transcript: " + transcript
        )

    @staticmethod
    def _parse_product_result(raw: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            # Some LLM adapters wrap JSON in markdown fences.
            start, end = raw.find("{"), raw.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("ProductAgent response was not valid JSON.")
            value = json.loads(raw[start:end + 1])
        if not isinstance(value, dict):
            raise ValueError("ProductAgent response must be a JSON object.")
        questions = value.get("clarification_questions", [])
        if not isinstance(questions, list) or any(not isinstance(q, str) for q in questions):
            raise ValueError("ProductAgent clarification_questions must be a list of strings.")
        value["clarification_questions"] = questions
        return value

    def _answer_permission_requests(self) -> None:
        while True:
            try:
                request = self.permission_requests.get_nowait()
            except queue.Empty:
                return
            decision = self.profile.decide_permission(request["action"])
            response = {**decision, "request_id": request["request_id"]}
            self.permission_responses.put(response)
            print(f"[TESTING AGENT] Permission response: {response['decision']} for {request['action']} — SIMULATED, not real authorization.", flush=True)

    def run_product_session(self, focus: str) -> dict[str, Any]:
        self.transcript = []
        final = {"is_clear": False, "confidence_score": 0.0, "understanding": "", "clarification_questions": []}
        for round_number in range(1, self.rounds_per_session + 1):
            self._answer_permission_requests()
            prompt = self._product_prompt(focus)
            try:
                raw = self.client.send("product", prompt, self.session_id)
                result = self._parse_product_result(raw)
            except Exception as exc:
                self.findings.append(f"ProductAgent interface failure in {focus}, round {round_number}: {type(exc).__name__}: {exc}")
                self.consecutive_interface_failures += 1
                print(f"[TESTING AGENT] FAIL: ProductAgent interaction failed: {exc}", flush=True)
                if self.consecutive_interface_failures >= 3:
                    self.findings.append("Circuit breaker stopped repeated ProductAgent interface failures after three consecutive failures.")
                    self.stop.set()
                break
            self.consecutive_interface_failures = 0
            final = result
            self.rounds_completed += 1
            questions = result["clarification_questions"]
            if not questions:
                if result.get("is_clear") is True and float(result.get("confidence_score", 0)) >= 0.90:
                    print(f"[PRODUCT AGENT] Focus '{focus}' is clear at confidence {result.get('confidence_score')}.", flush=True)
                    break
                self.findings.append(f"ProductAgent returned no actionable question and did not establish clarity for focus '{focus}'.")
                print(f"[TESTING AGENT] FAIL: ProductAgent returned no question and did not establish clarity for '{focus}'.", flush=True)
                break
            question = questions[0].strip()
            if not question:
                self.findings.append(f"ProductAgent returned an empty clarification question for '{focus}'.")
                break
            answer = self.profile.answer(question)
            self.questions_asked += 1
            self.transcript.extend([
                {"role": "assistant", "content": question},
                {"role": "user", "content": answer},
            ])
            print(f"\n[PRODUCT AGENT → TESTING AGENT] {question}", flush=True)
            print(f"[TESTING AGENT → PRODUCT AGENT] {answer}\n", flush=True)
        return final

    def _permission_worker(self) -> None:
        while not self.stop.is_set():
            try:
                request = self.permission_requests.get(timeout=0.25)
            except queue.Empty:
                continue
            decision = self.profile.decide_permission(request["action"])
            self.permission_responses.put({**decision, "request_id": request["request_id"]})
            print(
                f"[TESTING AGENT] Permission response: {decision['decision']} for "
                f"{request['action']} — SIMULATED, not real authorization.",
                flush=True,
            )

    def run(self, *, sessions: int = 0) -> dict[str, Any]:
        self.history.mkdir(parents=True, exist_ok=True)
        goal = GoalAgent(self.workspace, self.status_path, self.stop, self.poll_interval, self.status_changed, getattr(self.client, "base_url", None))
        gtm = GTMStatusAgent(self.workspace, self.status_path, self.stop,
                             self.permission_requests, self.permission_responses, self.poll_interval,
                             self.status_changed, self.client)
        threads = [
            threading.Thread(target=goal.run, name="ASCM-Goal-Agent", daemon=True),
            threading.Thread(target=gtm.run, name="ASCM-GTM-Status-Agent", daemon=True),
            threading.Thread(target=self._permission_worker, name="ASCM-Testing-Agent-Permissions", daemon=True),
        ]
        for thread in threads:
            thread.start()
        print(f"[TESTING AGENT] Session {self.session_id}; workspace={self.workspace}", flush=True)
        print("[TESTING AGENT] Goal Agent and GTM status agent are running in parallel. Ctrl-C stops the harness.", flush=True)
        permission_log = self.history / "gtm_permission_requests.jsonl"
        initial_permission_log_size = permission_log.stat().st_size if permission_log.exists() else 0
        session_count = 0
        try:
            while not self.stop.is_set() and (sessions == 0 or session_count < sessions):
                focus = PROBE_AREAS[session_count % len(PROBE_AREAS)]
                result = self.run_product_session(focus)
                session_count += 1
                self._answer_permission_requests()
                report = {
                    "session_id": self.session_id,
                    "updated_at": utc_now(),
                    "workspace": str(self.workspace),
                    "sessions_completed": session_count,
                    "rounds_completed": self.rounds_completed,
                    "questions_asked": self.questions_asked,
                    "last_focus": focus,
                    "last_product_result": result,
                    "open_findings": list(self.findings),
                    "external_publishing_enabled": False,
                    "simulated_founder_only": True,
                }
                atomic_json(self.report_path, report)
                # Force a fresh status snapshot after every completed session so a
                # finite CI run exercises the GTM permission handoff as well.
                goal.snapshot()
                if sessions > 0 and session_count >= sessions:
                    # Finite CI runs must allow the parallel GTM agent to request a
                    # simulated permission and record the response before shutdown.
                    deadline = time.monotonic() + min(5.0, max(2.0, self.poll_interval))
                    while not self.stop.is_set() and time.monotonic() < deadline:
                        current_size = permission_log.stat().st_size if permission_log.exists() else 0
                        if current_size > initial_permission_log_size:
                            break
                        self.stop.wait(0.1)
                if sessions == 0 or session_count < sessions:
                    deadline = time.monotonic() + max(1.0, self.poll_interval)
                    while not self.stop.is_set() and time.monotonic() < deadline:
                        self.stop.wait(0.1)
        except KeyboardInterrupt:
            print("\n[TESTING AGENT] Stop requested.", flush=True)
        finally:
            self.stop.set()
            for thread in threads:
                thread.join(timeout=2.0)
            report = {
                "session_id": self.session_id,
                "updated_at": utc_now(),
                "workspace": str(self.workspace),
                "sessions_completed": session_count,
                "rounds_completed": self.rounds_completed,
                "questions_asked": self.questions_asked,
                "open_findings": list(self.findings),
                "external_publishing_enabled": False,
                "simulated_founder_only": True,
            }
            atomic_json(self.report_path, report)
            print(f"[TESTING AGENT] Report written to {self.report_path}", flush=True)
        return report


def ensure_gateway(base_url: str, workspace: Path, *, start_server: bool) -> subprocess.Popen | None:
    try:
        response = httpx.get(base_url.rstrip("/") + "/.well-known/agent-card.json", timeout=1.5)
        if response.status_code == 200:
            return None
    except httpx.HTTPError:
        pass
    if not start_server:
        raise RuntimeError(f"ASCM A2A gateway is unavailable at {base_url}. Start it or remove --no-start-server.")
    host_port = base_url.removeprefix("http://").removeprefix("https://")
    host, _, port_text = host_port.partition(":")
    port = int(port_text or "8090")
    history = workspace / ".ascm_history"
    history.mkdir(parents=True, exist_ok=True)
    log_handle = (history / "testing_agent_a2a.log").open("a", encoding="utf-8")
    env = os.environ.copy()
    env["ASCM_A2A_HOST"] = "127.0.0.1"
    env["ASCM_A2A_PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, "-m", "orchestrator.a2a.server"],
        cwd=workspace, env=env, stdout=log_handle, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"ASCM A2A gateway exited early; inspect {history / 'testing_agent_a2a.log'}")
        try:
            response = httpx.get(base_url.rstrip("/") + "/.well-known/agent-card.json", timeout=1.0)
            if response.status_code == 200:
                return process
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    process.terminate()
    raise RuntimeError(f"ASCM A2A gateway did not become ready; inspect {history / 'testing_agent_a2a.log'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ASCM's continuous founder-simulation Testing Agent.")
    parser.add_argument("--workspace", default=".", help="ASCM repository/workspace to monitor.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8090", help="ASCM A2A gateway URL.")
    parser.add_argument("--scenario", type=Path, help="Optional JSON simulated-founder profile.")
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--rounds-per-session", type=int, default=8)
    parser.add_argument("--sessions", type=int, default=0, help="Number of sessions; 0 means keep running until Ctrl-C.")
    parser.add_argument("--no-start-server", action="store_true", help="Require an already-running A2A gateway.")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    profile = FounderProfile.load(args.scenario)
    process = None
    try:
        process = ensure_gateway(args.base_url, workspace, start_server=not args.no_start_server)
        runtime = ContinuousFounderTestingRuntime(
            workspace, base_url=args.base_url, profile=profile,
            poll_interval=args.poll_interval, rounds_per_session=args.rounds_per_session,
        )
        runtime.run(sessions=args.sessions)
        return 0
    except Exception as exc:
        logger.exception("Testing Agent could not start")
        print(f"[TESTING AGENT] FATAL: {exc}", file=sys.stderr, flush=True)
        return 2
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(main())

import json
import os
import socketserver
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Any, Optional

from orchestrator.auth.user_manager import USER_MANAGER

HISTORY_DIR = Path.cwd() / ".ascm_history"


class DashboardState:
    def __init__(self, user_goal: str = ""):
        self.lock = threading.Lock()
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.stop_heartbeat = False
        self.run_id: Optional[str] = None
        self.file_path: Optional[Path] = None
        self.start_time: str = ""
        self.last_heartbeat: float = time.time()
        self.user_goal: str = user_goal
        self.phase: str = "Initializing Orchestrator"
        self.active_agent: str = "None"
        self.active_action: str = "Waiting for workflow start"
        self.logs: List[str] = []
        self.timeline_events: List[Dict[str, Any]] = []
        self.known_agents = [
            "DiscoveryAgent",
            "ProductAgent",
            "DesignAgent",
            "ArchitectAgent",
            "PlannerAgent",
            "DatabaseAgent",
            "GoCoderAgent",
            "SecurityAuditorAgent",
            "CodeReviewAgent",
        ]
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.tasks: List[Dict[str, Any]] = []
        self.test_results: List[Dict[str, Any]] = []

        # Interactive Governance & Human Gate State
        self.pending_approval: bool = False
        self.pending_changes_data: List[Dict[str, Any]] = []
        self.approval_decision: Optional[bool] = None
        self.approval_event = threading.Event()

        self.clarification_needed: bool = False
        self.clarification_questions: List[str] = []
        self.clarification_answer: Optional[str] = None
        self.clarification_event = threading.Event()

        self.pending_milestone: bool = False
        self.milestone_name: str = ""
        self.milestone_summary: str = ""
        self.milestone_decision: Optional[bool] = None
        self.milestone_feedback_text: str = ""
        self.milestone_event = threading.Event()

        if user_goal:
            self.new_session(user_goal)

    def new_session(self, user_goal: str = "") -> None:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        now_dt = datetime.now()
        timestamp_str = now_dt.strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        
        with getattr(self, "lock", threading.Lock()):
            self.run_id = f"run_{timestamp_str}_{short_id}"
            self.file_path = HISTORY_DIR / f"{self.run_id}.json"
            self.start_time = now_dt.isoformat()
            self.last_heartbeat = time.time()
            self.user_goal = user_goal
            self.phase = "Initializing Orchestrator"
            self.active_agent = "None"
            self.active_action = "Waiting for workflow start"
            
            t_fmt = now_dt.strftime("%I:%M:%S %p")
            self.logs = [f"[{t_fmt}] Dashboard server initialized."]
            self.timeline_events = [
                {"timestamp": t_fmt, "agent": "System", "status": "info", "action": "Workflow Session Created"}
            ]
            
            self.agents = {
                name: {
                    "status": "waiting",
                    "action": "Idle",
                    "updated_at": t_fmt,
                    "duration_sec": 0,
                    "started_at": None,
                }
                for name in self.known_agents
            }
            
            self.tasks = []
            self.test_results = []
            self.pending_approval = False
            self.pending_changes_data = []
            self.approval_decision = None
            self.approval_event.clear()
            self.clarification_needed = False
            self.clarification_questions = []
            self.clarification_answer = None
            self.clarification_event.clear()
            self.pending_milestone = False
            self.milestone_name = ""
            self.milestone_summary = ""
            self.milestone_decision = None
            self.milestone_feedback_text = ""
            self.milestone_event.clear()
            self._flush_to_disk()

        self._start_heartbeat_worker()

    def record_test_result(
        self,
        repo: str,
        language: str,
        passed: bool,
        test_output: str = "",
        vet_output: str = "",
        sandboxed: bool = False,
        framework: str = "",
        total_tests: int = 0,
        passed_count: int = 0,
        failed_count: int = 0,
        test_cases: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        with self.lock:
            if not hasattr(self, "test_results"):
                self.test_results = []

            tc_list = test_cases or []
            t_total = total_tests or (len(tc_list) if tc_list else 1)
            t_passed = passed_count if total_tests > 0 else (t_total if passed else 0)
            t_failed = failed_count if total_tests > 0 else (0 if passed else t_total)

            entry = {
                "id": f"test_{len(self.test_results) + 1}",
                "timestamp": t_fmt,
                "repo": repo,
                "language": language,
                "framework": framework or ("testify / go test" if language == "go" else "pytest / unittest" if language == "python" else "jest / npm test"),
                "passed": passed,
                "total_tests": t_total,
                "passed_count": t_passed,
                "failed_count": t_failed,
                "sandboxed": sandboxed,
                "test_output": test_output,
                "vet_output": vet_output,
                "test_cases": tc_list,
            }
            self.test_results.append(entry)
            self.last_heartbeat = time.time()
            st_text = "PASSED" if passed else "FAILED"
            self.logs.append(f"[{t_fmt}] [UNIT_TESTS] {repo} ({language.upper()} via {entry['framework']}): {st_text} ({t_passed}/{t_total} passed)")
            self.timeline_events.append({
                "timestamp": t_fmt,
                "agent": "VerifierEngine",
                "status": "completed" if passed else "failed",
                "action": f"Unit tests {st_text} for {repo} ({t_passed}/{t_total} passed)",
            })
            self._flush_to_disk()


    def request_approval(self, pending_changes: List[Dict[str, Any]]) -> None:
        with self.lock:
            self.pending_approval = True
            self.pending_changes_data = pending_changes
            self.approval_decision = None
            self.approval_event.clear()
            self.phase = "Waiting for Human Approval (Web Dashboard or CLI)"
            self.logs.append(f"[{datetime.now().strftime('%I:%M:%S %p')}] [GOVERNANCE] Approval requested for {len(pending_changes)} repos.")
            self._flush_to_disk()

    def submit_approval(self, approved: bool) -> None:
        with self.lock:
            self.approval_decision = approved
            self.pending_approval = False
            self.approval_event.set()
            status_text = "APPROVED" if approved else "REJECTED"
            self.logs.append(f"[{datetime.now().strftime('%I:%M:%S %p')}] [GOVERNANCE] Human decision received: {status_text}")
            self._flush_to_disk()

    def request_clarification(self, questions: List[str]) -> None:
        with self.lock:
            self.clarification_needed = True
            self.clarification_questions = questions
            self.clarification_answer = None
            self.clarification_event.clear()
            self.phase = "Waiting for PRD Clarification (Web Dashboard or CLI)"
            self.logs.append(f"[{datetime.now().strftime('%I:%M:%S %p')}] [GOVERNANCE] Clarification questions submitted to human.")
            self._flush_to_disk()

    def submit_clarification(self, answer: str) -> None:
        with self.lock:
            self.clarification_answer = answer
            self.clarification_needed = False
            self.clarification_event.set()
            self.logs.append(f"[{datetime.now().strftime('%I:%M:%S %p')}] [GOVERNANCE] Human clarification response received.")
            self._flush_to_disk()

    def request_milestone_review(self, name: str, summary: str) -> None:
        with self.lock:
            self.pending_milestone = True
            self.milestone_name = name
            self.milestone_summary = summary
            self.milestone_decision = None
            self.milestone_feedback_text = ""
            self.milestone_event.clear()
            self.phase = f"Milestone Review Gate: {name}"
            self.logs.append(f"[{datetime.now().strftime('%I:%M:%S %p')}] [MILESTONE] User feedback requested for: '{name}'.")
            self._flush_to_disk()

    def submit_milestone_review(self, proceed: bool, feedback: str = "") -> None:
        with self.lock:
            self.milestone_decision = proceed
            self.milestone_feedback_text = feedback
            self.pending_milestone = False
            self.milestone_event.set()
            decision_label = "CONFIRMED & PROCEED" if proceed else f"REWORK REQUESTED ({feedback})"
            self.logs.append(f"[{datetime.now().strftime('%I:%M:%S %p')}] [MILESTONE] User decision for '{self.milestone_name}': {decision_label}")
            self._flush_to_disk()

    def _start_heartbeat_worker(self) -> None:
        self.stop_heartbeat = True
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=0.5)
        self.stop_heartbeat = False

        def _worker():
            while not self.stop_heartbeat:
                time.sleep(2)
                with self.lock:
                    if any(term in self.phase.upper() for term in ("FAILED", "CRASHED", "COMPLETED", "ABORTED")):
                        break
                    self.last_heartbeat = time.time()
                    self._flush_to_disk()

        self.heartbeat_thread = threading.Thread(target=_worker, daemon=True)
        self.heartbeat_thread.start()

    def set_phase(self, phase_name: str) -> None:
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        with self.lock:
            self.phase = phase_name
            self.last_heartbeat = time.time()
            self.logs.append(f"[{t_fmt}] [PHASE] {phase_name}")
            self.timeline_events.append({
                "timestamp": t_fmt,
                "agent": "System",
                "status": "phase",
                "action": f"Entered {phase_name}"
            })
            self._flush_to_disk()

    def update_agent(self, agent_name: str, status: str, action: str = "") -> None:
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        now_ts = time.time()
        with self.lock:
            self.last_heartbeat = now_ts
            if status == "running":
                self.active_agent = agent_name
                self.active_action = action or f"{agent_name} is running"
            elif self.active_agent == agent_name and status in ("completed", "failed"):
                self.active_agent = "None"
                self.active_action = "Idle"

            if agent_name in self.agents:
                ag = self.agents[agent_name]
                if status == "running" and ag["status"] != "running":
                    ag["started_at_ts"] = now_ts
                elif status in ("completed", "failed") and ag.get("started_at_ts"):
                    ag["duration_sec"] = round(now_ts - ag["started_at_ts"], 1)

                ag["status"] = status
                if action:
                    ag["action"] = action
                ag["updated_at"] = t_fmt
            else:
                self.agents[agent_name] = {
                    "status": status,
                    "action": action or "Running",
                    "updated_at": t_fmt,
                    "duration_sec": 0,
                }

            self.timeline_events.append({
                "timestamp": t_fmt,
                "agent": agent_name,
                "status": status,
                "action": action or f"Agent status set to {status}"
            })
            self._flush_to_disk()

    def set_tasks(self, tasks_list: List[Dict[str, Any]]) -> None:
        with self.lock:
            self.tasks = tasks_list
            self.last_heartbeat = time.time()
            self._flush_to_disk()

    def update_task_status(self, task_id: str, status: str) -> None:
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        with self.lock:
            self.last_heartbeat = time.time()
            for task in self.tasks:
                if task.get("id") == task_id:
                    task["status"] = status
                    task["updated_at"] = t_fmt
            self._flush_to_disk()

    def log(self, message: str) -> None:
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        with self.lock:
            self.last_heartbeat = time.time()
            formatted_msg = f"[{t_fmt}] {message}"
            self.logs.append(formatted_msg)
            if len(self.logs) > 300:
                self.logs.pop(0)
            self._flush_to_disk()

    def record_crash(self, error: Exception) -> None:
        import traceback
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        err_msg = str(error) or type(error).__name__
        with self.lock:
            self.phase = f"FAILED / CRASHED ({err_msg})"
            self.last_heartbeat = time.time()
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            formatted_crash = f"[{t_fmt}] [CRASH] Execution failed: {error}\n{tb_str}"
            self.logs.append(formatted_crash)
            
            if self.active_agent and self.active_agent != "None":
                if self.active_agent in self.agents:
                    self.agents[self.active_agent]["status"] = "failed"
                    self.agents[self.active_agent]["action"] = f"CRASHED: {error}"
            
            self.timeline_events.append({
                "timestamp": t_fmt,
                "agent": self.active_agent if self.active_agent != "None" else "System",
                "status": "failed",
                "action": f"FAILED / CRASHED: {error}"
            })
            self._flush_to_disk()

    def get_snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return self._build_snapshot_dict()

    def _build_snapshot_dict(self) -> Dict[str, Any]:
        running_cnt = sum(1 for a in self.agents.values() if a["status"] == "running")
        completed_cnt = sum(1 for a in self.agents.values() if a["status"] == "completed")
        waiting_cnt = sum(1 for a in self.agents.values() if a["status"] == "waiting")

        return {
            "run_id": self.run_id,
            "start_time": self.start_time,
            "last_heartbeat": getattr(self, "last_heartbeat", time.time()),
            "user_goal": self.user_goal,
            "phase": self.phase,
            "active_agent": self.active_agent,
            "active_action": self.active_action,
            "counts": {
                "running": running_cnt,
                "completed": completed_cnt,
                "waiting": waiting_cnt,
                "total_agents": len(self.agents),
                "total_tasks": len(self.tasks),
            },
            "agents": self.agents,
            "tasks": self.tasks,
            "pending_approval": getattr(self, "pending_approval", False),
            "pending_changes_data": getattr(self, "pending_changes_data", []),
            "approval_decision": getattr(self, "approval_decision", None),
            "clarification_needed": getattr(self, "clarification_needed", False),
            "clarification_questions": getattr(self, "clarification_questions", []),
            "pending_milestone": getattr(self, "pending_milestone", False),
            "milestone_name": getattr(self, "milestone_name", ""),
            "milestone_summary": getattr(self, "milestone_summary", ""),
            "milestone_decision": getattr(self, "milestone_decision", None),
            "test_results": getattr(self, "test_results", []),
            "timeline_events": self.timeline_events[-100:],
            "logs": self.logs[-100:],
        }


    def _flush_to_disk(self) -> None:
        try:
            snapshot = self._build_snapshot_dict()
            temp_path = self.file_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            temp_path.replace(self.file_path)
        except OSError:
            pass


def check_and_update_staleness(snapshot: Dict[str, Any], filepath: Optional[Path] = None) -> Dict[str, Any]:
    if not snapshot or not isinstance(snapshot, dict):
        return snapshot

    phase = snapshot.get("phase", "")
    terminal_keywords = ["FAILED", "CRASHED", "COMPLETED", "ABORTED"]
    if any(k in phase.upper() for k in terminal_keywords):
        return snapshot

    last_hb = snapshot.get("last_heartbeat", 0)
    if not last_hb and filepath and filepath.exists():
        try:
            last_hb = filepath.stat().st_mtime
        except OSError:
            last_hb = 0

    if last_hb > 0 and (time.time() - last_hb > 10.0):
        t_fmt = datetime.now().strftime("%I:%M:%S %p")
        snapshot["phase"] = "FAILED / CRASHED (Process Disconnected)"
        snapshot["active_agent"] = "None"
        snapshot["active_action"] = "Process heartbeat stopped (> 10s)"

        logs = snapshot.setdefault("logs", [])
        logs.append(
            f"[{t_fmt}] [CRASH] Application process heartbeat stopped (> 10s delay limit reached). Execution marked as crashed."
        )

        events = snapshot.setdefault("timeline_events", [])
        events.append({
            "timestamp": t_fmt,
            "agent": "System",
            "status": "failed",
            "action": "FAILED / CRASHED: Process heartbeat stopped (> 10s delay limit reached)",
        })

        if filepath and filepath.exists():
            try:
                temp_path = filepath.with_suffix(".tmp")
                temp_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
                temp_path.replace(filepath)
            except OSError:
                pass

    return snapshot


def get_latest_live_run() -> Dict[str, Any]:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    run_files = sorted(HISTORY_DIR.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if run_files:
        latest_file = run_files[0]
        if GLOBAL_DASHBOARD_STATE.file_path and GLOBAL_DASHBOARD_STATE.file_path.name == latest_file.name:
            snap = GLOBAL_DASHBOARD_STATE.get_snapshot()
            return check_and_update_staleness(snap, GLOBAL_DASHBOARD_STATE.file_path)

        try:
            data = json.loads(latest_file.read_text(encoding="utf-8"))
            return check_and_update_staleness(data, latest_file)
        except (json.JSONDecodeError, OSError):
            pass

    return GLOBAL_DASHBOARD_STATE.get_snapshot()


def list_historical_runs() -> List[Dict[str, Any]]:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    runs = []
    for filepath in sorted(HISTORY_DIR.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            data = check_and_update_staleness(data, filepath)
            runs.append({
                "run_id": data.get("run_id", filepath.stem),
                "start_time": data.get("start_time", ""),
                "goal": data.get("user_goal", "No Goal Specified"),
                "phase": data.get("phase", "Unknown"),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return runs


def load_historical_run(run_id: str) -> Optional[Dict[str, Any]]:
    filepath = HISTORY_DIR / f"{run_id}.json"
    if not filepath.exists():
        return None
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return check_and_update_staleness(data, filepath)
    except (json.JSONDecodeError, OSError):
        return None


# Global dashboard state singleton
GLOBAL_DASHBOARD_STATE = DashboardState()


class DashboardHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        if path == "/api/runs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            history_list = list_historical_runs()
            self.wfile.write(json.dumps(history_list).encode("utf-8"))

        elif path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            run_id = query_params.get("run_id", [None])[0]
            if run_id and run_id != "live":
                snapshot = load_historical_run(run_id) or get_latest_live_run()
            else:
                snapshot = get_latest_live_run()
                
            self.wfile.write(json.dumps(snapshot).encode("utf-8"))

        elif path == "/api/auth/current":
            user = USER_MANAGER.get_active_user()
            self._send_json({"status": "ok", "user": user})

        elif path == "/api/repos/detect":
            detected = []
            cur = Path.cwd()
            candidates = [cur]
            try:
                for sub in cur.iterdir():
                    if sub.is_dir() and not sub.name.startswith("."):
                        candidates.append(sub)
            except OSError:
                pass
            
            for c in candidates:
                if (c / ".git").exists() or (c / "go.mod").exists() or (c / "SKILL.md").exists() or (c / "package.json").exists() or (c / "requirements.txt").exists():
                    detected.append({
                        "name": c.name,
                        "path": str(c.resolve()),
                        "has_contract": (c / "SKILL.md").exists() or (c / ".agents").exists(),
                    })
            self._send_json({"status": "ok", "repos": detected[:15]})

        elif path == "/api/topology/visual":
            snap = get_latest_live_run()
            agents_count = len(snap.get("agents", {}))
            repos = []
            for k in snap.get("pending_changes_data", []):
                repos.append(k.get("repo", "Service"))
            if not repos:
                repos = ["provider-api", "consumer-client"]

            nodes = [
                {"id": "goal", "label": "Stakeholder Requirement", "type": "input", "active": True},
                {"id": "product_agent", "label": "Product Agent (PRD)", "type": "agent", "active": True},
                {"id": "architect_agent", "label": "Architect Agent (HLD/LLD)", "type": "agent", "active": True},
                {"id": "provider_repo", "label": f"Provider: {repos[0]}", "type": "repo", "active": True},
                {"id": "consumer_repo", "label": f"Consumer: {repos[-1] if len(repos) > 1 else 'client-sdk'}", "type": "repo", "active": True},
                {"id": "sandbox_verifier", "label": "Docker Hermetic Verifier", "type": "verifier", "active": True},
                {"id": "unit_tests", "label": "Unit Test Suites (TDD)", "type": "tests", "active": True},
                {"id": "audit_log", "label": "SOC2 & PII Audit Log", "type": "compliance", "active": True},
            ]
            edges = [
                {"from": "goal", "to": "product_agent", "label": "Grilling & Clarifications (>=90%)"},
                {"from": "product_agent", "to": "architect_agent", "label": "Functional + NFR Spec"},
                {"from": "architect_agent", "to": "provider_repo", "label": "Go/Python Coder Agent"},
                {"from": "provider_repo", "to": "consumer_repo", "label": "Synchronized Client Callers"},
                {"from": "provider_repo", "to": "sandbox_verifier", "label": "Isolated Checks"},
                {"from": "sandbox_verifier", "to": "unit_tests", "label": "Testify / Pytest / Jest"},
                {"from": "unit_tests", "to": "audit_log", "label": "Tamper-proof Telemetry"},
            ]
            self._send_json({"status": "ok", "nodes": nodes, "edges": edges, "phase": snap.get("phase", "")})

        elif path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD_PAGE.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        from urllib.parse import urlparse
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        if path == "/api/action/approve":
            GLOBAL_DASHBOARD_STATE.submit_approval(True)
            self._send_json({"status": "ok", "message": "Changes approved via dashboard"})
        elif path == "/api/action/reject":
            GLOBAL_DASHBOARD_STATE.submit_approval(False)
            self._send_json({"status": "ok", "message": "Changes rejected via dashboard"})
        elif path == "/api/action/clarify":
            answer = payload.get("answer", "")
            GLOBAL_DASHBOARD_STATE.submit_clarification(answer)
            self._send_json({"status": "ok", "message": "Clarification submitted via dashboard"})
        elif path == "/api/action/milestone":
            proceed = bool(payload.get("proceed", True))
            feedback = payload.get("feedback", "")
            GLOBAL_DASHBOARD_STATE.submit_milestone_review(proceed, feedback)
            self._send_json({"status": "ok", "message": f"Milestone review submitted: proceed={proceed}"})
        elif path == "/api/auth/send-otp":
            ident = payload.get("identifier", "").strip()
            name = payload.get("name")
            res = USER_MANAGER.send_otp(ident, name=name)
            self._send_json(res)
        elif path == "/api/auth/verify-otp":
            ident = payload.get("identifier", "").strip()
            otp = payload.get("otp", "").strip()
            name = payload.get("name")
            phone = payload.get("phone")
            email = payload.get("email")
            res = USER_MANAGER.verify_otp(ident, otp, name=name, phone=phone, email=email)
            self._send_json(res)
        elif path == "/api/auth/profile":
            ident = payload.get("identifier") or (USER_MANAGER.get_active_user() or {}).get("id", "")
            updates = payload.get("updates", payload)
            if not ident and updates.get("email"):
                ident = updates["email"]
            if not ident and updates.get("phone"):
                ident = updates["phone"]
            res = USER_MANAGER.update_profile(ident, updates) if ident else {"status": "error", "message": "No active user session"}
            self._send_json(res)
        elif path == "/api/auth/logout":
            USER_MANAGER.logout()
            self._send_json({"status": "ok", "message": "Logged out successfully"})
        elif path == "/api/action/launch":
            goal = payload.get("goal", "").strip()
            repos = payload.get("repos", [])
            auto_approve = bool(payload.get("auto_approve", False))
            if not goal:
                self._send_json({"status": "error", "message": "Goal cannot be empty"}, status=400)
                return
            if not repos:
                repos = [str(Path.cwd().resolve())]

            def _run_bg():
                from orchestrator.orchestrator_core import OrchestratorEngine
                try:
                    engine = OrchestratorEngine(repo_paths=repos, initial_goal=goal, enable_dashboard=False)
                    engine.run(auto_approve=auto_approve)
                except Exception as ex:
                    GLOBAL_DASHBOARD_STATE.record_crash(ex)

            threading.Thread(target=_run_bg, daemon=True).start()
            self._send_json({"status": "ok", "message": f"Orchestrator launched for goal: '{goal}'"})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))



class DashboardServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.actual_port = port

    def start(self) -> int:
        for p in range(self.port, self.port + 10):
            try:
                self.server = HTTPServer((self.host, p), DashboardHTTPRequestHandler)
                self.actual_port = p
                break
            except OSError:
                continue
        
        if not self.server:
            print(f"[!] Warning: Could not bind dashboard server on ports {self.port}-{self.port+10}")
            return 0

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"[+] 🌐 Dashboard live & persistent at: http://localhost:{self.actual_port}")
        return self.actual_port

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()


HTML_DASHBOARD_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ASCM Orchestrator - Autonomous Engineering Platform</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0d1117;
      --card-bg: #161b22;
      --card-sub-bg: #090d13;
      --border-color: #30363d;
      --text-main: #c9d1d9;
      --text-muted: #8b949e;
      --accent-blue: #58a6ff;
      --accent-green: #3fb950;
      --accent-yellow: #d29922;
      --accent-red: #f85149;
      --accent-purple: #bc8cff;
      --accent-cyan: #39c5cf;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      line-height: 1.5;
      padding: 24px;
    }

    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
      flex-wrap: wrap;
      gap: 12px;
    }
    .logo { display: flex; align-items: center; gap: 12px; }
    .logo h1 { font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; }
    .header-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    
    .run-select {
      background: var(--card-bg);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 7px 12px;
      border-radius: 6px;
      font-size: 13px;
      outline: none;
      cursor: pointer;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      background: rgba(63, 185, 80, 0.15);
      color: var(--accent-green);
      border: 1px solid rgba(63, 185, 80, 0.3);
    }
    .pulse {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--accent-green);
      box-shadow: 0 0 8px var(--accent-green);
      animation: pulse-anim 1.5s infinite;
    }
    @keyframes pulse-anim { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

    /* User Profile Pill */
    .user-profile-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      color: #ffffff;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }
    .user-profile-btn:hover {
      border-color: var(--accent-blue);
      background: rgba(88, 166, 255, 0.1);
    }
    .user-avatar-mini {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--accent-purple);
      display: inline-block;
    }

    /* Phase Bar */
    .phase-bar {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .phase-title { font-size: 12px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; letter-spacing: 0.5px; }
    .phase-name { font-size: 16px; font-weight: 600; color: var(--accent-blue); margin-top: 2px; }

    /* Nav Tabs */
    .tabs-bar {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
      overflow-x: auto;
    }
    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
      transition: all 0.2s ease;
    }
    .tab-btn:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }
    .tab-btn.active {
      color: #ffffff;
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-bottom-color: var(--card-bg);
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .tab-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      background: rgba(88, 166, 255, 0.2);
      color: var(--accent-blue);
      font-weight: 700;
    }
    .tab-badge.pending {
      background: rgba(210, 153, 34, 0.2);
      color: var(--accent-yellow);
      animation: pulse-anim 1.5s infinite;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Buttons */
    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; }
    .btn-primary { background: var(--accent-blue); color: #fff; }
    .btn-success { background: var(--accent-green); color: #fff; }
    .btn-danger { background: var(--accent-red); color: #fff; }
    .btn-warning { background: var(--accent-yellow); color: #000; }
    .btn-outline { background: transparent; border: 1px solid var(--border-color); color: var(--text-main); }
    .btn-outline:hover { background: rgba(255, 255, 255, 0.05); }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
    }
    .stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
    .stat-val { font-size: 28px; font-weight: 700; margin-top: 4px; }
    .val-running { color: var(--accent-blue); }
    .val-completed { color: var(--accent-green); }
    .val-waiting { color: var(--accent-yellow); }
    .val-tasks { color: var(--accent-purple); }
    .val-failed { color: var(--accent-red); }
    .val-cyan { color: var(--accent-cyan); }

    .main-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .panel {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .panel-header {
      font-size: 14px;
      font-weight: 600;
      color: #ffffff;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }
    .agent-list { display: flex; flex-direction: column; gap: 10px; }
    .agent-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 14px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 6px;
    }
    .agent-name { font-weight: 600; font-size: 13px; }
    .agent-action { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

    .pill {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 12px;
      text-transform: uppercase;
      display: inline-block;
    }
    .pill-running { background: rgba(88, 166, 255, 0.15); color: var(--accent-blue); border: 1px solid rgba(88, 166, 255, 0.3); }
    .pill-completed { background: rgba(63, 185, 80, 0.15); color: var(--accent-green); border: 1px solid rgba(63, 185, 80, 0.3); }
    .pill-waiting { background: rgba(210, 153, 34, 0.15); color: var(--accent-yellow); border: 1px solid rgba(210, 153, 34, 0.3); }
    .pill-failed { background: rgba(248, 81, 73, 0.15); color: var(--accent-red); border: 1px solid rgba(248, 81, 73, 0.3); }
    .pill-lang { background: rgba(188, 140, 255, 0.15); color: var(--accent-purple); border: 1px solid rgba(188, 140, 255, 0.3); }
    .pill-fw { background: rgba(57, 197, 207, 0.15); color: var(--accent-cyan); border: 1px solid rgba(57, 197, 207, 0.3); font-family: 'Fira Code', monospace; }

    .timeline-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 380px;
      overflow-y: auto;
    }
    .timeline-item {
      display: flex;
      gap: 12px;
      font-size: 12px;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.02);
      border-left: 2px solid var(--accent-blue);
      border-radius: 4px;
    }
    .time-stamp { font-family: 'Fira Code', monospace; color: var(--accent-purple); font-weight: 500; min-width: 85px; }

    .log-box {
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      background: var(--card-sub-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px;
      height: 380px;
      overflow-y: auto;
      color: #8b949e;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .log-line { white-space: pre-wrap; word-break: break-all; }
    .log-line.phase { color: var(--accent-blue); font-weight: 600; }

    /* Unit Tests View Styles */
    .ut-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .ut-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .ut-title-area {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .ut-repo-name { font-size: 16px; font-weight: 700; color: #ffffff; }
    .ut-stats-summary { display: flex; align-items: center; gap: 12px; }
    .ut-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
    .ut-table th { text-align: left; padding: 8px 12px; color: var(--text-muted); border-bottom: 1px solid var(--border-color); font-size: 11px; text-transform: uppercase; font-weight: 600; }
    .ut-table td { padding: 8px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
    .ut-case-name { font-family: 'Fira Code', monospace; color: var(--text-main); font-weight: 500; }
    .ut-details-toggle {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      align-self: flex-start;
    }
    .ut-details-toggle:hover { color: var(--text-main); }
    .ut-raw-output {
      font-family: 'Fira Code', monospace;
      font-size: 11px;
      background: var(--card-sub-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px;
      max-height: 220px;
      overflow-y: auto;
      color: #8b949e;
      white-space: pre-wrap;
      word-break: break-all;
      display: none;
    }
    .ut-raw-output.visible { display: block; }
    .empty-state {
      text-align: center;
      padding: 48px 24px;
      background: var(--card-bg);
      border: 1px dashed var(--border-color);
      border-radius: 8px;
      color: var(--text-muted);
    }
    .empty-state h3 { color: #ffffff; font-size: 16px; margin-bottom: 6px; }
    .empty-state p { font-size: 13px; }

    /* Governance Forms */
    .gov-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .gov-card h3 { font-size: 15px; font-weight: 600; color: #ffffff; }
    .gov-textarea {
      width: 100%;
      background: var(--card-sub-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px;
      color: var(--text-main);
      font-family: inherit;
      font-size: 13px;
      resize: vertical;
      min-height: 60px;
    }

    /* Profile & Choices Form Styles */
    .profile-grid {
      display: grid;
      grid-template-columns: 1fr 1.3fr;
      gap: 24px;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }
    .form-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .form-input, .form-select {
      background: var(--card-sub-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 8px 12px;
      color: var(--text-main);
      font-family: inherit;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }
    .form-input:focus, .form-select:focus {
      border-color: var(--accent-blue);
    }
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .key-input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }
    .key-input-wrapper input {
      width: 100%;
      padding-right: 40px;
    }
    .key-toggle-btn {
      position: absolute;
      right: 8px;
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 14px;
    }

    /* Modal Backdrop */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    .modal-backdrop.active { display: flex; }
    .modal-box {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      width: 90%;
      max-width: 520px;
      padding: 28px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
      display: flex;
      flex-direction: column;
      gap: 16px;
      animation: modal-pop 0.25s ease-out;
    }
    @keyframes modal-pop { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 12px;
    }
    .modal-header h2 { font-size: 18px; font-weight: 700; color: #ffffff; }
    .close-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }

    /* Architecture Flowchart Visualizer */
    .topology-container {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .flowchart-svg-box {
      width: 100%;
      height: 420px;
      background: var(--card-sub-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* Notification Toast */
    .toast-msg {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--card-bg);
      border: 1px solid var(--accent-green);
      color: #ffffff;
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
      z-index: 2000;
      display: none;
      align-items: center;
      gap: 10px;
      font-size: 13px;
    }
    .toast-msg.error { border-color: var(--accent-red); }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div class="logo">
      <div class="pulse"></div>
      <h1>ASCM Autonomous Engineering Platform</h1>
    </div>
    <div class="header-actions">
      <select class="run-select" id="run-selector" onchange="onRunChanged()">
        <option value="live">🔴 Live Active Session</option>
      </select>
      <button class="btn btn-primary" onclick="openLaunchModal()">
        <span>+ Launch Goal</span>
      </button>
      <div class="user-profile-btn" id="user-nav-btn" onclick="onUserNavClick()">
        <span class="user-avatar-mini" id="nav-avatar"></span>
        <span id="nav-username">Guest</span>
      </div>
      <div class="status-badge" id="live-badge">SYSTEM ACTIVE</div>
    </div>
  </div>

  <!-- Phase & Agent Bar -->
  <div class="phase-bar">
    <div>
      <div class="phase-title">Current Phase / Goal</div>
      <div class="phase-name" id="phase-name">Initializing...</div>
    </div>
    <div>
      <div class="phase-title">Active Agent</div>
      <div class="phase-name" id="active-agent" style="color: var(--accent-purple);">None</div>
    </div>
  </div>

  <!-- Navigation Tabs -->
  <div class="tabs-bar">
    <button class="tab-btn active" id="tab-btn-pipeline" onclick="switchTab('pipeline')">
      <span>Pipeline & Agents</span>
    </button>
    <button class="tab-btn" id="tab-btn-unittests" onclick="switchTab('unittests')">
      <span>Unit Tests</span>
      <span class="tab-badge" id="tab-badge-tests">0</span>
    </button>
    <button class="tab-btn" id="tab-btn-architecture" onclick="switchTab('architecture')">
      <span>System Architecture</span>
    </button>
    <button class="tab-btn" id="tab-btn-governance" onclick="switchTab('governance')">
      <span>Governance & Milestones</span>
      <span class="tab-badge pending" id="tab-badge-gov" style="display: none;">Action Req</span>
    </button>
    <button class="tab-btn" id="tab-btn-profile" onclick="switchTab('profile')">
      <span>My Profile & Choices</span>
    </button>
  </div>

  <!-- VIEW 1: PIPELINE & AGENTS -->
  <div class="tab-content active" id="view-pipeline">
    <div id="pipeline-gov-banner" style="display: none;" class="gov-banner">
      <div>
        <div class="gov-banner-title" id="pipeline-gov-title">Action Required</div>
        <div class="gov-banner-desc" id="pipeline-gov-desc">Pending review or clarification</div>
      </div>
      <button class="btn btn-warning" onclick="switchTab('governance')">Open Governance Gate &rarr;</button>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">RUNNING AGENTS</span>
        <span class="stat-val val-running" id="cnt-running">0</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">COMPLETED AGENTS</span>
        <span class="stat-val val-completed" id="cnt-completed">0</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">WAITING AGENTS</span>
        <span class="stat-val val-waiting" id="cnt-waiting">0</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">TOTAL SUB-TASKS</span>
        <span class="stat-val val-tasks" id="cnt-tasks">0</span>
      </div>
    </div>

    <div class="main-grid">
      <div class="panel">
        <div class="panel-header">
          <span>Agent Pipeline & Status</span>
          <span style="font-size: 12px; color: var(--text-muted);" id="active-action-text">Idle</span>
        </div>
        <div class="agent-list" id="agent-list"></div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span>Timestamped Audit Timeline</span>
          <span style="font-size: 12px; color: var(--text-muted);">Exact Start & Transition Times</span>
        </div>
        <div class="timeline-list" id="timeline-list"></div>
      </div>
    </div>

    <div class="panel" style="margin-top: 24px;">
      <div class="panel-header">
        <span>Execution Log Audit Stream</span>
        <span style="font-size: 12px; color: var(--text-muted);">Timestamped Output</span>
      </div>
      <div class="log-box" id="log-box"></div>
    </div>
  </div>

  <!-- VIEW 2: UNIT TESTS TAB -->
  <div class="tab-content" id="view-unittests">
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">TOTAL UNIT TESTS</span>
        <span class="stat-val val-cyan" id="ut-stat-total">0</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">PASSED TESTS</span>
        <span class="stat-val val-completed" id="ut-stat-passed">0</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">FAILED TESTS</span>
        <span class="stat-val val-failed" id="ut-stat-failed">0</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">OVERALL PASS RATE</span>
        <span class="stat-val val-running" id="ut-stat-rate">100%</span>
      </div>
    </div>

    <div id="ut-runs-container">
      <div class="empty-state">
        <h3>No Unit Tests Executed Yet</h3>
        <p>Unit test cases are generated and executed dynamically as the Coder & Verifier engines produce polyglot microservice code.</p>
      </div>
    </div>
  </div>

  <!-- VIEW 3: SYSTEM ARCHITECTURE & FLOWCHART TAB -->
  <div class="tab-content" id="view-architecture">
    <div class="topology-container">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h3 style="color: #fff; font-size: 16px;">Live System Topology & Microservice Data Flow</h3>
          <p style="font-size: 13px; color: var(--text-muted);">Automated cross-repository dependency graph, contract boundaries, and verification gates.</p>
        </div>
        <span class="pill pill-running">Hermetic Container Verified</span>
      </div>

      <div class="flowchart-svg-box" id="flowchart-box">
        <svg width="100%" height="100%" viewBox="0 0 960 400" style="overflow: visible;">
          <defs>
            <linearGradient id="grad-blue" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#1f6feb" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#58a6ff" stop-opacity="0.1"/>
            </linearGradient>
            <linearGradient id="grad-green" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#2ea043" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#3fb950" stop-opacity="0.1"/>
            </linearGradient>
            <linearGradient id="grad-purple" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#8957e5" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#bc8cff" stop-opacity="0.1"/>
            </linearGradient>
            <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff"/>
            </marker>
          </defs>

          <!-- Step 1: Input Goal -->
          <g transform="translate(40, 160)">
            <rect width="160" height="70" rx="8" fill="url(#grad-blue)" stroke="#58a6ff" stroke-width="1.5"/>
            <text x="80" y="32" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">STAKEHOLDER GOAL</text>
            <text x="80" y="52" fill="#8b949e" font-size="11" text-anchor="middle">PRD / Feature Request</text>
          </g>

          <!-- Arrow 1 -->
          <line x1="200" y1="195" x2="250" y2="195" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)"/>

          <!-- Step 2: Product & Architect Agents -->
          <g transform="translate(250, 140)">
            <rect width="180" height="110" rx="8" fill="url(#grad-purple)" stroke="#bc8cff" stroke-width="1.5"/>
            <text x="90" y="28" fill="#bc8cff" font-size="12" font-weight="700" text-anchor="middle">AUTONOMOUS SQUAD</text>
            <text x="90" y="52" fill="#ffffff" font-size="11" text-anchor="middle">ProductAgent (90% Conf)</text>
            <text x="90" y="72" fill="#ffffff" font-size="11" text-anchor="middle">ArchitectAgent (HLD/LLD)</text>
            <text x="90" y="92" fill="#8b949e" font-size="10" text-anchor="middle">Model Tiering & Cascading</text>
          </g>

          <!-- Arrow 2 to Provider -->
          <path d="M 430 170 L 480 170 L 480 100 L 520 100" fill="none" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)"/>
          
          <!-- Arrow 2 to Consumer -->
          <path d="M 430 220 L 480 220 L 480 290 L 520 290" fill="none" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)"/>

          <!-- Step 3a: Provider Microservice -->
          <g transform="translate(520, 65)">
            <rect width="190" height="70" rx="8" fill="url(#grad-green)" stroke="#3fb950" stroke-width="1.5"/>
            <text x="95" y="30" fill="#3fb950" font-size="12" font-weight="700" text-anchor="middle">PROVIDER REPO</text>
            <text x="95" y="50" fill="#ffffff" font-size="11" text-anchor="middle">gRPC / REST Endpoints</text>
          </g>

          <!-- Step 3b: Consumer Microservice -->
          <g transform="translate(520, 255)">
            <rect width="190" height="70" rx="8" fill="url(#grad-green)" stroke="#3fb950" stroke-width="1.5"/>
            <text x="95" y="30" fill="#3fb950" font-size="12" font-weight="700" text-anchor="middle">CONSUMER REPO</text>
            <text x="95" y="50" fill="#ffffff" font-size="11" text-anchor="middle">Synchronized Client SDK</text>
          </g>

          <!-- Bidirectional sync arrow -->
          <line x1="615" y1="135" x2="615" y2="255" stroke="#39c5cf" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrow)"/>
          <text x="625" y="195" fill="#39c5cf" font-size="10">Contract Sync</text>

          <!-- Arrows to Verifier -->
          <path d="M 710 100 L 750 100 L 750 170 L 770 170" fill="none" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)"/>
          <path d="M 710 290 L 750 290 L 750 210 L 770 210" fill="none" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)"/>

          <!-- Step 4: Hermetic Sandbox & Unit Tests -->
          <g transform="translate(770, 145)">
            <rect width="160" height="95" rx="8" fill="url(#grad-blue)" stroke="#39c5cf" stroke-width="1.5"/>
            <text x="80" y="28" fill="#39c5cf" font-size="12" font-weight="700" text-anchor="middle">DOCKER VERIFIER</text>
            <text x="80" y="48" fill="#ffffff" font-size="11" text-anchor="middle">Isolated Execution</text>
            <text x="80" y="66" fill="#3fb950" font-size="11" text-anchor="middle">Testify / PyTest / Jest</text>
            <text x="80" y="84" fill="#8b949e" font-size="10" text-anchor="middle">Audit Logs & PII Clean</text>
          </g>
        </svg>
      </div>
    </div>
  </div>

  <!-- VIEW 4: GOVERNANCE & MILESTONES TAB -->
  <div class="tab-content" id="view-governance">
    <div id="gov-container">
      <div class="empty-state">
        <h3>Governance & Milestones Status</h3>
        <p>No human intervention is currently blocking pipeline execution. All gates will automatically prompt here if clarification or milestone feedback is required.</p>
      </div>
    </div>
  </div>

  <!-- VIEW 5: MY PROFILE & BYOK CHOICES TAB -->
  <div class="tab-content" id="view-profile">
    <div class="profile-grid">
      <!-- Profile Details Card -->
      <div class="panel">
        <div class="panel-header">
          <span>Personal Profile Details</span>
          <button class="btn btn-outline" style="padding: 4px 10px; font-size: 11px;" onclick="logoutUser()">Log Out</button>
        </div>
        <div class="form-group">
          <label class="form-label">Full Name</label>
          <input type="text" id="prof-name" class="form-input" placeholder="e.g., Alex Mercer">
        </div>
        <div class="form-group">
          <label class="form-label">Email Address</label>
          <input type="email" id="prof-email" class="form-input" placeholder="alex@company.com">
        </div>
        <div class="form-group">
          <label class="form-label">Mobile Phone Number</label>
          <input type="tel" id="prof-phone" class="form-input" placeholder="+1 (555) 000-0000">
        </div>
        <div style="font-size: 12px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; margin-top: 10px;">
          <div><strong>Member ID:</strong> <span id="prof-id" style="font-family: 'Fira Code', monospace; color: var(--accent-purple);">-</span></div>
          <div><strong>Account Created:</strong> <span id="prof-created">-</span></div>
          <div><strong>Last Active Login:</strong> <span id="prof-lastlogin">-</span></div>
        </div>
      </div>

      <!-- User Choices & BYOK Settings Card -->
      <div class="panel">
        <div class="panel-header">
          <span>User Choices & Bring Your Own Keys (BYOK)</span>
          <span class="pill pill-lang">Enterprise Encrypted</span>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Preferred LLM Provider</label>
            <select id="choice-provider" class="form-select">
              <option value="gemini">Google Gemini</option>
              <option value="openai">OpenAI (GPT-4o)</option>
              <option value="anthropic">Anthropic (Claude 3.5)</option>
              <option value="ollama">Local Open-Source (Ollama)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Fast / Triage Model</label>
            <input type="text" id="choice-fastmodel" class="form-input" placeholder="gemini-1.5-flash, gpt-4o-mini, llama3.2">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Primary Frontier Model</label>
          <input type="text" id="choice-primarymodel" class="form-input" placeholder="gemini-2.5-flash, gpt-4o, claude-3-5-sonnet">
        </div>

        <div class="form-group">
          <label class="form-label">Google Gemini API Key</label>
          <div class="key-input-wrapper">
            <input type="password" id="key-gemini" class="form-input" placeholder="AIzaSy...">
            <button type="button" class="key-toggle-btn" onclick="toggleKeyVisibility('key-gemini')">👁️</button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">OpenAI API Key</label>
          <div class="key-input-wrapper">
            <input type="password" id="key-openai" class="form-input" placeholder="sk-proj-...">
            <button type="button" class="key-toggle-btn" onclick="toggleKeyVisibility('key-openai')">👁️</button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Anthropic Claude API Key</label>
          <div class="key-input-wrapper">
            <input type="password" id="key-anthropic" class="form-input" placeholder="sk-ant-...">
            <button type="button" class="key-toggle-btn" onclick="toggleKeyVisibility('key-anthropic')">👁️</button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Local Ollama Base URL</label>
          <input type="text" id="key-ollama" class="form-input" placeholder="http://localhost:11434">
        </div>

        <div style="display: flex; gap: 20px; margin-top: 10px; margin-bottom: 16px;">
          <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer;">
            <input type="checkbox" id="choice-sandbox">
            <span>Hermetic Docker Sandbox</span>
          </label>
          <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer;">
            <input type="checkbox" id="choice-autoapprove">
            <span>Auto-Approve Checkpoints</span>
          </label>
        </div>

        <button class="btn btn-primary" style="align-self: flex-start;" onclick="saveUserProfile()">
          <span>Save Choices & Apply to Engine</span>
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL: LOGIN / SIGNUP SINGLE PAGER (EMAIL / MOBILE + OTP) -->
  <div class="modal-backdrop" id="modal-auth">
    <div class="modal-box">
      <div class="modal-header">
        <h2>Sign In or Create Account</h2>
        <button class="close-btn" onclick="closeAuthModal()">&times;</button>
      </div>
      <p style="font-size: 13px; color: var(--text-muted);">
        Enter your Email address or Mobile phone number. We'll send a 6-digit one-time passcode (OTP) for instant passwordless authentication.
      </p>

      <div id="auth-step-1">
        <div class="form-group">
          <label class="form-label">Email Address or Mobile Number</label>
          <input type="text" id="auth-identifier" class="form-input" placeholder="you@company.com or +15551234567">
        </div>
        <div class="form-group">
          <label class="form-label">Your Name (Optional for new users)</label>
          <input type="text" id="auth-name" class="form-input" placeholder="e.g. Jordan Lee">
        </div>
        <button class="btn btn-primary" style="width: 100%; margin-top: 8px;" onclick="sendAuthOtp()">
          <span>Send Verification Code (OTP) &rarr;</span>
        </button>
      </div>

      <div id="auth-step-2" style="display: none;">
        <div style="background: rgba(88, 166, 255, 0.1); border: 1px solid var(--accent-blue); padding: 10px; border-radius: 6px; font-size: 13px;">
          Verification code dispatched! <span id="auth-dev-hint" style="font-weight: 700; color: var(--accent-cyan);"></span>
        </div>
        <div class="form-group" style="margin-top: 14px;">
          <label class="form-label">Enter 6-Digit OTP</label>
          <input type="text" id="auth-otp" class="form-input" style="font-size: 20px; letter-spacing: 4px; text-align: center;" placeholder="123456" maxlength="6">
        </div>
        <div style="display: flex; gap: 10px; margin-top: 12px;">
          <button class="btn btn-primary" style="flex: 1;" onclick="verifyAuthOtp()">
            <span>Verify & Sign In</span>
          </button>
          <button class="btn btn-outline" onclick="resetAuthFlow()">
            <span>Back</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL: NEW GOAL LAUNCHER -->
  <div class="modal-backdrop" id="modal-launch">
    <div class="modal-box" style="max-width: 600px;">
      <div class="modal-header">
        <h2>Launch Autonomous Multi-Agent Sprint</h2>
        <button class="close-btn" onclick="closeLaunchModal()">&times;</button>
      </div>
      <p style="font-size: 13px; color: var(--text-muted);">
        Type your stakeholder requirement or feature goal. The squad will grill for clarifications, generate specs, implement code across repos, write unit tests, and self-heal.
      </p>

      <div class="form-group">
        <label class="form-label">Stakeholder Goal / PRD</label>
        <textarea id="launch-goal-text" class="gov-textarea" style="min-height: 90px;" placeholder="e.g. Implement credit purchase checkout with Stripe webhook and update consumer client..."></textarea>
      </div>

      <!-- Quick suggestions for founders and non-tech users -->
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
        <button class="pill pill-fw" style="cursor: pointer;" onclick="fillGoalSuggestion('Build Stripe payment webhook and update consumer client SDK with retries')">+ Stripe Webhook</button>
        <button class="pill pill-fw" style="cursor: pointer;" onclick="fillGoalSuggestion('Add Redis caching layer for user session verification with 15-minute TTL')">+ Redis Cache</button>
        <button class="pill pill-fw" style="cursor: pointer;" onclick="fillGoalSuggestion('Implement JWT token authentication middleware with sliding expiration')">+ JWT Auth</button>
      </div>

      <div class="form-group">
        <label class="form-label">Target Repositories</label>
        <div id="launch-repo-list" style="max-height: 120px; overflow-y: auto; background: var(--card-sub-bg); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 12px;">
          <span style="font-size: 12px; color: var(--text-muted);">Detecting workspace repositories...</span>
        </div>
      </div>

      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <input type="checkbox" id="launch-autoapprove" checked>
        <label for="launch-autoapprove" style="font-size: 13px; color: var(--text-muted); cursor: pointer;">Auto-approve milestones and low-impact checkpoints</label>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
        <button class="btn btn-outline" onclick="closeLaunchModal()">Cancel</button>
        <button class="btn btn-success" onclick="executeLaunch()">
          <span>🚀 Start Autonomous Sprint</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div class="toast-msg" id="toast-msg">Notification</div>

  <script>
    let selectedRunId = 'live';
    let currentTab = 'pipeline';
    let currentUser = null;

    function showToast(msg, isError = false) {
      const toast = document.getElementById('toast-msg');
      toast.innerText = msg;
      toast.className = 'toast-msg' + (isError ? ' error' : '');
      toast.style.display = 'flex';
      setTimeout(() => { toast.style.display = 'none'; }, 3500);
    }

    function switchTab(tabName) {
      currentTab = tabName;
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      const activeBtn = document.getElementById(`tab-btn-${tabName}`);
      const activeContent = document.getElementById(`view-${tabName}`);
      if (activeBtn) activeBtn.classList.add('active');
      if (activeContent) activeContent.classList.add('active');
    }

    /* Auth & User Management */
    async function loadCurrentUser() {
      try {
        const res = await fetch('/api/auth/current');
        const data = await res.json();
        currentUser = data.user;
        renderNavUser();
        if (currentUser) {
          fillProfileForm(currentUser);
        }
      } catch (err) {
        console.error("Failed to load user:", err);
      }
    }

    function renderNavUser() {
      const btn = document.getElementById('user-nav-btn');
      const nameSpan = document.getElementById('nav-username');
      if (currentUser && currentUser.name) {
        nameSpan.innerText = currentUser.name;
        btn.title = `Logged in as ${currentUser.email || currentUser.phone || currentUser.name}`;
      } else {
        nameSpan.innerText = "Sign In / OTP";
        btn.title = "Click to sign in or create an account with OTP";
      }
    }

    function onUserNavClick() {
      if (currentUser) {
        switchTab('profile');
      } else {
        openAuthModal();
      }
    }

    function openAuthModal() {
      document.getElementById('modal-auth').classList.add('active');
      resetAuthFlow();
    }

    function closeAuthModal() {
      document.getElementById('modal-auth').classList.remove('active');
    }

    function resetAuthFlow() {
      document.getElementById('auth-step-1').style.display = 'block';
      document.getElementById('auth-step-2').style.display = 'none';
      document.getElementById('auth-otp').value = '';
    }

    async function sendAuthOtp() {
      const ident = document.getElementById('auth-identifier').value.trim();
      const name = document.getElementById('auth-name').value.trim();
      if (!ident) {
        alert("Please enter a valid email address or mobile phone number.");
        return;
      }

      try {
        const res = await fetch('/api/auth/send-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier: ident, name: name })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          document.getElementById('auth-step-1').style.display = 'none';
          document.getElementById('auth-step-2').style.display = 'block';
          if (data.dev_otp) {
            document.getElementById('auth-dev-hint').innerText = `(Test Passcode: ${data.dev_otp})`;
            document.getElementById('auth-otp').value = data.dev_otp;
          }
          showToast("OTP sent successfully!");
        } else {
          alert(data.message || "Failed to send OTP.");
        }
      } catch (err) {
        alert("Request error: " + err);
      }
    }

    async function verifyAuthOtp() {
      const ident = document.getElementById('auth-identifier').value.trim();
      const otp = document.getElementById('auth-otp').value.trim();
      const name = document.getElementById('auth-name').value.trim();

      if (!otp) {
        alert("Please enter the 6-digit OTP.");
        return;
      }

      try {
        const res = await fetch('/api/auth/verify-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier: ident, otp: otp, name: name })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          currentUser = data.user;
          renderNavUser();
          fillProfileForm(currentUser);
          closeAuthModal();
          showToast(`Welcome, ${currentUser.name}!`);
          switchTab('profile');
        } else {
          alert(data.message || "Invalid OTP verification.");
        }
      } catch (err) {
        alert("Verification error: " + err);
      }
    }

    function fillProfileForm(u) {
      if (!u) return;
      document.getElementById('prof-name').value = u.name || '';
      document.getElementById('prof-email').value = u.email || '';
      document.getElementById('prof-phone').value = u.phone || '';
      document.getElementById('prof-id').innerText = u.id || '-';
      document.getElementById('prof-created').innerText = u.created_at ? new Date(u.created_at).toLocaleString() : '-';
      document.getElementById('prof-lastlogin').innerText = u.last_login ? new Date(u.last_login).toLocaleString() : '-';

      const ch = u.choices || {};
      if (ch.preferred_provider) document.getElementById('choice-provider').value = ch.preferred_provider;
      if (ch.fast_model) document.getElementById('choice-fastmodel').value = ch.fast_model;
      if (ch.primary_model) document.getElementById('choice-primarymodel').value = ch.primary_model;
      if (ch.gemini_api_key) document.getElementById('key-gemini').value = ch.gemini_api_key;
      if (ch.openai_api_key) document.getElementById('key-openai').value = ch.openai_api_key;
      if (ch.anthropic_api_key) document.getElementById('key-anthropic').value = ch.anthropic_api_key;
      if (ch.ollama_base_url) document.getElementById('key-ollama').value = ch.ollama_base_url;
      document.getElementById('choice-sandbox').checked = !!ch.use_sandbox;
      document.getElementById('choice-autoapprove').checked = !!ch.auto_approve;
    }

    async function saveUserProfile() {
      const updates = {
        name: document.getElementById('prof-name').value.trim(),
        email: document.getElementById('prof-email').value.trim(),
        phone: document.getElementById('prof-phone').value.trim(),
        choices: {
          preferred_provider: document.getElementById('choice-provider').value,
          fast_model: document.getElementById('choice-fastmodel').value.trim(),
          primary_model: document.getElementById('choice-primarymodel').value.trim(),
          gemini_api_key: document.getElementById('key-gemini').value.trim(),
          openai_api_key: document.getElementById('key-openai').value.trim(),
          anthropic_api_key: document.getElementById('key-anthropic').value.trim(),
          ollama_base_url: document.getElementById('key-ollama').value.trim(),
          use_sandbox: document.getElementById('choice-sandbox').checked,
          auto_approve: document.getElementById('choice-autoapprove').checked,
        }
      };

      try {
        const res = await fetch('/api/auth/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier: (currentUser || {}).id, updates: updates })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          currentUser = data.user;
          renderNavUser();
          showToast("Choices & API keys saved successfully!");
        } else {
          alert(data.message || "Failed to update profile.");
        }
      } catch (err) {
        alert("Error saving profile: " + err);
      }
    }

    async function logoutUser() {
      try {
        await fetch('/api/auth/logout', { method: 'POST' });
        currentUser = null;
        renderNavUser();
        showToast("Logged out");
        switchTab('pipeline');
      } catch (err) {
        console.error(err);
      }
    }

    function toggleKeyVisibility(elemId) {
      const elem = document.getElementById(elemId);
      if (elem.type === 'password') {
        elem.type = 'text';
      } else {
        elem.type = 'password';
      }
    }

    /* Launch Goal Modal */
    function openLaunchModal() {
      document.getElementById('modal-launch').classList.add('active');
      detectWorkspaceRepos();
    }

    function closeLaunchModal() {
      document.getElementById('modal-launch').classList.remove('active');
    }

    function fillGoalSuggestion(text) {
      document.getElementById('launch-goal-text').value = text;
    }

    async function detectWorkspaceRepos() {
      try {
        const res = await fetch('/api/repos/detect');
        const data = await res.json();
        const container = document.getElementById('launch-repo-list');
        const repos = data.repos || [];
        if (repos.length === 0) {
          container.innerHTML = '<span style="font-size: 12px; color: var(--text-muted);">Current workspace will be used by default.</span>';
          return;
        }
        container.innerHTML = repos.map(r => `
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <input type="checkbox" name="launch_repos" value="${r.path}" id="repo_${r.name}" checked>
            <label for="repo_${r.name}" style="font-size: 12px; color: #fff; cursor: pointer;">
              <strong>${r.name}</strong> <span style="color: var(--text-muted); font-size: 11px;">(${r.path})</span>
            </label>
          </div>
        `).join('');
      } catch (err) {
        console.error("Failed to detect repos:", err);
      }
    }

    async function executeLaunch() {
      const goal = document.getElementById('launch-goal-text').value.trim();
      if (!goal) {
        alert("Please enter a goal.");
        return;
      }
      const checkedBoxes = Array.from(document.querySelectorAll('input[name="launch_repos"]:checked'));
      const repos = checkedBoxes.map(c => c.value);
      const autoApprove = document.getElementById('launch-autoapprove').checked;

      try {
        const res = await fetch('/api/action/launch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ goal: goal, repos: repos, auto_approve: autoApprove })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          closeLaunchModal();
          showToast("Squad launched! Connecting live stream...");
          selectedRunId = 'live';
          document.getElementById('run-selector').value = 'live';
          switchTab('pipeline');
          fetchState();
        } else {
          alert(data.message || "Launch failed.");
        }
      } catch (err) {
        alert("Launch error: " + err);
      }
    }

    /* Core Runs & Telemetry */
    async function loadRunsList() {
      try {
        const res = await fetch('/api/runs');
        const runs = await res.json();
        const sel = document.getElementById('run-selector');
        
        const currentVal = sel.value;
        sel.innerHTML = '<option value="live">🔴 Live Active Session</option>';
        
        runs.forEach(r => {
          const opt = document.createElement('option');
          opt.value = r.run_id;
          opt.innerText = `📁 ${r.run_id} - Goal: "${(r.goal || '').substring(0, 30)}"`;
          sel.appendChild(opt);
        });

        if (currentVal && Array.from(sel.options).some(o => o.value === currentVal)) {
          sel.value = currentVal;
        }
      } catch (err) {
        console.error("Failed to fetch runs list:", err);
      }
    }

    function onRunChanged() {
      selectedRunId = document.getElementById('run-selector').value;
      fetchState();
    }

    async function submitGovAction(endpoint, payload) {
      try {
        await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        fetchState();
      } catch (err) {
        alert("Action failed: " + err);
      }
    }

    function toggleRawOutput(id) {
      const box = document.getElementById(id);
      if (box) box.classList.toggle('visible');
    }

    async function fetchState() {
      try {
        const url = `/api/state?run_id=${selectedRunId}`;
        const res = await fetch(url);
        const data = await res.json();

        // Phase & Status
        const phaseElem = document.getElementById('phase-name');
        phaseElem.innerText = data.phase + (data.user_goal ? ` (${data.user_goal})` : '');
        
        const badge = document.getElementById('live-badge');
        const isCrashed = data.phase && (data.phase.includes('FAILED') || data.phase.includes('CRASHED'));
        const isCompleted = data.phase && data.phase.includes('Completed');

        if (isCrashed) {
          phaseElem.style.color = 'var(--accent-red)';
          badge.innerText = 'SYSTEM CRASHED';
          badge.style.background = 'rgba(248, 81, 73, 0.15)';
          badge.style.color = 'var(--accent-red)';
          badge.style.borderColor = 'rgba(248, 81, 73, 0.3)';
        } else if (isCompleted) {
          phaseElem.style.color = 'var(--accent-green)';
          badge.innerText = 'WORKFLOW COMPLETED';
          badge.style.background = 'rgba(63, 185, 80, 0.15)';
          badge.style.color = 'var(--accent-green)';
          badge.style.borderColor = 'rgba(63, 185, 80, 0.3)';
        } else {
          phaseElem.style.color = 'var(--accent-blue)';
          badge.innerText = 'SYSTEM ACTIVE';
          badge.style.background = 'rgba(88, 166, 255, 0.15)';
          badge.style.color = 'var(--accent-blue)';
          badge.style.borderColor = 'rgba(88, 166, 255, 0.3)';
        }

        document.getElementById('active-agent').innerText = data.active_agent || 'None';
        document.getElementById('active-action-text').innerText = data.active_action || 'Idle';

        // Pipeline stats
        document.getElementById('cnt-running').innerText = data.counts.running || 0;
        document.getElementById('cnt-completed').innerText = data.counts.completed || 0;
        document.getElementById('cnt-waiting').innerText = data.counts.waiting || 0;
        document.getElementById('cnt-tasks').innerText = data.counts.total_tasks || 0;

        // Render Agents
        const agentContainer = document.getElementById('agent-list');
        agentContainer.innerHTML = '';
        for (const [name, info] of Object.entries(data.agents || {})) {
          const item = document.createElement('div');
          item.className = 'agent-item';
          const durText = info.duration_sec ? ` (${info.duration_sec}s)` : '';
          item.innerHTML = `
            <div>
              <div class="agent-name">${name}${durText}</div>
              <div class="agent-action">${info.action || 'Idle'}</div>
            </div>
            <span class="pill pill-${info.status}">${info.status}</span>
          `;
          agentContainer.appendChild(item);
        }

        // Render Timeline
        const timeContainer = document.getElementById('timeline-list');
        timeContainer.innerHTML = '';
        (data.timeline_events || []).forEach(evt => {
          const div = document.createElement('div');
          div.className = 'timeline-item';
          div.innerHTML = `
            <span class="time-stamp">${evt.timestamp}</span>
            <div><strong>${evt.agent}</strong>: ${evt.action}</div>
          `;
          timeContainer.appendChild(div);
        });
        timeContainer.scrollTop = timeContainer.scrollHeight;

        // Render Logs
        const logBox = document.getElementById('log-box');
        logBox.innerHTML = '';
        (data.logs || []).forEach(line => {
          const div = document.createElement('div');
          div.className = 'log-line' + (line.includes('[PHASE]') ? ' phase' : '');
          div.innerText = line;
          logBox.appendChild(div);
        });
        logBox.scrollTop = logBox.scrollHeight;

        // Render Unit Tests
        const testResults = data.test_results || [];
        document.getElementById('tab-badge-tests').innerText = testResults.length;

        let totalTests = 0;
        let totalPassed = 0;
        let totalFailed = 0;

        testResults.forEach(r => {
          totalTests += (r.total_tests || 0);
          totalPassed += (r.passed_count || 0);
          totalFailed += (r.failed_count || 0);
        });

        document.getElementById('ut-stat-total').innerText = totalTests;
        document.getElementById('ut-stat-passed').innerText = totalPassed;
        document.getElementById('ut-stat-failed').innerText = totalFailed;
        const passRate = totalTests > 0 ? Math.round((totalPassed / totalTests) * 100) : 100;
        document.getElementById('ut-stat-rate').innerText = `${passRate}%`;

        const utContainer = document.getElementById('ut-runs-container');
        if (testResults.length === 0) {
          utContainer.innerHTML = `
            <div class="empty-state">
              <h3>No Unit Tests Executed Yet</h3>
              <p>Unit test cases are generated and executed dynamically as the Coder & Verifier engines produce polyglot microservice code.</p>
            </div>
          `;
        } else {
          utContainer.innerHTML = '';
          testResults.forEach((run, idx) => {
            const card = document.createElement('div');
            card.className = 'ut-card';
            const rawId = `ut-raw-${idx}`;

            const cases = run.test_cases || [];
            let tableHtml = '';
            if (cases.length > 0) {
              const rows = cases.map(c => `
                <tr>
                  <td class="ut-case-name">${c.name || 'Unnamed test'}</td>
                  <td><span class="pill pill-${(c.status || '').toLowerCase() === 'pass' ? 'completed' : 'failed'}">${c.status || 'PASS'}</span></td>
                  <td style="color: var(--text-muted); font-size: 12px;">${c.duration || '-'}</td>
                  <td style="color: var(--accent-red); font-size: 11px;">${c.details || ''}</td>
                </tr>
              `).join('');
              tableHtml = `
                <table class="ut-table">
                  <thead>
                    <tr><th>Test Case</th><th>Status</th><th>Duration</th><th>Details</th></tr>
                  </thead>
                  <tbody>${rows}</tbody>
                </table>
              `;
            } else {
              tableHtml = `<div style="font-size: 12px; color: var(--text-muted); font-style: italic;">All ${run.total_tests} test cases executed cleanly in suite.</div>`;
            }

            const rawContent = (run.test_output || '') + (run.vet_output ? `\n\n--- Code Analysis / Vet Output ---\n${run.vet_output}` : '');

            card.innerHTML = `
              <div class="ut-header">
                <div class="ut-title-area">
                  <span class="ut-repo-name">${run.repo || 'Target Service'}</span>
                  <span class="pill pill-lang">${(run.language || 'polyglot').toUpperCase()}</span>
                  <span class="pill pill-fw">${run.framework || 'Language Runner'}</span>
                  <span class="pill pill-${run.passed ? 'completed' : 'failed'}">${run.passed ? 'PASSED' : 'FAILED'}</span>
                </div>
                <div class="ut-stats-summary">
                  <span style="font-size: 13px; font-weight: 600; color: ${run.passed ? 'var(--accent-green)' : 'var(--accent-red)'};">
                    ${run.passed_count}/${run.total_tests} Passed
                  </span>
                  <span style="font-size: 12px; color: var(--text-muted);">${run.timestamp || ''}</span>
                </div>
              </div>
              <div>${tableHtml}</div>
              <button class="ut-details-toggle" onclick="toggleRawOutput('${rawId}')">
                <span>Toggle Raw Runner Output (stdout & stderr)</span>
              </button>
              <div class="ut-raw-output" id="${rawId}">${rawContent || 'No raw stdout logged.'}</div>
            `;
            utContainer.appendChild(card);
          });
        }

        // Governance Check
        const govBadge = document.getElementById('tab-badge-gov');
        const govBanner = document.getElementById('pipeline-gov-banner');
        const govTitle = document.getElementById('pipeline-gov-title');
        const govDesc = document.getElementById('pipeline-gov-desc');
        const govContainer = document.getElementById('gov-container');

        const hasGov = data.pending_milestone || data.pending_approval || data.clarification_needed;
        if (hasGov) {
          govBadge.style.display = 'inline-block';
          govBanner.style.display = 'flex';
          if (data.pending_milestone) {
            govTitle.innerText = `Milestone Review Required: ${data.milestone_name}`;
            govDesc.innerText = data.milestone_summary || 'Review required before proceeding.';
          } else if (data.pending_approval) {
            govTitle.innerText = 'Code Changes Approval Required';
            govDesc.innerText = `${(data.pending_changes_data || []).length} repository modifications await sign-off.`;
          } else if (data.clarification_needed) {
            govTitle.innerText = 'Clarification Requested';
            govDesc.innerText = 'Product agent requires requirement clarifications.';
          }
        } else {
          govBadge.style.display = 'none';
          govBanner.style.display = 'none';
        }

        // Render Governance Tab
        if (hasGov) {
          let govHtml = '';
          if (data.pending_milestone) {
            govHtml += `
              <div class="gov-card">
                <h3>Milestone Gate: ${data.milestone_name}</h3>
                <p style="font-size: 13px; color: var(--text-muted);">${data.milestone_summary}</p>
                <textarea id="milestone-feedback" class="gov-textarea" placeholder="Optional feedback or rework instructions..."></textarea>
                <div style="display: flex; gap: 10px; margin-top: 8px;">
                  <button class="btn btn-success" onclick="submitGovAction('/api/action/milestone', { proceed: true, feedback: document.getElementById('milestone-feedback').value })">Confirm & Proceed</button>
                  <button class="btn btn-danger" onclick="submitGovAction('/api/action/milestone', { proceed: false, feedback: document.getElementById('milestone-feedback').value })">Request Rework</button>
                </div>
              </div>
            `;
          }
          if (data.pending_approval) {
            govHtml += `
              <div class="gov-card">
                <h3>Code Changes Sign-Off Gate</h3>
                <p style="font-size: 13px; color: var(--text-muted);">Please inspect the pending modifications generated by Coder agents across repositories:</p>
                <ul style="font-size: 12px; margin-left: 18px; color: var(--accent-blue);">
                  ${(data.pending_changes_data || []).map(c => `<li>${c.repo}: ${c.file_count} files</li>`).join('')}
                </ul>
                <div style="display: flex; gap: 10px; margin-top: 8px;">
                  <button class="btn btn-success" onclick="submitGovAction('/api/action/approve', {})">Approve & Merge</button>
                  <button class="btn btn-danger" onclick="submitGovAction('/api/action/reject', {})">Reject Changes</button>
                </div>
              </div>
            `;
          }
          if (data.clarification_needed) {
            const qList = (data.clarification_questions || []).map(q => `<li>${q}</li>`).join('');
            govHtml += `
              <div class="gov-card">
                <h3>PRD Clarifications Needed</h3>
                <ul style="font-size: 13px; margin-left: 18px; color: var(--accent-yellow); margin-bottom: 8px;">${qList}</ul>
                <textarea id="clarify-answer" class="gov-textarea" placeholder="Provide clarifications..."></textarea>
                <div style="margin-top: 8px;">
                  <button class="btn btn-primary" onclick="submitGovAction('/api/action/clarify', { answer: document.getElementById('clarify-answer').value })">Submit Clarification</button>
                </div>
              </div>
            `;
          }
          govContainer.innerHTML = govHtml;
        } else {
          govContainer.innerHTML = `
            <div class="empty-state">
              <h3>Governance & Milestones Status</h3>
              <p>No human intervention is currently blocking pipeline execution. All gates will automatically prompt here if clarification or milestone feedback is required.</p>
            </div>
          `;
        }

      } catch (err) {
        console.error("Failed to fetch state:", err);
      }
    }

    loadCurrentUser();
    loadRunsList();
    setInterval(loadRunsList, 5000);
    setInterval(() => {
      if (selectedRunId === 'live') fetchState();
    }, 1000);
    fetchState();
  </script>
</body>
</html>
"""

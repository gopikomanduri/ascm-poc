"""Privacy-minimized, project-scoped activity correlation for the ASCM mentor.

The first version consumes filesystem and test-result events supplied by adapters.
It stores hypotheses separately from founder-confirmed goals/tasks. It does not
capture keystrokes, source contents, terminal output, browser contents, or screenshots.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


ALLOWED_EVENT_TYPES = {"file_changed", "test_passed", "test_failed", "active_app_changed", "browser_domain_seen", "terminal_command"}
MAX_EVENTS_READ = 1000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class ContextFusionEngine:
    """Correlate events per Git project and persist explainable task hypotheses."""

    def __init__(self, workspace_path: str | Path = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.history_dir = self.workspace_path / ".ascm_history"
        self.events_path = self.history_dir / "activity_events.jsonl"
        self.contexts_dir = self.history_dir / "project_contexts"
        self._write_lock = threading.Lock()

    def _project_root_for(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser().resolve()
        start = candidate if candidate.is_dir() else candidate.parent
        try:
            result = subprocess.run(
                ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                root = Path(result.stdout.strip()).resolve()
                if root == self.workspace_path or self.workspace_path in root.parents:
                    return root
        except (OSError, subprocess.SubprocessError):
            pass
        return self.workspace_path

    @staticmethod
    def _project_id(root: Path) -> str:
        return hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:16]

    def _append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            with self.events_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def record_file_change(self, path: str | Path) -> Dict[str, Any]:
        """Record a changed file path only; never read the file's contents."""
        changed = Path(path).expanduser().resolve()
        try:
            changed.relative_to(self.workspace_path)
        except ValueError:
            raise ValueError("Observed file must be inside the configured workspace") from None

        root = self._project_root_for(changed)
        try:
            relative_path = changed.relative_to(root).as_posix()
        except ValueError:
            relative_path = changed.name
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": _iso(_now()),
            "event_type": "file_changed",
            "source": "filesystem",
            "project_id": self._project_id(root),
            "project_root": str(root),
            "path": relative_path[:500],
        }
        return self._append(event)

    def record_test_result(
        self, *, project_path: str | Path, passed: bool, exit_code: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record test status only; do not persist command output or test contents."""
        root = self._project_root_for(project_path)
        if exit_code is not None and not isinstance(exit_code, int):
            raise ValueError("exit_code must be an integer or None")
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": _iso(_now()),
            "event_type": "test_passed" if passed else "test_failed",
            "source": "test_adapter",
            "project_id": self._project_id(root),
            "project_root": str(root),
            "exit_code": exit_code,
        }
        return self._append(event)

    def _record_project_event(self, *, project_path: str | Path, event_type: str, source: str, **metadata: Any) -> Dict[str, Any]:
        """Append a schema-limited metadata event, never raw content."""
        if event_type not in ALLOWED_EVENT_TYPES or event_type == "file_changed":
            raise ValueError("Unsupported generic activity event")
        root = self._project_root_for(project_path)
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": _iso(_now()),
            "event_type": event_type,
            "source": source,
            "project_id": self._project_id(root),
            "project_root": str(root),
        }
        allowed = {
            "app_name": (str, 100),
            "domain": (str, 253),
            "command_category": (str, 40),
            "exit_code": (int, None),
        }
        for key, value in metadata.items():
            if key not in allowed:
                raise ValueError(f"Unsupported activity metadata field: {key}")
            expected, max_len = allowed[key]
            if value is not None and (not isinstance(value, expected) or isinstance(value, bool)):
                raise ValueError(f"Invalid value for {key}")
            if isinstance(value, str):
                value = value.strip()
                if not value or (max_len and len(value) > max_len):
                    raise ValueError(f"Invalid value for {key}")
            event[key] = value
        return self._append(event)

    def record_active_app(self, *, cwd: str | Path, app_name: str) -> Dict[str, Any]:
        return self._record_project_event(
            project_path=cwd, event_type="active_app_changed", source="active_window",
            app_name=app_name,
        )

    def record_browser_domain(self, *, cwd: str | Path, domain: str) -> Dict[str, Any]:
        # Caller must normalize and validate the domain; paths and query strings are never stored.
        if "/" in domain or "?" in domain or "@" in domain:
            raise ValueError("Only a hostname may be recorded")
        return self._record_project_event(
            project_path=cwd, event_type="browser_domain_seen", source="browser_opt_in",
            domain=domain.lower(),
        )

    def record_terminal_event(
        self, *, cwd: str | Path, command_category: str, exit_code: Optional[int] = None
    ) -> Dict[str, Any]:
        if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
            raise ValueError("exit_code must be an integer or None")
        return self._record_project_event(
            project_path=cwd, event_type="terminal_command", source="shell_hook",
            command_category=command_category, exit_code=exit_code,
        )

    def _read_events(self) -> list[Dict[str, Any]]:
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()[-MAX_EVENTS_READ:]
        except OSError:
            return []
        events = []
        for line in lines:
            try:
                event = json.loads(line)
                if isinstance(event, dict) and event.get("event_type") in ALLOWED_EVENT_TYPES:
                    events.append(event)
            except json.JSONDecodeError:
                continue
        return events

    def _persist_context(self, project_id: str, context: Dict[str, Any]) -> None:
        self.contexts_dir.mkdir(parents=True, exist_ok=True)
        path = self.contexts_dir / f"{project_id}.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(context, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(path)

    def infer_context(self, project_path: str | Path | None = None) -> Dict[str, Any]:
        """Infer a task hypothesis for one project, or return hypotheses for all observed projects."""
        events = self._read_events()
        if project_path is not None:
            root = self._project_root_for(project_path)
            project_id = self._project_id(root)
            selected = [e for e in events if e.get("project_id") == project_id]
            return self._infer_one(project_id, str(root), selected)

        grouped: Dict[str, list[Dict[str, Any]]] = {}
        roots: Dict[str, str] = {}
        for event in events:
            project_id = event.get("project_id")
            root = event.get("project_root")
            if not isinstance(project_id, str) or not isinstance(root, str):
                continue
            grouped.setdefault(project_id, []).append(event)
            roots[project_id] = root
        contexts = [self._infer_one(pid, roots[pid], group) for pid, group in grouped.items()]
        return sorted(contexts, key=lambda item: item.get("updated_at") or "", reverse=True)

    def _infer_one(
        self, project_id: str, project_root: str, events: Iterable[Dict[str, Any]]
    ) -> Dict[str, Any]:
        now = _now()
        ordered = sorted(
            (event for event in events if _parse_time(event.get("timestamp")) is not None),
            key=lambda event: _parse_time(event["timestamp"]) or now,
        )
        recent = [
            event for event in ordered
            if now - (_parse_time(event["timestamp"]) or now) <= timedelta(minutes=30)
        ]
        edits = [e for e in recent if e.get("event_type") == "file_changed"]
        tests = [e for e in recent if e.get("event_type") in {"test_passed", "test_failed"}]
        latest_edit = max(edits, key=lambda e: e["timestamp"], default=None)
        latest_test = max(tests, key=lambda e: e["timestamp"], default=None)

        task = None
        confidence = 0.0
        rationale = "No recent activity is available for this project."
        evidence = []
        terminal = [e for e in recent if e.get("event_type") == "terminal_command"]
        active_apps = [e for e in recent if e.get("event_type") == "active_app_changed"]
        browser_events = [e for e in recent if e.get("event_type") == "browser_domain_seen"]
        latest_terminal = max(terminal, key=lambda e: e["timestamp"], default=None)
        if latest_test and latest_edit and latest_test["timestamp"] >= latest_edit["timestamp"]:
            if latest_test["event_type"] == "test_failed":
                task = "Investigating test failures after recent code changes"
                confidence = 0.82
                rationale = "A test failure was recorded after a code change in the same project."
            else:
                task = "Verifying recent code changes with tests"
                confidence = 0.74
                rationale = "A passing test result was recorded after a code change in the same project."
            evidence = [latest_edit["event_id"], latest_test["event_id"]]
        elif len(edits) >= 3:
            parent = str(Path(latest_edit.get("path", "")).parent) if latest_edit else "."
            task = f"Implementing changes in {parent if parent != '.' else 'the project'}"
            confidence = 0.61
            rationale = "Several code-file changes were observed recently; the exact intent remains unconfirmed."
            evidence = [e["event_id"] for e in edits[-5:]]
        elif latest_edit:
            task = f"Recent code activity in {Path(latest_edit.get('path', '')).parent.as_posix() or 'the project'}"
            confidence = 0.35
            rationale = "A file changed, but there is not enough evidence to infer the underlying task."
            evidence = [latest_edit["event_id"]]
        elif latest_terminal and latest_terminal.get("command_category") in {"python_tests", "javascript_tests", "go_tests", "rust_tests"}:
            task = "Running and evaluating the project test suite"
            confidence = 0.58
            rationale = "A test command category was observed; no command text or output was retained."
            evidence = [latest_terminal["event_id"]]
        elif active_apps:
            latest_app = max(active_apps, key=lambda e: e["timestamp"])
            task = f"Working in {latest_app.get('app_name', 'an application')}"
            confidence = 0.25
            rationale = "Foreground application metadata is weak evidence and cannot establish project intent."
            evidence = [latest_app["event_id"]]
        elif browser_events:
            latest_domain = max(browser_events, key=lambda e: e["timestamp"])
            task = f"Researching {latest_domain.get('domain', 'a website')}"
            confidence = 0.30
            rationale = "An opt-in browser domain was observed; no page URL, path, title, or content was retained."
            evidence = [latest_domain["event_id"]]

        context = {
            "project_id": project_id,
            "project_root": project_root,
            "task_hypothesis": task,
            "confidence": confidence,
            "is_confirmed": False,
            "status": "hypothesis" if task else "unknown",
            "rationale": rationale,
            "evidence_event_ids": evidence,
            "updated_at": _iso(now),
        }
        self._persist_context(project_id, context)
        return context

    def list_saved_contexts(self) -> list[Dict[str, Any]]:
        """Return persisted per-project hypotheses without reading project source files."""
        contexts = []
        try:
            paths = list(self.contexts_dir.glob("*.json"))
        except OSError:
            return []
        for path in paths:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    contexts.append(value)
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(contexts, key=lambda item: item.get("updated_at") or "", reverse=True)

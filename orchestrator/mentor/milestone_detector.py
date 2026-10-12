"""Evidence-based local milestone/checkpoint detector.

It records Git checkpoint metadata only: commit hashes, file counts and test-event
timestamps. Commit messages, source contents and diffs are never copied into the
history. A checkpoint is not labelled complete unless there is recent passing
test evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.security.audit_logger import AuditLogger


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MilestoneDetector:
    def __init__(self, repo_path: str | Path, audit_logger: AuditLogger | None = None):
        self.repo_path = Path(repo_path).resolve()
        self.history_dir = self.repo_path / ".ascm_history"
        self.state_path = self.history_dir / "milestone_detector_state.json"
        self.events_path = self.history_dir / "detected_milestones.jsonl"
        self.audit = audit_logger or AuditLogger(log_dir=str(self.history_dir / "audit"))

    def _git(self, *args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), *args],
                capture_output=True, text=True, timeout=3, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    def _read_state(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_json(self, path: Path, value: Any) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(path)

    def poll(self) -> dict[str, Any] | None:
        head = self._git("rev-parse", "HEAD")
        if not head or len(head) > 80:
            return None
        state = self._read_state()
        if state.get("last_head") == head:
            return None

        previous = state.get("last_head")
        counts = self._git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", head)
        changed_paths = [line for line in (counts or "").splitlines() if line]
        tracked = self._git("status", "--porcelain", "--untracked-files=no")
        status_lines = [line for line in (tracked or "").splitlines() if line]
        latest_test = None
        try:
            events_path = self.history_dir / "activity_events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()[-1000:]]
            tests = [event for event in events if event.get("event_type") in {"test_passed", "test_failed"}]
            latest_test = max(tests, key=lambda item: item.get("timestamp", ""), default=None)
        except (OSError, json.JSONDecodeError):
            pass

        tested_at = latest_test.get("timestamp") if latest_test else None
        test_passed = bool(latest_test and latest_test.get("event_type") == "test_passed")
        checkpoint = {
            "event_id": str(uuid.uuid4()),
            "timestamp": _utc_now().isoformat(),
            "event_type": "git_checkpoint",
            "project_id": hashlib.sha256(str(self.repo_path).encode("utf-8")).hexdigest()[:16],
            "head": head,
            "previous_head": previous if isinstance(previous, str) else None,
            "changed_file_count": len(changed_paths),
            "uncommitted_tracked_file_count": len(status_lines),
            "test_evidence": {
                "latest_event_type": latest_test.get("event_type") if latest_test else None,
                "timestamp": tested_at,
                "passed": test_passed,
            },
            "status": "checkpoint_with_passing_test_evidence" if test_passed else "checkpoint_needs_test_verification",
        }
        self.history_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.events_path), os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            os.write(fd, (json.dumps(checkpoint, sort_keys=True) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
        self._write_json(self.state_path, {"last_head": head, "updated_at": checkpoint["timestamp"]})
        self.audit.log_event(
            "MILESTONE_CHECKPOINT_DETECTED", agent="MILESTONE_DETECTOR",
            action=checkpoint["status"],
            details={
                "event_id": checkpoint["event_id"], "project_id": checkpoint["project_id"],
                "changed_file_count": checkpoint["changed_file_count"],
                "uncommitted_tracked_file_count": checkpoint["uncommitted_tracked_file_count"],
                "test_evidence_present": bool(latest_test),
                "test_passed": test_passed,
            },
        )
        return checkpoint

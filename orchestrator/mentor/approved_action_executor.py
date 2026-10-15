"""Explicitly approved, allowlisted local action executor.

Only fixed read-only inspection and test commands are supported. Arbitrary shell
commands, generated scripts, publishing, outreach, and file edits are not allowed.
Execution is disabled unless ASCM_ENABLE_APPROVED_EXECUTION=1 is set.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.security.audit_logger import AuditLogger
from orchestrator.mentor.approval_security import verify_approval

ALLOWED_ACTIONS = {"inspect_git_status", "run_pytest"}


class ApprovedActionExecutor:
    def __init__(self, workspace_path: str | Path, audit_logger: AuditLogger | None = None):
        self.workspace = Path(workspace_path).expanduser().resolve()
        self.history_dir = self.workspace / ".ascm_history"
        self.proposals_path = self.history_dir / "action_proposals.json"
        self.audit = audit_logger or AuditLogger(log_dir=str(self.history_dir / "audit"))

    def execute(self, proposal_id: str, *, actor: str = "founder") -> dict[str, Any]:
        if os.environ.get("ASCM_ENABLE_APPROVED_EXECUTION", "").lower() not in {"1", "true", "yes"}:
            raise PermissionError("Approved execution is disabled; set ASCM_ENABLE_APPROVED_EXECUTION=1 after reviewing the workspace")
        try:
            proposals = json.loads(self.proposals_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("No readable proposal ledger exists") from exc
        if not isinstance(proposals, list):
            raise ValueError("Proposal ledger is invalid")
        proposal = next((item for item in proposals if item.get("proposal_id") == proposal_id), None)
        if proposal is None:
            raise KeyError("Unknown proposal ID")
        if proposal.get("status") != "approved":
            raise PermissionError("Proposal must be explicitly approved before execution")
        if not verify_approval(self.workspace, proposal):
            raise PermissionError("Approval is missing, stale, or not bound to this exact proposal; review and approve it again")
        if proposal.get("execution_status") not in (None, "not_started"):
            raise ValueError("Proposal has already been executed or attempted")
        action = proposal.get("action_type")
        if action not in ALLOWED_ACTIONS:
            raise PermissionError("This action type is not in the safe execution allowlist")

        if action == "inspect_git_status":
            command = ["git", "-C", str(self.workspace), "status", "--short", "--branch"]
        else:
            if not (self.workspace / "tests").is_dir():
                raise ValueError("No tests/ directory exists in the configured workspace")
            command = [os.sys.executable, "-m", "pytest", "-q", "tests/"]

        started = datetime.now(timezone.utc).isoformat()
        proposal["execution_status"] = "running"
        proposal["execution_started_at"] = started
        proposal["execution_actor"] = actor[:100]
        self._save(proposals)
        self.audit.log_event("APPROVED_ACTION_STARTED", agent="APPROVED_ACTION_EXECUTOR",
                             action=action, details={"proposal_id": proposal_id, "actor": actor[:100]})
        try:
            result = subprocess.run(
                command, cwd=str(self.workspace), capture_output=True, text=True,
                timeout=300, check=False, shell=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            outcome = {
                "return_code": result.returncode,
                "passed": result.returncode == 0,
                # Output may contain secrets; don't persist raw output in audit or proposal history.
                "output_excerpt": (result.stdout + "\n" + result.stderr)[-1000:],
            }
            proposal["execution_status"] = "succeeded" if result.returncode == 0 else "failed"
            proposal["execution_return_code"] = result.returncode
            proposal["execution_finished_at"] = datetime.now(timezone.utc).isoformat()
            self._save(proposals)
            self.audit.log_event("APPROVED_ACTION_FINISHED", agent="APPROVED_ACTION_EXECUTOR",
                                 action=action, details={"proposal_id": proposal_id,
                                 "return_code": result.returncode, "passed": result.returncode == 0})
            return outcome
        except subprocess.TimeoutExpired:
            proposal["execution_status"] = "timed_out"
            proposal["execution_finished_at"] = datetime.now(timezone.utc).isoformat()
            self._save(proposals)
            self.audit.log_event("APPROVED_ACTION_TIMED_OUT", agent="APPROVED_ACTION_EXECUTOR",
                                 action=action, details={"proposal_id": proposal_id, "timeout_seconds": 300},
                                 level="WARN")
            raise TimeoutError("Approved action exceeded the 300-second timeout") from None

    def _save(self, proposals: list[dict[str, Any]]) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        temp = self.proposals_path.with_suffix(".tmp")
        temp.write_text(json.dumps(proposals, indent=2, sort_keys=True), encoding="utf-8")
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(self.proposals_path)
        try:
            self.proposals_path.chmod(0o600)
        except OSError:
            pass

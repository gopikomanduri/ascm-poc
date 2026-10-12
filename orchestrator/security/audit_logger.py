import datetime
import json
import logging
import os
import stat
import threading
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from orchestrator.security.pii_scrubber import PIIScrubber


class AuditLogger:
    """
    Structured local audit logger with PII/credential scrubbing and bounded storage.
    It supports audit evidence collection but does not by itself guarantee SOC 2
    or ISO 27001 compliance. Callers should log decisions and outcomes without
    placing secrets, source contents, or raw customer communications in details.
    Produces both human-readable text logs (.log) and structured NDJSON (.jsonl)
    ready for open-source and commercial log aggregators (ELK, Datadog, Loki, Splunk).
    """

    def __init__(self, log_dir: Optional[str] = None, run_id: Optional[str] = None):
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        base_dir = log_dir or os.environ.get("ASCM_LOG_DIR") or "logs"
        self.log_path = Path(base_dir).resolve()
        self.log_path.mkdir(parents=True, exist_ok=True)
        self._jsonl_lock = threading.Lock()
        try:
            self.log_path.chmod(0o700)
        except OSError:
            pass

        self.text_log_file = self.log_path / "ascm_audit.log"
        self.jsonl_log_file = self.log_path / "ascm_audit.jsonl"

        # Setup standard Python rotating logger for human inspection
        self.logger = logging.getLogger(f"ascm_audit_{self.run_id}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            formatter = logging.Formatter(
                fmt="[%(asctime)s] [%(levelname)s] [run=%(run_id)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
            # Text file handler (10MB max, keeping 5 backups)
            file_handler = RotatingFileHandler(
                str(self.text_log_file),
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            try:
                self.text_log_file.chmod(0o600)
            except OSError:
                pass

    def _rotate_jsonl(self) -> None:
        """Bound local audit storage to six 10-MB files."""
        if not self.jsonl_log_file.exists() or self.jsonl_log_file.stat().st_size < 10 * 1024 * 1024:
            return
        oldest = self.jsonl_log_file.with_suffix(".jsonl.5")
        try:
            if oldest.exists():
                oldest.unlink()
            for index in range(4, 0, -1):
                src = self.jsonl_log_file.with_suffix(f".jsonl.{index}")
                if src.exists():
                    src.replace(self.jsonl_log_file.with_suffix(f".jsonl.{index + 1}"))
            self.jsonl_log_file.replace(self.jsonl_log_file.with_suffix(".jsonl.1"))
        except OSError as err:
            self.logger.error(f"Failed rotating JSONL audit log: {type(err).__name__}")

    def _write_jsonl(self, record: Dict[str, Any]) -> None:
        """Appends a sanitized, structured JSON record to the bounded JSONL audit log."""
        try:
            line = json.dumps(record, ensure_ascii=False) + "\n"
            with self._jsonl_lock:
                self._rotate_jsonl()
                fd = os.open(str(self.jsonl_log_file), os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
                try:
                    os.write(fd, line.encode("utf-8"))
                finally:
                    os.close(fd)
                try:
                    self.jsonl_log_file.chmod(0o600)
                except OSError:
                    pass
        except Exception as err:
            # Audit failures are surfaced in logs; do not break unrelated product flows.
            self.logger.error(f"Failed writing JSONL audit log: {type(err).__name__}")

    def log_event(
        self,
        event_type: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Any] = None,
        level: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Core audit logging method. Automatically redacts all PII and credentials.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Sanitize details
        raw_details = details
        if isinstance(raw_details, (dict, list)):
            details_str = json.dumps(raw_details)
            scrubbed_str = PIIScrubber.scrub(details_str)
            try:
                scrubbed_details = json.loads(scrubbed_str)
            except Exception:
                scrubbed_details = scrubbed_str
        elif raw_details is not None:
            scrubbed_details = PIIScrubber.scrub(str(raw_details))
        else:
            scrubbed_details = None

        record = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "event_type": event_type,
            "level": level.upper(),
            "agent": agent or "SYSTEM",
            "action": action or "",
            "details": scrubbed_details,
            "metadata": metadata or {},
        }

        # Check for PII detection in raw data to record security metrics
        if raw_details is not None:
            findings = PIIScrubber.audit_findings(str(raw_details))
            if findings:
                record["metadata"]["pii_redacted"] = findings

        # 1. Output to standard text log
        msg = f"[{event_type}] agent={record['agent']} action={record['action']} details={record['details']}"
        extra = {"run_id": self.run_id}
        if level.upper() == "ERROR":
            self.logger.error(msg, extra=extra)
        elif level.upper() == "WARN" or level.upper() == "WARNING":
            self.logger.warning(msg, extra=extra)
        else:
            self.logger.info(msg, extra=extra)

        # 2. Output to structured JSON Lines log
        self._write_jsonl(record)
        return record

    def log_phase(self, phase_name: str) -> None:
        self.log_event(
            event_type="PHASE_TRANSITION",
            agent="ORCHESTRATOR",
            action="PHASE_START",
            details={"phase": phase_name},
        )

    def log_step(self, agent: str, action: str, details: Any, status: str = "success") -> None:
        self.log_event(
            event_type="AGENT_STEP",
            agent=agent,
            action=action,
            details=details,
            metadata={"status": status},
        )

    def log_llm_interaction(
        self,
        agent: str,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        latency_ms: float,
        json_mode: bool = False,
    ) -> None:
        """
        Logs every LLM prompt and response with PII scrubbing and performance telemetry.
        """
        scrubbed_prompt = PIIScrubber.scrub(prompt)
        scrubbed_response = PIIScrubber.scrub(response)

        self.log_event(
            event_type="LLM_CALL",
            agent=agent,
            action="GENERATE_CONTENT",
            details={
                "provider": provider,
                "model": model,
                "json_mode": json_mode,
                "latency_ms": round(latency_ms, 2),
                "prompt_char_length": len(prompt),
                "response_char_length": len(response),
                "prompt_preview": scrubbed_prompt[:250] + ("..." if len(scrubbed_prompt) > 250 else ""),
                "response_preview": scrubbed_response[:250] + ("..." if len(scrubbed_response) > 250 else ""),
            },
            metadata={
                "provider": provider,
                "model": model,
                "latency_ms": round(latency_ms, 2),
            },
        )

    def log_security_event(self, event_type: str, details: Any, severity: str = "WARN") -> None:
        self.log_event(
            event_type=f"SECURITY_{event_type.upper()}",
            agent="SECURITY_ENGINE",
            action="SECURITY_CHECK",
            details=details,
            level=severity,
        )

    def log_verification(
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
    ) -> None:
        self.log_event(
            event_type="VERIFICATION",
            agent="VERIFIER_ENGINE",
            action="RUN_CHECKS",
            details={
                "repo": repo,
                "language": language,
                "framework": framework,
                "passed": passed,
                "total_tests": total_tests,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "sandboxed": sandboxed,
                "error_summary": None if passed else PIIScrubber.scrub(f"{test_output}\n{vet_output}".strip()),
            },
            level="INFO" if passed else "WARN",
        )

    def log_governance(
        self,
        milestone: str,
        decision: str,
        feedback: Optional[str] = None,
        auto_approved: bool = False,
    ) -> None:
        self.log_event(
            event_type="GOVERNANCE_DECISION",
            agent="HUMAN_IN_THE_LOOP",
            action="MILESTONE_REVIEW",
            details={
                "milestone": milestone,
                "decision": decision,
                "feedback": PIIScrubber.scrub(feedback) if feedback else None,
                "auto_approved": auto_approved,
            },
        )

    def log_git_commit(
        self,
        repo: str,
        branch: str,
        goal: str,
        files: list[str],
        pr_path: Optional[str] = None,
    ) -> None:
        self.log_event(
            event_type="GIT_COMMIT",
            agent="GIT_SERVICE",
            action="COMMIT_AND_BRANCH",
            details={
                "repo": repo,
                "branch": branch,
                "goal": goal,
                "files": files,
                "pr_artifact": pr_path,
            },
        )


# Global singleton instance
AUDIT_LOGGER = AuditLogger()

"""Small, testable governance coordinator for ASCM A2A handoffs.

This first slice coordinates local handlers. Production deployment still needs a
durable store and authenticated caller identity; in-memory state is process-local.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

from orchestrator.a2a.contracts import HandoffEnvelope, HandoffStatus

logger = logging.getLogger("ASCM.A2A.Coordinator")
Handler = Callable[[HandoffEnvelope], Mapping[str, Any]]


class HandoffError(RuntimeError):
    """Raised when a governed handoff cannot safely complete."""


class A2ACoordinator:
    def __init__(self, *, handlers: Mapping[str, Handler], max_attempts: int = 2,
                 audit_sink: Callable[[dict[str, Any]], None] | None = None):
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5.")
        self.handlers = dict(handlers)
        self.max_attempts = max_attempts
        self.audit_sink = audit_sink or (lambda event: logger.info("a2a_audit %s", json.dumps(event, sort_keys=True)))
        self._results: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _fingerprint(envelope: HandoffEnvelope) -> str:
        payload = {
            "sender": envelope.sender,
            "recipient": envelope.recipient,
            "goal": envelope.goal,
            "expected_output": envelope.expected_output,
            "evidence": [e.__dict__ for e in envelope.evidence],
            "proposed_action": envelope.proposed_action,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _audit(self, envelope: HandoffEnvelope, event: str, **details: Any) -> None:
        record = {
            "contract_version": envelope.contract_version,
            "task_id": envelope.task_id,
            "correlation_id": envelope.correlation_id,
            "sender": envelope.sender,
            "recipient": envelope.recipient,
            "event": event,
            "status": envelope.status.value,
            "timestamp": envelope.updated_at,
            **details,
        }
        self.audit_sink(record)

    def dispatch(self, envelope: HandoffEnvelope, *, timeout_seconds: float = 30.0) -> dict[str, Any]:
        if timeout_seconds <= 0 or timeout_seconds > 600:
            raise ValueError("timeout_seconds must be in the range (0, 600].")
        if envelope.recipient not in self.handlers:
            envelope.transition(HandoffStatus.REJECTED, error_code="unknown_recipient")
            self._audit(envelope, "rejected", reason="unknown_recipient")
            raise HandoffError(f"No handler registered for recipient '{envelope.recipient}'.")
        fingerprint = self._fingerprint(envelope)
        prior = self._results.get(envelope.task_id)
        if prior is not None:
            if prior["fingerprint"] != fingerprint:
                self._audit(envelope, "duplicate_conflict")
                raise HandoffError("task_id was reused with a different payload.")
            self._audit(envelope, "idempotent_replay")
            return dict(prior["result"])

        # Recommendations and routing do not grant permission to perform side effects.
        if envelope.proposed_action and not envelope.approval_scope.authorizes(envelope.proposed_action):
            envelope.transition(HandoffStatus.REJECTED, error_code="approval_required",
                                follow_up="Obtain explicit, action-scoped founder approval before execution.")
            self._audit(envelope, "approval_gate_rejected", proposed_action=envelope.proposed_action)
            raise HandoffError("Proposed action lacks a valid scoped approval.")

        envelope.transition(HandoffStatus.ACCEPTED)
        self._audit(envelope, "accepted")
        envelope.transition(HandoffStatus.RUNNING)
        self._audit(envelope, "started", timeout_seconds=timeout_seconds)
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        handler = self.handlers[envelope.recipient]
        for attempt in range(1, self.max_attempts + 1):
            if time.monotonic() >= deadline:
                envelope.transition(HandoffStatus.TIMED_OUT, error_code="deadline_exceeded")
                self._audit(envelope, "timed_out", attempt=attempt)
                raise HandoffError("A2A handoff deadline exceeded.")
            try:
                result = handler(envelope)
                if not isinstance(result, Mapping):
                    raise TypeError("A2A handler must return a mapping.")
                if time.monotonic() >= deadline:
                    envelope.transition(HandoffStatus.TIMED_OUT, error_code="deadline_exceeded")
                    self._audit(envelope, "timed_out", attempt=attempt, handler_returned_after_deadline=True)
                    raise HandoffError("A2A handoff deadline exceeded after handler returned.")
                normalized = dict(result)
                if "conflicting_recommendations" in normalized and normalized["conflicting_recommendations"]:
                    envelope.transition(HandoffStatus.NEEDS_HUMAN_REVIEW, result=normalized,
                                        follow_up="Resolve conflicting recommendations before proceeding.")
                    self._audit(envelope, "conflict_escalated", attempt=attempt)
                    return envelope.to_dict()
                envelope.transition(HandoffStatus.SUCCEEDED, result=normalized)
                self._results[envelope.task_id] = {"fingerprint": fingerprint, "result": normalized}
                self._audit(envelope, "succeeded", attempt=attempt)
                return normalized
            except Exception as exc:
                last_error = exc
                if envelope.status is HandoffStatus.TIMED_OUT:
                    raise HandoffError("A2A handoff deadline exceeded.") from exc
                if time.monotonic() >= deadline:
                    envelope.transition(HandoffStatus.TIMED_OUT, error_code="deadline_exceeded")
                    self._audit(envelope, "timed_out", attempt=attempt, error_type=type(exc).__name__)
                    raise HandoffError("A2A handoff deadline exceeded.") from exc
                self._audit(envelope, "attempt_failed", attempt=attempt, error_type=type(exc).__name__)
                if attempt < self.max_attempts:
                    continue
        envelope.transition(HandoffStatus.FAILED, error_code=type(last_error).__name__ if last_error else "handler_failed")
        self._audit(envelope, "failed", attempts=self.max_attempts, error_code=envelope.error_code)
        raise HandoffError(f"A2A handoff failed after {self.max_attempts} attempt(s).") from last_error

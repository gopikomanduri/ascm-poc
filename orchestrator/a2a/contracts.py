"""Versioned ASCM governance envelope carried alongside standard A2A messages.

The envelope is an ASCM extension contract, not a replacement for A2A. It describes
intent and governance metadata; it never grants execution permission by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


CONTRACT_VERSION = "1.0"


class HandoffStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


@dataclass(frozen=True)
class Evidence:
    source: str
    description: str
    observed_at: str
    confidence: float
    reference: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.description.strip():
            raise ValueError("Evidence source and description are required.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Evidence confidence must be between 0 and 1.")


@dataclass(frozen=True)
class ApprovalScope:
    required: bool = True
    actions: tuple[str, ...] = ()
    approved_by: str | None = None
    approved_at: str | None = None
    approval_id: str | None = None

    @property
    def authorized(self) -> bool:
        # An approval is scoped and attributable. A boolean alone is not consent.
        return bool(
            self.required is False
            or (
                self.approved_by
                and self.approved_at
                and self.approval_id
                and self.actions
            )
        )


@dataclass
class HandoffEnvelope:
    goal: str
    sender: str
    recipient: str
    expected_output: str
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = field(default_factory=lambda: str(uuid4()))
    contract_version: str = CONTRACT_VERSION
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 0.0
    proposed_action: str | None = None
    approval_scope: ApprovalScope = field(default_factory=ApprovalScope)
    status: HandoffStatus = HandoffStatus.PROPOSED
    result: dict[str, Any] | None = None
    error_code: str | None = None
    follow_up: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        for name in ("goal", "sender", "recipient", "expected_output"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(f"Unsupported ASCM handoff contract version: {self.contract_version}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Handoff confidence must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    def transition(self, status: HandoffStatus, *, result: dict[str, Any] | None = None,
                   error_code: str | None = None, follow_up: str | None = None) -> None:
        allowed = {
            HandoffStatus.PROPOSED: {HandoffStatus.ACCEPTED, HandoffStatus.REJECTED, HandoffStatus.NEEDS_HUMAN_REVIEW},
            HandoffStatus.ACCEPTED: {HandoffStatus.RUNNING, HandoffStatus.REJECTED},
            HandoffStatus.RUNNING: {HandoffStatus.SUCCEEDED, HandoffStatus.FAILED, HandoffStatus.TIMED_OUT, HandoffStatus.NEEDS_HUMAN_REVIEW},
            HandoffStatus.NEEDS_HUMAN_REVIEW: {HandoffStatus.ACCEPTED, HandoffStatus.REJECTED},
        }
        if status not in allowed.get(self.status, set()):
            raise ValueError(f"Invalid handoff transition: {self.status.value} -> {status.value}")
        self.status = status
        self.result = result
        self.error_code = error_code
        self.follow_up = follow_up
        self.updated_at = datetime.now(timezone.utc).isoformat()

"""Human-controlled state transitions for Mentor-proposed founder actions.

Proposals are inert until a human approves them. This module never executes an
action; it appends an auditable decision event to .ascm_history/founder_action_events.jsonl.
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL in {path} at line {line_number}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Expected a JSON object in {path} at line {line_number}")
        records.append(item)
    return records

def action_states(workspace: str | Path) -> dict[str, dict[str, Any]]:
    history = Path(workspace).resolve() / ".ascm_history"
    proposals = _read_jsonl(history / "founder_actions.jsonl")
    events = _read_jsonl(history / "founder_action_events.jsonl")
    states: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        action_id = proposal.get("action_id")
        if isinstance(action_id, str) and action_id:
            states[action_id] = {**proposal, "current_status": "proposed"}
    for event in events:
        action_id = event.get("action_id")
        if action_id in states:
            status = event.get("new_status", states[action_id]["current_status"])
            states[action_id]["current_status"] = status
            states[action_id]["approved"] = status in {"approved", "in_progress", "completed"}
            states[action_id]["executed"] = status == "completed"
            states[action_id]["outcome_status"] = "evidence_attached" if status == "completed" else "awaiting_evidence"
            if status == "completed" and event.get("evidence_ref"):
                states[action_id]["completion_evidence_ref"] = event["evidence_ref"]
            states[action_id]["last_event"] = event
    return states

def transition_action(
    workspace: str | Path, action_id: str, decision: str, actor: str,
    *, evidence_ref: str | None = None,
) -> dict[str, Any]:
    if decision not in {"approve", "reject", "start", "complete"}:
        raise ValueError("decision must be approve, reject, start, or complete")
    if not action_id.strip() or not actor.strip():
        raise ValueError("action_id and actor are required")
    states = action_states(workspace)
    if action_id not in states:
        raise ValueError(f"Unknown founder action: {action_id}")
    current = states[action_id]["current_status"]
    transitions = {
        ("proposed", "approve"): "approved",
        ("proposed", "reject"): "rejected",
        ("approved", "start"): "in_progress",
        ("in_progress", "complete"): "completed",
    }
    target = transitions.get((current, decision))
    if target is None:
        raise ValueError(f"Invalid founder-action transition: {current} -> {decision}")
    if decision == "complete" and not (isinstance(evidence_ref, str) and evidence_ref.strip()):
        raise ValueError("Completing an action requires an evidence_ref.")
    event = {
        "event_id": "founder-action-event-" + str(uuid.uuid4()),
        "action_id": action_id,
        "decision": decision,
        "actor": actor.strip(),
        "previous_status": current,
        "new_status": target,
        "evidence_ref": evidence_ref.strip() if isinstance(evidence_ref, str) and evidence_ref.strip() else None,
        "approval_id": "founder-action-approval-" + str(uuid.uuid4()) if decision == "approve" else None,
        "is_external_action": False,
        "executed_by_this_module": False,
        "created_at": _now(),
    }
    history = Path(workspace).resolve() / ".ascm_history"
    history.mkdir(parents=True, exist_ok=True)
    path = history / "founder_action_events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    try:
        path.chmod(0o600)
        history.chmod(0o700)
    except OSError:
        pass
    return event

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Approve/reject/track a proposed ASCM founder action. This never executes it.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--decision", required=True, choices=("approve", "reject", "start", "complete"))
    parser.add_argument("--actor", required=True, help="Human reviewer/owner making this state transition.")
    parser.add_argument("--evidence-ref", help="Required when decision=complete.")
    args = parser.parse_args(argv)
    try:
        event = transition_action(args.workspace, args.action_id, args.decision, args.actor, evidence_ref=args.evidence_ref)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(event, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

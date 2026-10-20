"""Append-only, human-verified customer outcome ledger for ASCM.

Only outcomes with a non-empty source evidence reference and an identified verifier
are written as verified. This records evidence; it does not contact customers.
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTCOME_TYPES = {
    "customer_reply", "customer_interview", "feature_request", "pilot_commitment",
    "waitlist_signup", "meeting_booked", "qualified_opportunity", "conversion",
}

def record_verified_outcome(
    workspace: str | Path, event_type: str, evidence_ref: str, verified_by: str,
    *, notes: str = "", cycle_id: str | None = None,
) -> dict[str, Any]:
    if event_type not in OUTCOME_TYPES:
        raise ValueError(f"Unsupported outcome type: {event_type}")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError("evidence_ref is required; do not use a generated asset ID as customer evidence.")
    if not isinstance(verified_by, str) or not verified_by.strip():
        raise ValueError("verified_by is required.")
    history = Path(workspace).resolve() / ".ascm_history"
    history.mkdir(parents=True, exist_ok=True)
    path = history / "gtm_outcomes.json"
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Outcome ledger is invalid JSON; refusing to overwrite it.") from exc
        if not isinstance(existing, list) or any(not isinstance(item, dict) for item in existing):
            raise ValueError("Outcome ledger must be a JSON array of objects; refusing to overwrite it.")
    else:
        existing = []
    record = {
        "event_id": "customer-outcome-" + str(uuid.uuid4()),
        "event_type": event_type,
        "evidence_ref": evidence_ref.strip(),
        "verification_status": "verified",
        "verified": True,
        "verified_by": verified_by.strip(),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source": "human_verified_outcome_ledger",
        "cycle_id": cycle_id.strip() if isinstance(cycle_id, str) and cycle_id.strip() else None,
        "notes": notes.strip(),
    }
    existing.append(record)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        temp.chmod(0o600)
        history.chmod(0o700)
    except OSError:
        pass
    temp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return record

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a human-verified customer outcome with source evidence.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--event-type", required=True, choices=sorted(OUTCOME_TYPES))
    parser.add_argument("--evidence-ref", required=True, help="CRM record, approved interview note, meeting record, or other source reference.")
    parser.add_argument("--verified-by", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--cycle-id", help="Optional GTM cycle ID for outcome attribution.")
    args = parser.parse_args(argv)
    try:
        record = record_verified_outcome(
            args.workspace, args.event_type, args.evidence_ref, args.verified_by,
            notes=args.notes, cycle_id=args.cycle_id,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""Workspace-local HMAC binding for founder-approved actions.

This protects against accidental/stale/cross-proposal approval reuse and casual
ledger edits. It is not an identity provider or a security boundary against an
attacker who already controls the founder's OS account.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any

KEY_NAME = "approval_signing.key"


def _key(workspace_path: str | Path, *, create: bool) -> bytes | None:
    history = Path(workspace_path).expanduser().resolve() / ".ascm_history"
    history.mkdir(parents=True, exist_ok=True)
    try:
        history.chmod(0o700)
    except OSError:
        pass
    path = history / KEY_NAME
    if not path.exists():
        if not create:
            return None
        key = secrets.token_bytes(32)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as handle:
                handle.write(key)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    try:
        value = path.read_bytes()
    except OSError:
        return None
    return value if len(value) >= 32 else None


def _approval_payload(proposal: dict[str, Any]) -> bytes:
    bound = {
        "proposal_id": proposal.get("proposal_id"),
        "action_type": proposal.get("action_type"),
        "status": proposal.get("status"),
        "decision_by": proposal.get("decision_by"),
        "decided_at": proposal.get("decided_at"),
    }
    return json.dumps(bound, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_approval(workspace_path: str | Path, proposal: dict[str, Any]) -> str:
    key = _key(workspace_path, create=True)
    if key is None:
        raise OSError("Could not load local approval signing key")
    return hmac.new(key, _approval_payload(proposal), hashlib.sha256).hexdigest()


def verify_approval(workspace_path: str | Path, proposal: dict[str, Any]) -> bool:
    signature = proposal.get("approval_signature")
    if not isinstance(signature, str) or len(signature) != 64:
        return False
    key = _key(workspace_path, create=False)
    if key is None:
        return False
    expected = hmac.new(key, _approval_payload(proposal), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)

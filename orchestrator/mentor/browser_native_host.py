"""Chrome Native Messaging host: records hostname-only browser events."""
from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

from orchestrator.mentor.activity_adapters import ActivityAdapters, normalize_domain
from orchestrator.security.audit_logger import AuditLogger


def _read_message():
    header = sys.stdin.buffer.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ValueError("Incomplete native-message header")
    length = struct.unpack("<I", header)[0]
    if length > 8192:
        raise ValueError("Native message too large")
    payload = sys.stdin.buffer.read(length)
    if len(payload) != length:
        raise ValueError("Incomplete native-message body")
    return json.loads(payload.decode("utf-8"))


def _write_message(value):
    payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(payload)))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def main():
    workspace = Path(os.environ.get("ASCM_WATCH_PATH", ".")).expanduser().resolve()
    adapter = ActivityAdapters(workspace)
    audit = AuditLogger(log_dir=str(workspace / ".ascm_history" / "audit"))
    while True:
        try:
            message = _read_message()
            if message is None:
                return 0
            if not isinstance(message, dict) or message.get("type") != "browser_domain":
                raise ValueError("Unsupported message type")
            # Deliberately accept only domain, ignore timestamp and all other browser data.
            domain = normalize_domain(str(message.get("domain", "")))
            event = adapter.browser_domain_event(cwd=workspace, url_or_domain=domain)
            audit.log_event("ACTIVITY_BROWSER_DOMAIN", agent="BROWSER_NATIVE_HOST",
                            action="RECORD_HOSTNAME", details={
                                "domain": domain, "project_id": event["project_id"],
                            })
            _write_message({"ok": True})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            audit.log_event("ACTIVITY_BROWSER_REJECTED", agent="BROWSER_NATIVE_HOST",
                            action="VALIDATE_MESSAGE",
                            details={"error_type": type(exc).__name__}, level="WARN")
            _write_message({"ok": False, "error": "invalid_event"})


if __name__ == "__main__":
    raise SystemExit(main())

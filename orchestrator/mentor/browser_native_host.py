"""Chrome Native Messaging host: records hostname-only browser events."""
from __future__ import annotations

import json
import os
import platform
import stat
import struct
import sys
from pathlib import Path
import argparse

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


def install_native_host(workspace: Path, extension_id: str) -> Path:
    if not extension_id or len(extension_id) > 128 or any(ch not in "abcdefghijklmnopqrstuvwxyz" for ch in extension_id):
        raise ValueError("extension-id must be the exact lowercase Chrome extension ID")
    system = platform.system().lower()
    if system == "darwin":
        manifest_dir = Path.home() / "Library/Application Support/Google/Chrome/NativeMessagingHosts"
    elif system == "linux":
        manifest_dir = Path.home() / ".config/google-chrome/NativeMessagingHosts"
    else:
        raise RuntimeError("Native host auto-registration currently supports macOS and Linux only")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    host_dir = Path.home() / ".local" / "bin"
    host_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]
    wrapper_path = host_dir / "ascm-browser-native-host"
    wrapper_path.write_text(
        "#!/bin/sh\\n"
        f"export ASCM_WATCH_PATH={json.dumps(str(workspace))}\\n"
        f"export PYTHONPATH={json.dumps(str(repo_root))}\\n"
        f"cd {json.dumps(str(repo_root))}\\n"
        f"exec {json.dumps(sys.executable)} -m orchestrator.mentor.browser_native_host\\n",
        encoding="utf-8",
    )
    wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    manifest = {
        "name": "com.ascm.activity",
        "description": "ASCM opt-in hostname-only activity recorder",
        "path": str(wrapper_path),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }
    manifest_path = manifest_dir / "com.ascm.activity.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description="ASCM browser native messaging host")
    parser.add_argument("--install", action="store_true", help="Register host for one Chrome extension ID")
    parser.add_argument("--extension-id", default="")
    parser.add_argument("--workspace", default=os.environ.get("ASCM_WATCH_PATH", "."))
    args, _ = parser.parse_known_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if args.install:
        manifest_path = install_native_host(workspace, args.extension_id)
        print(f"Installed native messaging host manifest at {manifest_path}")
        return 0

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

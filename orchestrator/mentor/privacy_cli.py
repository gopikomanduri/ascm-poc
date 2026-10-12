"""User-facing local privacy controls for ASCM activity history."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


def history_path(workspace: str | Path) -> Path:
    root = Path(workspace).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("Workspace must be an existing directory")
    return root / ".ascm_history"


def status(workspace: str | Path) -> dict:
    root = Path(workspace).expanduser().resolve()
    history = history_path(root)
    return {
        "workspace": str(root),
        "history_exists": history.exists(),
        "history_bytes": sum(
            item.stat().st_size for item in history.rglob("*")
            if item.is_file() and not item.is_symlink()
        ) if history.is_dir() and not history.is_symlink() else 0,
        "foreground_app_names_enabled": os.environ.get("ASCM_ACTIVE_WINDOW_MONITOR", "0").strip() == "1",
        "shell_hooks": "opt-in; inspect ~/.bashrc or ~/.zshrc",
        "browser_signals": "opt-in; disable/remove the ASCM browser extension",
        "note": "Stopping autostart and deleting history are separate actions. Local file deletion is not guaranteed secure erasure on SSDs or backups.",
    }


def delete_history(workspace: str | Path, *, confirmed: bool = False) -> dict:
    history = history_path(workspace)
    if not confirmed:
        raise ValueError("Refusing to delete history without --confirm")
    if history.is_symlink():
        raise ValueError("Refusing to follow a symlink for .ascm_history")
    if not history.exists():
        return {"deleted": False, "message": "No local ASCM history exists."}
    if not history.is_dir():
        raise ValueError(".ascm_history exists but is not a directory")
    shutil.rmtree(history)
    return {
        "deleted": True,
        "path": str(history),
        "message": "Local ASCM history removed. Stop the daemon first or it may recreate history files.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or delete local ASCM activity history")
    parser.add_argument("--workspace", default=os.environ.get("ASCM_WATCH_PATH", "."))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show local activity configuration and history size")
    purge = sub.add_parser("delete-history", help="Delete the local .ascm_history directory")
    purge.add_argument("--confirm", action="store_true", help="Confirm deletion of local ASCM history")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = status(args.workspace)
        else:
            result = delete_history(args.workspace, confirmed=args.confirm)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

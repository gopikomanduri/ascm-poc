"""Low-content activity adapters for the always-on ASCM mentor.

These adapters record event metadata only. They never persist raw shell commands,
browser URLs/paths, window titles, page contents, clipboard data, or keystrokes.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from orchestrator.mentor.context_fusion import ContextFusionEngine


def classify_command(command: str) -> str:
    """Map a command string to a safe category; never persist the command itself."""
    value = (command or "").strip().lower()
    if not value:
        return "unknown"
    rules = (
        (r"\b(pytest|unittest|tox|nox)\b", "python_tests"),
        (r"\b(npm|pnpm|yarn)\s+(test|run\s+test|vitest|jest)\b", "javascript_tests"),
        (r"\b(go\s+test)\b", "go_tests"),
        (r"\b(cargo\s+test)\b", "rust_tests"),
        (r"\b(bandit|pip-audit|semgrep|gitleaks|trivy)\b", "security_scan"),
        (r"\b(git\s+(commit|push|merge|rebase))\b", "git_workflow"),
        (r"\b(pip|uv|poetry|npm|pnpm|yarn|cargo)\s+(install|add|update)\b", "dependency_change"),
        (r"\b(python|python3|node|go|cargo|make)\b", "build_or_run"),
    )
    for pattern, category in rules:
        if re.search(pattern, value):
            return category
    return "other"


def normalize_domain(url_or_domain: str) -> str:
    """Return a hostname only; reject credentials, paths, query strings, and malformed values."""
    raw = (url_or_domain or "").strip()
    if not raw or len(raw) > 2048:
        raise ValueError("A non-empty URL/domain of at most 2048 characters is required")
    candidate = raw if "://" in raw else "https://" + raw
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only http/https URLs or hostnames are supported")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not accepted")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("Local hostnames are not recorded as browser activity")
    if len(host) > 253 or any(not part or len(part) > 63 for part in host.split(".")):
        raise ValueError("Invalid hostname")
    return host


class ActiveWindowAdapter:
    """Best-effort foreground application detector, without titles or window contents."""

    def __init__(self):
        self._last_app: Optional[str] = None

    @staticmethod
    def _run(args: list[str], timeout: float = 1.5) -> str:
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    def current_app(self) -> Optional[str]:
        system = platform.system().lower()
        app = ""
        if system == "darwin" and shutil.which("osascript"):
            app = self._run([
                "osascript", "-e",
                'tell application "System Events" to get name of first application process whose frontmost is true',
            ])
        elif system == "windows":
            script = (
                "Add-Type @'\n"
                "using System; using System.Runtime.InteropServices;\n"
                "public class ForegroundWindow { [DllImport(\"user32.dll\")] "
                "public static extern IntPtr GetForegroundWindow(); }\n"
                "'@; "
                "$h=[ForegroundWindow]::GetForegroundWindow(); "
                "$p=Get-Process | Where-Object { $_.MainWindowHandle -eq $h } | Select-Object -First 1 -ExpandProperty ProcessName; "
                "if ($p) { $p }"
            )
            app = self._run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
        elif system == "linux":
            if shutil.which("xdotool"):
                window = self._run(["xdotool", "getactivewindow"])
                if window:
                    pid = self._run(["xdotool", "getwindowpid", window])
                    if pid.isdigit():
                        app = self._run(["ps", "-p", pid, "-o", "comm="])
            elif shutil.which("hyprctl"):
                # Hyprland exposes the active client class; deliberately ignore title.
                raw = self._run(["hyprctl", "-j", "activewindow"])
                try:
                    import json
                    app = str(json.loads(raw).get("class", ""))
                except (ValueError, TypeError):
                    app = ""
        app = re.sub(r"[^A-Za-z0-9_.+-]", "", app.strip())[:100]
        return app or None

    def poll(self) -> Optional[str]:
        app = self.current_app()
        if app and app != self._last_app:
            self._last_app = app
            return app
        return None


class ActivityAdapters:
    """Small event adapter facade used by CLI hooks, browser opt-in, and daemon."""

    def __init__(self, workspace_path: str | Path = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.fusion = ContextFusionEngine(self.workspace_path)

    def terminal_event(self, *, cwd: str | Path, command_category: str, exit_code: Optional[int] = None) -> dict:
        if command_category not in {
            "unknown", "python_tests", "javascript_tests", "go_tests", "rust_tests",
            "security_scan", "git_workflow", "dependency_change", "build_or_run", "other",
        }:
            raise ValueError("Unsupported command category")
        return self.fusion.record_terminal_event(
            cwd=cwd, command_category=command_category, exit_code=exit_code
        )

    def browser_domain_event(self, *, cwd: str | Path, url_or_domain: str) -> dict:
        domain = normalize_domain(url_or_domain)
        return self.fusion.record_browser_domain(cwd=cwd, domain=domain)

    def active_app_event(self, *, app_name: str, cwd: str | Path | None = None) -> dict:
        safe_name = re.sub(r"[^A-Za-z0-9_.+-]", "", app_name.strip())[:100]
        if not safe_name:
            raise ValueError("app_name is required")
        return self.fusion.record_active_app(cwd=cwd or self.workspace_path, app_name=safe_name)

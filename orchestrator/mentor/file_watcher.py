#!/usr/bin/env python3
"""
ASCM Universal File System Watcher
Cross-platform activity monitor that tracks code changes BEYOND git commits.

Why this matters:
  - Git polling only sees commits, not in-progress edits.
  - Developers using Cursor, Replit, Jupyter, or Excel never commit mid-session.
  - This watcher detects ANY file modification in the repo directory in real-time.

Strategy (best available per OS):
  1. macOS  → watchdog + FSEventObserver (native kqueue/FSEvents API)
  2. Linux  → watchdog + InotifyObserver (inotify kernel events)
  3. Windows → watchdog + WindowsApiObserver (ReadDirectoryChangesW)
  4. Fallback → Manual polling every 10s (no watchdog required)

Install watchdog for best performance:
  pip install watchdog>=4.0.0

Usage:
  watcher = UniversalFileWatcher(repo_path=".", on_change=my_callback)
  watcher.start()   # non-blocking
  watcher.stop()
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Callable, Optional, Set, List
from datetime import datetime, timezone

logger = logging.getLogger("ASCMFileWatcher")

# File extensions considered "code" (not config noise)
CODE_EXTENSIONS: Set[str] = {
    ".py", ".go", ".ts", ".js", ".tsx", ".jsx",
    ".rs", ".java", ".kt", ".swift", ".cpp", ".c", ".h",
    ".rb", ".php", ".cs", ".scala", ".ex", ".exs",
    ".ipynb", ".r", ".m", ".sql",
}

# Directories to ignore
IGNORE_DIRS: Set[str] = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".ascm_history", ".ascm_domains",
}


def _is_code_file(path: str) -> bool:
    p = Path(path)
    return (
        p.suffix.lower() in CODE_EXTENSIONS
        and not any(part in IGNORE_DIRS for part in p.parts)
    )


# ─── Watchdog-based Observer ────────────────────────────────────────────────────

def _try_watchdog_observer(repo_path: str, on_code_change: Callable[[str], None]):
    """
    Returns a started watchdog Observer if watchdog is available.
    Returns None if watchdog is not installed.
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

        class _CodeChangeHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory and _is_code_file(event.src_path):
                    on_code_change(event.src_path)

            def on_created(self, event):
                if not event.is_directory and _is_code_file(event.src_path):
                    on_code_change(event.src_path)

        observer = Observer()
        observer.schedule(_CodeChangeHandler(), repo_path, recursive=True)
        observer.start()
        logger.info(f"[FileWatcher] watchdog Observer started on {repo_path} (native OS events)")
        return observer

    except ImportError:
        logger.info("[FileWatcher] watchdog not installed. Falling back to polling. "
                    "For native events: pip install watchdog>=4.0.0")
        return None


# ─── Polling-based Fallback ─────────────────────────────────────────────────────

class _PollingWatcher(threading.Thread):
    """
    Fallback watcher: scans the repo directory every `interval_sec` seconds
    and fires on_code_change for any file whose mtime has increased.
    No external dependencies required.
    """

    def __init__(self, repo_path: str, on_code_change: Callable[[str], None], interval_sec: int = 10):
        super().__init__(daemon=True, name="ASCMPollingWatcher")
        self.repo_path = Path(repo_path)
        self.on_code_change = on_code_change
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._known_mtimes: dict = {}

    def run(self):
        logger.info(f"[FileWatcher] Polling watcher active on {self.repo_path} (interval: {self.interval_sec}s)")
        while not self._stop_event.is_set():
            try:
                self._scan()
            except Exception as e:
                logger.debug(f"[FileWatcher] Polling scan error: {e}")
            self._stop_event.wait(self.interval_sec)

    def stop(self):
        self._stop_event.set()

    def _scan(self):
        for path in self.repo_path.rglob("*"):
            if path.is_file() and _is_code_file(str(path)):
                try:
                    mtime = path.stat().st_mtime
                    prev = self._known_mtimes.get(str(path), 0)
                    if mtime > prev:
                        self._known_mtimes[str(path)] = mtime
                        if prev > 0:  # Only fire on changes, not initial scan
                            self.on_code_change(str(path))
                except OSError:
                    pass


# ─── Unified Watcher Interface ──────────────────────────────────────────────────

class UniversalFileWatcher:
    """
    Cross-platform code activity watcher.
    Uses watchdog (native OS events) when available; falls back to polling.

    on_change: Callable[[filepath: str], None]
        Called whenever a code file is modified or created.
    """

    def __init__(
        self,
        repo_path: str = ".",
        on_change: Optional[Callable[[str], None]] = None,
        polling_interval_sec: int = 10,
    ):
        self.repo_path = str(Path(repo_path).resolve())
        self.on_change = on_change or self._default_on_change
        self.polling_interval_sec = polling_interval_sec
        self._watchdog_observer = None
        self._polling_watcher: Optional[_PollingWatcher] = None
        self._last_activity: Optional[datetime] = None
        self._recent_files: List[str] = []

    def _default_on_change(self, filepath: str):
        self._last_activity = datetime.now(timezone.utc)
        self._recent_files.append(filepath)
        if len(self._recent_files) > 50:
            self._recent_files = self._recent_files[-50:]
        logger.debug(f"[FileWatcher] Changed: {filepath}")

    def start(self):
        """Start monitoring. Non-blocking."""
        self._watchdog_observer = _try_watchdog_observer(self.repo_path, self.on_change)
        if self._watchdog_observer is None:
            self._polling_watcher = _PollingWatcher(
                self.repo_path, self.on_change, self.polling_interval_sec
            )
            self._polling_watcher.start()

    def stop(self):
        """Stop monitoring cleanly."""
        if self._watchdog_observer:
            self._watchdog_observer.stop()
            self._watchdog_observer.join(timeout=3)
        if self._polling_watcher:
            self._polling_watcher.stop()

    def seconds_since_last_code_edit(self) -> Optional[float]:
        """
        Returns seconds since the last detected code file modification.
        Returns None if no activity has been recorded yet.
        """
        if not self._last_activity:
            return None
        delta = datetime.now(timezone.utc) - self._last_activity
        return delta.total_seconds()

    def recently_edited_files(self, last_n: int = 10) -> List[str]:
        """Return the last N changed file paths."""
        return list(self._recent_files[-last_n:])

    @property
    def is_active(self) -> bool:
        return (
            (self._watchdog_observer is not None and self._watchdog_observer.is_alive())
            or (self._polling_watcher is not None and self._polling_watcher.is_alive())
        )


# ─── Integration with ProactiveGitMonitor ──────────────────────────────────────

class ActivityAwareMonitor:
    """
    Combines UniversalFileWatcher (filesystem) + ProactiveGitMonitor (git)
    for a complete picture of developer activity regardless of IDE.

    Use this instead of ProactiveGitMonitor alone when you want to catch
    in-progress edits from Cursor, Replit, Jupyter, Excel, etc.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.file_watcher = UniversalFileWatcher(repo_path=repo_path)

    def start(self):
        self.file_watcher.start()
        logger.info(f"[ActivityAwareMonitor] Watching {self.repo_path} for code changes across all tools.")

    def stop(self):
        self.file_watcher.stop()

    def get_activity_summary(self) -> dict:
        """
        Returns a combined activity summary with both filesystem and git signals.
        """
        from orchestrator.gtm.strategy.proactive_monitor import ProactiveGitMonitor
        git_monitor = ProactiveGitMonitor(repo_path=self.repo_path)
        git_metrics = git_monitor.measure_gtm_activity()

        secs = self.file_watcher.seconds_since_last_code_edit()
        recent = self.file_watcher.recently_edited_files(5)

        return {
            "filesystem_activity": {
                "seconds_since_last_edit": secs,
                "minutes_since_last_edit": round(secs / 60, 1) if secs is not None else None,
                "recently_edited_files": recent,
                "watcher_active": self.file_watcher.is_active,
                "watcher_mode": "watchdog" if self.file_watcher._watchdog_observer else "polling",
            },
            "git_activity": {
                "commits_7d": git_metrics.total_commits_7d,
                "commits_today": git_metrics.commits_today,
                "days_since_gtm": git_metrics.days_since_last_gtm_action,
                "risk_level": git_metrics.risk_level,
                "is_code_avoidance": git_metrics.is_code_avoidance,
            },
            "combined_signal": {
                # True if dev is actively coding right now (any IDE)
                "actively_coding_now": secs is not None and secs < 300,
                # True if editing but not committing (refactor in progress)
                "editing_without_committing": (
                    secs is not None and secs < 3600
                    and git_metrics.commits_today == 0
                ),
            },
        }


# ─── CLI test entrypoint ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ASCM Universal File System Watcher")
    parser.add_argument("--repo", default=".", help="Repository path to watch")
    parser.add_argument("--interval", type=int, default=5, help="Polling fallback interval (seconds)")
    args = parser.parse_args()

    print(f"[+] Watching {Path(args.repo).resolve()} for code changes (Ctrl+C to stop)...")

    monitor = ActivityAwareMonitor(repo_path=args.repo)
    monitor.start()

    try:
        while True:
            time.sleep(15)
            summary = monitor.get_activity_summary()
            fs = summary["filesystem_activity"]
            git = summary["git_activity"]
            combined = summary["combined_signal"]
            print(f"\n📊 Activity Report @ {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Watcher mode  : {fs['watcher_mode']}")
            print(f"   Last edit     : {fs['minutes_since_last_edit']} min ago" if fs['minutes_since_last_edit'] else "   Last edit     : (none recorded yet)")
            print(f"   Recent files  : {fs['recently_edited_files']}")
            print(f"   Git commits/7d: {git['commits_7d']} | Today: {git['commits_today']}")
            print(f"   GTM risk      : {git['risk_level']} (days since GTM: {git['days_since_gtm']:.0f})")
            print(f"   Actively coding now: {combined['actively_coding_now']}")
            print(f"   Editing w/o commit: {combined['editing_without_committing']}")
    except KeyboardInterrupt:
        monitor.stop()
        print("\n[+] Watcher stopped.")

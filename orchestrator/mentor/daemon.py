#!/usr/bin/env python3
"""
ASCM Universal Background Daemon & System Monitor
Cross-platform daemon engine for:
- macOS (launchd agent plist)
- Linux (systemd user unit)
- Windows (Scheduled Task / Startup Shortcut)
- Standalone Universal Background Daemon (nohup / python process)

Continuously watches the repository, tracks code milestones,
and prompts the user with proactive advice across all OSs.
"""

import os
import sys
import time
import json
import subprocess
import logging
from pathlib import Path

from orchestrator.mentor.notifier import CrossPlatformNotifier
from orchestrator.mentor.proactive_mentor import ASCMProactiveMentor

logger = logging.getLogger("ASCMDaemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class UniversalASCMDaemon:
    """Universal cross-platform daemon for ASCM Proactive Mentor."""

    def __init__(self, repo_path: str = ".", poll_interval_sec: int = 30):
        self.repo_path = Path(repo_path).resolve()
        self.poll_interval_sec = poll_interval_sec
        self.mentor = ASCMProactiveMentor(repo_path=str(self.repo_path))
        self.history_dir = self.repo_path / ".ascm_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.history_dir / "ascm_daemon.pid"

    def run_daemon_loop(self):
        """Infinite monitoring loop running quietly in the background."""
        logger.info(f"Starting ASCM Proactive Daemon for {self.repo_path} (Poll interval: {self.poll_interval_sec}s)")
        CrossPlatformNotifier.notify(
            "ASCM Proactive Mentor",
            f"Active and monitoring {self.repo_path.name} in background across your OS.",
            app_name="ASCM Mentor"
        )

        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        last_gtm_prompt_time = 0

        try:
            while True:
                time.sleep(self.poll_interval_sec)

                # Check repo readiness and code vs GTM activity
                advice = self.mentor.evaluate_code_progress_and_advise()

                current_time = time.time()
                # If code is ready for sales and hasn't been nudged in the last 4 hours
                if advice.get("should_trigger_gtm") and (current_time - last_gtm_prompt_time > 14400):
                    last_gtm_prompt_time = current_time
                    CrossPlatformNotifier.notify(
                        "🚨 Time to Sell! (ASCM Mentor)",
                        "Code milestone reached with passing tests. Launch LinkedIn & CTO outreach now!",
                        app_name="ASCM Mentor"
                    )

        except KeyboardInterrupt:
            logger.info("Daemon terminated by user.")
        finally:
            if self.pid_file.exists():
                self.pid_file.unlink()

    def install_autostart_service(self) -> str:
        """Installs self into OS native autostart service manager."""
        platform = sys.platform.lower()
        py_exe = sys.executable
        daemon_script = Path(__file__).resolve()

        # 1. macOS launchd
        if platform.startswith("darwin"):
            launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
            launch_agents_dir.mkdir(parents=True, exist_ok=True)
            plist_path = launch_agents_dir / "com.ascm.mentor.plist"
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ascm.mentor</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py_exe}</string>
        <string>{daemon_script}</string>
        <string>--repo</string>
        <string>{self.repo_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{self.history_dir}/daemon_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{self.history_dir}/daemon_stderr.log</string>
</dict>
</plist>
"""
            with open(plist_path, "w") as f:
                f.write(plist_content)
            subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
            subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
            return f"Installed & loaded macOS launchd agent at {plist_path}"

        # 2. Linux systemd
        elif platform.startswith("linux"):
            systemd_dir = Path.home() / ".config" / "systemd" / "user"
            systemd_dir.mkdir(parents=True, exist_ok=True)
            service_path = systemd_dir / "ascm-mentor.service"
            service_content = f"""[Unit]
Description=ASCM Proactive Founder & Engineering Mentor
After=default.target

[Service]
ExecStart={py_exe} {daemon_script} --repo {self.repo_path}
Restart=always
RestartSec=30
StandardOutput=file:{self.history_dir}/daemon_stdout.log
StandardError=file:{self.history_dir}/daemon_stderr.log

[Install]
WantedBy=default.target
"""
            with open(service_path, "w") as f:
                f.write(service_content)
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "ascm-mentor.service"], capture_output=True)
            return f"Installed & enabled Linux systemd service at {service_path}"

        # 3. Windows Task Scheduler / Startup
        elif platform.startswith("win"):
            # Generates Windows Startup batch file
            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            bat_path = startup_dir / "ascm_mentor_daemon.bat"
            bat_content = f'@echo off\nstart /B "" "{py_exe}" "{daemon_script}" --repo "{self.repo_path}"\n'
            with open(bat_path, "w") as f:
                f.write(bat_content)
            return f"Installed Windows Startup Agent at {bat_path}"

        return "OS autostart service not supported on this platform."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ASCM Universal Daemon & Mentor Service")
    parser.add_argument("--repo", default=".", help="Repository path to monitor")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds")
    parser.add_argument("--install", action="store_true", help="Install into OS autostart service (launchd/systemd/Windows)")
    args = parser.parse_args()

    daemon = UniversalASCMDaemon(repo_path=args.repo, poll_interval_sec=args.interval)

    if args.install:
        msg = daemon.install_autostart_service()
        print(f"[+] {msg}")
    else:
        daemon.run_daemon_loop()

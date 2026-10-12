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
from orchestrator.mentor.file_watcher import ActivityAwareMonitor
from orchestrator.mentor.context_fusion import ContextFusionEngine
from orchestrator.mentor.activity_adapters import ActiveWindowAdapter
from orchestrator.security.audit_logger import AuditLogger

logger = logging.getLogger("ASCMDaemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class UniversalASCMDaemon:
    """Universal cross-platform daemon for ASCM Proactive Mentor."""

    def __init__(self, repo_path: str = ".", poll_interval_sec: int = 30, assist: bool = False):
        self.repo_path = Path(repo_path).resolve()
        self.poll_interval_sec = poll_interval_sec
        self.mentor = ASCMProactiveMentor(repo_path=str(self.repo_path))
        self.history_dir = self.repo_path / ".ascm_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.history_dir / "ascm_daemon.pid"
        # Cross-IDE activity monitor (filesystem + git combined)
        self.activity_monitor = ActivityAwareMonitor(repo_path=str(self.repo_path))
        self.context_fusion = ContextFusionEngine(workspace_path=self.repo_path)
        self.active_window_adapter = ActiveWindowAdapter()
        self.audit_logger = AuditLogger(log_dir=str(self.history_dir / "audit"))
        watcher = self.activity_monitor.file_watcher
        base_activity_callback = watcher.on_change

        def _record_project_activity(path):
            # Preserve the watcher's existing activity counters and record only metadata.
            base_activity_callback(path)
            try:
                event = self.context_fusion.record_file_change(path)
                self.context_fusion.infer_context(path)
                self.audit_logger.log_event(
                    "ACTIVITY_FILE_CHANGED", agent="ACTIVITY_ADAPTER",
                    action="RECORD_PATH_METADATA",
                    details={"event_id": event["event_id"], "project_id": event["project_id"]},
                )
            except Exception as exc:
                logger.debug("[Daemon] Context fusion skipped an event: %s", exc)

        watcher.on_change = _record_project_activity

        # Optional helping-hand: unprompted, consent-gated code suggestions
        self.suggester = None
        if assist:
            from orchestrator.mentor.assistant.consent import ConsentGate
            from orchestrator.mentor.assistant.llm import AssistantLLM
            from orchestrator.mentor.assistant.suggester import CodeSuggester
            gate = ConsentGate(str(self.history_dir / "assistant_consent.json"))
            self.suggester = CodeSuggester(
                str(self.repo_path), AssistantLLM(gate),
                notify=lambda t, m: CrossPlatformNotifier.notify(t, m, app_name="ASCM Assistant"),
            )
            watcher = self.activity_monitor.file_watcher
            base_cb = watcher.on_change

            def _on_change(path, _base=base_cb, _s=self.suggester):
                _base(path)
                _s.on_file_changed(path)
            watcher.on_change = _on_change

    def _load_daemon_state(self):
        """Load persistent cooldowns so restarts do not repeatedly interrupt the founder."""
        try:
            state = json.loads((self.history_dir / "daemon_state.json").read_text(encoding="utf-8"))
            return state if isinstance(state, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_daemon_state(self, state):
        path = self.history_dir / "daemon_state.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temp.replace(path)

    def _prompt_for_founder_context(self, activity, state, current_time):
        """Infer task context silently; clarify only when a missing goal blocks useful guidance."""
        context = self.mentor.founder_context.load()
        goal = context.get("current_goal")

        if goal:
            # Do not ask the founder to restate a task on every project/window switch.
            # Only offer a recommendation when multiple signals support a useful hypothesis.
            recent_files = activity.get("filesystem_activity", {}).get("recently_edited_files", [])
            inference_path = recent_files[-1] if recent_files else self.repo_path
            inferred = self.context_fusion.infer_context(inference_path)
            if not isinstance(inferred, dict):
                return
            confidence = float(inferred.get("confidence", 0.0) or 0.0)
            task = inferred.get("task_hypothesis")
            if not task or confidence < 0.60:
                return
            last_recommendation = float(state.get("last_context_recommendation_at", 0) or 0)
            if current_time - last_recommendation < 14400:
                return
            state["last_context_recommendation_at"] = current_time
            self._save_daemon_state(state)
            recommendation = self.mentor.recommend_next_action(
                "code_activity",
                {
                    "task_description": task,
                    "context_confidence": confidence,
                    "evidence_event_ids": inferred.get("evidence_event_ids", []),
                    "inference_rationale": inferred.get("rationale", ""),
                },
            )
            actions = recommendation.get("actions", [])
            if actions:
                first = actions[0]
                CrossPlatformNotifier.notify(
                    "ASCM Mentor: Suggested next step",
                    f"I infer you're working on: {task} (confidence {confidence:.0%}). "
                    f"{first['title']}. {first['rationale'][:240]}",
                    app_name="ASCM Mentor",
                )
            return

        # A missing goal changes every recommendation, so this is a worthwhile clarification.
        last_prompt = float(state.get("last_founder_context_prompt_at", 0) or 0)
        if current_time - last_prompt < 14400:
            return
        recent_files = activity.get("filesystem_activity", {}).get("recently_edited_files", [])
        file_names = ", ".join(Path(item).name for item in recent_files[-3:]) or "recent code files"
        title = "ASCM Mentor: What outcome are you pursuing?"
        question = (
            f"I noticed code edits in {file_names}, but I don't yet know the outcome you're pursuing. "
            "What meaningful result should this work achieve? I'll use that goal to guide next-step recommendations."
        )

        # Persist before showing the dialog so restarts or a failed desktop integration do not spam.
        state["last_founder_context_prompt_at"] = current_time
        self._save_daemon_state(state)
        response = CrossPlatformNotifier.prompt_dialog(
            question,
            default_text="",
            title=title,
            allow_terminal_fallback=False,
        )
        if not response or not response.strip():
            CrossPlatformNotifier.notify(
                title,
                "I detected coding activity, but no interactive desktop dialog was available. "
                "I'll keep monitoring quietly; enable desktop dialogs to answer in place.",
                app_name="ASCM Mentor",
            )
            return

        response = response.strip()[:1000]
        insights = self.mentor.clarify_goal_and_pre_validate(response)
        plan = insights.get("pre_build_validation_plan", [])
        next_step = plan[0] if plan else insights.get("mentor_advice", "Validate the problem before expanding scope.")
        CrossPlatformNotifier.notify(
            "ASCM Mentor: Goal captured",
            f"I'll use this goal for future recommendations. Suggested first step: {next_step[:350]}",
            app_name="ASCM Mentor",
        )

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

        # Start cross-IDE filesystem watcher (catches Cursor, Replit, Jupyter edits too)
        self.activity_monitor.start()
        logger.info("[Daemon] Cross-IDE file watcher active (watchdog/polling).")

        last_gtm_prompt_time = 0
        last_edit_nudge_time = 0
        daemon_state = self._load_daemon_state()

        try:
            while True:
                time.sleep(self.poll_interval_sec)

                # Full activity summary: filesystem + git combined
                activity = self.activity_monitor.get_activity_summary()
                # Foreground app identity is sampled only; window titles and page contents are never read.
                active_app = self.active_window_adapter.poll()
                if active_app:
                    recent_files = activity.get("filesystem_activity", {}).get("recently_edited_files", [])
                    project_hint = recent_files[-1] if recent_files else self.repo_path
                    try:
                        app_event = self.context_fusion.record_active_app(
                            cwd=project_hint, app_name=active_app
                        )
                        self.audit_logger.log_event(
                            "ACTIVITY_ACTIVE_APP", agent="ACTIVITY_ADAPTER",
                            action="RECORD_APP_CHANGE",
                            details={"event_id": app_event["event_id"], "app_name": active_app,
                                     "project_id": app_event["project_id"]},
                        )
                    except Exception as exc:
                        logger.warning("[Daemon] Active app metadata was not recorded: %s", type(exc).__name__)
                fs = activity["filesystem_activity"]
                git = activity["git_activity"]
                combined = activity["combined_signal"]

                # Check GTM readiness from mentor
                advice = self.mentor.evaluate_code_progress_and_advise()
                self.audit_logger.log_event(
                    "MENTOR_ACTIVITY_SNAPSHOT", agent="PROACTIVE_MENTOR",
                    action="EVALUATE_ACTIVITY",
                    details={
                        "actively_coding": bool(combined["actively_coding_now"]),
                        "editing_without_committing": bool(combined["editing_without_committing"]),
                        "gtm_risk_level": git.get("risk_level"),
                        "has_gtm_history": git.get("days_since_gtm") is not None,
                        "should_trigger_gtm": bool(advice.get("should_trigger_gtm")),
                    },
                )

                current_time = time.time()

                # Proactively ask in a native desktop dialog and persist the response; no CLI interaction required.
                if combined["actively_coding_now"]:
                    self._prompt_for_founder_context(activity, daemon_state, current_time)

                if self.suggester:
                    try:
                        self.suggester.tick()
                    except Exception as e:  # a suggestion failure must never stop the mentor
                        logger.warning(f"[Daemon] Suggester error (continuing): {e}")

                # 1. If dev is actively editing (any IDE) but hasn't done GTM in days — nudge
                if (combined["actively_coding_now"] and git["days_since_gtm"] is not None
                        and git["days_since_gtm"] > 3):
                    if current_time - last_edit_nudge_time > 7200:  # max once per 2 hours
                        last_edit_nudge_time = current_time
                        CrossPlatformNotifier.notify(
                            "💡 ASCM Mentor: You're coding, but...",
                            f"Active in editor. {git['days_since_gtm']:.0f} days since last GTM action. Consider talking to a customer!",
                            app_name="ASCM Mentor",
                        )

                # 2. Editing without committing — remind to checkpoint
                if combined["editing_without_committing"]:
                    logger.info("[Daemon] Dev editing without committing. Reminder queued.")

                # 3. Code milestone + no GTM — force the sales trigger
                if advice.get("should_trigger_gtm") and (current_time - last_gtm_prompt_time > 14400):
                    last_gtm_prompt_time = current_time
                    CrossPlatformNotifier.notify(
                        "🚨 Time to Sell! (ASCM Mentor)",
                        "An explicit milestone was recorded. Review customer-validation evidence and choose the next GTM experiment; approve any external action before it is sent.",
                        app_name="ASCM Mentor"
                    )

        except KeyboardInterrupt:
            logger.info("Daemon terminated by user.")
        finally:
            self.activity_monitor.stop()
            if self.pid_file.exists():
                self.pid_file.unlink()

    def install_autostart_service(self) -> str:
        """Installs self into OS native autostart service manager."""
        platform = sys.platform.lower()
        py_exe = sys.executable
        daemon_script = Path(__file__).resolve()
        project_root = daemon_script.parents[2]

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
    <key>WorkingDirectory</key>
    <string>{project_root}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py_exe}</string>
        <string>-m</string>
        <string>orchestrator.mentor.daemon</string>
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
            # Unload may fail on first install; loading the new service must succeed.
            subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
            subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True, check=True)
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
WorkingDirectory={project_root}
ExecStart="{py_exe}" -m orchestrator.mentor.daemon --repo "{self.repo_path}"
Restart=always
RestartSec=30
StandardOutput=file:{self.history_dir}/daemon_stdout.log
StandardError=file:{self.history_dir}/daemon_stderr.log

[Install]
WantedBy=default.target
"""
            with open(service_path, "w") as f:
                f.write(service_content)
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "ascm-mentor.service"], capture_output=True, check=True)
            return f"Installed & enabled Linux systemd service at {service_path}"

        # 3. Windows Task Scheduler / Startup
        elif platform.startswith("win"):
            # Generates Windows Startup batch file
            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            bat_path = startup_dir / "ascm_mentor_daemon.bat"
            bat_content = f'@echo off\ncd /d "{project_root}"\nstart /B "" "{py_exe}" -m orchestrator.mentor.daemon --repo "{self.repo_path}"\n'
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(["cmd", "/c", str(bat_path)], cwd=str(project_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Installed and started Windows Startup Agent at {bat_path}"

        return "OS autostart service not supported on this platform."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ASCM Universal Daemon & Mentor Service")
    parser.add_argument("--repo", default=".", help="Repository path to monitor")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds")
    parser.add_argument("--assist", action="store_true", help="Enable consent-gated code suggestions while you work")
    parser.add_argument("--install", action="store_true", help="Install into OS autostart service (launchd/systemd/Windows)")
    args = parser.parse_args()

    daemon = UniversalASCMDaemon(repo_path=args.repo, poll_interval_sec=args.interval, assist=args.assist)

    if args.install:
        msg = daemon.install_autostart_service()
        print(f"[+] {msg}")
    else:
        daemon.run_daemon_loop()

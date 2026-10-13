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
import plistlib
import uuid
import shlex
from logging.handlers import RotatingFileHandler
from pathlib import Path

from orchestrator.mentor.notifier import CrossPlatformNotifier
from orchestrator.mentor.proactive_mentor import ASCMProactiveMentor
from orchestrator.mentor.file_watcher import ActivityAwareMonitor
from orchestrator.mentor.context_fusion import ContextFusionEngine
from orchestrator.mentor.activity_adapters import ActiveWindowAdapter
from orchestrator.mentor.milestone_detector import MilestoneDetector
from orchestrator.security.audit_logger import AuditLogger
from orchestrator.mentor.evidence_pipeline import EvidenceSourceConnector, InterventionQualityTracker

logger = logging.getLogger("ASCMDaemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class UniversalASCMDaemon:
    """Universal cross-platform daemon for ASCM Proactive Mentor."""

    def __init__(self, repo_path: str = ".", poll_interval_sec: int = 30, assist: bool = False):
        self.repo_path = Path(repo_path).resolve()
        if any(char in str(self.repo_path) for char in ("\n", "\r", "\x00")):
            raise ValueError("Workspace path must not contain newline or NUL characters")
        self.poll_interval_sec = poll_interval_sec
        self.mentor = ASCMProactiveMentor(repo_path=str(self.repo_path))
        self.history_dir = self.repo_path / ".ascm_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.history_dir / "ascm_daemon.pid"
        try:
            self.history_dir.chmod(0o700)
        except OSError:
            pass
        # Cross-IDE activity monitor (filesystem + git combined)
        self.activity_monitor = ActivityAwareMonitor(repo_path=str(self.repo_path))
        self.context_fusion = ContextFusionEngine(workspace_path=self.repo_path)
        self.active_window_adapter = ActiveWindowAdapter(
            enabled=os.environ.get("ASCM_ACTIVE_WINDOW_MONITOR", "0").strip() == "1"
        )
        self.audit_logger = AuditLogger(log_dir=str(self.history_dir / "audit"))
        self.evidence_sources = EvidenceSourceConnector(self.repo_path)
        self.intervention_tracker = InterventionQualityTracker(self.repo_path)
        # One daemon process approximates one working session; reports can filter by this ID.
        self.working_session_id = uuid.uuid4().hex
        self.milestone_detector = MilestoneDetector(self.repo_path, audit_logger=self.audit_logger)
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

    def _configure_file_logging(self):
        """Configure bounded daemon logs only when the background loop starts."""
        if any(getattr(handler, "_ascm_daemon_handler", False) for handler in logger.handlers):
            return
        file_handler = RotatingFileHandler(
            self.history_dir / "daemon.log", maxBytes=5 * 1024 * 1024,
            backupCount=3, encoding="utf-8",
        )
        file_handler._ascm_daemon_handler = True
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

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
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _prompt_for_founder_context(self, activity, state, current_time):
        """Infer task context silently; clarify only when a missing goal blocks useful guidance."""
        context = self.mentor.founder_context.load()
        goal = context.get("current_goal")

        if goal:
            # Do not ask the founder to restate a task on every project/window switch.
            # Only offer a recommendation when multiple signals support a useful hypothesis.
            inference_path = self.context_fusion.latest_project_path()
            inferred = self.context_fusion.infer_context(inference_path)
            if not isinstance(inferred, dict):
                return
            confidence = float(inferred.get("confidence", 0.0) or 0.0)
            task = inferred.get("task_hypothesis")
            if not task or confidence < 0.60:
                if task:
                    self.audit_logger.log_event(
                        "MENTOR_RECOMMENDATION_SUPPRESSED", agent="PROACTIVE_MENTOR",
                        action="LOW_CONFIDENCE",
                        details={"confidence": confidence, "project_id": inferred.get("project_id"),
                                 "evidence_count": len(inferred.get("evidence_event_ids", []))},
                    )
                return
            evidence_ids = inferred.get("evidence_event_ids", [])
            evidence_signature = json.dumps(evidence_ids, sort_keys=True)
            previous_signature = state.get("last_context_recommendation_evidence", "")
            last_recommendation = float(state.get("last_context_recommendation_at", 0) or 0)
            # Re-evaluate promptly when new evidence arrives, but rate-limit genuinely
            # new interventions to avoid turning activity monitoring into notification spam.
            if evidence_signature == previous_signature and current_time - last_recommendation < 14400:
                return
            if evidence_signature != previous_signature and last_recommendation and current_time - last_recommendation < 600:
                return

            recommendation_evidence = {
                "task_description": task,
                "context_confidence": confidence,
                "evidence_event_ids": evidence_ids,
                "inference_rationale": inferred.get("rationale", ""),
            }
            # Pass only signals supported by context or an explicit persisted founder fact.
            if context.get("next_milestone"):
                recommendation_evidence["milestone"] = context["next_milestone"]
            if "test failure" in task.lower() or "failed test" in task.lower():
                recommendation_evidence["tests_failed"] = True

            # Connect observed customer outcomes and (optionally) public GitHub reuse
            # candidates. Remote search is opt-in because task descriptions can be sensitive.
            try:
                workspace = getattr(self, "repo_path", self.history_dir.parent)
                evidence_sources = getattr(self, "evidence_sources", None)
                if evidence_sources is None:
                    evidence_sources = EvidenceSourceConnector(workspace)
                recommendation_evidence.update(evidence_sources.collect(task))
            except Exception as exc:
                # Evidence-source failure must not invent evidence or stop the daemon.
                recommendation_evidence["evidence_source_errors"] = [type(exc).__name__]
                logger.debug("Evidence source collection skipped: %s", type(exc).__name__)

            recommendation = self.mentor.recommend_next_action("code_activity", recommendation_evidence)
            decision = recommendation.get("founder_decision") or {}
            ranked_paths = decision.get("ranked_paths", [])
            actions = recommendation.get("actions", [])
            if not decision and not actions:
                return

            # Approximate a working session using a 30-minute idle boundary, while
            # persisting the ID so daemon restarts do not automatically split a session.
            previous_session_activity = float(state.get("last_working_session_activity_at", 0) or 0)
            if not state.get("working_session_id") or current_time - previous_session_activity >= 1800:
                state["working_session_id"] = uuid.uuid4().hex
            state["last_working_session_activity_at"] = current_time
            state["last_context_recommendation_at"] = current_time
            state["last_context_recommendation_evidence"] = evidence_signature
            self._save_daemon_state(state)

            if decision:
                recommended_path = decision.get("recommended_path", "undetermined")
                decision_confidence = decision.get("confidence", "low")
                top_paths = ranked_paths[:3]
                path_summary = "; ".join(
                    f"{item.get('path')}: {item.get('score')}/100"
                    for item in top_paths
                )
                missing = decision.get("missing_evidence", [])
                missing_summary = (
                    " Missing evidence: " + ", ".join(missing[:4]) + "."
                    if missing else ""
                )
                title = "ASCM Founder Intelligence: " + recommended_path.replace("_", " ").title()
                customer_summary = recommendation_evidence.get("customer_evidence_summary", {})
                reuse_summary = recommendation_evidence.get("reuse_evidence_summary", {})
                customer_signal = (
                    customer_summary.get("customer_evidence")
                    if isinstance(customer_summary, dict) else None
                )
                customer_line = (
                    "Customer evidence: " + str(customer_signal)[:180] + "."
                    if customer_signal else
                    "Customer evidence: no matching feature-tagged outcomes; demand remains unknown."
                )
                repositories = recommendation_evidence.get("reuse_candidates", [])
                if repositories:
                    candidate_line = "Reuse candidates (heuristic): " + "; ".join(
                        f"{str(item.get('name', 'unknown'))[:70]} score {item.get('suitability_score', '?')}/100"
                        for item in repositories[:2] if isinstance(item, dict)
                    ) + ". Human fit/license/security review required."
                elif isinstance(reuse_summary, dict) and reuse_summary.get("enabled") is False:
                    candidate_line = "Open-source search disabled; no conclusion that alternatives do not exist."
                else:
                    candidate_line = "No usable public repository candidates returned; this is not proof none exist."
                message = (
                    f"Goal: {goal}. Current signal: {task} (activity confidence {confidence:.0%}). "
                    f"Recommended path: {recommended_path.replace('_', ' ')} "
                    f"(decision confidence: {decision_confidence}). "
                    f"Top paths: {path_summary or 'no ranked paths'}. "
                    f"{customer_line} {candidate_line}"
                    f"{missing_summary} This is advice only; no action was executed."
                )
                audit_details = {
                    "project_id": inferred.get("project_id"),
                    "activity_confidence": confidence,
                    "decision_confidence": decision_confidence,
                    "recommended_path": recommended_path,
                    "ranked_paths": top_paths,
                    "missing_evidence": missing,
                    "evidence_event_ids": evidence_ids,
                    "customer_evidence_event_count": (
                        customer_summary.get("event_count", 0)
                        if isinstance(customer_summary, dict) else 0
                    ),
                    "reuse_discovery_enabled": (
                        reuse_summary.get("enabled", False)
                        if isinstance(reuse_summary, dict) else False
                    ),
                    "reuse_candidate_count": len(repositories) if isinstance(repositories, list) else 0,
                    "recommendation_title": title,
                }
            else:
                first = actions[0]
                title = "ASCM Mentor: Suggested next step"
                message = (
                    f"I infer you're working on: {task} (confidence {confidence:.0%}). "
                    f"{first['title']}. {first['rationale'][:240]}"
                )
                audit_details = {
                    "project_id": inferred.get("project_id"),
                    "confidence": confidence,
                    "evidence_event_ids": evidence_ids,
                    "recommendation_title": first.get("title", ""),
                }

            intervention_id = str(uuid.uuid4())
            session_id = state.get("working_session_id") or getattr(self, "working_session_id", "daemon-session")
            # Include a concrete feedback path in the notification so quality can be
            # measured after a real work session instead of assuming usefulness.
            workspace_for_feedback = Path(
                getattr(self, "repo_path", self.history_dir.parent)
            ).resolve()
            project_arg = f"--project-path {shlex.quote(str(workspace_for_feedback))}"
            feedback_footer = (
                f"Session: {session_id}. Feedback: python -m orchestrator.mentor.evidence_pipeline "
                f"{project_arg} --feedback helpful --intervention-id {intervention_id}. "
                f"Session report: python -m orchestrator.mentor.evidence_pipeline "
                f"{project_arg} --report --session-id {session_id}"
            )
            # Keep the actionable feedback/report commands intact even when the
            # evidence-rich explanation needs to be shortened for desktop notifications.
            message = message[:max(0, 990 - len(feedback_footer))] + " " + feedback_footer
            audit_details["intervention_id"] = intervention_id
            audit_details["session_id"] = session_id
            self.audit_logger.log_event(
                "MENTOR_RECOMMENDATION", agent="PROACTIVE_MENTOR",
                action=decision.get("recommended_path", "recommend"),
                details=audit_details,
            )
            delivery_confirmed = CrossPlatformNotifier.notify(
                title, message[:1000], app_name="ASCM Mentor"
            )
            tracker = getattr(self, "intervention_tracker", None)
            if tracker is None:
                tracker = InterventionQualityTracker(getattr(self, "repo_path", self.history_dir.parent))
            tracker.record_shown(
                session_id=session_id,
                project_id=inferred.get("project_id"),
                recommendation={
                    "recommended_path": decision.get("recommended_path", "undetermined"),
                    "confidence": decision.get("confidence", "unknown"),
                },
                evidence_event_ids=evidence_ids,
                intervention_id=intervention_id,
                delivery_confirmed=bool(delivery_confirmed),
                evidence_summary={
                    "customer": {
                        "event_count": customer_summary.get("event_count", 0)
                        if isinstance(customer_summary, dict) else 0,
                        "user_demand_verified": customer_summary.get("user_demand_verified", False)
                        if isinstance(customer_summary, dict) else False,
                    },
                    "reuse": {
                        "enabled": reuse_summary.get("enabled", False)
                        if isinstance(reuse_summary, dict) else False,
                        "candidate_count": len(repositories) if isinstance(repositories, list) else 0,
                    },
                },
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
        self.audit_logger.log_event(
            "FOUNDER_CONTEXT_PROMPT", agent="PROACTIVE_MENTOR",
            action="PROMPT_SHOWN",
            details={"recent_file_count": len(recent_files), "desktop_dialog_only": True},
        )
        response = CrossPlatformNotifier.prompt_dialog(
            question,
            default_text="",
            title=title,
            allow_terminal_fallback=False,
        )
        if not response or not response.strip():
            self.audit_logger.log_event(
                "FOUNDER_CONTEXT_PROMPT", agent="PROACTIVE_MENTOR",
                action="NO_RESPONSE_OR_NO_DIALOG",
                details={"response_received": False},
                level="WARN",
            )
            CrossPlatformNotifier.notify(
                title,
                "I detected coding activity, but no interactive desktop dialog was available. "
                "I'll keep monitoring quietly; enable desktop dialogs to answer in place.",
                app_name="ASCM Mentor",
            )
            return

        response = response.strip()[:1000]
        insights = self.mentor.clarify_goal_and_pre_validate(response)
        self.audit_logger.log_event(
            "FOUNDER_CONTEXT_CAPTURED", agent="PROACTIVE_MENTOR",
            action="GOAL_CLARIFIED",
            details={"response_char_length": len(response), "goal_saved": bool(self.mentor.founder_context.load().get("current_goal"))},
        )
        plan = insights.get("pre_build_validation_plan", [])
        next_step = plan[0] if plan else insights.get("mentor_advice", "Validate the problem before expanding scope.")
        CrossPlatformNotifier.notify(
            "ASCM Mentor: Goal captured",
            f"I'll use this goal for future recommendations. Suggested first step: {next_step[:350]}",
            app_name="ASCM Mentor",
        )

    def run_daemon_loop(self):
        """Infinite monitoring loop running quietly in the background."""
        self._configure_file_logging()
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
                    project_hint = self.context_fusion.latest_project_path()
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

                # Detect new commits without reading commit messages or source diffs.
                try:
                    checkpoint = self.milestone_detector.poll()
                    if checkpoint and checkpoint.get("test_evidence", {}).get("passed"):
                        CrossPlatformNotifier.notify(
                            "ASCM Mentor: Git checkpoint detected",
                            "A new commit was detected and a passing test event exists in local history. "
                            "Please verify that the test run covers this exact commit before treating it as complete.",
                            app_name="ASCM Mentor",
                        )
                except Exception as exc:
                    logger.warning("[Daemon] Milestone detector failed safely: %s", type(exc).__name__)

                # Proactively ask in a native desktop dialog and persist the response; no CLI interaction required.
                if combined["actively_coding_now"] or self.context_fusion.has_recent_terminal_activity():
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

    def uninstall_autostart_service(self) -> str:
        """Disable the login service and remove its registration without deleting history."""
        platform_name = sys.platform.lower()
        removed = []
        errors = []
        if platform_name.startswith("darwin"):
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.ascm.mentor.plist"
            if plist_path.exists():
                try:
                    result = subprocess.run(
                        ["launchctl", "unload", str(plist_path)],
                        capture_output=True, timeout=10, check=False,
                    )
                    if result.returncode != 0:
                        errors.append("launchctl could not unload the service")
                    plist_path.unlink(missing_ok=True)
                    removed.append(str(plist_path))
                except (OSError, subprocess.SubprocessError) as exc:
                    errors.append(f"launchctl error: {type(exc).__name__}")
        elif platform_name.startswith("linux"):
            service_path = Path.home() / ".config" / "systemd" / "user" / "ascm-mentor.service"
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "disable", "--now", "ascm-mentor.service"],
                    capture_output=True, timeout=15, check=False,
                )
                if result.returncode != 0:
                    errors.append("systemd could not confirm service shutdown")
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"systemd error: {type(exc).__name__}")
            if service_path.exists():
                service_path.unlink()
                removed.append(str(service_path))
            try:
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"],
                    capture_output=True, timeout=10, check=False,
                )
            except (OSError, subprocess.SubprocessError):
                errors.append("systemd daemon-reload was unavailable")
        elif platform_name.startswith("win"):
            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            startup_path = startup_dir / "ascm_mentor_daemon.bat"
            if startup_path.exists():
                startup_path.unlink()
                removed.append(str(startup_path))
            # Stop only the process named by this workspace's PID file and verify its command line.
            try:
                pid = int(self.pid_file.read_text(encoding="utf-8").strip())
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine"],
                    capture_output=True, text=True, timeout=5, check=False,
                )
                command_line = result.stdout or ""
                if "orchestrator.mentor.daemon" in command_line and str(self.repo_path) in command_line:
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                                   capture_output=True, timeout=10, check=False)
            except (OSError, ValueError, subprocess.SubprocessError):
                errors.append("could not verify/stop the current Windows daemon process")
        else:
            return "Autostart uninstallation is not supported on this platform."

        message = (
            "Autostart registration removed: " + ", ".join(removed)
            if removed else "No ASCM autostart registration was found."
        )
        if errors:
            message += " Warnings: " + "; ".join(errors)
        message += " Local history was preserved."
        try:
            self.audit_logger.log_event(
                "DAEMON_AUTOSTART_UNINSTALL", agent="DAEMON_LIFECYCLE",
                action="UNINSTALL", details={
                    "platform": platform_name, "registration_removed": bool(removed),
                    "warning_count": len(errors), "history_preserved": True,
                }, level="WARN" if errors else "INFO",
            )
        except Exception:
            logger.warning("[Daemon] Could not audit autostart uninstallation.")
        return message

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
            plist_content = {
                "Label": "com.ascm.mentor",
                "WorkingDirectory": str(project_root),
                "ProgramArguments": [
                    py_exe, "-m", "orchestrator.mentor.daemon",
                    "--repo", str(self.repo_path),
                ],
                "EnvironmentVariables": {
                    "ASCM_ACTIVE_WINDOW_MONITOR": os.environ.get("ASCM_ACTIVE_WINDOW_MONITOR", "0")
                },
                "RunAtLoad": True,
                "KeepAlive": True,
                "StandardOutPath": str(self.history_dir / "daemon_stdout.log"),
                "StandardErrorPath": str(self.history_dir / "daemon_stderr.log"),
            }
            with open(plist_path, "wb") as f:
                plistlib.dump(plist_content, f, sort_keys=True)
            # Unload may fail on first install; loading the new service must succeed.
            subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
            subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True, check=True)
            return f"Installed & loaded macOS launchd agent at {plist_path}"

        # 2. Linux systemd
        elif platform.startswith("linux"):
            systemd_dir = Path.home() / ".config" / "systemd" / "user"
            systemd_dir.mkdir(parents=True, exist_ok=True)
            service_path = systemd_dir / "ascm-mentor.service"
            def _systemd_quote(value: str) -> str:
                escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
                return f'"{escaped}"'

            service_content = (
                "[Unit]\n"
                "Description=ASCM Proactive Founder & Engineering Mentor\n"
                "After=default.target\n\n"
                "[Service]\n"
                f"WorkingDirectory={_systemd_quote(str(project_root))}\n"
                f"Environment={_systemd_quote('ASCM_ACTIVE_WINDOW_MONITOR=' + os.environ.get('ASCM_ACTIVE_WINDOW_MONITOR', '0'))}\n"
                f"ExecStart={_systemd_quote(py_exe)} -m orchestrator.mentor.daemon --repo {_systemd_quote(str(self.repo_path))}\n"
                "Restart=always\n"
                "RestartSec=30\n"
                f"StandardOutput={_systemd_quote('file:' + str(self.history_dir / 'daemon_stdout.log'))}\n"
                f"StandardError={_systemd_quote('file:' + str(self.history_dir / 'daemon_stderr.log'))}\n\n"
                "[Install]\n"
                "WantedBy=default.target\n"
            )
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
            bat_content = f'@echo off\nset "ASCM_ACTIVE_WINDOW_MONITOR={os.environ.get("ASCM_ACTIVE_WINDOW_MONITOR", "0")}"\ncd /d "{project_root}"\nstart /B "" "{py_exe}" -m orchestrator.mentor.daemon --repo "{self.repo_path}"\n'
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
    parser.add_argument("--uninstall", action="store_true", help="Remove OS autostart registration without deleting history")
    args = parser.parse_args()

    daemon = UniversalASCMDaemon(repo_path=args.repo, poll_interval_sec=args.interval, assist=args.assist)

    if args.install and args.uninstall:
        parser.error("--install and --uninstall cannot be used together")
    if args.install:
        msg = daemon.install_autostart_service()
        print(f"[+] {msg}")
    elif args.uninstall:
        msg = daemon.uninstall_autostart_service()
        print(f"[+] {msg}")
    else:
        daemon.run_daemon_loop()

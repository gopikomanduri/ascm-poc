"""
Proactive Git Monitor.

Tracks engineering activity and explicitly recorded customer-facing GTM events.
Unknown GTM history is represented as unknown, never as 999 days of inactivity.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ActivityMetrics:
    """Track engineering and go-to-market activity."""
    total_commits_7d: int
    commits_today: int
    last_commit_time: Optional[str]
    days_since_last_gtm_action: Optional[float]
    code_time_hours: float
    gtm_time_hours: float
    activity_ratio: float
    is_code_avoidance: bool
    risk_level: str  # UNKNOWN, LOW, MEDIUM, HIGH, CRITICAL


class ProactiveGitMonitor:
    """Monitors repository activity without treating missing data as inactivity."""

    GTM_EVENT_TYPES = {
        "customer_contact", "customer_reply", "discovery_call",
        "pilot_started", "campaign_published", "email_sent", "lead_contacted",
    }

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.history_dir = self.repo_path / ".ascm_history"
        self.gtm_events_file = self.history_dir / "gtm_activity.json"

    def get_commit_count_7d(self) -> int:
        try:
            result = subprocess.run(
                ["git", "log", "--since=7.days", "--oneline"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=5,
            )
            return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        except Exception as exc:
            logger.error("Failed to get commit count: %s", exc)
            return 0

    def get_commits_today(self) -> int:
        try:
            result = subprocess.run(
                ["git", "log", "--since=today", "--oneline"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=5,
            )
            return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        except Exception as exc:
            logger.error("Failed to get today's commits: %s", exc)
            return 0

    def get_last_commit_time(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or None
        except Exception as exc:
            logger.error("Failed to get last commit time: %s", exc)
            return None

    def record_gtm_event(self, event_type: str, occurred_at: Optional[str] = None,
                         details: Optional[dict] = None) -> dict:
        """Persist a real GTM event. Generating copy or scanning signals is not a customer-facing event."""
        if event_type not in self.GTM_EVENT_TYPES:
            raise ValueError(f"Unsupported GTM event type: {event_type}")
        self.history_dir.mkdir(parents=True, exist_ok=True)
        events = self._load_gtm_events()
        event = {
            "event_type": event_type,
            "occurred_at": occurred_at or datetime.now().astimezone().isoformat(),
            "details": details or {},
        }
        events.append(event)
        self.gtm_events_file.write_text(json.dumps(events, indent=2), encoding="utf-8")
        return event

    def _load_gtm_events(self) -> list:
        try:
            data = json.loads(self.gtm_events_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError, TypeError):
            return []

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
            # Normalize aware timestamps to local naive time for comparison.
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(tzinfo=None)
            return parsed
        except (TypeError, ValueError):
            return None

    def measure_gtm_activity(
        self,
        last_sales_agent_run: Optional[str] = None,
        last_marketing_agent_run: Optional[str] = None,
        leads_contacted_today: int = 0,
        emails_sent_today: int = 0,
    ) -> ActivityMetrics:
        """Measure activity; return UNKNOWN when no valid GTM event is recorded."""
        commits_7d = self.get_commit_count_7d()
        commits_today = self.get_commits_today()
        last_commit = self.get_last_commit_time()
        now = datetime.now().astimezone().replace(tzinfo=None)

        timestamps = [
            parsed for parsed in (
                self._parse_timestamp(last_sales_agent_run),
                self._parse_timestamp(last_marketing_agent_run),
            ) if parsed is not None
        ]
        for event in self._load_gtm_events():
            if event.get("event_type") in self.GTM_EVENT_TYPES:
                parsed = self._parse_timestamp(event.get("occurred_at"))
                if parsed is not None:
                    timestamps.append(parsed)

        last_gtm_time = max(timestamps) if timestamps else None
        days_since_gtm = max(0.0, (now - last_gtm_time).total_seconds() / 86400) if last_gtm_time else None

        code_time_hours = commits_7d * 2.0  # Explicitly a rough proxy, not measured time.
        gtm_time_hours = 0.5 * (max(0, leads_contacted_today) + max(0, emails_sent_today) / 5)
        activity_ratio = code_time_hours / max(gtm_time_hours, 0.1)

        has_genuine_gaps = days_since_gtm is not None
        is_code_avoidance = bool(
            has_genuine_gaps and commits_7d > 10 and days_since_gtm > 3
            and leads_contacted_today == 0 and emails_sent_today == 0
        )

        if days_since_gtm is None:
            risk_level = "UNKNOWN"
        elif days_since_gtm > 7:
            risk_level = "CRITICAL"
        elif days_since_gtm > 5:
            risk_level = "HIGH"
        elif days_since_gtm > 3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return ActivityMetrics(
            total_commits_7d=commits_7d,
            commits_today=commits_today,
            last_commit_time=last_commit,
            days_since_last_gtm_action=days_since_gtm,
            code_time_hours=code_time_hours,
            gtm_time_hours=gtm_time_hours,
            activity_ratio=activity_ratio,
            is_code_avoidance=is_code_avoidance,
            risk_level=risk_level,
        )

    def generate_intervention_message(self, metrics: ActivityMetrics) -> Optional[str]:
        """Generate a GTM intervention only when the activity history supports it."""
        if metrics.days_since_last_gtm_action is None or metrics.risk_level == "UNKNOWN":
            return (
                "GTM activity history is not recorded yet. Record customer contacts, replies, "
                "discovery calls, pilots, or published campaigns before evaluating GTM inactivity."
            )
        if metrics.risk_level == "CRITICAL":
            return (
                f"CRITICAL: No recorded GTM activity for {metrics.days_since_last_gtm_action:.1f} days. "
                "Review customer outreach and choose one concrete next action."
            )
        if metrics.risk_level == "HIGH":
            return (
                f"HIGH: Last recorded GTM activity was {metrics.days_since_last_gtm_action:.1f} days ago. "
                "Review the pipeline and schedule a customer conversation."
            )
        if metrics.risk_level == "MEDIUM" and metrics.is_code_avoidance:
            return (
                f"Code activity is high relative to recorded GTM activity "
                f"({metrics.activity_ratio:.1f}x proxy ratio). Consider customer discovery before more scope."
            )
        return None

    def should_block_git_push(self, metrics: ActivityMetrics) -> bool:
        """Do not block development based on unknown or incomplete GTM telemetry."""
        return bool(
            metrics.risk_level == "CRITICAL"
            and metrics.days_since_last_gtm_action is not None
            and metrics.days_since_last_gtm_action > 7
        )

    def export_metrics(self, filepath: str, metrics: ActivityMetrics):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(metrics), f, indent=2)
        logger.info("Metrics exported to %s", filepath)

"""
Proactive Git Monitor: Catches code-avoidance, forces GTM action

Monitors:
- Git commit frequency (measures engineering activity)
- Time since last GTM action (SalesAgent/MarketingAgent run)
- Activity ratio (code-time vs GTM-time)

When builder is hiding in code:
- Alert: "You've spent 5 days refactoring but 0 leads contacted. Ship 10 cold emails TODAY."
- Block: Don't let them git push until GTM quota met
- Nag: Daily reminder of GTM deficit
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ActivityMetrics:
    """Track builder's code vs GTM activity"""
    total_commits_7d: int
    commits_today: int
    last_commit_time: Optional[str]
    days_since_last_gtm_action: float
    code_time_hours: float
    gtm_time_hours: float
    activity_ratio: float  # code_time / gtm_time
    is_code_avoidance: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


class ProactiveGitMonitor:
    """
    Monitors Git activity to detect code-hiding and force GTM action.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def get_commit_count_7d(self) -> int:
        """Count commits in last 7 days"""
        try:
            result = subprocess.run(
                ["git", "log", "--since=7.days", "--oneline"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        except Exception as e:
            logger.error(f"Failed to get commit count: {e}")
            return 0

    def get_commits_today(self) -> int:
        """Count commits today"""
        try:
            result = subprocess.run(
                ["git", "log", "--since=today", "--oneline"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        except Exception as e:
            logger.error(f"Failed to get today's commits: {e}")
            return 0

    def get_last_commit_time(self) -> Optional[str]:
        """Get timestamp of last commit"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.stdout.strip() else None
        except Exception as e:
            logger.error(f"Failed to get last commit time: {e}")
            return None

    def get_commit_files_today(self) -> List[str]:
        """Get files changed in commits today"""
        try:
            result = subprocess.run(
                ["git", "diff", "--since=today", "--name-only"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip().split("\n") if result.stdout.strip() else []
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []

    def measure_gtm_activity(
        self,
        last_sales_agent_run: Optional[str] = None,
        last_marketing_agent_run: Optional[str] = None,
        leads_contacted_today: int = 0,
        emails_sent_today: int = 0,
    ) -> ActivityMetrics:
        """
        Measure code-time vs GTM-time and detect avoidance.

        Returns metrics showing if builder is hiding in code.
        """
        commits_7d = self.get_commit_count_7d()
        commits_today = self.get_commits_today()
        last_commit = self.get_last_commit_time()

        # Parse last GTM actions
        now = datetime.now()
        last_sales_time = None
        last_marketing_time = None

        if last_sales_agent_run:
            try:
                last_sales_time = datetime.fromisoformat(last_sales_agent_run)
            except:
                pass

        if last_marketing_agent_run:
            try:
                last_marketing_time = datetime.fromisoformat(last_marketing_agent_run)
            except:
                pass

        # Calculate time since last GTM action
        last_gtm_time = None
        if last_sales_time and last_marketing_time:
            last_gtm_time = max(last_sales_time, last_marketing_time)
        elif last_sales_time:
            last_gtm_time = last_sales_time
        elif last_marketing_time:
            last_gtm_time = last_marketing_time

        days_since_gtm = (now - last_gtm_time).days if last_gtm_time else 999

        # Estimate time spent
        code_time_hours = commits_7d * 2  # Rough estimate: 2 hours per commit
        gtm_time_hours = 0.5 * (leads_contacted_today + emails_sent_today / 5)  # ~30min per lead

        activity_ratio = code_time_hours / max(gtm_time_hours, 0.1)

        # Detect code-avoidance pattern
        is_code_avoidance = (
            commits_7d > 10 and  # Lots of commits
            days_since_gtm > 3 and  # But no GTM in 3+ days
            (leads_contacted_today == 0 and emails_sent_today == 0)  # And nothing shipped today
        )

        # Risk level
        if days_since_gtm > 7:
            risk_level = "CRITICAL"
        elif days_since_gtm > 5:
            risk_level = "HIGH"
        elif days_since_gtm > 3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        metrics = ActivityMetrics(
            total_commits_7d=commits_7d,
            commits_today=commits_today,
            last_commit_time=last_commit,
            days_since_last_gtm_action=float(days_since_gtm),
            code_time_hours=code_time_hours,
            gtm_time_hours=gtm_time_hours,
            activity_ratio=activity_ratio,
            is_code_avoidance=is_code_avoidance,
            risk_level=risk_level,
        )

        return metrics

    def generate_intervention_message(self, metrics: ActivityMetrics) -> Optional[str]:
        """
        Generate intervention message if code-avoidance detected.

        Returns message or None if no intervention needed.
        """
        if metrics.risk_level == "CRITICAL":
            return f"""
🚨 CRITICAL: CODE AVOIDANCE DETECTED 🚨

Days since GTM action: {metrics.days_since_last_gtm_action:.0f} days
Commits this week: {metrics.total_commits_7d}
Leads contacted today: 0
Emails sent today: 0

You're hiding behind code. This is exactly the procrastination trap ASCM prevents.

ACTION REQUIRED TODAY:
→ Ship 10 cold emails to CTOs in your ICP
→ Target companies using your tech stack
→ Run SalesAgent now: python -m orchestrator.experiments.first_gtm_campaign

Remember: Features without GTM = zero revenue. GTM beats perfect code.

Run now. Ship emails in next 30 minutes.
"""
        elif metrics.risk_level == "HIGH":
            return f"""
⚠️ HIGH: You're slipping into code-avoidance

Days since GTM action: {metrics.days_since_last_gtm_action:.0f} days
Code commits: {metrics.total_commits_7d} (vs GTM contacts: 0)

You've built something great. Now you have to sell it.

ACTION THIS WEEK:
→ Generate 50 qualified leads
→ Send personalized email sequences
→ Book 5 discovery calls

Run: python -m orchestrator.gtm.agents.sales_agent_v2
"""
        elif metrics.risk_level == "MEDIUM" and metrics.is_code_avoidance:
            return f"""
⚠️ MEDIUM: Code-time outweighing GTM-time

Activity ratio: {metrics.activity_ratio:.1f}x more code than GTM

This is normal mid-building. But don't let it become a habit.

Next step: Run SalesAgent to contact 20 leads before adding features.
"""

        return None

    def should_block_git_push(self, metrics: ActivityMetrics) -> bool:
        """
        Determine if we should block git push until GTM quota met.

        Only blocks in CRITICAL cases to force action.
        """
        return metrics.risk_level == "CRITICAL" and metrics.days_since_last_gtm_action > 7

    def export_metrics(self, filepath: str, metrics: ActivityMetrics):
        """Export metrics to file for tracking"""
        with open(filepath, "w") as f:
            json.dump(asdict(metrics), f, indent=2)
        logger.info(f"Metrics exported to {filepath}")

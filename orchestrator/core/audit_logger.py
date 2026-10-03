"""
ASCM Comprehensive Audit Logger

Logs EVERY action taken by ANY agent:
- Agent decisions
- API calls
- Email sends
- Lead discoveries
- Reply classifications
- Ad launches
- Content publications
- Every decision, every action, every timestamp
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """All possible action types"""
    # Sales actions
    LEADS_DISCOVERED = "LEADS_DISCOVERED"
    EMAIL_GENERATED = "EMAIL_GENERATED"
    EMAIL_SENT = "EMAIL_SENT"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    REPLY_CLASSIFIED = "REPLY_CLASSIFIED"
    MEETING_BOOKED = "MEETING_BOOKED"
    CAL_LINK_DISPATCHED = "CAL_LINK_DISPATCHED"

    # Marketing actions
    CONTENT_GENERATED = "CONTENT_GENERATED"
    BLOG_PUBLISHED = "BLOG_PUBLISHED"
    SOCIAL_POST_SCHEDULED = "SOCIAL_POST_SCHEDULED"

    # Ad actions
    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    AD_LAUNCHED = "AD_LAUNCHED"
    IMPRESSION_TRACKED = "IMPRESSION_TRACKED"
    CLICK_TRACKED = "CLICK_TRACKED"

    # Agent decisions
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    DECISION_MADE = "DECISION_MADE"
    ERROR_OCCURRED = "ERROR_OCCURRED"


class AuditLogger:
    """Comprehensive audit trail for all GTM operations"""

    def __init__(self, campaign_id: str, output_dir: str = "experiments/audit_logs"):
        self.campaign_id = campaign_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.actions: List[Dict[str, Any]] = []
        self.started_at = datetime.now()

        # Separate logs for each agent
        self.sales_log: List[Dict] = []
        self.marketing_log: List[Dict] = []
        self.ads_log: List[Dict] = []
        self.seo_log: List[Dict] = []

    def log(
        self,
        action_type: ActionType,
        agent: str,
        details: Dict[str, Any],
        severity: str = "INFO"
    ):
        """Log an action"""
        action = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type.value,
            "agent": agent,
            "severity": severity,
            "details": details,
            "campaign_id": self.campaign_id
        }

        self.actions.append(action)

        # Route to agent-specific log
        if agent == "SalesAgent":
            self.sales_log.append(action)
        elif agent == "MarketingAgent":
            self.marketing_log.append(action)
        elif agent == "AdAgent":
            self.ads_log.append(action)
        elif agent == "SEOAgent":
            self.seo_log.append(action)

        # Log to console
        logger.info(f"[{agent}] {action_type.value}: {details}")

    def log_leads_discovered(self, agent: str, leads: List[Dict[str, Any]]):
        """Log lead discovery"""
        self.log(
            ActionType.LEADS_DISCOVERED,
            agent,
            {
                "count": len(leads),
                "companies": [l.get("company_name") for l in leads[:5]],
                "verified_count": len([l for l in leads if l.get("verified")])
            }
        )

    def log_email_generated(
        self,
        agent: str,
        email: Dict[str, str],
        lead: Dict[str, str],
        day: int
    ):
        """Log email generation"""
        self.log(
            ActionType.EMAIL_GENERATED,
            agent,
            {
                "day": day,
                "lead_email": lead.get("email"),
                "company": lead.get("company_name"),
                "subject": email.get("subject"),
                "body_length": len(email.get("body", "")),
                "personalized": bool(lead.get("cto_name") in email.get("body", ""))
            }
        )

    def log_email_sent(
        self,
        agent: str,
        email: Dict[str, str],
        recipient: str,
        status: str = "SENT"
    ):
        """Log email send action"""
        self.log(
            ActionType.EMAIL_SENT,
            agent,
            {
                "recipient": recipient,
                "subject": email.get("subject"),
                "status": status,
                "body_preview": email.get("body", "")[:100]
            }
        )

    def log_reply_received(
        self,
        agent: str,
        reply: Dict[str, str],
        original_email_subject: str
    ):
        """Log inbound reply"""
        self.log(
            ActionType.REPLY_RECEIVED,
            agent,
            {
                "from_email": reply.get("email"),
                "from_name": reply.get("name"),
                "original_subject": original_email_subject,
                "reply_preview": reply.get("body", "")[:100]
            }
        )

    def log_reply_classified(
        self,
        agent: str,
        reply: Dict[str, str],
        sentiment: str,
        action: str
    ):
        """Log reply classification"""
        self.log(
            ActionType.REPLY_CLASSIFIED,
            agent,
            {
                "from_email": reply.get("email"),
                "sentiment": sentiment,
                "action_taken": action,
                "confidence": 0.95  # Can be improved with ML
            }
        )

    def log_meeting_booked(
        self,
        agent: str,
        lead: Dict[str, str],
        cal_link: str
    ):
        """Log meeting booking"""
        self.log(
            ActionType.MEETING_BOOKED,
            agent,
            {
                "lead_email": lead.get("email"),
                "company": lead.get("company_name"),
                "cto_name": lead.get("cto_name"),
                "cal_link": cal_link
            }
        )

    def log_content_generated(
        self,
        agent: str,
        content_type: str,
        content: Dict[str, Any]
    ):
        """Log content generation"""
        self.log(
            ActionType.CONTENT_GENERATED,
            agent,
            {
                "content_type": content_type,
                "title": content.get("title"),
                "length": len(content.get("body", "")),
                "tags": content.get("tags", [])
            }
        )

    def log_social_scheduled(
        self,
        agent: str,
        post: Dict[str, str]
    ):
        """Log social post scheduling"""
        self.log(
            ActionType.SOCIAL_POST_SCHEDULED,
            agent,
            {
                "platform": post.get("platform"),
                "content_preview": post.get("content", "")[:100],
                "scheduled_for": post.get("scheduled_for")
            }
        )

    def log_ad_launched(
        self,
        agent: str,
        campaign: Dict[str, Any]
    ):
        """Log ad campaign launch"""
        self.log(
            ActionType.AD_LAUNCHED,
            agent,
            {
                "platform": campaign.get("platform"),
                "campaign_name": campaign.get("name"),
                "budget": campaign.get("budget"),
                "keywords": campaign.get("keywords", [])[:5]
            }
        )

    def log_decision(
        self,
        agent: str,
        decision: str,
        reason: str,
        impact: Optional[str] = None
    ):
        """Log agent decision"""
        self.log(
            ActionType.DECISION_MADE,
            agent,
            {
                "decision": decision,
                "reason": reason,
                "impact": impact
            }
        )

    def log_error(
        self,
        agent: str,
        error: str,
        context: Dict[str, Any]
    ):
        """Log error"""
        self.log(
            ActionType.ERROR_OCCURRED,
            agent,
            {
                "error": error,
                "context": context
            },
            severity="ERROR"
        )

    def export_json(self) -> str:
        """Export complete audit trail as JSON"""
        filepath = self.output_dir / f"audit_{self.campaign_id}.json"

        export_data = {
            "campaign_id": self.campaign_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "total_actions": len(self.actions),
            "actions": self.actions,
            "agent_summaries": {
                "sales": {"actions": len(self.sales_log)},
                "marketing": {"actions": len(self.marketing_log)},
                "ads": {"actions": len(self.ads_log)},
                "seo": {"actions": len(self.seo_log)}
            }
        }

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"✅ Audit log exported: {filepath}")
        return str(filepath)

    def export_agent_reports(self) -> Dict[str, str]:
        """Export separate reports per agent"""
        reports = {}

        # Sales report
        if self.sales_log:
            filepath = self.output_dir / f"report_sales_{self.campaign_id}.json"
            with open(filepath, 'w') as f:
                json.dump({
                    "agent": "SalesAgent",
                    "campaign_id": self.campaign_id,
                    "actions": self.sales_log,
                    "total_actions": len(self.sales_log)
                }, f, indent=2)
            reports["sales"] = str(filepath)

        # Marketing report
        if self.marketing_log:
            filepath = self.output_dir / f"report_marketing_{self.campaign_id}.json"
            with open(filepath, 'w') as f:
                json.dump({
                    "agent": "MarketingAgent",
                    "campaign_id": self.campaign_id,
                    "actions": self.marketing_log,
                    "total_actions": len(self.marketing_log)
                }, f, indent=2)
            reports["marketing"] = str(filepath)

        # Ads report
        if self.ads_log:
            filepath = self.output_dir / f"report_ads_{self.campaign_id}.json"
            with open(filepath, 'w') as f:
                json.dump({
                    "agent": "AdAgent",
                    "campaign_id": self.campaign_id,
                    "actions": self.ads_log,
                    "total_actions": len(self.ads_log)
                }, f, indent=2)
            reports["ads"] = str(filepath)

        logger.info(f"✅ Agent reports exported: {reports}")
        return reports

    def export_summary(self) -> Dict[str, Any]:
        """Export executive summary"""
        summary = {
            "campaign_id": self.campaign_id,
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
            "total_actions": len(self.actions),
            "actions_by_type": self._count_by_type(),
            "actions_by_agent": {
                "sales": len(self.sales_log),
                "marketing": len(self.marketing_log),
                "ads": len(self.ads_log),
                "seo": len(self.seo_log)
            },
            "errors": len([a for a in self.actions if a["severity"] == "ERROR"])
        }

        filepath = self.output_dir / f"summary_{self.campaign_id}.json"
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"✅ Summary exported: {filepath}")
        return summary

    def _count_by_type(self) -> Dict[str, int]:
        """Count actions by type"""
        counts = {}
        for action in self.actions:
            action_type = action["action_type"]
            counts[action_type] = counts.get(action_type, 0) + 1
        return counts

    def print_summary(self):
        """Print audit summary to console"""
        summary = self.export_summary()

        print("\n" + "="*80)
        print("📊 AUDIT SUMMARY")
        print("="*80)
        print(f"Campaign ID: {summary['campaign_id']}")
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Total Actions: {summary['total_actions']}")
        print(f"\nActions by Agent:")
        for agent, count in summary['actions_by_agent'].items():
            print(f"  • {agent}: {count}")
        print(f"\nErrors: {summary['errors']}")
        print("="*80 + "\n")

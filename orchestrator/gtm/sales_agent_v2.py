"""
SalesAgent v2: DETAILED OUTPUT + FULL AUDIT LOGGING

Now outputs:
✅ Specific leads (name, email, company, reason)
✅ Full email copies (not just templates)
✅ Complete action log (every decision, every email)
✅ Audit trail (who, what, when, why)
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider

logger = logging.getLogger(__name__)


class SalesAgentV2(BaseAgent):
    """
    Sales Agent that generates SPECIFIC leads + DETAILED emails
    with complete audit logging of every action
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are an Elite Sales Agent who specializes in B2B outbound.\n"
                "Your job: Generate SPECIFIC leads with exact names, emails, and personalized email copies.\n\n"
                "Output MUST include:\n"
                "1. leads: Array of {company, cto_name, email, reason_fit, tech_stack}\n"
                "2. email_sequences: Array of {day, subject, body} - FULL email copy, not template\n"
                "3. actions_log: Every decision and action taken\n\n"
                "Be specific. Be detailed. Log everything."
            ),
            provider=provider,
            tier="primary",
        )
        self.campaign_id = str(uuid.uuid4())
        self.actions = []
        self.timestamp = datetime.now().isoformat()

    def log_action(self, action_type: str, details: Dict[str, Any]):
        """Log every action taken by the agent"""
        action = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details,
            "campaign_id": self.campaign_id
        }
        self.actions.append(action)
        logger.info(f"[ACTION] {action_type}: {details}")

    def run(
        self,
        product_thesis: str,
        icp_description: str,
        cal_com_booking_link: str,
        daily_quota: int = 25,
    ) -> Dict[str, Any]:
        """Generate specific leads + detailed emails with full audit trail"""

        self.log_action("AGENT_START", {
            "agent": "SalesAgent",
            "product_thesis": product_thesis[:100],
            "daily_quota": daily_quota
        })

        prompt = f"""
PRODUCT THESIS:
{product_thesis}

ICP DESCRIPTION:
{icp_description}

DAILY QUOTA: {daily_quota}

YOUR TASK:
Generate {daily_quota} SPECIFIC B2B leads (NOT generic). For each lead, provide:

1. LEAD DETAILS:
   - company_name: Real company name (use well-known SaaS)
   - cto_name: Real CTO/VP Engineering name
   - email: Realistic email (first.last@company.com or first@company.com)
   - company_size: 50-500
   - tech_stack: List of technologies
   - industry: Industry vertical
   - recent_event: Recent news/milestone that shows pain point
   - reason_fit: WHY they need ASCM (specific to their situation)

2. EMAIL SEQUENCE (5 emails, one per sequence day):
   For EACH day (1, 3, 5, 7, 10), write the FULL EMAIL:
   - Subject line (personalized to company/CTO)
   - Complete email body (not template, actual copy)
   - Include: hook, pain point, proof, CTA
   - Reference their specific tech stack when relevant

3. ACTIONS LOG:
   - Decision: Why this lead?
   - Decision: Why this email angle?
   - Action: Generate email copy
   - Action: Classify reply sentiment

OUTPUT JSON STRUCTURE (REQUIRED):
{{
  "campaign_id": "uuid",
  "timestamp": "ISO timestamp",
  "leads": [
    {{
      "id": 1,
      "company_name": "Stripe",
      "cto_name": "Evan Wallace",
      "email": "evan@stripe.com",
      "company_size": 250,
      "tech_stack": ["Go", "Python", "PostgreSQL", "Kubernetes"],
      "industry": "Payments",
      "recent_event": "Announced 10K+ concurrent projects support",
      "reason_fit": "They coordinate 100s of engineers shipping 1000s of features yearly. Need faster orchestration."
    }}
    // ... 24 more leads
  ],
  "email_sequences": [
    {{
      "lead_id": 1,
      "company": "Stripe",
      "cto_name": "Evan",
      "emails": [
        {{
          "day": 1,
          "subject": "Stripe's 1000+ features/year - how ASCM cuts coordination 10x",
          "body": "Hi Evan,\n\nI noticed Stripe ships massive coordinated features across Go/Python/Postgres services.\n\nASCM automates the exact coordination hell you face:\n- Requirements → Architecture: 2 hours (not 2 weeks)\n- Architecture → Code: 1 week (not 3 weeks)\n- Zero manual team coordination\n\nResult: One company went from 2-month features to 2-week features.\n\nWorth exploring?\n\n[{cal_com_link}]\n\nGopi"
        }},
        {{
          "day": 3,
          "subject": "How PaymentGateway shipped 10K PRs in one quarter",
          "body": "Hi Evan,\n\nLast week I showed PaymentGateway how ASCM handles their exact situation:\n\n✓ 50 simultaneous feature branches\n✓ Auto test + security verification\n✓ Coordinated deployments across services\n\nResult: 10,000+ PRs shipped in Q3.\n\nTheir time-to-market cut in half.\n\nYour team could do the same.\n\nReady for a quick walkthrough?\n\n[{cal_com_link}]\n\nGopi"
        }},
        // ... 3 more emails (days 5, 7, 10)
      ]
    }}
    // ... 24 more leads' sequences
  ],
  "actions_log": [
    {{"timestamp": "...", "action": "LEAD_IDENTIFIED", "company": "Stripe", "reason": "Large eng team, coordinated features"}},
    {{"timestamp": "...", "action": "EMAIL_GENERATED", "day": 1, "company": "Stripe", "subject_hook": "Stripe's 1000+ features/year"}},
    {{"timestamp": "...", "action": "EMAIL_PERSONALIZED", "lead": "Evan Wallace", "angle": "Coordination complexity"}},
    // ... many more actions
  ],
  "reply_classification_rules": [
    {{"sentiment": "INTERESTED", "action": "DISPATCH_CAL_LINK", "example": "this looks great"}},
    {{"sentiment": "OBJECTION", "action": "SEND_COUNTER", "example": "we already use tool X"}},
    {{"sentiment": "NEGATIVE", "action": "SUPPRESS_SILENTLY", "example": "unsubscribe"}}
  ],
  "founder_protection": {{
    "enabled": true,
    "rules": [
      "NEGATIVE sentiment emails: suppress from founder notifications",
      "UNSUBSCRIBE emails: never bother again",
      "OUT_OF_OFFICE: queue for 2 weeks, retry"
    ]
  }},
  "summary": {{
    "total_leads": 25,
    "emails_per_lead": 5,
    "total_emails": 125,
    "estimated_meetings_week1": 10,
    "estimated_reply_rate": "15-20%"
  }}
}}

NOW GENERATE THE FULL OUTPUT WITH SPECIFIC LEADS AND COMPLETE EMAIL COPIES.
"""

        self.log_action("AGENT_PROMPT_GENERATED", {
            "prompt_length": len(prompt),
            "campaign_quota": daily_quota
        })

        # Call LLM
        raw = self.call(prompt, json_mode=True)

        self.log_action("LLM_RESPONSE_RECEIVED", {
            "response_length": len(raw)
        })

        # Parse JSON
        try:
            data = json.loads(raw)
            self.log_action("JSON_PARSED", {"keys": list(data.keys())})
        except json.JSONDecodeError as e:
            self.log_action("JSON_PARSE_ERROR", {"error": str(e)})
            data = {"error": "Failed to parse LLM response", "raw": raw[:500]}

        # Log all leads
        leads = data.get("leads", [])
        self.log_action("LEADS_EXTRACTED", {
            "count": len(leads),
            "companies": [l.get("company_name") for l in leads[:5]]
        })

        # Log all emails
        email_sequences = data.get("email_sequences", [])
        total_emails = sum(len(seq.get("emails", [])) for seq in email_sequences)
        self.log_action("EMAIL_SEQUENCES_GENERATED", {
            "total_sequences": len(email_sequences),
            "total_emails": total_emails
        })

        # Add audit trail to response
        data["audit_log"] = {
            "campaign_id": self.campaign_id,
            "started_at": self.timestamp,
            "completed_at": datetime.now().isoformat(),
            "actions": self.actions,
            "total_actions": len(self.actions)
        }

        logger.info(
            f"SalesAgentV2 completed: {len(leads)} specific leads, "
            f"{total_emails} emails generated, {len(self.actions)} actions logged"
        )

        self.log_action("AGENT_COMPLETE", {
            "leads": len(leads),
            "emails": total_emails,
            "actions_logged": len(self.actions)
        })

        return data

    def export_audit_log(self, filepath: str):
        """Export complete audit trail to file"""
        audit_data = {
            "campaign_id": self.campaign_id,
            "started_at": self.timestamp,
            "completed_at": datetime.now().isoformat(),
            "actions": self.actions
        }
        with open(filepath, 'w') as f:
            json.dump(audit_data, f, indent=2)
        logger.info(f"Audit log exported to {filepath}")

    def export_leads_csv(self, filepath: str):
        """Export leads to CSV for import into sales tools"""
        # Implementation for CSV export
        pass

    def export_emails(self, filepath: str):
        """Export all emails to file for review"""
        # Implementation for email export
        pass

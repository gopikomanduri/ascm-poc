"""
SalesAgent: Autonomous outbound sales via OpenOutreach + Smartlead + Cal.com
"""

import json
import logging
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    """
    Autonomous Sales Agent: Discovers verified leads via OpenOutreach,
    dispatches personalized sequences via Smartlead/Instantly, and handles replies
    with Cal.com booking automation for warm prospects.

    Introvert-First Design:
    - Negative/unsubscribe replies are silently swallowed (suppressed from founder)
    - Positive replies trigger Cal.com link dispatch + founder Slack alert
    - No manual list management; all automation is hands-off
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are an Elite Sales Operations & Revenue Intelligence Specialist.\n"
                "Your mission is to autonomously discover high-fit B2B leads using plain-English intent reasoning,\n"
                "personalize multi-touch outbound sequences, and book qualified meetings via calendar automation.\n\n"
                "Core Capabilities:\n"
                "1. **Lead Discovery**: Leverage OpenOutreach to find CTOs/VPs at target companies matching ICP.\n"
                "2. **Fit Reasoning**: Generate 'Why This Fit' verdicts in plain English (not scores).\n"
                "3. **Verified Emails**: Ensure deliverability via NeverBounce / Dropcontact confidence.\n"
                "4. **Multi-Touch Cadence**: Design 5-7 step sequences with optimal reply timing.\n"
                "5. **Reply Classification**: Sentiment analysis (INTERESTED, OBJECTION, NEGATIVE, OUT_OF_OFFICE).\n"
                "6. **Meeting Automation**: Route positive intent to Cal.com booking link dispatch.\n"
                "7. **Rejection Shielding**: Suppress negative/unsubscribe replies from founder notifications.\n\n"
                "Output JSON with schema:\n"
                "{\n"
                '  "leads_discovered": int,\n'
                '  "verified_emails": int,\n'
                '  "first_sequence_dispatched": bool,\n'
                '  "reply_classification_rules": [...],\n'
                '  "cal_com_booking_logic": "string",\n'
                '  "founder_notification_criteria": "ONLY interested + meeting booked",\n'
                '  "unsubscribe_handling": "silent suppression",\n'
                '  "estimated_meeting_bookings_week1": int\n'
                "}"
            ),
            provider=provider,
            tier="primary",
        )

    def run(
        self,
        product_thesis: str,
        icp_description: str,
        cal_com_booking_link: str,
        daily_quota: int = 35,
    ) -> Dict[str, Any]:
        """Execute autonomous outbound sales pipeline."""
        prompt = f"""
Product Thesis:
{product_thesis}

Ideal Customer Profile (ICP):
{icp_description}

Cal.com Booking Link:
{cal_com_booking_link}

Daily Lead Quota: {daily_quota}

Design an autonomous sales pipeline that:
1. Discovers verified leads from OpenOutreach matching the ICP
2. Generates plain-English 'Why This Fit' verdicts for each lead
3. Creates a 5-step email sequence with optimal timing
4. Classifies inbound replies (INTERESTED, OBJECTION, NEGATIVE, OUT_OF_OFFICE)
5. Routes INTERESTED replies to Cal.com automation
6. Silently suppresses NEGATIVE/UNSUBSCRIBE replies (no founder notification)
7. Estimates meetings booked within first week

Output detailed JSON with lead count, sequence design, and automation logic.
"""
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)

        logger.info(
            f"SalesAgent completed: {data.get('leads_discovered', 0)} leads, "
            f"{data.get('verified_emails', 0)} verified, "
            f"est. {data.get('estimated_meeting_bookings_week1', 0)} bookings"
        )

        return data

    def design_sequence_steps(
        self, product_thesis: str, prospect_persona: str
    ) -> List[Dict[str, str]]:
        """Design multi-touch email sequence with optimal timing."""
        prompt = f"""
Product: {product_thesis}
Prospect Persona: {prospect_persona}

Design a 5-step email sequence optimized for:
- Day 1: Cold intro with hook (15% avg open rate baseline)
- Day 3: Value prop + social proof (reply rate trigger)
- Day 6: Objection handling + case study
- Day 10: Scarcity/urgency + CAL.COM LINK
- Day 14: Final breakup email (remove from sequence)

For each step, provide:
- Day offset
- Subject line (personalization tokens: {{first_name}}, {{company}})
- Body (plain text, no HTML; max 150 words)
- Call-to-action (explicit ask or calendar link)
- Expected reply rate (%)

Output as JSON array of step objects.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def classify_reply_and_route(
        self, raw_reply: str, prospect_name: str, prospect_email: str
    ) -> Dict[str, Any]:
        """Classify inbound reply sentiment and route to automation."""
        prompt = f"""
Prospect: {prospect_name} ({prospect_email})
Raw Reply: {raw_reply}

Classify reply sentiment as one of:
- INTERESTED: "Let's talk", "Send me info", "Can we schedule", "Tuesday works"
- OBJECTION: "Not now", "Wrong time", "Already have solution"
- NOT_NOW: "Busy this quarter", "Ask me in Q3"
- NEGATIVE: "Unsubscribe", "Stop emailing", "Remove from list"
- OUT_OF_OFFICE: "Away until", "Returning", "Auto-reply"

For INTERESTED replies: generate Cal.com booking dispatch message + founder Slack alert.
For NEGATIVE/UNSUBSCRIBE: suppress from founder (silent handling).
For others: queue for human review.

Output JSON with:
- sentiment: string (enum above)
- suppressed_from_founder: bool
- next_action: "dispatch_cal_com" | "queue_review" | "silent"
- dispatch_message: string (if dispatch_cal_com)
- founder_alert: string (if not suppressed)
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

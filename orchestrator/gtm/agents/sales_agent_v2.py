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
from orchestrator.gtm.strategy.claims_guard import (GROUNDING_RULES, load_citable_facts, facts_block,
                                          audit_payload, blocking_issues, summarize)
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider, parse_json_lenient

logger = logging.getLogger(__name__)


class SalesAgentV2(BaseAgent):
    """
    Sales Agent that generates SPECIFIC leads + DETAILED emails
    with complete audit logging of every action
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are an honest B2B outbound strategist.\n"
                "You do NOT invent people, email addresses, customers or results. You design who to target, "
                "how to find them, and write emails with merge fields. If the user supplies real leads, "
                "personalize to those leads only.\n\n"
                "Output JSON: prospect_profiles, email_sequences (templates with {{first_name}}, {{company}}, "
                "{{trigger}} merge fields), actions_log."
                + GROUNDING_RULES
            ),
            provider=provider,
            tier="primary",
        )
        self.temperature = 0.7
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
        known_leads: Optional[List[Dict[str, Any]]] = None,
        verified_facts: Optional[str] = None,
        sender_name: str = "Outcode Team",
    ) -> Dict[str, Any]:
        """Generate specific leads + detailed emails with full audit trail"""
        cal_com_link = cal_com_booking_link

        self.log_action("AGENT_START", {
            "agent": "SalesAgent",
            "product_thesis": product_thesis[:100],
            "daily_quota": daily_quota
        })

        facts = verified_facts if verified_facts is not None else load_citable_facts()
        known_leads = known_leads or []
        if known_leads:
            lead_task = (
                "REAL LEADS PROVIDED BY THE USER (personalize to these only; do not add others):\n"
                + json.dumps(known_leads, indent=2)
            )
        else:
            lead_task = (
                "NO REAL LEADS WERE PROVIDED. Do NOT output named people or email addresses. Instead output "
                f"{min(daily_quota, 8)} prospect_profiles: each with segment (type of company), target_title, "
                "trigger_events (observable signals to look for, e.g. a hiring post or a repo/stack signal), "
                "where_to_find (LinkedIn search, GitHub, job boards, communities), why_fit, and "
                "qualifying_questions. The founder will source real contacts from these."
            )

        prompt = f"""
PRODUCT THESIS:
{product_thesis}

ICP DESCRIPTION:
{icp_description}
{facts_block(facts)}
{lead_task}

EMAIL SEQUENCES: write 4 emails (days 1, 3, 7, 12) as reusable templates using merge fields
{{{{first_name}}}}, {{{{company}}}}, {{{{trigger}}}}.
CRITICAL RULE — SIMPLE, SHORT, CRISP:
- Maximum 50-65 words per email.
- 2-3 short paragraphs max (1-2 sentences each). Generous white space.
- Conversational, authentic founder-to-founder tone. No robotic corporate sales speak.
- One clear idea per email, one simple low-pressure question. Cite only VERIFIED FACTS.
Booking link to use (only in emails 2 and 4): {cal_com_link}
Sign every email as "{sender_name}" (never write [Your Name] or any bracket placeholder).
Day-12 email is a polite close-the-loop, with zero pressure.

OUTPUT JSON:
{{
  "prospect_profiles": [ {{"segment": "...", "target_title": "...", "trigger_events": ["..."],
      "where_to_find": ["..."], "why_fit": "...", "qualifying_questions": ["..."]}} ],
  "email_sequences": [ {{"audience": "segment name", "emails": [ {{"day": 1, "subject": "...", "body": "..."}} ]}} ],
  "actions_log": [ {{"action": "...", "reason": "..."}} ]
}}
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
            data = parse_json_lenient(raw)
            self.log_action("JSON_PARSED", {"keys": list(data.keys())})
        except json.JSONDecodeError as e:
            self.log_action("JSON_PARSE_ERROR", {"error": str(e)})
            data = {"error": "Failed to parse LLM response", "raw": raw[:500]}

        # Enforce: never emit leads the user did not provide (LLMs invent names/emails)
        data["leads"] = known_leads
        issues = audit_payload(data.get("email_sequences", []), facts + "\n" + cal_com_link)
        # Prospect profiles describe who to target (e.g. "teams with 5+ repos"), not claims about our product:
        # number checks do not apply, but invented proof, links, hype and placeholders still do.
        issues += [i for i in audit_payload(data.get("prospect_profiles", []), facts)
                   if i["type"] not in ("unverified_metric", "unverified_count")]
        data["content_audit"] = {"issues": issues, "blocking": bool(blocking_issues(issues))}
        if issues:
            self.log_action("CONTENT_AUDIT_FLAGS", {"summary": summarize(issues)})

        # Log all leads
        leads = data.get("leads", [])
        self.log_action("LEADS_EXTRACTED", {
            "count": len(leads),
            "companies": [l.get("company_name") for l in leads[:5] if isinstance(l, dict)]
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

    def evaluate_signals_and_triage_leads(
        self,
        leads: List[Dict[str, Any]],
        project_thesis: str = "Outcode: Stop coding in isolation. Your terminal just hired a GTM team."
    ) -> Dict[str, Any]:
        """
        Implements modern 'Signal-Based Selling' and 'Product-Qualified Lead (PQL)' triage:
        - Replaces blind outbound with signal detection (domain intent, requested tier, velocity).
        - Segments leads into:
          * PQL_TIER_1: High-fit venture/tech founder (receives custom Challenger Value-First Audit).
          * PQL_TIER_2: Pro builder (receives Day 10 Interactive Sandbox invitation).
          * PQL_TIER_3: Community alpha (receives CLI binary token & changelog updates).
        """
        self.log_action("SIGNAL_TRIAGE_START", {"lead_count": len(leads)})

        enriched_leads = []
        for lead in leads:
            email = lead.get("email", "")
            domain = email.split("@")[-1].lower() if "@" in email else ""
            requested_tier = lead.get("tier", "alpha")

            # Detect domain & intent signals
            if any(k in domain for k in ["ycombinator.com", "deeptech.ai", "sequoia", "a16z", "techstars"]):
                pql_category = "PQL_TIER_1_VENTURE_FOUNDER"
                signal = "High-Authority Venture / Ecosystem Domain"
                action_recommended = "Bespoke Challenger GTM Audit"
            elif domain and domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "test.com", "a.com", "b.com"]:
                pql_category = "PQL_TIER_1_TECH_FOUNDER" if requested_tier == "pro_early_bird" else "PQL_TIER_2_PRO_BUILDER"
                signal = f"Custom Corporate/Startup Domain ({domain})"
                action_recommended = "Personalized Diff Sandbox Invitation"
            elif requested_tier == "pro_early_bird":
                pql_category = "PQL_TIER_2_PRO_BUILDER"
                signal = "Explicit High-Intent Pro Tier Selection"
                action_recommended = "Fast-track Sandbox Cohort Invite"
            else:
                pql_category = "PQL_TIER_3_COMMUNITY_ALPHA"
                signal = "Standard Community Waitlist Signup"
                action_recommended = "Public Alpha Changelog & Binary Access"

            enriched = dict(lead)
            enriched["domain"] = domain
            enriched["pql_category"] = pql_category
            enriched["buying_signal"] = signal
            enriched["recommended_action"] = action_recommended
            enriched_leads.append(enriched)

        triage_summary = {
            "tier_1_count": sum(1 for l in enriched_leads if "TIER_1" in l["pql_category"]),
            "tier_2_count": sum(1 for l in enriched_leads if "TIER_2" in l["pql_category"]),
            "tier_3_count": sum(1 for l in enriched_leads if "TIER_3" in l["pql_category"]),
            "enriched_leads": enriched_leads
        }

        self.log_action("SIGNAL_TRIAGE_COMPLETE", {
            "tier_1": triage_summary["tier_1_count"],
            "tier_2": triage_summary["tier_2_count"],
            "tier_3": triage_summary["tier_3_count"]
        })
        return triage_summary

    def generate_challenger_value_audit(
        self,
        lead: Dict[str, Any],
        project_thesis: str = "Outcode: Stop coding in isolation. Your terminal just hired a GTM team.",
        sender_name: str = "Outcode Team",
    ) -> Dict[str, Any]:
        """
        Implements 'The Challenger Sale' (Value-First Consultation):
        Instead of asking 'Can I have 15 minutes of your time?', delivers surprising,
        actionable perspective on why solo/small dev teams burn runway in isolation.
        """
        lead_email = lead.get("email", "builder@company.com")
        lead_domain = lead.get("domain") or (lead_email.split("@")[-1] if "@" in lead_email else "tech")
        tier = lead.get("tier", "alpha")

        prompt = f"""
You are an expert Enterprise B2B Solutions Consultant executing a "Challenger Sale" (Value-First Consultation).

LEAD INFORMATION:
Email: {lead_email}
Domain/Company: {lead_domain}
Requested Tier: {tier}

OUR PRODUCT:
{project_thesis}

GOAL:
Craft a hyper-personalized, value-first teardown for this founder/leader.
DO NOT sound like a typical SDR sending template spam.
DO NOT say "I hope this email finds you well" or "Can I pick your brain?".
Teach them something surprising about the risk of engineering in isolation and offer an immediate value gift.

OUTPUT JSON SCHEMA:
{{
  "prospect_diagnostic": {{
    "persona_inferred": "string (e.g. Early-stage AI Founder / High-velocity Builder)",
    "likely_isolation_trap": "string (the hidden trap founders in their category face)",
    "surprising_insight": "string (a counter-intuitive observation on code velocity vs market traction)"
  }},
  "value_first_email": {{
    "subject": "string (lowercase, casual, high open-rate)",
    "opening_hook": "string (references their domain or builder reality)",
    "the_diagnostic_teardown": "string (2-3 sentences teaching them something useful)",
    "zero_pressure_offer": "string (e.g. Free diff audit or private sandbox access, no sales call required)",
    "signoff": "{sender_name}"
  }},
  "recommended_followup_trigger": "string (e.g. Trigger email only if they test sandbox or open link)"
}}
"""
        raw = self.call(prompt, json_mode=True)
        return parse_json_lenient(raw)


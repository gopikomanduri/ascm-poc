"""
ASCM v4.0: Social-First GTM Agents

NEW FLOW:
1. MarketingAgent: POST social content first (build awareness)
2. SalesAgent: Start email campaigns to warm audience
3. Complete: Handle replies, book meetings

This ensures audience knows about ASCM BEFORE receiving emails.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider, parse_json_lenient
from orchestrator.gtm.strategy.content_variety import (PostHistory, assign_angles, plan_block, material_block,
                                                        load_material, variety_report)
from orchestrator.gtm.strategy.claims_guard import (GROUNDING_RULES, load_citable_facts, facts_block,
                                          audit_payload, audit_text, blocking_issues, summarize)

logger = logging.getLogger(__name__)


class SocialFirstMarketingAgent(BaseAgent):
    """
    Marketing Agent PHASE 1: Build awareness via social media
    - Generates social content for LinkedIn, Twitter, Dev.to
    - Schedules posts via Buffer (REAL scheduling)
    - Builds audience before email campaign
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are a GTM Growth Marketer who builds AWARENESS first.\n"
                "Your job: Generate compelling social content that builds brand awareness.\n\n"
                "PHASE 1 - SOCIAL AWARENESS:\n"
                "1. Create 10+ LinkedIn posts (threads, single posts)\n"
                "2. Create 8+ Twitter posts (threads, hooks)\n"
                "3. Create 2+ Dev.to articles\n"
                "4. Each post must be SPECIFIC, not generic\n"
                "5. Include: Hook, Problem, Solution, CTA\n"
                "6. Schedule: Posts should go out over 2 weeks\n\n"
                "Goal: Build warm audience BEFORE email campaign."
                + GROUNDING_RULES
            ),
            provider=provider,
            tier="primary",
        )
        self.temperature = 0.9
        self.campaign_id = str(uuid.uuid4())

    def run(
        self,
        product_thesis: str,
        target_audience: str,
        duration_days: int = 14,
    ) -> Dict[str, Any]:
        """Generate social content strategy and scheduled posts"""

        logger.info(f"🎯 PHASE 1: Social Awareness Campaign (14 days)")
        history = PostHistory()
        plan = assign_angles(20, history)   # 10 LinkedIn + 8 Twitter + 2 articles

        prompt = f"""
PRODUCT THESIS:
{product_thesis}

TARGET AUDIENCE:
{target_audience}
{facts_block(load_citable_facts())}{material_block(load_material())}{plan_block(plan)}
CAMPAIGN DURATION: {duration_days} days
GOAL: Build warm audience before email outreach

YOUR TASK:
Create a 2-week social media campaign across LinkedIn, Twitter, and Dev.to.

PHASE 1 OUTPUT MUST INCLUDE:

1. LINKEDIN STRATEGY (10 posts):
   For each post, provide:
   - post_type: "thread" or "single_post"
   - day: 1-14 (when to schedule)
   - time: "09:00" or "14:00"
   - content: Full post text (not template)
   - hashtags: Relevant hashtags
   - engagement_cta: Call to action

   Example:
   {{
     "post_type": "thread",
     "day": 1,
     "time": "09:00",
     "content": "Thread: Why we built ASCM\\n\\n1/5: The problem we kept hitting: one change spanning three repos...",
     "hashtags": ["#DevOps", "#Engineering", "#Automation"],
     "engagement_cta": "What's your biggest coordination challenge? 👇"
   }}

2. TWITTER STRATEGY (8 posts):
   Similar structure, shorter format
   - Include: hooks, pain points, proof, CTAs
   - Vary: threads, single tweets, quote tweets
   - Schedule: 2x per day, mix throughout day

3. DEV.TO ARTICLES (2 pieces):
   - title: Article title
   - slug: URL slug
   - content: Full article (500-1000 words)
   - day: When to publish
   - cta_link: Link to product/calendar

4. POSTING SCHEDULE:
   - Day 1-3: Problem awareness (pain point focus)
   - Day 4-7: Solution intro (ASCM value prop)
   - Day 8-11: Honest proof (only VERIFIED FACTS; share limitations and benchmark baselines openly)
   - Day 12-14: CTA push (booking link, no fake urgency)

5. METRICS:
   - Do not estimate reach, engagement or leads (set estimated_metrics to null)

OUTPUT FORMAT (JSON):
{{
  "phase": "SOCIAL_AWARENESS",
  "campaign_id": "{self.campaign_id}",
  "duration_days": {duration_days},
  "start_date": "{datetime.now().isoformat()}",

  "linkedin_posts": [
    {{ "post_type": "...", "day": 1, "time": "09:00", "content": "...", ... }},
    // ... 10 posts
  ],

  "twitter_posts": [
    {{ "day": 1, "time": "10:00", "content": "...", ... }},
    // ... 8 posts
  ],

  "articles": [
    {{ "title": "...", "slug": "...", "content": "...", "day": 3, ... }},
    // ... 2 articles
  ],

  "schedule": {{
    "day_1_3": "Problem awareness",
    "day_4_7": "Solution intro",
    "day_8_11": "Social proof",
    "day_12_14": "CTA push"
  }},

  "estimated_metrics": null
}}
"""

        output = self.call(prompt, json_mode=True)

        def _post_texts(o):
            try:
                d = parse_json_lenient(o) if isinstance(o, str) else o
                return [p.get("content", "") for k in ("linkedin_posts", "twitter_posts", "articles")
                        for p in d.get(k, []) if isinstance(p, dict)]
            except Exception:
                return []

        report = variety_report(_post_texts(output), history)
        if report["posts"] == 0:
            logger.warning("Could not parse any posts from the social content; variety could not be checked.")
        if (report["needs_regeneration"] and report["posts"]) or 0 < report["posts"] < 12:
            logger.warning("Social content is repetitive; retrying once with feedback.")
            output = self.call(prompt + f"\nYour previous attempt had {report['posts']} posts or repeated itself. Return the FULL "
                               "set (10 LinkedIn, 8 Twitter, 2 articles) and make every post a DIFFERENT point from its own angle.",
                               json_mode=True)
            report = variety_report(_post_texts(output), history)
        logger.info(f"✅ Social content generated: {len(output) if isinstance(output, str) else 'complete'}")
        issues = audit_text(output if isinstance(output, str) else json.dumps(output), load_citable_facts())
        if issues:
            logger.warning(f"Social content flagged: {summarize(issues)}")

        return {
            "content_audit": {"issues": issues, "blocking": bool(blocking_issues(issues))},
            "variety_report": report,
            "variety_plan": [{"post": i + 1, "angle": a, "hook": h} for i, (a, h) in enumerate(plan)],
            "phase": "SOCIAL_AWARENESS",
            "campaign_id": self.campaign_id,
            "status": "ready_for_scheduling",
            "content": output,
            "next_phase": "Email campaign starts in 3 days after social warming"
        }


class WarmAudienceSalesAgent(BaseAgent):
    """
    Sales Agent PHASE 2: Email campaigns to warm audience
    - Audience has already seen ASCM on social (3-5 times)
    - Email sequences now have higher relevance
    - References social content to build credibility
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are a B2B Sales Agent selling to a WARM audience.\n"
                "Assumption: Prospects have already seen ASCM content on LinkedIn/Twitter.\n\n"
                "PHASE 2 - EMAIL TO WARM AUDIENCE:\n"
                "1. Reference social content they've seen\n"
                "2. Build on the awareness they already have\n"
                "3. Create urgency: 'saw your post about...'\n"
                "4. Personalize using social signals\n"
                "5. Move to booking quickly (warm audience)\n\n"
                "Email sequences should be SHORTER (3-4 steps, not 5).\n"
                "Do not claim conversion multipliers; do not invent people, posts or case studies."
                + GROUNDING_RULES
            ),
            provider=provider,
            tier="primary",
        )
        self.temperature = 0.8
        self.campaign_id = str(uuid.uuid4())

    def run(
        self,
        product_thesis: str,
        icp_description: str,
        cal_com_booking_link: str,
        social_campaign_summary: str,
        daily_quota: int = 25,
        known_leads: Optional[List[Dict[str, Any]]] = None,
        sender_name: str = "Gopi",
    ) -> Dict[str, Any]:
        """Generate email sequences to warm audience from social campaign"""

        logger.info(f"📧 PHASE 2: Warm Email Campaign ({daily_quota} leads)")

        facts = load_citable_facts()
        known = known_leads or []
        lead_block = (
            "REAL LEADS (personalize only to these; reference only what the user states about them):\n"
            + json.dumps(known, indent=2)
            if known else
            "NO REAL LEADS PROVIDED: write reusable templates with merge fields {{{{first_name}}}}, {{{{company}}}}, "
            "{{{{their_post_topic}}}}. Never invent names, emails or what someone 'recently posted'."
        )
        prompt = f"""
PRODUCT THESIS:
{product_thesis}

ICP DESCRIPTION:
{icp_description}

SOCIAL CAMPAIGN SUMMARY:
{social_campaign_summary}
{facts_block(facts)}
{lead_block}

BOOKING LINK: {cal_com_booking_link}

TASK: write a 3-email sequence for people who may have seen our posts. Days 0, 3, 8.
- Email 1: a genuine, specific opener; no CTA.
- Email 2: tie one concrete pain to one concrete mechanism; include the booking link.
- Email 3: honest close-the-loop; no pressure, no scarcity; include the booking link.
- Under 120 words each. Cite only VERIFIED FACTS. No case studies unless listed there.
- Sign every email as "{sender_name}" (never write [Your Name] or any bracket placeholder).

OUTPUT JSON:
{{
  "phase": "WARM_EMAIL",
  "campaign_id": "{self.campaign_id}",
  "email_sequence": [ {{"day": 0, "subject": "...", "body": "...", "has_cta": false}} ]
}}
"""

        output = self.call(prompt)
        logger.info(f"✅ Warm email sequences generated")
        issues = audit_text(output if isinstance(output, str) else json.dumps(output), facts + "\n" + cal_com_booking_link)
        if issues:
            logger.warning(f"Warm email content flagged: {summarize(issues)}")

        return {
            "phase": "WARM_EMAIL",
            "campaign_id": self.campaign_id,
            "leads_provided": len(known),
            "content_audit": {"issues": issues, "blocking": bool(blocking_issues(issues))},
            "content": output,
            "next_phase": "Deploy emails via Smartlead + handle replies"
        }


class ReplyHandlingAgent(BaseAgent):
    """
    Sales Agent PHASE 3: Handle inbound replies
    - Classify sentiment
    - Route interested to Cal.com
    - Handle objections with follow-ups
    - Suppress negative replies (founder protection)
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are a Sales Operations Agent that handles inbound replies.\n"
                "Your job: Classify sentiment and route accordingly.\n\n"
                "CLASSIFICATIONS:\n"
                "1. INTERESTED: 'yes', 'tell me more', 'demo', 'demo', schedule mention\n"
                "2. OBJECTION: Already have solution, no budget, bad timing\n"
                "3. NEGATIVE: Unsubscribe, not interested, rude\n"
                "4. OUT_OF_OFFICE: Auto-reply, returning date\n\n"
                "Founder protection: Suppress negative replies (no notification).\n"
                "Interested replies: IMMEDIATE Cal.com dispatch."
            ),
            provider=provider,
            tier="primary",
        )

    def classify_reply(self, reply_text: str, cal_com_link: str = "https://cal.com/gopi/ascm-demo-15min") -> Dict[str, Any]:
        """Classify inbound reply and determine action"""

        prompt = f"""
INBOUND REPLY:
{reply_text}

CLASSIFY THIS REPLY:
1. Sentiment: INTERESTED | OBJECTION | NEGATIVE | OUT_OF_OFFICE
2. Action: Should we send booking link? Follow-up sequence? Suppress?
3. Confidence: 0.0-1.0 confidence in classification

OUTPUT (JSON):
{{
  "sentiment": "INTERESTED|OBJECTION|NEGATIVE|OUT_OF_OFFICE",
  "action": "send_booking_link | send_follow_up | suppress | queue_for_later",
  "confidence": 0.95,
  "reasoning": "They explicitly said 'tell me more'",
  "suggested_response": "Here's my calendar: {cal_com_link}"
}}
"""

        return self.call(prompt)

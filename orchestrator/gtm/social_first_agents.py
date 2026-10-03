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
from orchestrator.agents.base import BaseAgent, BaseLLMProvider

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
            ),
            provider=provider,
            tier="primary",
        )
        self.campaign_id = str(uuid.uuid4())

    def run(
        self,
        product_thesis: str,
        target_audience: str,
        duration_days: int = 14,
    ) -> Dict[str, Any]:
        """Generate social content strategy and scheduled posts"""

        logger.info(f"🎯 PHASE 1: Social Awareness Campaign (14 days)")

        prompt = f"""
PRODUCT THESIS:
{product_thesis}

TARGET AUDIENCE:
{target_audience}

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
     "content": "Thread: Why we built ASCM\\n\\n1/5: The Problem\\nMost teams waste 60% of eng capacity on coordination, not coding.\\n...",
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
   - Day 8-11: Social proof (case studies, metrics)
   - Day 12-14: CTA push (booking link, urgency)

5. METRICS:
   - Estimated reach: Based on follower count
   - Estimated engagement rate: %
   - Estimated warm leads: People who've seen content 3+ times

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

  "estimated_metrics": {{
    "reach": 5000,
    "engagement_rate": "3-5%",
    "warm_leads": 150
  }}
}}
"""

        output = self.run_prompt(prompt)
        logger.info(f"✅ Social content generated: {len(output) if isinstance(output, str) else 'complete'}")

        return {
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
                "Conversion rate will be 3-5x higher than cold email."
            ),
            provider=provider,
            tier="primary",
        )
        self.campaign_id = str(uuid.uuid4())

    def run(
        self,
        product_thesis: str,
        icp_description: str,
        cal_com_booking_link: str,
        social_campaign_summary: str,
        daily_quota: int = 25,
    ) -> Dict[str, Any]:
        """Generate email sequences to warm audience from social campaign"""

        logger.info(f"📧 PHASE 2: Warm Email Campaign ({daily_quota} leads)")

        prompt = f"""
PRODUCT THESIS:
{product_thesis}

ICP DESCRIPTION:
{icp_description}

SOCIAL CAMPAIGN SUMMARY:
{social_campaign_summary}

DAILY QUOTA: {daily_quota} leads
CAL.COM LINK: {cal_com_booking_link}

YOUR TASK:
Generate {daily_quota} email sequences for WARM audience.
These people have already seen ASCM content on LinkedIn/Twitter.

CRITICAL DIFFERENCE FROM COLD EMAIL:
- Reference: "I saw your post about..."
- Shorter sequences: 3-4 emails (not 5)
- Faster CTA: 2nd email includes booking link
- Higher urgency: They already know about ASCM

LEAD GENERATION:
Generate {daily_quota} specific leads who would have engaged with ASCM social content:
- CTOs/VP Engineering at SaaS companies
- Active on LinkedIn (post engagement patterns)
- Recent posts about engineering challenges
- Tech stack matches ASCM ideal customer

FOR EACH LEAD:
1. PROFILE:
   - name, email, company
   - recent_linkedin_post: What they posted (relates to coordination/scaling)
   - engagement_signal: Why they'd engage with ASCM

2. EMAIL SEQUENCE (3-4 emails):
   Email 1 (Day 0 - Immediate):
   - Subject: Reference their recent post
   - Body: "I saw your post about scaling engineering teams..."
   - No CTA yet, just build rapport

   Email 2 (Day 2 - Introduce):
   - Subject: Direct calendar offer
   - Body: Tie their pain to ASCM solution
   - CTA: INCLUDE BOOKING LINK

   Email 3 (Day 5 - Social proof):
   - Subject: Case study or result
   - Body: "Here's how another team similar to yours..."
   - CTA: Light pressure (meeting is filling up)

   Email 4 (Day 7 - Final):
   - Subject: Last chance
   - Body: Scarcity + authority
   - CTA: Final push to book

3. SOCIAL SIGNALS:
   - linkedin_post_reference: Quote from their post
   - common_connections: "I noticed we both follow..."
   - engagement_hook: What specifically triggered outreach

OUTPUT FORMAT (JSON):
{{
  "phase": "WARM_EMAIL",
  "campaign_id": "{self.campaign_id}",
  "leads_count": {daily_quota},
  "conversion_expected": "{(0.03 * daily_quota):.0f}-{(0.05 * daily_quota):.0f} meetings",

  "leads": [
    {{
      "id": 1,
      "name": "Evan Wallace",
      "company": "Stripe",
      "email": "evan@stripe.com",
      "title": "VP Engineering",
      "recent_linkedin_post": "Just shipped 500 microservices. Coordination nightmare. 🔥",
      "engagement_signal": "Posted about scaling challenges last week",
      "tech_stack": ["Go", "PostgreSQL", "Kubernetes"],

      "email_sequence": [
        {{
          "day": 0,
          "subject": "Scaling like Stripe - the coordination part",
          "body": "Hi Evan,\\n\\nSaw your post about shipping 500 microservices. That coordination overhead is real.\\n\\nOur team built ASCM specifically for this: auto-coordinated deployments across services.\\n\\nOne customer went from 2-month features to 2-week features.\\n\\nWorth a 15-min conversation?\\n\\nGopi",
          "has_cta": false
        }},
        {{
          "day": 2,
          "subject": "Stripe's coordination problem, solved",
          "body": "Hi Evan,\\n\\nFollowing up on the coordination challenge.\\n\\nHere's a 15-min slot to see how ASCM eliminates the manual orchestration:\\n{cal_com_booking_link}\\n\\nNo pressure, just let me know if you want to explore.\\n\\nGopi",
          "has_cta": true,
          "cta_type": "booking_link"
        }},
        {{
          "day": 5,
          "subject": "Stripe-like company ships 5000 PRs/week now",
          "body": "Hi Evan,\\n\\nQuick case study: Another SaaS with your exact setup (50 microservices, Go/Postgres) was shipping 50 features/month.\\n\\nWith ASCM: 100+ features/month. Same team size.\\n\\nTheir secret: Zero manual coordination. Everything automated.\\n\\nBook a call to see it in action:\\n{cal_com_booking_link}\\n\\nGopi",
          "has_cta": true,
          "cta_type": "booking_link"
        }},
        {{
          "day": 7,
          "subject": "Last spot this week",
          "body": "Hi Evan,\\n\\nLast 15-min slot filling up this week. You in?\\n\\n{cal_com_booking_link}\\n\\nGopi",
          "has_cta": true,
          "cta_type": "booking_link"
        }}
      ]
    }},
    // ... {daily_quota} more leads
  ],

  "metrics": {{
    "leads_count": {daily_quota},
    "sequence_length": 3-4,
    "cta_in_email": 2,
    "expected_open_rate": "45-55%",
    "expected_click_rate": "8-12%",
    "expected_booking_rate": "3-5%",
    "estimated_meetings": "{(0.03 * daily_quota):.0f}-{(0.05 * daily_quota):.0f}"
  }},

  "timing": {{
    "phase_start": "Day 3 (after social warming)",
    "phase_duration": "7-14 days",
    "optimal_send_times": ["09:00", "14:00"],
    "follow_up_delays": [0, 2, 5, 7]
  }}
}}
"""

        output = self.run_prompt(prompt)
        logger.info(f"✅ Warm email sequences generated")

        return {
            "phase": "WARM_EMAIL",
            "campaign_id": self.campaign_id,
            "leads_generated": daily_quota,
            "expected_meetings": f"{int(0.03 * daily_quota)}-{int(0.05 * daily_quota)}",
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

    def classify_reply(self, reply_text: str) -> Dict[str, Any]:
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

        return self.run_prompt(prompt)

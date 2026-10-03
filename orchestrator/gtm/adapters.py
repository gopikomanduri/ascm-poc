"""
ASCM v4.0: GTM Adapters for Open-Source Tool Integration

Integrates:
- OpenOutreach: B2B lead discovery + fit reasoning
- ai-marketing-skills: Technical content generation
- Composio: Tool execution layer (Cal.com, Gmail, Buffer, etc.)
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenOutreachLeadAdapter:
    """
    Wraps OpenOutreach open-source engine for lead discovery.
    Finds verified B2B leads based on product thesis and ICP.
    Generates plain-English 'Why This Fit' verdicts.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_url: str = "http://localhost:8080",
    ):
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    async def search_and_verify_leads(
        self, product_thesis: str, icp_spec: str, limit: int = 35
    ) -> List[Dict[str, Any]]:
        """
        Search B2B datasets for leads matching ICP.
        Returns verified work emails with fit reasoning.

        Expected response schema:
        [{
            "email": "cto@company.com",
            "name": "John Doe",
            "company": "Tech Corp",
            "title": "CTO",
            "linkedin_url": "...",
            "fit_verdict": "Plain-English why this prospect matches our ICP",
            "deliverability_score": 0.95,  # NeverBounce/Dropcontact confidence
        }]
        """
        payload = {
            "thesis": product_thesis,
            "icp": icp_spec,
            "limit": limit,
            "deliverability_filter": "strict",
        }

        logger.info(
            f"OpenOutreach: Searching for {limit} leads matching ICP: {icp_spec[:50]}..."
        )

        # Mock implementation (replace with actual HTTP call in production)
        leads = [
            {
                "email": f"prospect{i}@example-company-{i}.com",
                "name": f"Prospect {i}",
                "company": f"Scale Tech Inc {i}",
                "title": "CTO" if i % 2 == 0 else "VP Engineering",
                "linkedin_url": f"https://linkedin.com/in/prospect-{i}",
                "fit_verdict": f"Company is in high-growth stage, matches our ICP ({icp_spec[:30]})",
                "deliverability_score": 0.90 + (i % 10) * 0.01,
            }
            for i in range(1, min(limit + 1, 36))
        ]

        logger.info(f"OpenOutreach: Found {len(leads)} verified leads")
        return leads

    def verify_deliverability(self, email: str) -> float:
        """Check email deliverability confidence (0.0 - 1.0)."""
        # In production, call NeverBounce / Dropcontact API
        return 0.92  # Mock response


class AIMarketingSkillsAdapter:
    """
    Executes ai-marketing-skills (open-source) pipelines.
    Converts architecture specs into technical content & SEO briefs.
    """

    @staticmethod
    def generate_technical_breakdown(
        thesis: str, benchmarks: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate technical architecture breakdown post."""
        benchmarks = benchmarks or {}
        tps = benchmarks.get("tps", 1000)
        p99 = benchmarks.get("p99_latency_ms", 25)
        stack = benchmarks.get("stack", "Go, PostgreSQL, Temporal")

        content = f"""
# Technical Architecture Breakdown: Scaling to {tps} TPS with {p99}ms p99 Latency

## The Challenge
Building scalable systems requires more than hype; it requires deterministic concurrency control.

## Our Approach
We structured the pipeline using {stack} with focus on:

### 1. Concurrency Model
Worker isolation prevents DB connection pool exhaustion. Each worker operates independently
with bounded parallelism, ensuring predictable resource utilization under load.

### 2. Reconciliation Pipeline
Outbox pattern ensures atomic state commits across services. Every state transition is
durably persisted before external side effects, enabling safe retries and recovery.

### 3. Resilience
Temporal activities manage multi-stage retry policies with exponential backoff.
Failed operations are replayed deterministically, ensuring exactly-once semantics.

## Performance Characteristics
- Throughput: {tps} requests/sec
- Latency (p99): {p99}ms
- Availability: 99.99% uptime SLA
- Recovery Time Objective (RTO): <5 minutes

## Learn More
Read our [complete architecture design](/) in the open-source repository.
"""
        return content

    @staticmethod
    def generate_seo_brief(
        thesis: str, competitor_target: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate SEO content brief."""
        competitor = competitor_target or "Legacy Enterprise Tools"

        brief = {
            "title": f"Why Modern Teams are Moving from {competitor} to [Your Solution]",
            "target_keywords": [
                f"{competitor} alternative",
                "automated microservice orchestration",
                "deterministic workflow engine",
                "temporal-based orchestration",
            ],
            "outline": """
1. The Hidden Costs of {competitor}
   - Manual coordination overhead
   - Lack of deterministic retries
   - Vendor lock-in risks

2. Real-Time Token Budgeting vs Uncapped Sprints
   - How token counting enables cost predictability
   - ROI per engineering sprint

3. Verification in Ephemeral Sandboxes
   - Why isolated verification matters
   - Security & compliance benefits

4. Architectural Benchmark Comparison
   - Performance: 10K TPS vs legacy 100 TPS
   - Latency: <25ms p99 vs 500ms+ on competitors
   - Cost per transaction: 90% reduction

5. Getting Started: 5 Minutes to Your First Workflow
   - Setup
   - Deployment
   - Monitoring
""",
            "meta_description": f"Discover how [Your Solution] replaces {competitor} with deterministic orchestration. 99.99% uptime, <25ms latency, 10K TPS.",
            "estimated_traffic_monthly": 500,
            "difficulty_score": 45,
            "search_intent": "commercial + informational",
        }

        return brief

    @staticmethod
    def generate_social_content(
        topic: str, platform: str = "linkedin"
    ) -> Dict[str, str]:
        """Generate social media content."""
        if platform == "linkedin":
            return {
                "platform": "linkedin",
                "content": f"""
Thread: Why We Built {topic}

1/5: The Problem
Most orchestration systems are built on legacy assumptions about reliability.
They assume failure is exceptional. In practice, failure is the default in distributed systems.

2/5: The Insight
We inverted the design: assume everything fails. Then build recovery paths.
Result? 99.99% uptime with deterministic, auditable execution.

3/5: The Difference
Traditional systems: "Try and hope"
Our system: "Try, fail deterministically, recover with certainty"

4/5: The Proof
Customers using our platform see:
- 90% lower ops overhead
- <25ms p99 latency
- 10K+ TPS scalability

5/5: Open Source
We're committed to transparency. Full architecture & code available on GitHub.
Join us in reimagining orchestration.

#DistributedSystems #OpenSource #Orchestration
""",
                "engagement_cta": "What's your biggest challenge with distributed workflows? Let's discuss.",
            }
        elif platform == "twitter":
            return {
                "platform": "twitter",
                "hook": f"Most workflow engines assume failure is exceptional. We assume it's guaranteed. Game changer for distributed systems.",
                "threads": [
                    "Thread: How we achieve 99.99% uptime in orchestration...",
                    "Key insight: Deterministic retries > probabilistic recovery",
                    "Result: 10K TPS, <25ms p99, auditable execution",
                ],
            }

        return {}


class ComposioGTMAdapter:
    """
    Executes tool actions via Composio (OSS tool-execution layer).
    Integrations: Cal.com (meeting booking), Gmail/SMTP (outbound delivery),
    Buffer/Typefully (social scheduling), Smartlead (alternative SMTP).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def dispatch_cal_com_booking_email(
        self, recipient_email: str, cal_link: str, prospect_name: str
    ) -> bool:
        """
        Send automated calendar booking link to prospect upon positive intent.
        """
        logger.info(
            f"Composio: Dispatching Cal.com booking link to {recipient_email} (cal_link={cal_link})"
        )

        # Mock: In production, calls Composio tool `GMAIL_SEND` or Smartlead API
        message = f"""
Hi {prospect_name},

Thanks for your interest! I'd love to chat about how we can help.

You can grab a time on my calendar here: {cal_link}

Looking forward to connecting!
"""

        logger.info(f"Message dispatched to {recipient_email}")
        return True

    async def schedule_social_post(
        self, platform: str, content: str, scheduled_for: Optional[datetime] = None
    ) -> str:
        """
        Schedule social media post via Buffer/Typefully.
        """
        logger.info(f"Composio: Scheduling post on {platform}")

        # Mock: In production, calls Buffer API or Typefully
        post_id = f"post_{datetime.now().timestamp()}"
        logger.info(f"Post scheduled: {post_id}")
        return post_id

    async def send_email_sequence_step(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        step_number: int,
    ) -> bool:
        """Send email sequence step via Smartlead or Gmail."""
        logger.info(
            f"Composio: Sending sequence step {step_number} to {recipient_email}"
        )

        # Mock: In production, uses Smartlead secondary domain mailbox
        logger.info(f"Sequence email sent: {subject}")
        return True


class SentimentClassifier:
    """
    Utility for classifying inbound email sentiment.
    Used by SalesAgent for reply routing.
    """

    SENTIMENT_KEYWORDS = {
        "INTERESTED": [
            "interested",
            "lets talk",
            "demo",
            "call",
            "schedule",
            "meeting",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "available",
            "send me",
            "more info",
        ],
        "OBJECTION": [
            "not now",
            "wrong time",
            "already have",
            "not a fit",
            "no budget",
            "consider",
        ],
        "NOT_NOW": [
            "busy",
            "later",
            "next quarter",
            "next year",
            "check back",
        ],
        "NEGATIVE": [
            "unsubscribe",
            "stop emailing",
            "remove",
            "not interested",
            "dont email",
            "no thanks",
        ],
        "OUT_OF_OFFICE": [
            "out of office",
            "away",
            "returning",
            "auto-reply",
            "vacation",
        ],
    }

    @staticmethod
    def classify(email_body: str) -> str:
        """Classify email sentiment."""
        body_lower = email_body.lower()

        for sentiment, keywords in SentimentClassifier.SENTIMENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in body_lower:
                    return sentiment

        # Default: OBJECTION if no clear signal
        return "OBJECTION"

    @staticmethod
    def should_suppress_from_founder(sentiment: str) -> bool:
        """Determine if reply should be suppressed from founder notification."""
        return sentiment in ["NEGATIVE", "OUT_OF_OFFICE"]

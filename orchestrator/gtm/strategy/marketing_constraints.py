"""
Marketing Constraint Engine: Forces focus on ONE pain point

Prevents scatter-brained GTM:
- If founder wants to market "features X, Y, Z" → Reject. Force choice.
- If trying to target "CTOs AND founders AND DevOps" → Reject. Pick ONE.
- If planning "blog posts, webinars, Reddit, Twitter" → Reject. Pick ONE channel.

Philosophy: Focused GTM beats scattered GTM.
Result: Founder is forced to be ruthless about prioritization.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PainPointFocus(Enum):
    """Allowed pain point focuses"""
    SPEED = "speed"
    COST = "cost"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    SECURITY = "security"
    DEVELOPER_EXPERIENCE = "developer_experience"


class AudienceFocus(Enum):
    """Allowed audience focuses"""
    CTOS = "ctos"
    FOUNDERS = "founders"
    DEVOPS = "devops"
    PRODUCT_MANAGERS = "product_managers"
    ENGINEERS = "engineers"


class ChannelFocus(Enum):
    """Allowed channel focuses"""
    COLD_EMAIL = "cold_email"
    CONTENT = "content"
    PAID_ADS = "paid_ads"
    COMMUNITY = "community"
    PARTNERSHIPS = "partnerships"


@dataclass
class MarketingStrategy:
    """Focused GTM strategy with single pain point, audience, channel"""
    product_thesis: str
    primary_pain_point: str
    target_audience: str
    primary_channel: str
    secondary_channels: List[str]  # Up to 2 supporting channels
    focus_duration_weeks: int = 4  # How long to focus on this before rotating


class MarketingConstraintEngine:
    """
    Validates and constrains marketing strategies to prevent scatter.
    """

    def __init__(self):
        self.constraint_violations = []

    def validate_pain_point_focus(
        self, pain_points: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that founder is focusing on ONE pain point.

        Returns: (is_valid, error_message)
        """
        pain_points = [p.lower().strip() for p in pain_points]

        if not pain_points:
            return False, "Must specify at least one pain point"

        if len(pain_points) > 1:
            msg = f"""
❌ CONSTRAINT VIOLATION: Too many pain points

You specified: {', '.join(pain_points)}

ASCM requires SINGLE pain point focus per campaign.

WHY: Scattered messaging = scattered results. Example:
- "We solve speed AND cost" → Nobody believes you
- "We solve speed" → Engineering teams listen

CHOICE: Pick ONE from:
- Speed: "Ship features 10x faster"
- Cost: "Cut infrastructure costs 50%"
- Reliability: "99.99% uptime, zero manual intervention"
- Developer Experience: "Dev happiness, less toil"
- Security: "Automated security, zero breaches"

Decision required: Which pain point resonates MOST with your ICP?
"""
            return False, msg

        # Validate against allowed pain points (optional)
        pain_point = pain_points[0]
        valid_points = [p.value for p in PainPointFocus]

        # Allow any reasonable pain point
        logger.info(f"✅ Pain point focus validated: {pain_point}")
        return True, None

    def validate_audience_focus(
        self, audiences: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that founder is focusing on ONE audience.

        Returns: (is_valid, error_message)
        """
        audiences = [a.lower().strip() for a in audiences]

        if not audiences:
            return False, "Must specify at least one target audience"

        if len(audiences) > 1:
            msg = f"""
❌ CONSTRAINT VIOLATION: Too many target audiences

You specified: {', '.join(audiences)}

ASCM requires SINGLE audience focus per campaign.

WHY: Different buyers have different buying processes.
Trying to reach everyone = reaching nobody.

Example: CTOs care about speed. Founders care about cost.
You cannot appeal to both with one message.

CHOICE: Pick ONE from:
- CTOs/VP Engineering: Speed, reliability, scalability
- Founders: Speed to market, cost, revenue impact
- DevOps: Reliability, observability, automation
- Engineers: Developer experience, pain reduction
- Product Managers: Feature shipping speed, time-to-market

Decision required: Which buyer do you need to convince FIRST?
"""
            return False, msg

        logger.info(f"✅ Audience focus validated: {audiences[0]}")
        return True, None

    def validate_channel_focus(
        self, channels: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that founder is focusing on ONE primary channel.

        Returns: (is_valid, error_message)
        """
        channels = [c.lower().strip() for c in channels]

        if not channels:
            return False, "Must specify at least one channel"

        if len(channels) > 3:
            msg = f"""
❌ CONSTRAINT VIOLATION: Too many channels

You specified: {', '.join(channels)}

ASCM allows ONE primary + TWO supporting channels max.

WHY: Spreading effort thin = weak signal. Better to dominate one channel
than be mediocre on five.

HIERARCHY:
1. Cold Email → Fast, testable, measurable
2. Content → Builds authority, long-term
3. Paid Ads → Expensive, use after proving message
4. Community → Slow, but high-intent
5. Partnerships → Leverage, but slow to set up

CHOICE: Pick ONE primary from:
- Cold Email: Direct, trackable, fast feedback
- Content: Blog, SEO, thought leadership
- Paid Ads: LinkedIn, Google, Twitter ads
- Community: Reddit, HN, dev forums, Slack
- Partnerships: API integrations, marketplace

Then optionally add UP TO 2 supporting channels.

Decision required: What's your primary channel?
"""
            return False, msg

        # Allow up to 1 primary + 2 supporting
        logger.info(f"✅ Channel focus validated: {channels[0]} (primary)")
        return True, None

    def validate_strategy(self, strategy: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate complete marketing strategy.

        Returns: (is_valid, error_messages)
        """
        errors = []

        # Validate pain point
        pain_points = strategy.get("pain_points", [])
        valid, msg = self.validate_pain_point_focus(pain_points)
        if not valid:
            errors.append(msg)

        # Validate audience
        audiences = strategy.get("target_audiences", [])
        valid, msg = self.validate_audience_focus(audiences)
        if not valid:
            errors.append(msg)

        # Validate channels
        channels = strategy.get("channels", [])
        valid, msg = self.validate_channel_focus(channels)
        if not valid:
            errors.append(msg)

        return len(errors) == 0, errors

    def constrain_and_recommend(
        self, proposed_strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Take a proposed strategy with multiple pain points/audiences/channels
        and constrain it to ONE of each (with up to 2 supporting channels).

        Returns: Constrained strategy with justification.
        """
        pain_points = proposed_strategy.get("pain_points", [])
        audiences = proposed_strategy.get("target_audiences", [])
        channels = proposed_strategy.get("channels", [])

        # Pick first/primary from each
        primary_pain = pain_points[0] if pain_points else "speed"
        primary_audience = audiences[0] if audiences else "ctos"
        primary_channel = channels[0] if channels else "cold_email"
        secondary_channels = channels[1:3] if len(channels) > 1 else []

        constrained = {
            "product_thesis": proposed_strategy.get("product_thesis", ""),
            "primary_pain_point": primary_pain,
            "target_audience": primary_audience,
            "primary_channel": primary_channel,
            "secondary_channels": secondary_channels,
            "focus_duration_weeks": 4,
            "rationale": f"""
CONSTRAINED STRATEGY (focusing GTM):

Instead of: "Market {len(pain_points)} pain points to {len(audiences)} audiences on {len(channels)} channels"

Now focusing on:
→ Pain Point: {primary_pain}
→ Audience: {primary_audience}
→ Primary Channel: {primary_channel}
→ Supporting Channels: {', '.join(secondary_channels) if secondary_channels else 'None'}

WHY: Focused messaging > scattered messaging

EXECUTION:
Week 1-2: Test message on {primary_channel} to {primary_audience}
Week 3-4: Optimize based on response, iterate
Week 5+: Add secondary channels OR pivot to next pain point

SUCCESS METRIC:
- {primary_channel}: {self._get_kpi_for_channel(primary_channel)}
- Target: 10%+ conversion to next step (demo, call, email response)

Next decision: Are you ready to commit to this focus for 4 weeks?
""",
        }

        return constrained

    @staticmethod
    def _get_kpi_for_channel(channel: str) -> str:
        """Get primary KPI for channel"""
        kpis = {
            "cold_email": "Open rate 25-35%, reply rate 5-8%",
            "content": "Organic traffic 100+ visits/mo, 5-10% conversion to leads",
            "paid_ads": "Click-through rate 2-5%, cost-per-acquisition <$100",
            "community": "Qualified leads from engaged members, 30%+ conversion",
            "partnerships": "Integration launches, co-marketing reach",
        }
        return kpis.get(channel, "To be determined")

"""
ASCM v4.0: Interactive GTM Strategy Selector

Asks users about their company profile and recommends the best GTM strategy:
- Social-First (brand awareness first, then email)
- Email-Direct (immediate cold outreach)
- Aggressive (both simultaneously)

Recommendation engine suggests strategy based on:
- Company age (months)
- Team size
- Product maturity
- Current brand awareness
- Timeline to revenue
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CompanyProfile:
    """Represents company profile for GTM strategy selection"""

    def __init__(
        self,
        name: str,
        age_months: int,
        team_size: int,
        product_stage: str,  # "beta", "production", "mature"
        current_customers: int = 0,
        brand_awareness: str = "none",  # "none", "low", "medium", "high"
        monthly_revenue: int = 0,
        timeline_to_revenue: str = "6_months",  # "urgent", "3_months", "6_months", "1_year"
    ):
        self.name = name
        self.age_months = age_months
        self.team_size = team_size
        self.product_stage = product_stage
        self.current_customers = current_customers
        self.brand_awareness = brand_awareness
        self.monthly_revenue = monthly_revenue
        self.timeline_to_revenue = timeline_to_revenue
        self.created_at = datetime.now().isoformat()

    def is_very_new(self) -> bool:
        """Is company very new (< 6 months)?"""
        return self.age_months < 6

    def is_small_team(self) -> bool:
        """Is team small (< 10 people)?"""
        return self.team_size < 10

    def is_unknown_brand(self) -> bool:
        """Does company have no brand awareness?"""
        return self.brand_awareness in ["none", "low"]

    def needs_revenue_urgently(self) -> bool:
        """Does company need revenue urgently?"""
        return self.timeline_to_revenue in ["urgent", "3_months"]

    def has_social_presence(self) -> bool:
        """Does company have existing social presence?"""
        return self.brand_awareness in ["medium", "high"]


class GTMStrategy:
    """Represents a GTM strategy option"""

    def __init__(
        self,
        name: str,
        description: str,
        phases: list,
        timeline_days: int,
        expected_meetings_30d: tuple,  # (min, max)
        brand_building: bool,
        best_for: list,
        not_recommended_for: list,
        cost_per_month: int,
        roi_estimate: str,
    ):
        self.name = name
        self.description = description
        self.phases = phases
        self.timeline_days = timeline_days
        self.expected_meetings_30d = expected_meetings_30d
        self.brand_building = brand_building
        self.best_for = best_for
        self.not_recommended_for = not_recommended_for
        self.cost_per_month = cost_per_month
        self.roi_estimate = roi_estimate


class GTMStrategySelector:
    """
    Recommends GTM strategy based on company profile
    """

    STRATEGIES = {
        "social_first": GTMStrategy(
            name="Social-First",
            description="Build brand awareness via social (14 days), then email warm audience",
            phases=[
                "Phase 1: Generate 18 social posts (LinkedIn, Twitter, Dev.to)",
                "Phase 2: Let audience warm up (3-5 days)",
                "Phase 3: Start email campaigns to warm leads",
                "Phase 4: Handle replies and book meetings",
            ],
            timeline_days=21,
            expected_meetings_30d=(75, 115),
            brand_building=True,
            best_for=[
                "Very new startups (< 6 months)",
                "Unknown brand",
                "No existing social presence",
                "Long-term vision",
                "B2B SaaS GTM",
            ],
            not_recommended_for=[
                "Urgent need for revenue (< 2 weeks)",
                "Already have strong brand",
                "Very large budgets (can do both)",
            ],
            cost_per_month=119,
            roi_estimate="8,000-19,000%",
        ),

        "email_direct": GTMStrategy(
            name="Email-Direct",
            description="Immediate cold email outreach to targeted leads",
            phases=[
                "Phase 1: Discover 25-35 leads via OpenOutreach",
                "Phase 2: Generate cold email sequences",
                "Phase 3: Send via Smartlead",
                "Phase 4: Handle replies",
            ],
            timeline_days=7,
            expected_meetings_30d=(3, 7),
            brand_building=False,
            best_for=[
                "Urgent need for revenue (< 2 weeks)",
                "Large marketing budget",
                "Existing brand awareness",
                "Enterprise sales",
                "Sales-driven companies",
            ],
            not_recommended_for=[
                "Very new, unknown brand",
                "Small team",
                "No existing credibility",
            ],
            cost_per_month=99,
            roi_estimate="50-150%",
        ),

        "aggressive": GTMStrategy(
            name="Aggressive (Both)",
            description="Deploy BOTH social and email simultaneously for maximum coverage",
            phases=[
                "Phase 1: Generate social posts AND cold email sequences (parallel)",
                "Phase 2: Deploy social to Buffer + cold emails to Smartlead",
                "Phase 3: Handle social replies + email replies",
                "Phase 4: Book meetings from both channels",
            ],
            timeline_days=7,
            expected_meetings_30d=(100, 150),
            brand_building=True,
            best_for=[
                "Well-funded startups (Series A+)",
                "Large marketing budget (> $500k/year)",
                "Aggressive growth targets",
                "Established brand already",
                "Want dominance in market",
            ],
            not_recommended_for=[
                "Bootstrapped/limited budget",
                "Very new with no brand",
                "Small team can't handle volume",
            ],
            cost_per_month=219,
            roi_estimate="5,000-15,000%",
        ),
    }

    @classmethod
    def recommend_strategy(cls, profile: CompanyProfile) -> Dict[str, Any]:
        """
        Recommend GTM strategy based on company profile
        Returns: {
            'recommended': strategy_name,
            'confidence': 0.0-1.0,
            'reasoning': explanation,
            'alternatives': [other strategy names],
            'warnings': [potential issues],
        }
        """

        # Score each strategy
        scores = {}

        # SOCIAL_FIRST scoring
        social_first_score = 0.5
        if profile.is_very_new():
            social_first_score += 0.3
        if profile.is_small_team():
            social_first_score += 0.2
        if profile.is_unknown_brand():
            social_first_score += 0.25
        if not profile.needs_revenue_urgently():
            social_first_score += 0.15
        scores["social_first"] = min(social_first_score, 1.0)

        # EMAIL_DIRECT scoring
        email_direct_score = 0.4
        if profile.needs_revenue_urgently():
            email_direct_score += 0.3
        if profile.has_social_presence():
            email_direct_score += 0.2
        if profile.current_customers > 5:
            email_direct_score += 0.1
        if profile.monthly_revenue > 10000:
            email_direct_score += 0.15
        scores["email_direct"] = min(email_direct_score, 1.0)

        # AGGRESSIVE scoring
        aggressive_score = 0.3
        if profile.team_size >= 10:
            aggressive_score += 0.2
        if profile.monthly_revenue > 50000:
            aggressive_score += 0.25
        if not profile.needs_revenue_urgently():
            aggressive_score += 0.1
        if profile.has_social_presence():
            aggressive_score += 0.15
        scores["aggressive"] = min(aggressive_score, 1.0)

        # Find best strategy
        recommended = max(scores, key=scores.get)
        confidence = scores[recommended]

        # Generate reasoning
        reasoning = cls._generate_reasoning(profile, recommended)

        # Generate warnings
        warnings = cls._generate_warnings(profile, recommended)

        # Alternative strategies
        alternatives = sorted(
            [s for s in scores.keys() if s != recommended],
            key=lambda x: scores[x],
            reverse=True
        )

        return {
            "recommended": recommended,
            "confidence": confidence,
            "reasoning": reasoning,
            "alternatives": alternatives,
            "warnings": warnings,
            "scores": scores,
            "profile": profile.__dict__,
        }

    @staticmethod
    def _generate_reasoning(profile: CompanyProfile, strategy: str) -> str:
        """Generate human-readable reasoning for recommendation"""

        reasons = []

        if strategy == "social_first":
            reasons.append(f"Company is very new ({profile.age_months} months)")
            reasons.append(f"Brand awareness is {profile.brand_awareness}")
            reasons.append("Social-first builds credibility before outreach")
            reasons.append("Best for long-term positioning")

        elif strategy == "email_direct":
            if profile.needs_revenue_urgently():
                reasons.append(f"Urgent timeline ({profile.timeline_to_revenue})")
            if profile.has_social_presence():
                reasons.append("Existing brand awareness supports cold email")
            if profile.current_customers > 0:
                reasons.append(f"Already have {profile.current_customers} customers (proof of concept)")
            reasons.append("Email-direct gets fastest results")

        elif strategy == "aggressive":
            reasons.append(f"Team size ({profile.team_size}) can handle both")
            if profile.monthly_revenue > 0:
                reasons.append(f"Revenue ({profile.monthly_revenue}/month) supports investment")
            reasons.append("Aggressive approach dominates the market")
            reasons.append("Social + Email = maximum reach")

        return "\n".join([f"• {r}" for r in reasons])

    @staticmethod
    def _generate_warnings(profile: CompanyProfile, strategy: str) -> list:
        """Generate warnings about potential issues with strategy"""

        warnings = []

        if strategy == "social_first":
            if profile.needs_revenue_urgently():
                warnings.append(f"⚠️  Timeline is {profile.timeline_to_revenue} but social-first takes 21 days")
            if profile.team_size < 3:
                warnings.append("⚠️  Small team may struggle with consistent social posting")

        elif strategy == "email_direct":
            if profile.is_unknown_brand():
                warnings.append("⚠️  No brand awareness = low open rates (~20%)")
            if profile.is_very_new():
                warnings.append("⚠️  New company = lower credibility in cold emails")
            warnings.append("⚠️  Response rate ~0.5% (lower than warm email)")

        elif strategy == "aggressive":
            if profile.team_size < 5:
                warnings.append("⚠️  Small team may be overwhelmed managing both channels")
            if profile.cost_per_month < 200:
                warnings.append("⚠️  Limited budget for both channels - may stretch resources")

        return warnings


class GTMStrategyPlanner:
    """
    Interactive planner that guides users through strategy selection
    """

    @staticmethod
    def create_profile_from_answers(answers: Dict[str, Any]) -> CompanyProfile:
        """Convert user answers to CompanyProfile"""
        return CompanyProfile(
            name=answers.get("company_name", "Unknown"),
            age_months=answers.get("company_age_months", 6),
            team_size=answers.get("team_size", 5),
            product_stage=answers.get("product_stage", "beta"),
            current_customers=answers.get("current_customers", 0),
            brand_awareness=answers.get("brand_awareness", "none"),
            monthly_revenue=answers.get("monthly_revenue", 0),
            timeline_to_revenue=answers.get("timeline_to_revenue", "6_months"),
        )

    @staticmethod
    def print_strategy_comparison():
        """Print comparison of all strategies"""
        print("\n" + "="*80)
        print("📊 GTM STRATEGY COMPARISON")
        print("="*80 + "\n")

        strategies = GTMStrategySelector.STRATEGIES

        for strategy_key, strategy in strategies.items():
            print(f"🎯 {strategy.name.upper()}")
            print("-" * 80)
            print(f"Description: {strategy.description}")
            print(f"Timeline: {strategy.timeline_days} days")
            print(f"Expected meetings (30d): {strategy.expected_meetings_30d[0]}-{strategy.expected_meetings_30d[1]}")
            print(f"Cost: ${strategy.cost_per_month}/month")
            print(f"ROI: {strategy.roi_estimate}")
            print(f"Brand building: {'✅ Yes' if strategy.brand_building else '❌ No'}")

            print(f"\nBest for:")
            for item in strategy.best_for[:3]:
                print(f"  ✓ {item}")

            print(f"\nNot recommended for:")
            for item in strategy.not_recommended_for[:2]:
                print(f"  ✗ {item}")
            print("\n")

    @staticmethod
    def get_recommendation_prompt() -> str:
        """Return prompt for user input"""
        return """
╔══════════════════════════════════════════════════════════════════╗
║  ASCM GTM STRATEGY SELECTOR                                      ║
║  Answer a few questions to get personalized recommendations      ║
╚══════════════════════════════════════════════════════════════════╝

Please provide the following information:

1. Company name?
   (e.g., "ASCM", "MyStartup")

2. How old is your company? (in months)
   (e.g., 2, 6, 12)

3. How many people in your team?
   (e.g., 2, 5, 20)

4. What stage is your product?
   Options: beta, production, mature
   (e.g., "beta")

5. How many current customers do you have?
   (e.g., 0, 5, 10)

6. What's your current brand awareness?
   Options: none, low, medium, high
   (e.g., "none")

7. Current monthly revenue? (in dollars)
   (e.g., 0, 5000, 50000)

8. Timeline to revenue?
   Options: urgent (< 2 weeks), 3_months, 6_months, 1_year
   (e.g., "6_months")
"""


def analyze_strategy(user_answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function: Takes user answers and returns strategy recommendation
    """

    # Create profile from answers
    profile = GTMStrategyPlanner.create_profile_from_answers(user_answers)

    # Get recommendation
    recommendation = GTMStrategySelector.recommend_strategy(profile)

    # Add strategic advice
    recommendation["advice"] = _generate_strategic_advice(profile, recommendation["recommended"])

    return recommendation


def _generate_strategic_advice(profile: CompanyProfile, strategy: str) -> str:
    """Generate strategic advice based on profile and recommended strategy"""

    advice = f"""
╔══════════════════════════════════════════════════════════════════╗
║  RECOMMENDED STRATEGY: {strategy.upper()}
╚══════════════════════════════════════════════════════════════════╝

IMPLEMENTATION PLAN:
"""

    if strategy == "social_first":
        advice += """
WEEK 1-2: Build Social Presence
├─ Generate 18 social posts (10 LinkedIn, 8 Twitter, 2 Dev.to)
├─ Schedule in Buffer
└─ Goal: 5,000-16,000 impressions, 150-200 warm leads

WEEK 2-3: Start Email Campaign
├─ Generate warm email sequences (25 leads)
├─ Send via Smartlead (references their posts)
├─ Expected: 45-55% open rate, 3-5% booking rate

WEEK 3+: Scale & Monitor
├─ Handle replies automatically
├─ Book meetings via Cal.com
├─ Track metrics: reach, open rate, booking rate

EXPECTED RESULTS:
├─ Month 1: 75-115 meetings
├─ Brand awareness: ✅ Established
├─ Cost: $119/month
├─ ROI: 8,000-19,000%
"""

    elif strategy == "email_direct":
        advice += """
WEEK 1: Discover & Sequence
├─ Discover 25-35 leads via OpenOutreach
├─ Generate cold email sequences (3-4 emails)
└─ Set up Smartlead

WEEK 1-2: Deploy
├─ Send 175+ cold emails
├─ Expected: 20-25% open rate, 2-3% click rate
├─ Expected: 0.5-1% response rate

WEEK 2+: Handle Replies
├─ Classify responses (interested/objection/negative)
├─ Send follow-ups
├─ Book meetings

EXPECTED RESULTS:
├─ Month 1: 3-7 meetings
├─ Brand awareness: ❌ No
├─ Cost: $99/month
├─ ROI: 50-150%

⚠️  NOTE: This is faster but lower conversion.
Consider switching to social-first if results are poor.
"""

    elif strategy == "aggressive":
        advice += """
WEEK 1: Deploy Both
├─ Generate social content (18 posts)
├─ Generate cold email sequences (25 leads)
└─ Schedule in Buffer + Smartlead (simultaneously)

WEEK 1-2: Social Warming + Email Outreach
├─ Social posts building awareness
├─ Cold emails going out
├─ Warm emails (from social leads) also starting

WEEK 2+: Scale
├─ Increase daily leads to 50-100
├─ Double email volume
├─ Monitor both channels

EXPECTED RESULTS:
├─ Month 1: 100-150 meetings
├─ Brand awareness: ✅ Rapidly established
├─ Cost: $219/month
├─ ROI: 5,000-15,000%

⚠️  WARNING: This requires:
    • Large budget ($500k+ marketing/year)
    • Dedicated ops person
    • Email/social monitoring
"""

    return advice


# Export for use in campaigns
__all__ = [
    "CompanyProfile",
    "GTMStrategy",
    "GTMStrategySelector",
    "GTMStrategyPlanner",
    "analyze_strategy",
]

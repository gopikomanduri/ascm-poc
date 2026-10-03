"""
AdAgent: Paid advertising campaigns (Google Ads, LinkedIn Ads, Programmatic)
"""

import json
import logging
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider

logger = logging.getLogger(__name__)


class AdAgent(BaseAgent):
    """
    Paid Advertising Agent: Designs and manages paid campaigns across
    Google Ads, LinkedIn Ads, and programmatic DSPs. Works in tandem with
    MarketingAgent (content) to drive qualified inbound volume.

    Autonomous capabilities:
    - Campaign structure & targeting optimization
    - Ad copy A/B testing strategy
    - Bid strategy & budget allocation
    - Landing page optimization briefs
    - ROAS tracking & optimization loops
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are a Performance Marketing & Paid Acquisition Specialist.\n"
                "Your mission is to design and optimize paid advertising campaigns that drive\n"
                "qualified inbound volume to the business with positive ROAS (Return on Ad Spend).\n\n"
                "Core Capabilities:\n"
                "1. **Google Ads Strategy**: Search, Display, YouTube targeting & bid strategies.\n"
                "2. **LinkedIn Ads**: Account-based marketing (ABM), lead gen, conversion campaigns.\n"
                "3. **Audience Segmentation**: ICP-based targeting, lookalike modeling, retargeting.\n"
                "4. **Ad Copy & Creative**: Performance-optimized copy, A/B testing framework.\n"
                "5. **Landing Page Brief**: Conversion optimization targets for marketing team.\n"
                "6. **Budget Allocation**: Multi-channel spend optimization based on CAC & ROAS.\n"
                "7. **Measurement Framework**: Attribution, UTM strategy, conversion tracking.\n\n"
                "Output JSON with schema:\n"
                "{\n"
                '  "campaign_structure": {...},\n'
                '  "target_channels": ["Google", "LinkedIn", ...],\n'
                '  "icp_audience_segments": [...],\n'
                '  "ad_copy_variants": [...],\n'
                '  "landing_page_brief": "string",\n'
                '  "budget_allocation": {...},\n'
                '  "monthly_budget_recommended": float,\n'
                '  "estimated_sql_monthly": int,\n'
                '  "target_cac": float,\n'
                '  "measurement_framework": {...}\n'
                "}"
            ),
            provider=provider,
            tier="primary",
        )

    def run(
        self,
        product_thesis: str,
        icp_description: str,
        monthly_budget_usd: float = 5000.0,
        target_cac_usd: float = 200.0,
    ) -> Dict[str, Any]:
        """Design comprehensive paid advertising strategy."""
        prompt = f"""
Product Thesis:
{product_thesis}

Ideal Customer Profile:
{icp_description}

Monthly Budget: ${monthly_budget_usd}
Target CAC (Customer Acquisition Cost): ${target_cac_usd}

Design a multi-channel paid advertising strategy that:
1. Targets ICP across Google Ads (Search + Display), LinkedIn Ads, and programmatic
2. Creates 3-5 ad copy variants per channel with A/B testing plan
3. Segments audiences by buyer persona, company size, intent signals
4. Proposes monthly budget allocation across channels
5. Estimates qualified SQL volume at target CAC
6. Provides landing page optimization brief
7. Sets up attribution & measurement framework
8. Specifies bid strategies & automation rules

Optimize for positive ROAS and qualified lead generation.
"""
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)

        logger.info(
            f"AdAgent completed: targeting {len(data.get('icp_audience_segments', []))} segments, "
            f"${monthly_budget_usd} budget, "
            f"est. {data.get('estimated_sql_monthly', 0)} SQL/month"
        )

        return data

    def design_google_ads_campaign(
        self, target_keywords: List[str], icp_description: str, budget_monthly: float = 2000.0
    ) -> Dict[str, Any]:
        """Design Google Ads search campaign structure."""
        keywords_str = ", ".join(target_keywords)
        prompt = f"""
Target Keywords: {keywords_str}
ICP: {icp_description}
Monthly Budget: ${budget_monthly}

Design a Google Ads search campaign that:
1. Structures keywords into ad groups (3-5 groups)
2. Creates headline & description variants (3 headlines, 2 descriptions each)
3. Proposes bid strategy (target CPA, maximize conversions, or manual?)
4. Specifies negative keywords to exclude
5. Estimates traffic, CTR, conversion rate, and leads
6. Provides landing page recommendations
7. Sets up conversion tracking via UTM parameters

Output JSON with complete campaign structure + copy variations.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def design_linkedin_ads_campaign(
        self, target_titles: List[str], target_companies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Design LinkedIn Ads lead gen or conversion campaign."""
        titles_str = ", ".join(target_titles)
        companies_str = ", ".join(target_companies) if target_companies else "All scales"
        prompt = f"""
Target Job Titles: {titles_str}
Target Companies: {companies_str}

Design a LinkedIn Ads campaign (lead gen or conversion):
1. Campaign objective & format (Sponsored Content, Message Ads, Lead Gen Forms, Conversions)
2. Audience targeting: Job titles, industries, seniority, company size, interests
3. 3-5 creative variants (single-image + carousel options)
4. Headline + body copy for each variant
5. CTA button optimization (Learn More, Sign Up, Get Demo, etc.)
6. Lead form strategy: Which fields to collect, gate level
7. Budget allocation & timeline
8. Estimated leads/conversions per 1000 impressions (eCPL/eCPC)

Output JSON with targeting, creative, and measurement strategy.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def design_abm_targeting_strategy(
        self, target_accounts: List[str], personas_per_account: List[str]
    ) -> Dict[str, Any]:
        """Design Account-Based Marketing (ABM) targeting across paid channels."""
        accounts_str = ", ".join(target_accounts)
        personas_str = ", ".join(personas_per_account)
        prompt = f"""
Target Enterprise Accounts: {accounts_str}
Personas per Account: {personas_str}

Design an Account-Based Marketing (ABM) strategy:
1. Account segmentation (tier 1/2/3 based on revenue potential)
2. Persona mapping (who are the stakeholders at each account?)
3. Multi-touch channel orchestration (Google Ads, LinkedIn, email, display retargeting)
4. Personalized messaging per persona & account
5. Coordination with sales team (handoff criteria, deal acceleration)
6. Budget allocation: $ per account tier
7. Success metrics: Account engagement, pipeline influence, deal velocity
8. Timeline: 90-180 day campaign progression

Output JSON with ABM framework, audience targeting, and channel orchestration.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

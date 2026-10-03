"""
MarketingAgent: Technical content, architecture breakdowns, and SEO-driven growth
"""

import json
import logging
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider

logger = logging.getLogger(__name__)


class MarketingAgent(BaseAgent):
    """
    Technical Marketing Agent: Generates architecture breakdowns, technical deep-dives,
    SEO briefs, and social media content to establish thought leadership and drive
    organic inbound interest.

    Uses ai-marketing-skills framework for:
    - Technical content generation (blog posts, architecture explainers)
    - SEO keyword research & brief generation
    - Social media content (LinkedIn, Twitter, Dev.to)
    - Competitor battlecards based on technical differentiation
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are a Technical Growth & Content Strategist specializing in developer-first GTM.\n"
                "Your mission is to generate high-signal technical content that drives organic inbound interest,\n"
                "establishes domain authority, and converts engineers & architects into qualified leads.\n\n"
                "Core Capabilities:\n"
                "1. **Technical Breakdowns**: Architecture explainers, performance benchmarks, design deep-dives.\n"
                "2. **SEO Strategy**: Keyword research, content briefs, long-form optimization targets.\n"
                "3. **Social Content**: LinkedIn posts, Twitter/X threads, Dev.to articles, HN submissions.\n"
                "4. **Competitor Analysis**: Technical differentiation, battlecards, positioning.\n"
                "5. **Content Calendar**: Monthly editorial plan with mix of thought leadership & announcements.\n"
                "6. **Inbound Funnel**: Blog → Newsletter → Webinar → Sales Handoff.\n\n"
                "Output JSON with schema:\n"
                "{\n"
                '  "content_pillars": ["pillar1", "pillar2"],\n'
                '  "technical_breakdown": "markdown string",\n'
                '  "seo_brief": {keywords: [...], title: "...", outline: "..."},\n'
                '  "social_posts": [{platform: "...", content: "...", cta: "..."}],\n'
                '  "monthly_calendar": [...],\n'
                '  "estimated_organic_reach_monthly": int,\n'
                '  "competitor_battlecards": [...]\n'
                "}"
            ),
            provider=provider,
            tier="primary",
        )

    def run(
        self,
        product_thesis: str,
        technical_specs: Optional[Dict[str, Any]] = None,
        competitor_landscape: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive technical marketing strategy & content."""
        specs_json = json.dumps(technical_specs or {}, indent=2)
        prompt = f"""
Product Thesis:
{product_thesis}

Technical Specifications (performance, architecture, stack):
{specs_json}

Competitor Landscape:
{competitor_landscape or 'No specific competitors provided; infer from product type'}

Generate a technical marketing playbook that includes:
1. **Content Pillars**: 3-5 core themes for organic content
2. **Technical Breakdown**: 500-word deep-dive on core architecture/innovation
3. **SEO Attack**: Target 10-20 keywords with content brief
4. **Social Content**: 5 LinkedIn posts + 5 Twitter threads + 2 Dev.to articles
5. **Competitor Analysis**: How we position differently vs legacy/incumbents
6. **30-Day Editorial Calendar**: Publishing schedule with mix & CTAs
7. **Estimated Reach**: Monthly impressions, inbound SQL potential

Optimize for developer/architect audience with technical credibility & authenticity.
"""
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)

        logger.info(
            f"MarketingAgent completed: {len(data.get('content_pillars', []))} pillars, "
            f"{len(data.get('social_posts', []))} social posts, "
            f"est. {data.get('estimated_organic_reach_monthly', 0)} monthly reach"
        )

        return data

    def generate_seo_brief(
        self, target_keyword: str, competitive_landscape: str
    ) -> Dict[str, str]:
        """Generate SEO content brief for target keyword."""
        prompt = f"""
Target Keyword: {target_keyword}
Competitive Landscape: {competitive_landscape}

Generate a comprehensive SEO brief optimized for ranking on {target_keyword}.

Provide:
1. **Intent Analysis**: What is the searcher trying to solve?
2. **Search Volume**: Estimated monthly searches
3. **Keyword Cluster**: 5-10 related keywords to target in content
4. **Content Outline**: 8-10 section headers
5. **Target Word Count**: 2000-3500 words
6. **Internal Link Strategy**: 3-5 internal link opportunities
7. **Featured Snippet Opportunity**: If yes, how to optimize
8. **Estimated Timeline**: Months to rank on first page
9. **CTA**: Optimal call-to-action for conversion

Output JSON with all above fields.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def generate_technical_post(
        self, topic: str, target_audience: str = "CTOs/VP Engineering"
    ) -> Dict[str, str]:
        """Generate LinkedIn/Twitter technical thought leadership post."""
        prompt = f"""
Topic: {topic}
Target Audience: {target_audience}

Generate a technical thought leadership post optimized for {target_audience}.

For LinkedIn (2000 char limit):
- Hook: Challenge incumbent assumptions or share fresh insight
- Core idea: Technical depth with actionable perspective
- CTA: Drive to blog, whitepaper, or calendar link

For Twitter/X (280 char limit):
- Punchy hook with technical substance
- 3-5 follow-up threads with depth
- Engagement hooks (quote, question, debate)

Output JSON with:
- linkedin_post: string
- twitter_hook: string
- twitter_threads: array of strings
- estimated_reach: int (LinkedIn)
- engagement_cta: string
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def analyze_competitor_positioning(
        self, our_thesis: str, competitor_names: List[str]
    ) -> Dict[str, Any]:
        """Analyze competitor positioning and identify differentiation angles."""
        competitors = ", ".join(competitor_names)
        prompt = f"""
Our Product Thesis:
{our_thesis}

Key Competitors: {competitors}

Conduct technical positioning analysis:
1. **Competitor Profiles**: Features, positioning, ICP, GTM
2. **Differentiation Angles**: Where we win technically
3. **Red Flags**: Where competitors are stronger
4. **Messaging Framework**: How to position us uniquely
5. **Battlecards**: 1-pager per competitor with talking points
6. **Market Positioning**: Where we fit in the landscape (leader/challenger/niche)
7. **Price Positioning**: Estimated price points vs competitors

Output comprehensive JSON with all above fields + competitive advantage matrix.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

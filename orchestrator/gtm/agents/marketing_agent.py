"""
MarketingAgent: Technical content, architecture breakdowns, and SEO-driven growth
"""

import json
import logging
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider, parse_json_lenient
from orchestrator.gtm.strategy.content_variety import (PostHistory, assign_angles, plan_block, material_block,
                                                        load_material, variety_report)
from orchestrator.gtm.strategy.claims_guard import (GROUNDING_RULES, load_citable_facts, facts_block,
                                          audit_payload, audit_text, blocking_issues, summarize, strip_placeholders)

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
                "You are a Startup Growth & Content Strategist specializing in developer-led products for founders and entrepreneurs.\n"
                "Your mission is to generate high-signal, engaging, authentic content that empowers first-time entrepreneurs and builders,\n"
                "establishes authority, resonates with founder pain points, and drives organic inbound interest.\n\n"
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
                + GROUNDING_RULES
            ),
            provider=provider,
            tier="primary",
        )
        self.temperature = 0.9   # creative copy: the 0.1 default makes every post sound the same

    def run(
        self,
        product_thesis: str,
        technical_specs: Optional[Dict[str, Any]] = None,
        competitor_landscape: Optional[str] = None,
        verified_facts: Optional[str] = None,
        target_audience: str = "first-time entrepreneurs",
    ) -> Dict[str, Any]:
        """Generate comprehensive technical marketing strategy & content tailored to target audience."""
        specs_json = json.dumps(technical_specs or {}, indent=2)
        facts = verified_facts if verified_facts is not None else load_citable_facts()
        history = PostHistory()
        plan = assign_angles(12, history)   # 5 LinkedIn + 5 Twitter + 2 articles, each its own angle + hook
        prompt = f"""
Target Audience: {target_audience}

Audience Mindset & Key Pain Points:
- First-time entrepreneurs, solo founders, and early-stage startup builders need extreme leverage, rapid execution, and capital efficiency.
- Major fears: Burning runway on expensive agencies ($50k-$100k+), building a fragile prototype that requires a total rewrite, getting trapped in code instead of talking to customers and validating demand.
- Voice & Tone: Founder-to-founder, authentic, empowering, candid, highly practical. No corporate buzzwords and NO dry internal bug tickets (e.g. do not write posts about internal garbage collection or low-level file prefixes). Focus on the founder journey, shipping fast without technical debt, and building with sanity.

Product Thesis:
{product_thesis}

Technical Specifications:
{specs_json}

Competitor Landscape:
{competitor_landscape or 'No specific competitors provided; infer from product type'}
{facts_block(facts)}{material_block(load_material())}{plan_block(plan)}
Generate a high-impact marketing playbook tailored specifically for {target_audience}.

CRITICAL FORMATTING INSTRUCTION — KEEP EVERYTHING SIMPLE, SHORT, AND CRISP:
- No walls of text. No academic or corporate jargon.
- Format for fast mobile reading with generous line breaks (1-2 sentences per line/paragraph).
- **LinkedIn Posts (50-80 words max)**:
  • Line 1: Killer hook (pointed question or relatable founder trap).
  • Line 2-3: The hidden pain or reality (coding in isolation, burning runway, fragile MVPs).
  • Line 4-5: The simple fix (ASCM's 5 specialized agents, mentor alert, human approval gate).
  • Line 6: Sharp, memorable punchline (e.g. "Stop writing code nobody asked for. Start validating.").
- **Twitter/X Posts (under 160 characters)**:
  • 1-2 ultra-crisp, memorable lines that punch above their weight.
- **Articles (under 250 words)**:
  • Fast-paced intro, 3-4 bullet takeaways, crisp conclusion.

Playbook Deliverables:
1. **Content Pillars**: 3-5 punchy themes (e.g. Solo Founder Leverage, The Isolation Trap, Safe AI with Human Gates).
2. **Technical Breakdown**: Concise overview (under 250 words) explaining how 5 agents + human gates give founders unfair leverage without tech debt.
3. **SEO Attack**: 10-15 high-intent queries first-time founders search for (e.g. "how to build MVP without agency", "AI co-founder for coding").
4. **Social Content**: 5 LinkedIn posts + 5 Twitter/X posts + 2 Dev.to articles. Every single post must be simple, short, and crisp.
5. **Competitor Analysis**: 3 concise battlecards (vs dev agencies, autocomplete, cloud black-boxes).
6. **30-Day Editorial Calendar**: Clean weekly publishing schedule with topics & CTAs.
7. **Estimated Reach**: set estimated_organic_reach_monthly to null (do not guess reach).
"""
        raw = self.call(prompt, json_mode=True)
        data = parse_json_lenient(raw)
        report = variety_report([p.get("content", "") for p in data.get("social_posts", []) if isinstance(p, dict)], history)
        if report["needs_regeneration"] or report["posts"] < 8:
            logger.warning(f"MarketingAgent output is repetitive or short ({report['posts']} posts) ({report['max_pairwise_overlap']} max overlap, "
                           f"openers={report['repeated_openers']}); retrying once with feedback.")
            raw = self.call(prompt + f"\nYour previous attempt had only {report['posts']} social posts or repeated itself. "
                            "Return ALL of: 5 LinkedIn posts, 5 Twitter threads, 2 Dev.to articles in social_posts, and make "
                            "every post a DIFFERENT point from its own angle.", json_mode=True)
            data = parse_json_lenient(raw)
            report = variety_report([p.get("content", "") for p in data.get("social_posts", []) if isinstance(p, dict)], history)
        data["variety_report"] = report
        data["variety_plan"] = [{"post": i + 1, "angle": a, "hook": h} for i, (a, h) in enumerate(plan)]
        if any(i["type"] == "placeholder" for i in audit_payload(data, facts)):
            data = strip_placeholders(data) | {"variety_report": data["variety_report"], "variety_plan": data["variety_plan"]}
            auto_fixed = "removed unresolved placeholders such as [Link]"
        else:
            auto_fixed = ""
        issues = audit_payload(data, facts)
        data["content_audit"] = {"issues": issues, "blocking": bool(blocking_issues(issues)), "auto_fixed": auto_fixed}
        if issues:
            logger.warning(f"MarketingAgent content flagged: {summarize(issues)}")

        logger.info(
            f"MarketingAgent completed: {len(data.get('content_pillars', []))} pillars, "
            f"{len(data.get('social_posts', []))} social posts, "
            f"{len(issues)} content flags"
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
        return parse_json_lenient(raw)

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
        return parse_json_lenient(raw)

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
        return parse_json_lenient(raw)

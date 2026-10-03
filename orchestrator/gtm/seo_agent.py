"""
SEOAgent: Organic search optimization and content strategy
"""

import json
import logging
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider

logger = logging.getLogger(__name__)


class SEOAgent(BaseAgent):
    """
    Search Engine Optimization Agent: Drives organic inbound traffic through
    keyword research, technical SEO audits, content strategy, and backlink
    acquisition planning.

    Autonomous capabilities:
    - Keyword research & opportunity mapping
    - Content gap analysis vs competitors
    - Technical SEO audit recommendations
    - Internal linking strategy
    - Backlink acquisition targets
    - Core Web Vitals optimization brief
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            system_instruction=(
                "You are an SEO Strategist & Organic Growth Specialist.\n"
                "Your mission is to systematically build organic visibility and inbound traffic\n"
                "through technical SEO, content strategy, and backlink acquisition.\n\n"
                "Core Capabilities:\n"
                "1. **Keyword Research**: High-volume, high-intent keyword identification.\n"
                "2. **Content Gap Analysis**: Competitors' content coverage vs. our plan.\n"
                "3. **Technical SEO**: Site speed, crawlability, indexation, Core Web Vitals.\n"
                "4. **On-Page Optimization**: Title tags, meta descriptions, heading structure, schema markup.\n"
                "5. **Internal Linking**: Strategy to pass authority to high-value pages.\n"
                "6. **Backlink Strategy**: Acquisition targets, guest post opportunities, PR angles.\n"
                "7. **Measurement Framework**: Ranking tracking, organic traffic attribution, ROAS.\n\n"
                "Output JSON with schema:\n"
                "{\n"
                '  "keyword_clusters": [...],\n'
                '  "content_gap_analysis": {...},\n'
                '  "technical_seo_audit": [...],\n'
                '  "on_page_strategy": {...},\n'
                '  "internal_linking_map": {...},\n'
                '  "backlink_targets": [...],\n'
                '  "estimated_organic_traffic_6mo": int,\n'
                '  "measurement_framework": {...},\n'
                '  "12_month_ramp_forecast": [...]\n'
                "}"
            ),
            provider=provider,
            tier="primary",
        )

    def run(
        self, product_thesis: str, competitor_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive SEO strategy."""
        competitors = ", ".join(competitor_domains) if competitor_domains else "Industry leaders"
        prompt = f"""
Product Thesis:
{product_thesis}

Competitor Domains for Analysis: {competitors}

Generate a 12-month SEO strategy that includes:
1. **Keyword Research**: 30-50 high-intent keywords mapped to buyer journey
2. **Keyword Clusters**: Organize into content clusters (topic + pillar pages)
3. **Content Gap**: Compare our content vs competitors' coverage
4. **Technical SEO Audit**: Site structure, speed, crawlability recommendations
5. **On-Page Optimization**: Title tag formula, meta description templates, schema markup strategy
6. **Internal Linking**: Strategy to connect related content + distribute authority
7. **Backlink Strategy**: 10-15 acquisition targets (guest posts, PR, resource pages)
8. **Content Calendar**: 12-month publishing schedule aligned to keyword clusters
9. **Measurement Framework**: Tracking setup for rankings, traffic, conversions
10. **Traffic Forecast**: Month-by-month estimated organic traffic ramp (conservative, realistic, optimistic)

Optimize for developer/technical audience with authority-building content.
"""
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)

        logger.info(
            f"SEOAgent completed: {len(data.get('keyword_clusters', []))} keyword clusters, "
            f"est. {data.get('estimated_organic_traffic_6mo', 0)} organic traffic in 6mo"
        )

        return data

    def conduct_keyword_research(
        self, product_category: str, icp_persona: str, search_volume_threshold: int = 50
    ) -> List[Dict[str, Any]]:
        """Conduct keyword research and identify high-opportunity terms."""
        prompt = f"""
Product Category: {product_category}
Target Persona: {icp_persona}
Minimum Search Volume: {search_volume_threshold}

Conduct keyword research that identifies:
1. **Head Terms** (high volume, high competition): 5-10 keywords
   - Example: "payment processing", "microservices architecture"
2. **Torso Keywords** (medium volume, medium competition): 10-15 keywords
   - Example: "golang payment gateway", "distributed transaction patterns"
3. **Long-Tail Keywords** (low volume, low competition, high intent): 15-20 keywords
   - Example: "how to implement 3d secure 2.0 golang", "temporal.io workflow retry patterns"

For each keyword, provide:
- Keyword phrase
- Estimated monthly search volume
- Keyword difficulty / competition (1-100 scale)
- Search intent (informational, navigational, commercial, transactional)
- Related search queries
- Content type recommendation (blog post, guide, video, demo, etc.)
- Opportunity score (0-100)

Output JSON array of keyword objects sorted by opportunity score descending.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def analyze_content_gap(
        self, target_keywords: List[str], competitor_domains: List[str]
    ) -> Dict[str, Any]:
        """Analyze content gap vs competitors for target keywords."""
        keywords_str = ", ".join(target_keywords)
        competitors_str = ", ".join(competitor_domains)
        prompt = f"""
Target Keywords: {keywords_str}
Competitor Domains: {competitors_str}

Analyze content gap:
1. **Our Current Content**: What content do we have for these keywords?
2. **Competitor Content**: What content exists on competitor domains? (simulated)
3. **Gap Analysis**: Where are we weak vs competitors?
4. **Content Opportunities**: Keywords with no good existing content (or low-quality content)
5. **Quick Wins**: Keywords we could rank for with existing content optimization
6. **New Content Needed**: Keywords requiring brand new content creation
7. **Content Depth Analysis**: Are competitors' content deep and authoritative? Or shallow?

Output JSON with gap analysis matrix showing:
- Keyword
- Our coverage (None, Thin, Good, Excellent)
- Top competitor coverage
- Gap opportunity score
- Recommended action (optimize existing, create new, expand)
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def audit_technical_seo(self) -> List[Dict[str, str]]:
        """Generate technical SEO audit recommendations."""
        prompt = """
Conduct a technical SEO audit across common areas:
1. **Site Architecture**: URL structure, sitemap organization, breadcrumbs
2. **Performance**: Page speed (LCP, FID, CLS), Core Web Vitals targets
3. **Crawlability**: robots.txt optimization, XML sitemap coverage, crawl budget
4. **Indexation**: Canonical tags, noindex/nofollow strategy, duplicate content
5. **Mobile**: Responsive design, mobile page speed, touch-friendly UI
6. **Schema Markup**: JSON-LD for organization, articles, FAQs, breadcrumbs
7. **Hreflang**: International/multi-language implementation (if applicable)
8. **Security**: HTTPS enforcement, CSP headers, security policies

For each area, provide:
- Current state (✅ Good, ⚠️ Needs improvement, ❌ Critical issue)
- Recommendation
- Priority (High, Medium, Low)
- Estimated impact on rankings
- Implementation effort (hours)

Output JSON array of audit findings sorted by impact × priority.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def plan_backlink_acquisition(
        self, target_keywords: List[str], brand_name: str
    ) -> Dict[str, Any]:
        """Plan backlink acquisition strategy."""
        keywords_str = ", ".join(target_keywords)
        prompt = f"""
Brand: {brand_name}
Target Keywords: {keywords_str}

Create a backlink acquisition strategy:
1. **Link Opportunity Types**:
   - Guest post opportunities (technical blogs, developer publications)
   - Resource page links (curated tool lists, dev tools directories)
   - PR opportunities (press coverage, awards, announcements)
   - Broken link reclamation (find broken competitor backlinks, replace with ours)
   - Community links (GitHub, Stack Overflow, Reddit, HackerNews)
   - Partnerships & integrations (API partners, marketplace listings)

2. **Target Sites**: Specific websites/publications where we should secure links
   - Authority score (DA 10-100 scale)
   - Relevance to our keywords
   - Contact email / submission process
   - Estimated win probability

3. **Link Building Calendar**: Month-by-month targets
   - Month 1: 5-10 guest posts
   - Month 2: 5 resource page links
   - Month 3: 10 community mentions
   - etc.

4. **Content Angles**: What stories/angles do we pitch?
   - "How we scaled to 10K TPS" → technical deep-dive
   - "Open-source contribution" → developer goodwill
   - "Industry benchmarking" → authoritative research

Output comprehensive JSON with link targets, contact info, and pitching strategy.
"""
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

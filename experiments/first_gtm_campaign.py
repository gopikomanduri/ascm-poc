#!/usr/bin/env python3
"""
ASCM First GTM Experiment: Market ASCM to CTOs using ASCM's own GTM agents

This script orchestrates the end-to-end experiment:
1. SalesAgent: Discover leads + ship sequences
2. MarketingAgent: Generate content strategy
3. AdAgent: Create paid campaigns
4. SEOAgent: Plan organic growth
5. Monitor: Track results daily

Usage:
    python experiments/first_gtm_campaign.py
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Import ASCM agents
from orchestrator.gtm.sales_agent import SalesAgent
from orchestrator.gtm.marketing_agent import MarketingAgent
from orchestrator.gtm.ad_agent import AdAgent
from orchestrator.gtm.seo_agent import SEOAgent
from orchestrator.models.intent import ProjectIntentRequest, TeamComposition


# ============================================================================
# EXPERIMENT CONFIGURATION
# ============================================================================

EXPERIMENT_CONFIG = {
    "name": "ASCM First GTM Experiment",
    "date_started": datetime.now().isoformat(),
    "duration_days": 14,
    "budget_usd": 200,

    "product": {
        "name": "ASCM",
        "tagline": "Autonomous Full-Stack Development Platform",
        "thesis": """
        ASCM automates the entire product development lifecycle:
        - Auto-discover product requirements from founders
        - Generate high-level architecture (HLD) and low-level design (LLD)
        - Implement full-stack code with comprehensive tests
        - Run security audits and quality validation
        - Deploy to production
        - Launch GTM campaigns autonomously

        Result: Ship production-ready features in 2-3 weeks instead of 2-3 months.
        Ideal for: MVP launches, features on deadline, rapid scaling.
        """,
    },

    "icp": {
        "title": "CTO / VP Engineering",
        "companies": "Series B-D SaaS ($20M-$500M ARR)",
        "team_size": "50-500 people",
        "pain": "Need to launch features faster, reduce cross-repo coordination, accelerate time-to-market",
        "tech_stack": "Go/Python + PostgreSQL + Microservices",
        "geography": "US/EU tech hubs",
        "budget": "$5K-50K/quarter for dev tools",
    },

    "founder_cal": "https://cal.com/gopi/ascm-demo-15min",
    "daily_lead_quota": 25,
    "campaign_duration_days": 14,
}


# ============================================================================
# PHASE 1: SALES AGENT - LEAD DISCOVERY & OUTBOUND
# ============================================================================

async def run_sales_agent_phase():
    """Execute SalesAgent: discover leads + design sequences + dispatch outbound"""
    logger.info("=" * 80)
    logger.info("PHASE 1: SALES AGENT - Lead Discovery & Outbound Sequences")
    logger.info("=" * 80)

    agent = SalesAgent()

    result = agent.run(
        product_thesis=EXPERIMENT_CONFIG["product"]["thesis"],
        icp_description=json.dumps(EXPERIMENT_CONFIG["icp"], indent=2),
        cal_com_booking_link=EXPERIMENT_CONFIG["founder_cal"],
        daily_quota=EXPERIMENT_CONFIG["daily_lead_quota"],
    )

    logger.info("\n✅ SalesAgent Execution Complete")
    logger.info(f"   Leads discovered: {result.get('leads_discovered', 0)}")
    logger.info(f"   Verified emails: {result.get('verified_emails', 0)}")
    logger.info(f"   First sequence dispatched: {result.get('first_sequence_dispatched', False)}")
    logger.info(f"   Est. meetings week 1: {result.get('estimated_meeting_bookings_week1', 0)}")

    return result


# ============================================================================
# PHASE 2: MARKETING AGENT - CONTENT STRATEGY
# ============================================================================

async def run_marketing_agent_phase():
    """Execute MarketingAgent: generate content strategy + social posts"""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: MARKETING AGENT - Content Strategy & Social Posts")
    logger.info("=" * 80)

    agent = MarketingAgent()

    result = agent.run(
        product_thesis=EXPERIMENT_CONFIG["product"]["thesis"],
        technical_specs={
            "orchestration_throughput": "100K events/sec",
            "deployment": "Kubernetes-native + Docker",
            "backend_stack": "Go + gRPC + PostgreSQL",
            "frontend_stack": "TypeScript + React",
            "workflow_engine": "Temporal.io",
            "tps_capability": "10K+ concurrent projects",
            "latency_p99": "<100ms for most operations",
        },
        competitor_landscape="GitHub Copilot (code only), Vercel (deployment), Stripe (payments), Traditional consultants",
    )

    logger.info("\n✅ MarketingAgent Execution Complete")
    logger.info(f"   Content pillars: {len(result.get('content_pillars', []))}")
    logger.info(f"   Social posts ready: {len(result.get('social_posts', []))}")
    logger.info(f"   SEO briefs: {result.get('seo_brief', {}).get('keywords', [])}")

    return result


# ============================================================================
# PHASE 3: AD AGENT - PAID CAMPAIGNS
# ============================================================================

async def run_ad_agent_phase():
    """Execute AdAgent: create Google Ads + LinkedIn Ads campaigns"""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: AD AGENT - Paid Campaign Design")
    logger.info("=" * 80)

    agent = AdAgent()

    result = agent.run(
        product_thesis=EXPERIMENT_CONFIG["product"]["thesis"],
        icp_description=json.dumps(EXPERIMENT_CONFIG["icp"], indent=2),
        monthly_budget_usd=EXPERIMENT_CONFIG["budget_usd"],
        target_cac_usd=50,  # Target $50 cost per acquisition
    )

    logger.info("\n✅ AdAgent Execution Complete")
    logger.info(f"   Target channels: {result.get('target_channels', [])}")
    logger.info(f"   Budget allocation: {result.get('budget_allocation', {})}")
    logger.info(f"   Est. SQL/month: {result.get('estimated_sql_monthly', 0)}")
    logger.info(f"   Target CAC: ${result.get('target_cac', 0)}")

    return result


# ============================================================================
# PHASE 4: SEO AGENT - ORGANIC STRATEGY
# ============================================================================

async def run_seo_agent_phase():
    """Execute SEOAgent: keyword research + content strategy + backlinks"""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 4: SEO AGENT - Organic Growth Strategy")
    logger.info("=" * 80)

    agent = SEOAgent()

    result = agent.run(
        product_thesis=EXPERIMENT_CONFIG["product"]["thesis"],
        competitor_domains=["github.com", "vercel.com", "stripe.com"],
    )

    logger.info("\n✅ SEOAgent Execution Complete")
    keyword_clusters = result.get('keyword_clusters', [])
    logger.info(f"   Keyword clusters: {len(keyword_clusters)}")
    if keyword_clusters:
        for cluster in keyword_clusters[:3]:
            logger.info(f"     - {cluster.get('cluster', 'Unknown')}: {len(cluster.get('keywords', []))} keywords")
    logger.info(f"   Est. organic traffic 6mo: {result.get('estimated_organic_traffic_6mo', 0)}")

    return result


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

async def main():
    """Run complete GTM experiment"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "🚀 ASCM FIRST GTM EXPERIMENT 🚀" + " " * 26 + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + f"  Marketing ASCM to CTOs using ASCM's own GTM Engine".ljust(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + f"  Budget: ${EXPERIMENT_CONFIG['budget_usd']} | Duration: {EXPERIMENT_CONFIG['campaign_duration_days']} days | Goal: 5-8 meetings".ljust(78) + "║")
    logger.info("╚" + "=" * 78 + "╝")

    try:
        # Run all phases in parallel where possible
        logger.info("\n📋 Experiment Configuration:")
        logger.info(f"   Product: {EXPERIMENT_CONFIG['product']['name']}")
        logger.info(f"   ICP: {EXPERIMENT_CONFIG['icp']['title']} at {EXPERIMENT_CONFIG['icp']['companies']}")
        logger.info(f"   Daily lead quota: {EXPERIMENT_CONFIG['daily_lead_quota']}")
        logger.info(f"   Founder Cal: {EXPERIMENT_CONFIG['founder_cal']}")

        # Phase 1 & 2 can run in parallel
        logger.info("\n🔄 Starting Phases 1-2 (Sales & Marketing in parallel)...")
        sales_task = asyncio.create_task(run_sales_agent_phase())
        marketing_task = asyncio.create_task(run_marketing_agent_phase())

        sales_result = await sales_task
        marketing_result = await marketing_task

        # Phase 3: Ads (sequential, builds on marketing)
        logger.info("\n🔄 Starting Phase 3 (Ads)...")
        ad_result = await run_ad_agent_phase()

        # Phase 4: SEO (sequential)
        logger.info("\n🔄 Starting Phase 4 (SEO)...")
        seo_result = await run_seo_agent_phase()

        # Compile results
        experiment_results = {
            "experiment_name": EXPERIMENT_CONFIG["name"],
            "date_completed": datetime.now().isoformat(),
            "phases": {
                "sales": sales_result,
                "marketing": marketing_result,
                "ads": ad_result,
                "seo": seo_result,
            },
            "summary": {
                "leads_discovered": sales_result.get("leads_discovered", 0),
                "verified_emails": sales_result.get("verified_emails", 0),
                "estimated_meetings_week1": sales_result.get("estimated_meeting_bookings_week1", 0),
                "content_pillars": len(marketing_result.get("content_pillars", [])),
                "social_posts_ready": len(marketing_result.get("social_posts", [])),
                "ad_channels": len(ad_result.get("target_channels", [])),
                "budget_allocated": EXPERIMENT_CONFIG["budget_usd"],
            }
        }

        # Save results
        results_file = Path("experiments/results") / f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(experiment_results, f, indent=2)

        logger.info("\n" + "=" * 80)
        logger.info("🎉 EXPERIMENT SETUP COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"\n✅ Results saved to: {results_file}")
        logger.info("\n📊 SUMMARY:")
        logger.info(f"   • Leads to contact: {experiment_results['summary']['leads_discovered']}")
        logger.info(f"   • Email sequences: Ready to dispatch")
        logger.info(f"   • Social posts: {experiment_results['summary']['social_posts_ready']} ready to schedule")
        logger.info(f"   • Ad budget: ${experiment_results['summary']['budget_allocated']}")
        logger.info(f"   • Est. meetings (Week 1): {experiment_results['summary']['estimated_meetings_week1']}")

        logger.info("\n🚀 NEXT STEPS:")
        logger.info("   1. ✅ Review generated content and sequences")
        logger.info("   2. ⏳ Deploy landing page")
        logger.info("   3. ⏳ Confirm founder Cal.com link")
        logger.info("   4. ⏳ Launch email sequences (Day 1)")
        logger.info("   5. ⏳ Launch paid ads (Day 4)")
        logger.info("   6. ⏳ Monitor daily: python experiments/monitor_campaign.py")
        logger.info("   7. ⏳ Generate report (Day 14): python experiments/generate_report.py")

        logger.info("\n📅 Campaign Timeline:")
        logger.info("   • Days 1-3: Email sequences + social posts launching")
        logger.info("   • Days 4-5: Paid ads live ($200 spend)")
        logger.info("   • Days 6-10: Monitor replies + book meetings")
        logger.info("   • Days 11-14: Final push + metrics collection")
        logger.info("   • Day 15: Final report generation")

        logger.info("\n" + "=" * 80)
        logger.info("💡 Remember: This validates that ASCM's GTM engine works!")
        logger.info("=" * 80 + "\n")

        return experiment_results

    except Exception as e:
        logger.error(f"\n❌ Experiment failed: {str(e)}", exc_info=True)
        return None


if __name__ == "__main__":
    asyncio.run(main())

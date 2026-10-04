#!/usr/bin/env python3
"""
ASCM Founder GTM Runner: Executes Marketing and Sales agents standalone for ASCM
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from orchestrator.agents.base import _load_dotenv, get_configured_provider
from orchestrator.gtm.marketing_agent import MarketingAgent
from orchestrator.gtm.sales_agent import SalesAgent
from orchestrator.gtm.sales_agent_v2 import SalesAgentV2

_load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ASCM_Founder_GTM")

ASCM_THESIS = """
ASCM (Autonomous Software Creation and Management) is an autonomous full-stack development platform.
It automates the software lifecycle from requirements discovery -> HLD/LLD architecture design -> full-stack implementation -> testing with 98% coverage -> security audit -> production deployment.
It cuts feature delivery cycles from 2-3 months to 2-3 weeks, eliminating the 60% engineering coordination overhead across microservices.
"""

ASCM_SPECS = {
    "backend_stack": "Go + Temporal.io + PostgreSQL",
    "architecture": "Deterministic workflow reconciliation via Outbox pattern and worker isolation",
    "throughput": "10,000+ TPS concurrent execution",
    "latency_p99": "<25ms across microservices",
    "testing_rigor": "98% test coverage, ephemeral Docker sandbox verification, zero-regression guarantee"
}

ASCM_ICP = {
    "title": "CTO / VP Engineering",
    "company_profile": "Series B-D SaaS companies ($20M-$200M ARR)",
    "team_size": "50-500 engineers",
    "primary_pain": "60% of engineering bandwidth lost to cross-repo coordination, architecture review delays, and sprint drag",
    "tech_stack": "Go/Python, Microservices, Kubernetes, PostgreSQL"
}

CAL_COM_LINK = "https://cal.com/gopi/ascm-demo-15min"

def run_founder_gtm():
    logger.info("=" * 80)
    logger.info("🚀 EXECUTING ASCM FOUNDER GTM RUN: MARKETING + SALES AGENTS")
    logger.info("=" * 80)

    provider = get_configured_provider()
    logger.info(f"Using Provider: {provider.provider_name} ({getattr(provider, 'model', 'default')})")

    # 1. RUN MARKETING AGENT
    logger.info("\n📢 [1/2] RUNNING MARKETING AGENT STANDALONE...")
    marketing_agent = MarketingAgent(provider=provider)
    marketing_result = marketing_agent.run(
        product_thesis=ASCM_THESIS,
        technical_specs=ASCM_SPECS,
        competitor_landscape="GitHub Copilot (code-only autocomplete), Vercel (frontend deployment only), Devin / Legacy dev agencies",
    )
    logger.info("✅ Marketing Agent completed successfully!")

    # 2. RUN SALES AGENT V2 (Produces specific leads + full email sequences + decision logs)
    logger.info("\n💼 [2/2] RUNNING SALES AGENT STANDALONE...")
    sales_agent = SalesAgentV2(provider=provider)
    sales_result = sales_agent.run(
        product_thesis=ASCM_THESIS,
        icp_description=json.dumps(ASCM_ICP, indent=2),
        cal_com_booking_link=CAL_COM_LINK,
        daily_quota=5
    )
    logger.info("✅ Sales Agent completed successfully!")

    # Compile Results
    output = {
        "timestamp": datetime.now().isoformat(),
        "product": "ASCM",
        "founder_cal_link": CAL_COM_LINK,
        "marketing_results": marketing_result,
        "sales_results": sales_result,
    }

    results_dir = Path("experiments/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "founder_gtm_run_latest.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"\n🎉 FULL RUN COMPLETE! Output saved to: {out_file}")
    return output

if __name__ == "__main__":
    run_founder_gtm()

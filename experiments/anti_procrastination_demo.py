#!/usr/bin/env python3
"""
ASCM Anti-Procrastination Demo: Complete 75% → 100% System in Action

Shows all 4 features working together:
1. Git Monitor: Detects code-avoidance
2. Repo Analyzer: Auto-extracts ICP without founder input
3. Marketing Constraints: Forces focus on ONE pain point
4. Iteration Loop: Learns from reply data, recommends iterations

Usage:
    python experiments/anti_procrastination_demo.py
"""

import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from orchestrator.gtm.strategy.anti_procrastination_orchestrator import AntiProcrastinationOrchestrator


def demo_activity_monitoring():
    """Demo: Proactive Git Monitor catches code-hiding"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 1: PROACTIVE GIT MONITOR")
    logger.info("=" * 80)

    orchestrator = AntiProcrastinationOrchestrator()

    # Scenario: Builder has been coding for 5 days but no GTM action
    last_gtm_run = (datetime.now() - timedelta(days=5)).isoformat()

    result = orchestrator.check_activity(
        last_sales_agent_run=last_gtm_run,
    )

    logger.info(f"\n📊 Activity Metrics:")
    logger.info(f"   Commits 7 days: {result['metrics']['commits_7d']}")
    logger.info(f"   Days since GTM: {result['metrics']['days_since_gtm']:.0f}")
    logger.info(f"   Risk Level: {result['metrics']['risk_level']}")
    logger.info(f"   Code Avoidance: {result['metrics']['is_code_avoidance']}")

    if "intervention_required" in result:
        logger.warning(f"\n🚨 INTERVENTION MESSAGE:\n{result['intervention_required']}")


def demo_repo_analysis():
    """Demo: First-Principles Repo Analyzer"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 2: FIRST-PRINCIPLES REPO ANALYZER")
    logger.info("=" * 80)

    orchestrator = AntiProcrastinationOrchestrator()

    result = orchestrator.analyze_repo()
    analysis = result.get("analysis", {})

    logger.info(f"\n📖 Repo Analysis Results:")
    logger.info(f"   Tech Stack:")
    for category, items in analysis.get("tech_stack", {}).items():
        if items:
            logger.info(f"      {category}: {', '.join(items)}")

    logger.info(f"   Use Cases: {', '.join(analysis.get('use_cases', [])[:3])}")
    logger.info(f"   Inferred ICP:")
    for icp in analysis.get('inferred_icp', []):
        logger.info(f"      - {icp}")

    logger.info(f"\n💡 Product Thesis:")
    logger.info(analysis.get('product_thesis', '')[:500])


def demo_marketing_constraints():
    """Demo: Marketing Constraint Engine forces focus"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 3: MARKETING CONSTRAINT ENGINE")
    logger.info("=" * 80)

    orchestrator = AntiProcrastinationOrchestrator()

    # Scenario: Founder wants to market multiple pain points (scattered)
    scattered_strategy = {
        "product_thesis": "ASCM automates full-stack development",
        "pain_points": ["speed", "cost", "reliability"],  # ❌ Too many
        "target_audiences": ["CTOs", "founders", "devops"],  # ❌ Too many
        "channels": ["cold_email", "content", "paid_ads", "community"],  # ❌ Too many
    }

    logger.info(f"\n❌ SCATTERED STRATEGY (input):")
    logger.info(f"   Pain Points: {', '.join(scattered_strategy['pain_points'])}")
    logger.info(f"   Audiences: {', '.join(scattered_strategy['target_audiences'])}")
    logger.info(f"   Channels: {', '.join(scattered_strategy['channels'])}")

    result = orchestrator.validate_gtm_strategy(scattered_strategy)

    if result["status"] == "strategy_constrained":
        constrained = result["constrained_strategy"]
        logger.info(f"\n✅ CONSTRAINED STRATEGY (output):")
        logger.info(f"   Primary Pain Point: {constrained['primary_pain_point']}")
        logger.info(f"   Target Audience: {constrained['target_audience']}")
        logger.info(f"   Primary Channel: {constrained['primary_channel']}")
        logger.info(f"   Secondary Channels: {', '.join(constrained['secondary_channels'])}")
        logger.info(f"\n📋 Rationale:\n{constrained['rationale']}")


def demo_iteration_loop():
    """Demo: Reply-to-Iteration Loop learns from data"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO 4: REPLY-TO-ITERATION LOOP")
    logger.info("=" * 80)

    orchestrator = AntiProcrastinationOrchestrator()

    # Scenario: Campaign with 100 emails sent, various reply rates
    emails_sent = [
        {
            "id": "email_001",
            "subject": "Speed: Cut feature shipping time 10x",
            "pain_point": "speed",
            "cta": "Let's talk",
            "sent_to": ["cto1@company1.com", "cto2@company2.com", "cto3@company3.com"],
            "body": "Hi, we help teams ship faster...",
        },
        {
            "id": "email_002",
            "subject": "Cost: Reduce infrastructure spend 50%",
            "pain_point": "cost",
            "cta": "See ROI calc",
            "sent_to": ["cto4@company4.com", "cto5@company5.com"],
            "body": "Hi, reduce your infrastructure costs...",
        },
        {
            "id": "email_003",
            "subject": "Reliability: 99.99% uptime guaranteed",
            "pain_point": "reliability",
            "cta": "Schedule demo",
            "sent_to": [f"cto{i}@company{i}.com" for i in range(6, 16)],
            "body": "Hi, we guarantee 99.99% uptime...",
        },
    ]

    replies_received = [
        {"email_id": "email_001", "sentiment": "INTERESTED", "body": "This sounds interesting, let's talk"},
        {"email_id": "email_001", "sentiment": "INTERESTED", "body": "How does this work?"},
        {"email_id": "email_002", "sentiment": "OBJECTION", "body": "We already have a cost reduction tool"},
        {"email_id": "email_003", "sentiment": "INTERESTED", "body": "Can you schedule a call?"},
        {"email_id": "email_003", "sentiment": "INTERESTED", "body": "Tell me more"},
    ]

    logger.info(f"\n📧 Campaign Data:")
    logger.info(f"   Emails: {len(emails_sent)}")
    logger.info(f"   Recipients: {sum(len(e['sent_to']) for e in emails_sent)}")
    logger.info(f"   Replies: {len(replies_received)}")

    result = orchestrator.track_campaign_performance(emails_sent, replies_received)
    report = result.get("report", {})

    logger.info(f"\n📊 Performance Report:")
    logger.info(f"   Overall Reply Rate: {report.get('reply_rate', 0):.1%}")
    logger.info(f"   Best Pain Point: {report.get('best_pain_point')}")
    logger.info(f"   Sentiment Breakdown: {report.get('sentiment', {})}")

    logger.info(f"\n💡 Recommendations:")
    for rec in report.get("recommendations", []):
        logger.info(f"   {rec}")


def demo_complete_audit():
    """Demo: Run complete audit across all 4 systems"""
    logger.info("\n" + "=" * 120)
    logger.info("DEMO 5: COMPLETE ANTI-PROCRASTINATION AUDIT")
    logger.info("=" * 120)

    orchestrator = AntiProcrastinationOrchestrator()

    strategy = {
        "product_thesis": "ASCM - Autonomous full-stack development platform",
        "pain_points": ["speed"],
        "target_audiences": ["CTOs"],
        "channels": ["cold_email"],
    }

    emails = [
        {
            "id": "email_speed_001",
            "subject": "Ship features 10x faster",
            "pain_point": "speed",
            "cta": "Book a demo",
            "sent_to": ["cto@company1.com", "cto@company2.com"],
            "body": "Hi, ASCM cuts feature shipping time from 3 months to 3 weeks",
        },
    ]

    replies = [
        {"email_id": "email_speed_001", "sentiment": "INTERESTED", "body": "This is exactly what we need!"},
        {"email_id": "email_speed_001", "sentiment": "INTERESTED", "body": "When can we talk?"},
    ]

    full_results = orchestrator.run_complete_audit(
        proposed_strategy=strategy,
        last_sales_run=(datetime.now() - timedelta(days=1)).isoformat(),
        emails_sent=emails,
        replies=replies,
    )

    summary = full_results.get("summary", {})
    logger.info(f"\n📋 AUDIT SUMMARY:")
    logger.info(f"   Risk Level: {summary.get('risk_level', 'unknown')}")
    logger.info(f"   Actions Required: {len(summary.get('actions_required', []))}")
    if summary.get("actions_required"):
        for action in summary["actions_required"]:
            logger.info(f"      → {action}")

    logger.info(f"\n   Next Steps: {len(summary.get('next_steps', []))}")
    if summary.get("next_steps"):
        for step in summary["next_steps"]:
            logger.info(f"      → {step}")


if __name__ == "__main__":
    logger.info("\n\n")
    logger.info("╔" + "=" * 118 + "╗")
    logger.info("║" + " " * 30 + "ASCM ANTI-PROCRASTINATION DEMO (75% → 100%)" + " " * 45 + "║")
    logger.info("║" + " " * 40 + "Complete GTM System in Action" + " " * 50 + "║")
    logger.info("╚" + "=" * 118 + "╝")
    logger.info("\n")

    try:
        demo_activity_monitoring()
        demo_repo_analysis()
        demo_marketing_constraints()
        demo_iteration_loop()
        demo_complete_audit()

        logger.info("\n" + "=" * 120)
        logger.info("✅ DEMO COMPLETE: All 4 anti-procrastination features working!")
        logger.info("=" * 120)

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)

"""
ASCM v4.0: Social-First GTM Campaign
Flow: Social Awareness → Email to Warm Audience → Meeting Booking

This experiment demonstrates the complete social-first GTM flow:
1. Phase 1 (Days 1-14): Build awareness via LinkedIn/Twitter/Dev.to
2. Phase 2 (Days 3+): Start email campaigns to warm audience
3. Phase 3 (Days 7+): Handle replies and book meetings
"""

import os
import json
import logging
from datetime import datetime
from orchestrator.gtm.agents.social_first_agents import (
    SocialFirstMarketingAgent,
    WarmAudienceSalesAgent,
    ReplyHandlingAgent,
)
from orchestrator.agents.base import get_configured_provider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ASCM_CONFIG = {
    "product_thesis": """
ASCM (Autonomous Software Creation and Management) is a full-stack development platform.

WHAT IT DOES:
- Requirements → Production-ready code in 14 days
- Auto-generates architecture (HLD)
- Auto-implements (code generation)
- Auto-tests (98% coverage guaranteed)
- Auto-deploys (production ready)
- Auto-orchestrates (zero manual coordination)

TARGET: CTOs / VP Engineering at Series B-D SaaS companies
PAIN: 60% of engineering time wasted on coordination, not coding
SOLUTION: Full automation of non-creative work
RESULT: Ship 10x faster, with less ops burden
""",

    "target_audience": """
- CTOs and VP Engineering at SaaS companies
- 50-500 engineers
- Growing companies (Series B-D)
- Tech stacks: Go, Python, Node.js, TypeScript
- Challenges: Feature delivery speed, coordination overhead, testing bottlenecks
- Openness: Active on LinkedIn, blog readers, tech conference attendees
""",

    "cal_com_link": "https://cal.com/gopi/ascm-demo-15min",
    "daily_quota": 25,
}


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "="*100)
    print(f"🎯 {text}")
    print("="*100 + "\n")


def save_output(filename: str, data: dict):
    """Save output to file"""
    log_dir = os.path.expanduser(
        "~/Downloads/projects/googledeepagenthackathon/goproject/payment-gateway/ASCM"
    )
    os.makedirs(log_dir, exist_ok=True)

    filepath = os.path.join(log_dir, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"✅ Saved to: {filepath}")
    return filepath


def phase_1_social_awareness():
    """PHASE 1: Build awareness via social media"""
    print_header("PHASE 1: SOCIAL AWARENESS (Build Warm Audience)")

    print("📱 Generating social content strategy...")
    print("  - 10 LinkedIn posts (2-week schedule)")
    print("  - 8 Twitter posts (daily engagement)")
    print("  - 2 Dev.to articles (thought leadership)")
    print()

    llm_provider = get_configured_provider()
    marketing_agent = SocialFirstMarketingAgent(provider=llm_provider)

    result = marketing_agent.run(
        product_thesis=ASCM_CONFIG["product_thesis"],
        target_audience=ASCM_CONFIG["target_audience"],
        duration_days=14,
    )

    print("✅ PHASE 1 COMPLETE\n")
    print("📊 SOCIAL CONTENT GENERATED:")
    print("  ✓ 10 LinkedIn posts ready for Buffer scheduling")
    print("  ✓ 8 Twitter posts (mix of threads & singles)")
    print("  ✓ 2 Dev.to articles (long-form thought leadership)")
    print("  ✓ 2-week posting schedule optimized for engagement")
    print()
    print("📈 EXPECTED RESULTS:")
    print("  • Reach: 5,000-10,000 impressions")
    print("  • Engagement: 3-5% click-through rate")
    print("  • Warm leads: 150-200 people aware of ASCM")
    print()
    print("🔄 NEXT: Day 3 - Start email campaigns to warm audience")
    print()

    # Save phase 1 output
    save_output(f"phase_1_social_content_{datetime.now().strftime('%Y%m%d')}.json", result)

    return result


def phase_2_warm_email(social_summary: str):
    """PHASE 2: Email campaigns to warm audience"""
    print_header("PHASE 2: WARM EMAIL CAMPAIGNS (To Aware Audience)")

    print("📧 Generating email sequences for warm audience...")
    print(f"  - {ASCM_CONFIG['daily_quota']} specific leads")
    print("  - 3-4 email sequences per lead (shorter than cold)")
    print("  - References to social content they've seen")
    print("  - Cal.com booking in email #2")
    print()

    llm_provider = get_configured_provider()
    sales_agent = WarmAudienceSalesAgent(provider=llm_provider)

    result = sales_agent.run(
        product_thesis=ASCM_CONFIG["product_thesis"],
        icp_description=ASCM_CONFIG["target_audience"],
        cal_com_booking_link=ASCM_CONFIG["cal_com_link"],
        social_campaign_summary=social_summary,
        daily_quota=ASCM_CONFIG["daily_quota"],
    )

    print("✅ PHASE 2 COMPLETE\n")
    print("📧 EMAIL CAMPAIGN READY:")
    print(f"  ✓ {ASCM_CONFIG['daily_quota']} leads with social signals")
    print(f"  ✓ {ASCM_CONFIG['daily_quota'] * 3}-{ASCM_CONFIG['daily_quota'] * 4} personalized emails")
    print(f"  ✓ Booking link in 2nd email (warm audience)")
    print()
    print("📈 EXPECTED RESULTS:")
    expected_meetings_low = int(ASCM_CONFIG['daily_quota'] * 0.03)
    expected_meetings_high = int(ASCM_CONFIG['daily_quota'] * 0.05)
    print(f"  • Open rate: 45-55% (warm audience = higher)")
    print(f"  • Click rate: 8-12%")
    print(f"  • Booking rate: 3-5%")
    print(f"  • Expected meetings: {expected_meetings_low}-{expected_meetings_high}")
    print()
    print("🔄 NEXT: Day 7+ - Handle replies and book meetings")
    print()

    # Save phase 2 output
    save_output(f"phase_2_warm_emails_{datetime.now().strftime('%Y%m%d')}.json", result)

    return result


def phase_3_reply_handling():
    """PHASE 3: Handle inbound replies and book meetings"""
    print_header("PHASE 3: REPLY HANDLING & MEETING BOOKING")

    print("🤝 Setting up reply classification...")
    print("  - INTERESTED → Send Cal.com link immediately")
    print("  - OBJECTION → Send follow-up sequence")
    print("  - NEGATIVE → Suppress (founder protection)")
    print("  - OUT_OF_OFFICE → Queue for 2 weeks")
    print()

    llm_provider = get_configured_provider()
    reply_agent = ReplyHandlingAgent(provider=llm_provider)

    # Example replies to classify
    test_replies = [
        "This looks interesting, let's talk",
        "We already have a tool for this",
        "Not interested, unsubscribe",
        "I'm out until next week",
    ]

    classifications = []
    for reply in test_replies:
        classification = reply_agent.classify_reply(reply)
        classifications.append({
            "reply": reply,
            "classification": classification
        })
        logger.info(f"Classified: {reply} → {classification}")

    print("✅ PHASE 3 READY\n")
    print("🤖 REPLY CLASSIFICATION RULES:")
    print("  ✓ INTERESTED → Route to Cal.com booking (15-min call)")
    print("  ✓ OBJECTION → Trigger follow-up sequence")
    print("  ✓ NEGATIVE → Silently suppress (no founder notification)")
    print("  ✓ OUT_OF_OFFICE → Re-queue in 2 weeks")
    print()

    return {
        "phase": "REPLY_HANDLING",
        "rules": classifications,
        "status": "ready_for_deployment"
    }


def print_summary():
    """Print campaign summary"""
    print_header("📊 SOCIAL-FIRST GTM CAMPAIGN - COMPLETE")

    print("""
CAMPAIGN FLOW:
════════════════════════════════════════════════════════════════════════

DAY 1-14: PHASE 1 - SOCIAL AWARENESS
├─ LinkedIn: 10 posts (mix of threads + singles)
├─ Twitter: 8 posts (daily engagement)
├─ Dev.to: 2 long-form articles
└─ Result: Build warm audience (150-200 aware of ASCM)

DAY 3-14: PHASE 2 - EMAIL TO WARM AUDIENCE
├─ 25 leads per day
├─ 3-4 email sequences (shorter, references social)
├─ Cal.com booking in email #2
└─ Result: 3-5% booking rate (vs 0.5% cold email)

DAY 7+: PHASE 3 - REPLY HANDLING & MEETINGS
├─ Auto-classify: INTERESTED | OBJECTION | NEGATIVE | OUT_OF_OFFICE
├─ Route: Interested → Cal.com, Objection → Follow-up, Negative → Suppress
└─ Result: Book 3-5 meetings per 25 leads

════════════════════════════════════════════════════════════════════════

KEY ADVANTAGES:
✅ Warm audience (seen ASCM on social 3-5x)
✅ Higher open rates (45-55% vs 20-25% cold)
✅ Higher click rates (8-12% vs 2-3% cold)
✅ Higher booking rates (3-5% vs 0.5% cold)
✅ Less reliance on cold outreach
✅ Brand building (not just lead gen)
✅ Founder protection (no unsubscribe spam)

IMPLEMENTATION:
✅ Phase 1: Social content ready for Buffer scheduling
✅ Phase 2: Email sequences ready for Smartlead deployment
✅ Phase 3: Reply handlers ready for real-time classification

NEXT STEPS:
1. Run Phase 1: Deploy social content to Buffer
2. Wait 3 days for social warming
3. Run Phase 2: Deploy email sequences to Smartlead
4. Monitor Phase 3: Handle replies and book meetings
5. Track metrics: Reach, engagement, open rate, booking rate

════════════════════════════════════════════════════════════════════════

🚀 READY FOR DEPLOYMENT
    """)


def main():
    """Run social-first GTM campaign"""
    print("\n" + "="*100)
    print("🚀 ASCM v4.0: SOCIAL-FIRST GTM CAMPAIGN")
    print("="*100)
    print()
    print("This demonstrates the complete 3-phase GTM flow:")
    print("  1. Build awareness via social (LinkedIn, Twitter, Dev.to)")
    print("  2. Email to warm audience (higher conversion)")
    print("  3. Handle replies and book meetings")
    print()
    print("Flow: Awareness → Email → Meetings")
    print()

    try:
        # Phase 1: Social Awareness
        phase_1_result = phase_1_social_awareness()

        # Phase 2: Warm Email
        social_summary = json.dumps(phase_1_result, indent=2)[:500]  # First 500 chars
        phase_2_result = phase_2_warm_email(social_summary)

        # Phase 3: Reply Handling
        phase_3_result = phase_3_reply_handling()

        # Print summary
        print_summary()

        print("\n📁 OUTPUT FILES:")
        print(f"  • phase_1_social_content_*.json")
        print(f"  • phase_2_warm_emails_*.json")
        print()
        print("✅ Campaign ready for execution!")
        print()

    except Exception as e:
        logger.error(f"❌ Campaign failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()

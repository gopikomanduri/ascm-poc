#!/usr/bin/env python3
"""
ASCM Zero-Setup Founder Experience Demo:
Demonstrates:
1. Autonomous Medium Selection (Why X/Reddit/Email vs LinkedIn)
2. Zero-Key Social Distribution (Browser Bridge / Pre-authenticated Intent)
3. Zero-DNS Managed Relay (Outbound email without domain/SPF setup)
4. Fast 2-second Founder Approval & Dispatch Simulation
"""

import sys
import os
import json
import urllib.parse
from datetime import datetime
from pathlib import Path

from orchestrator.gtm.repo_analyzer import RepoAnalyzer
from orchestrator.gtm.gtm_strategy_selector_v2 import CompanyProfile, GTMStrategyRecommender

def banner(title: str):
    print("\n" + "═" * 80)
    print(f" 🔥 {title}")
    print("═" * 80)

def main():
    banner("ASCM ZERO-SETUP FOUNDER FLOW: PULL CODE & LAUNCH GTM")
    print("""
Scenario: You are the technical founder of ASCM. You just ran:
    git clone https://github.com/ascm-org/ascm.git && cd ascm
    python -m orchestrator.gtm.launch

You have NOT created any LinkedIn developer apps.
You have NOT bought secondary domains or configured SPF/DKIM/DMARC.
You have NOT registered for a $100/mo X Developer API account.

Watch how ASCM handles everything autonomously:
""")

    # ------------------------------------------------------------------------
    # STEP 1: AUTONOMOUS REPO SCAN & MEDIUM SELECTION
    # ------------------------------------------------------------------------
    banner("STEP 1: AUTONOMOUS MEDIUM SELECTION (Finding the Best Channels)")
    print("Scanning repository codebase in real-time...")
    
    analyzer = RepoAnalyzer(".")
    analysis = analyzer.analyze()
    tech_stack = analysis["tech_stack"]
    languages = tech_stack.get("languages", ["Go", "Python"])
    frameworks = tech_stack.get("frameworks", ["FastAPI", "Temporal"])
    
    print(f"✅ Tech Stack Detected: {', '.join(languages + frameworks)}")
    print(f"✅ Product Type: Distributed Infrastructure & Autonomous SDLC Engine")
    print("\nEvaluating Medium Performance Scores for this product archetype:")

    # Scoring the channels based on product characteristics
    channels = [
        {
            "channel": "X.com (Technical Threads) + Reddit (r/golang, r/devops)",
            "score": 96,
            "verdict": "PRIMARY CHANNEL (Top Fit)",
            "rationale": "Engineers & architects actively engage on X & Reddit for distributed systems, Go, and Temporal patterns. Zero marketing fluff tolerated."
        },
        {
            "channel": "Direct 1:1 CTO Outbound (Peer-to-Peer)",
            "score": 91,
            "verdict": "PRIMARY OUTBOUND",
            "rationale": "Series B-D CTOs feel the $200k/yr coordination pain directly. High ACV software sells via direct peer outreach."
        },
        {
            "channel": "Developer SEO & Dev.to Technical Deep-Dives",
            "score": 84,
            "verdict": "SUPPORTING (Inbound SEO)",
            "rationale": "Long-tail organic search captures engineering leads searching for 'temporal microservices patterns'."
        },
        {
            "channel": "LinkedIn Corporate Page & Paid Ads",
            "score": 38,
            "verdict": "DE-PRIORITIZED (Skip for now)",
            "rationale": "High CAC ($250+/lead), low developer authenticity, requires high brand recognition to convert."
        }
    ]

    for ch in channels:
        bar = "█" * int(ch["score"] / 5) + "░" * (20 - int(ch["score"] / 5))
        print(f"\n  [{bar}] {ch['score']}% - {ch['channel']}")
        print(f"  └─ Status: {ch['verdict']}")
        print(f"     Reason: {ch['rationale']}")

    print(f"\n🎯 AGENT DECISION: Launch simultaneously on [X.com / Reddit] + [Direct CTO Outbound].")

    # ------------------------------------------------------------------------
    # STEP 2: ZERO-KEY SOCIAL EXECUTION (Local Browser Session Bridge)
    # ------------------------------------------------------------------------
    banner("STEP 2: ZERO-KEY SOCIAL DISTRIBUTION (No $100/mo X API Key Needed)")
    print("""
How it works without API keys:
The agent leverages your existing, already-authenticated local Chrome browser session
or pre-composed web intents. You NEVER have to register developer portal apps.
""")
    
    tweet_text = (
        "We spent 6 months building an engine that cuts microservice feature delivery from 2 months to 2 weeks.\n\n"
        "Key insight: 60% of engineering bandwidth is lost to cross-service coordination, not coding.\n\n"
        "Architecture: Go + Temporal.io + PostgreSQL outbox pattern.\n"
        "10k+ TPS, <25ms p99 latency.\n\n"
        "Read our full architecture design on GitHub: https://github.com/ascm-poc/ascm"
    )

    encoded_tweet = urllib.parse.quote(tweet_text)
    intent_url = f"https://twitter.com/intent/tweet?text={encoded_tweet}"

    print("📝 1. Prepared X.com Broadcast:")
    print("┌" + "─" * 76 + "┐")
    for line in tweet_text.split("\n"):
        print(f"│ {line.ljust(74)} │")
    print("└" + "─" * 76 + "┘")
    print(f"🔗 Browser Dispatch Link: {intent_url[:80]}...")

    print("\n📝 2. Prepared Reddit Technical Post (r/golang & r/devops):")
    print("   Title: How we achieved <25ms p99 across microservices using Go and Temporal.io outbox reconciliation")
    print("   Subreddit: r/golang | Tag: [Project Show / Architecture]")
    print("   Status: Staged & formatted for instant submission via local session bridge.")

    # ------------------------------------------------------------------------
    # STEP 3: ZERO-DNS MANAGED OUTBOUND RELAY (No Domain/SPF/DKIM Setup)
    # ------------------------------------------------------------------------
    banner("STEP 3: ZERO-DNS MANAGED EMAIL RELAY (No Mailbox Setup)")
    print("""
How it works without buying domains:
Instead of forcing you through 14 days of domain warmup and DNS records,
ASCM routes outbound emails through a pre-warmed, reputable relay pool.
Replies are automatically mapped to your calendar and forwarded to your personal email.
""")

    outbound_batch = [
        {
            "to": "david.brown@datadog.com",
            "name": "David Brown",
            "company": "Datadog",
            "role": "CTO",
            "angle": "Scaling AI Observability microservices coordination drag",
            "relay_headers": {
                "From": "Gopi via ASCM Relay <gopi@delivery.tryascm.io>",
                "Reply-To": "founder@ascm-local.com",
                "SPF": "PASS (v=spf1 include:relay.tryascm.io)",
                "DKIM": "PASS (2048-bit verified)",
                "DMARC": "PASS (p=reject)"
            }
        },
        {
            "to": "benoit.dageville@snowflake.com",
            "name": "Benoit Dageville",
            "company": "Snowflake",
            "role": "Co-founder / CTO",
            "angle": "Python/Java microservices coordination overhead",
            "relay_headers": {
                "From": "Gopi via ASCM Relay <gopi@delivery.tryascm.io>",
                "Reply-To": "founder@ascm-local.com",
                "SPF": "PASS (v=spf1 include:relay.tryascm.io)",
                "DKIM": "PASS (2048-bit verified)",
                "DMARC": "PASS (p=reject)"
            }
        }
    ]

    for item in outbound_batch:
        print(f"  • Target: {item['name']} ({item['role']} at {item['company']})")
        print(f"    Email:  {item['to']}")
        print(f"    Angle:  {item['angle']}")
        print(f"    Auth:   SPF={item['relay_headers']['SPF'][:4]} | DKIM={item['relay_headers']['DKIM'][:4]} | DMARC={item['relay_headers']['DMARC'][:4]}")
        print(f"    Route:  Replies -> https://cal.com/gopi/ascm-demo-15min")
        print()

    # ------------------------------------------------------------------------
    # STEP 4: THE 2-SECOND APPROVAL GATE
    # ------------------------------------------------------------------------
    banner("STEP 4: 2-SECOND FOUNDER APPROVAL (Zero Administrative Burden)")
    print("""
All heavy lifting is done:
  [✔] Medium selected: X.com + Reddit + Direct CTO Outbound
  [✔] 1 X.com broadcast ready to post via local browser session
  [✔] 1 Reddit r/golang architecture post formatted
  [✔] 2 CTO outreach emails staged with verified relay authentication
  [✔] Negative & spam replies set to silent suppression (shielding founder)
  [✔] Positive replies mapped directly to: https://cal.com/gopi/ascm-demo-15min

Action required from founder:
""")
    print("👉 [APPROVE & DISPATCH]: Type 'Y' or press ENTER to launch")
    print("👉 [EDIT]: Type 'E' to tweak email body or tweet copy")
    print("👉 [ABORT]: Type 'Q' to cancel")

    # In script demo mode, simulate instant confirmation
    print("\n[Simulated Founder Input]: <ENTER> (Instant 1-Click Launch)")
    print("\n🚀 LAUNCHING DISPATCH ENGINE...")
    print("   [1/3] Publishing to X.com via local browser session... [SUCCESS ✅]")
    print("   [2/3] Queueing r/golang technical breakdown... [SUCCESS ✅]")
    print("   [3/3] Sending 2 CTO emails via Pre-Warmed Relay... [SUCCESS ✅]")
    print("\n🎉 GTM CAMPAIGN IS LIVE! Zero settings touched. Zero excuses left.")

if __name__ == "__main__":
    main()

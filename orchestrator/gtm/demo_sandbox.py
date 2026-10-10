import os
import json
import logging
from typing import Dict, Any, Optional

from orchestrator.agents.base import _load_dotenv

_load_dotenv()
logger = logging.getLogger("DemoSandbox")


class DemoSandboxService:
    """
    Curated Scenario Showcase for MentorAgent, MarketingAgent, and SalesAgent.
    Provides instant, zero-latency, high-fidelity agent outputs for V1.
    """

    # Static Curated Scenario Data for V1
    CURATED_DATA = {
        "mentor": {
            "database_refactor": {
                "status": "ok",
                "agent": "MentorAgent",
                "scenario_title": "3-Week Schema Refactor (142 files, 0 customer calls)",
                "risk_score": 92,
                "risk_level": "CRITICAL ISOLATION ALERT",
                "headline": "🚨 You are hiding behind your compiler.",
                "analysis": "You have spent 21 straight days refactoring Postgres schema tables, edge cases, and migrations without speaking to a single paying customer. Code written in a vacuum has zero market value until validated by user behavior.",
                "tough_love_quote": "Stop optimizing database architecture nobody asked for. Put down the keyboard, step away from the compiler, and put 3 customer discovery calls on your calendar today.",
                "validation_actions": [
                    "Draft a 1-page architecture breakdown on LinkedIn/X asking: 'How do you handle this migration in prod?'",
                    "Send 5 direct messages to target engineering managers before writing another line of SQL.",
                    "Lock in 2 design partner validation interviews before merging this PR."
                ],
                "next_step": "👉 Run MarketingAgent above to turn this diff into authentic developer launch content."
            },
            "css_polishing": {
                "status": "ok",
                "agent": "MentorAgent",
                "scenario_title": "6 Days Polishing Custom CSS Shadows & Dark Mode",
                "risk_score": 86,
                "risk_level": "HIGH PROCRASTINATION RISK",
                "headline": "🛑 The Pixel-Perfection Coping Mechanism.",
                "analysis": "Spending 6 consecutive days adjusting border-radii, glassmorphism blur, and button hovers when your core value proposition has zero traffic is emotional avoidance of customer rejection.",
                "tough_love_quote": "Ugly products that solve hair-on-fire problems generate millions. Beautiful products nobody needs go to the startup graveyard. Ship it raw and talk to users.",
                "validation_actions": [
                    "Deploy the current unpolished UI to production immediately.",
                    "Post a 90-second raw Loom walkthrough on Twitter/X demonstrating the core utility.",
                    "Ask 3 beta developers to click through the user flow while screen-sharing."
                ],
                "next_step": "👉 Run MarketingAgent above to generate your raw 'building in public' launch story."
            },
            "complex_auth": {
                "status": "ok",
                "agent": "MentorAgent",
                "scenario_title": "Premature OAuth2, Redis Caching & Microservice Split",
                "risk_score": 95,
                "risk_level": "CRITICAL OVER-ENGINEERING RISK",
                "headline": "⚠️ Premature Scale on an Empty Product.",
                "analysis": "You architected enterprise-grade multi-tenant JWT rotation, distributed Redis rate limiters, and split services into Docker containers for exactly zero active users.",
                "tough_love_quote": "You are building infrastructure for 100,000 concurrent requests when you can't even get 1 person to sign up. Replace the microservice with a monolith in 1 repo and get your first user.",
                "validation_actions": [
                    "Collapse the microservices back into a single fast monolith executable.",
                    "Manually onboard your first 3 users via a shared spreadsheet if needed.",
                    "Validate payment willingness with a Stripe checkout link before configuring Redis clusters."
                ],
                "next_step": "👉 Run SalesAgent above to draft a cold outreach email to test willingness to pay."
            }
        },
        "marketing": {
            "git_daemon": {
                "status": "ok",
                "agent": "MarketingAgent",
                "scenario_title": "Outcode: Local Git Daemon & Auto-GTM Launch Stories",
                "x_post": {
                    "headline": "𝕏 / Twitter Viral Launch Thread",
                    "copy": "Most technical founders don't fail because they can't code.\n\nThey fail because they build in isolation for 6 months without ever telling the world.\n\nWe built Outcode: a local git daemon that lives in your terminal, catches you when you over-engineer in a vacuum, and auto-generates your social launches directly from your git diffs.\n\nYour terminal just hired a 24/7 GTM team. Stop coding in the dark ⚡👇",
                    "cta": "Join the Public Alpha: outcode.ai"
                },
                "linkedin_post": {
                    "headline": "LinkedIn Technical Founder Story",
                    "copy": "Last week, I almost wasted another 2 weeks over-engineering a database cache nobody asked for.\n\nWhy? Because fixing code feels comfortable. Talking to customers feels vulnerable.\n\nTechnical co-founders fall into this trap constantly: we hide behind our compilers.\n\nThat's why we built Outcode. It runs locally as a git daemon. Every time you commit, it checks your isolation risk, reminds you to talk to users, and drafts your developer launch posts and outbound emails directly from code changes.\n\nEngineers: what feature did you waste the most runway building before speaking to a customer?",
                    "cta": "Link to free early access in comments 🚀"
                },
                "show_hn": {
                    "headline": "Hacker News (Show HN)",
                    "copy": "Show HN: Outcode – Git daemon that prevents over-engineering & turns diffs into launches\n\nHey HN! We're building Outcode to solve the #1 cause of developer burnout: spending months writing pristine code that nobody ever hears about. Runs 100% locally with zero cloud vendor lock-in.",
                    "cta": "https://github.com/gopikomanduri/ascm-poc"
                }
            },
            "paypulse_fraud": {
                "status": "ok",
                "agent": "MarketingAgent",
                "scenario_title": "PayPulse: Real-Time FinTech Fraud Pipeline",
                "x_post": {
                    "headline": "𝕏 / Twitter Viral Launch Thread",
                    "copy": "Card fraud costs merchants $38B every year.\n\nLegacy rule engines take 800ms per checkout. We built PayPulse: sub-40ms anomaly scoring with instant Webhook reconciliation.\n\nHere's how we reduced false declines by 64% using real-time streaming graph analysis 🧵👇",
                    "cta": "Read the engineering benchmark: paypulse.dev/speed"
                },
                "linkedin_post": {
                    "headline": "LinkedIn Technical Founder Story",
                    "copy": "Most fraud engines penalize your best customers. When a false positive blocks a legitimate checkout, you lose lifetime value.\n\nWe just shipped PayPulse v1: a high-throughput transaction evaluation pipeline processing 10,000 tx/sec with zero latency overhead.\n\nTo the FinTech builders out there: what's your biggest headache with legacy fraud APIs?",
                    "cta": "Live benchmark & API playground in the comments 👇"
                },
                "show_hn": {
                    "headline": "Hacker News (Show HN)",
                    "copy": "Show HN: PayPulse – Open-source streaming fraud scoring engine (<40ms latency)\n\nBuilt in Go and Rust to eliminate false positives in cross-border checkout flows without slowing down user authorization.",
                    "cta": "https://paypulse.dev"
                }
            },
            "ast_verifier": {
                "status": "ok",
                "agent": "MarketingAgent",
                "scenario_title": "Autonomous AST Multi-Repo Contract Verifier",
                "x_post": {
                    "headline": "𝕏 / Twitter Viral Launch Thread",
                    "copy": "Breaking changes in private microservice APIs are a nightmare.\n\nWe just shipped AST Verifier: intercepts pull requests, parses downstream client ASTs, and blocks breaking schema changes before CI runs.\n\nStop debugging runtime type mismatches in production ⚡",
                    "cta": "Try the CLI: npm i -g @ast/verifier"
                },
                "linkedin_post": {
                    "headline": "LinkedIn Technical Founder Story",
                    "copy": "If your engineering team has ever broken a production client SDK because of an undocumented REST field rename, you know the pain.\n\nWe automated cross-repo AST inspection into git commit hooks. Catch semantic contract breaks in 200ms without spinning up Docker containers.\n\nEngineering managers: how do you prevent breaking schema changes across repositories today?",
                    "cta": "Open-source repo linked below 👇"
                },
                "show_hn": {
                    "headline": "Hacker News (Show HN)",
                    "copy": "Show HN: AST Verifier – Instant cross-repo breaking contract detection at commit time\n\nParses TypeScript and Go ASTs in git staging hooks to detect breaking schema mutations before you push.",
                    "cta": "https://github.com/ast-verifier"
                }
            }
        },
        "sales": {
            "vp_eng_saas": {
                "status": "ok",
                "agent": "SalesAgent",
                "scenario_title": "Target: VP of Engineering at Series A-B B2B SaaS",
                "target_persona": "VP of Engineering / Head of Tech (Series A-B SaaS, 25-100 devs)",
                "cold_email": {
                    "subject": "quick question on engineering sprint velocity",
                    "body": "Hey Alex,\n\nNoticed your engineering team has doubled this quarter. Most growing squads burn ~20% of dev bandwidth over-engineering features before customer validation.\n\nWe built an autonomous daemon that flags isolation risk directly from git diffs.\n\nOpen to a 5-minute teardown this Thursday?",
                    "word_count": 39
                },
                "discovery_questions": [
                    "How do your tech leads currently identify PRs that are over-engineered before they get merged?",
                    "How many developer hours per sprint get spent refactoring modules that end up with near-zero user engagement?",
                    "If a background daemon automatically drafted customer discovery questions for new PRs, would your team test it?"
                ],
                "cal_booking_flow": "Warm reply detected → Auto-dispatches Cal.com 15-min discovery link with founder calendar."
            },
            "cto_healthtech": {
                "status": "ok",
                "agent": "SalesAgent",
                "scenario_title": "Target: CTOs at High-Compliance FinTech / HealthTech",
                "target_persona": "CTO / Chief Information Security Officer (HealthTech & FinTech)",
                "cold_email": {
                    "subject": "audit trail overhead on your latest release",
                    "body": "Hey Sarah,\n\nSaw your recent SOC-2 Type II announcement. Usually that compliance workload pulls 2-3 senior devs off product features for months.\n\nWe built an automated terminal daemon that generates tamper-evident audit logs directly from commit diffs.\n\nWorth a quick 5-min look?",
                    "word_count": 41
                },
                "discovery_questions": [
                    "What's the current engineering burden of compiling release evidence for external security audits?",
                    "How often do code changes bypass your compliance checklist during emergency hotfixes?",
                    "Would automating commit verification into your git workflow save your team at least 10 hours a week?"
                ],
                "cal_booking_flow": "Direct routing into priority compliance pilot queue."
            },
            "head_payments": {
                "status": "ok",
                "agent": "SalesAgent",
                "scenario_title": "Target: Head of Payments & Operations",
                "target_persona": "Head of Payments / Director of Financial Infrastructure",
                "cold_email": {
                    "subject": "handling cross-border settlement volatility",
                    "body": "Hey Marcus,\n\nQuick note — seen your cross-border volume growing in LATAM. Most payment ops teams lose 1-2% on hidden FX slippage during weekend batches.\n\nWe built a real-time ledger verification tool that catches settlement discrepancies instantly.\n\nFree for a brief 7-minute intro next week?",
                    "word_count": 38
                },
                "discovery_questions": [
                    "What is your current reconciliation delay between transaction authorization and bank settlement?",
                    "How do you handle automated dispute detection before chargeback penalties kick in?",
                    "Would real-time settlement monitoring allow your team to expand into new currency corridors faster?"
                ],
                "cal_booking_flow": "Direct calendar invite with payment engineering lead."
            }
        }
    }

    @staticmethod
    def _get_gemini_client():
        from google import genai
        use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1", "yes")
        gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        timeout_ms = int(float(os.environ.get("GEMINI_TIMEOUT_SEC", "120")) * 1000)
        if use_vertex or gcp_project:
            return genai.Client(vertexai=True, project=gcp_project, location=location, http_options={"timeout": timeout_ms})
        return genai.Client(http_options={"timeout": timeout_ms})

    @staticmethod
    def run_agent_demo(
        agent_type: str,
        scenario: str = "database_refactor",
        custom_input: Optional[str] = None,
        domain: str = "devtools",
    ) -> Dict[str, Any]:
        agent_type = (agent_type or "mentor").lower().strip()
        scenario_key = (scenario or "").lower().strip()
        user_prompt = (custom_input or "").strip()

        # If custom prompt is provided, run live through Google Models SDK
        if user_prompt:
            try:
                client = DemoSandboxService._get_gemini_client()
                model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
                if agent_type == "mentor":
                    prompt = f"Analyze developer isolation risk for: '{user_prompt}'. Return JSON with keys: risk_score (int), risk_level, headline, analysis, tough_love_quote, validation_actions (list)."
                elif agent_type == "marketing":
                    prompt = f"Generate developer launch copy for: '{user_prompt}'. Return JSON with keys: x_post (headline, copy, cta), linkedin_post (headline, copy, cta), show_hn (headline, copy, cta)."
                else:
                    prompt = f"Generate B2B cold outbound for: '{user_prompt}'. Return JSON with keys: target_persona, cold_email (subject, body, word_count), discovery_questions (list), cal_booking_flow."
                
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                if resp and resp.text:
                    parsed = json.loads(resp.text)
                    return {"status": "ok", "agent": agent_type.capitalize() + "Agent", "live_google_models_sdk": True, **parsed}
            except Exception as e:
                logger.warning(f"Live Google Models SDK execution failed, falling back to curated: {e}")

        # If a curated scenario is matched, return curated static benchmark immediately
        agent_scenarios = DemoSandboxService.CURATED_DATA.get(agent_type, {})
        if scenario_key in agent_scenarios:
            return agent_scenarios[scenario_key]

        # Default fallback to first scenario in category
        if agent_scenarios:
            first_key = list(agent_scenarios.keys())[0]
            return agent_scenarios[first_key]

        return {"status": "error", "message": f"Unknown agent type: {agent_type}"}

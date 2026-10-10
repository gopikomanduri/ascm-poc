import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("DemoSandbox")


class DemoSandboxService:
    """
    Executes live browser demos of MentorAgent, MarketingAgent, and SalesAgent.
    Works seamlessly on Google Cloud Run with Gemini API when available,
    and provides instant high-fidelity domain responses when offline.
    """

    @staticmethod
    def run_agent_demo(
        agent_type: str,
        scenario: str = "database_refactor",
        custom_input: Optional[str] = None,
        domain: str = "devtools",
    ) -> Dict[str, Any]:
        agent_type = (agent_type or "mentor").lower().strip()
        user_prompt = (custom_input or "").strip()

        # Preset descriptions
        presets = {
            "database_refactor": "Refactoring Postgres schema and edge cases for 3 weeks (142 files, 0 customer conversations)",
            "css_polishing": "Polishing dark-mode CSS shadows and custom buttons for 6 days straight (no landing page live)",
            "complex_auth": "Built full OAuth2, Redis token caching, and rate limiting microservice (0 paying users)",
        }
        active_scenario = user_prompt if user_prompt else presets.get(scenario, presets["database_refactor"])

        if agent_type == "mentor":
            return DemoSandboxService._run_mentor_demo(active_scenario, domain)
        elif agent_type == "marketing":
            return DemoSandboxService._run_marketing_demo(active_scenario, domain)
        elif agent_type == "sales":
            return DemoSandboxService._run_sales_demo(active_scenario, domain)
        else:
            return {"status": "error", "message": f"Unknown agent type: {agent_type}"}

    @staticmethod
    def _run_mentor_demo(scenario_text: str, domain: str) -> Dict[str, Any]:
        # Try live Gemini call if API key present
        if os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                client = genai.Client()
                model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-2.0-flash"
                prompt = (
                    "You are the Outcode Proactive Founder Mentor, a tough-love YC partner.\n"
                    "A founder commits the following coding activity:\n"
                    f"'{scenario_text}'\n"
                    "Analyze the isolation risk, sound the intervention alarm, and provide tough-love advice.\n"
                    "Respond with JSON having keys: risk_score (int 0-99), risk_level (str), headline (str), analysis (str), tough_love_quote (str), validation_actions (list of 3 strings)."
                )
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                data = json.loads(resp.text)
                return {"status": "ok", "agent": "MentorAgent", "scenario": scenario_text, **data}
            except Exception as e:
                logger.warning(f"Live Gemini mentor call fallback: {e}")

        # Deterministic instant fallback
        risk = 88 if "week" in scenario_text or "142" in scenario_text else 76
        return {
            "status": "ok",
            "agent": "MentorAgent",
            "scenario": scenario_text,
            "risk_score": risk,
            "risk_level": "CRITICAL ISOLATION ALERT",
            "headline": "🚨 You are hiding behind your compiler.",
            "analysis": f"You are spending valuable runway optimizing '{scenario_text}' without speaking to users. Code written in a vacuum has zero market value until real users validate demand.",
            "tough_love_quote": "Stop optimizing architecture nobody asked for. Put down the keyboard and get 3 target customer discovery calls on your calendar today.",
            "validation_actions": [
                "Draft a 1-page architecture breakdown on LinkedIn/X highlighting the exact bottleneck you are solving.",
                "Send 5 direct messages to engineering leaders asking: 'How do you currently handle this in production?'",
                "Lock in 2 design partner interviews before writing any further backend code."
            ],
            "next_step": "Auto-generate your launch story and outreach sequence now with Marketing & Sales Agents."
        }

    @staticmethod
    def _run_marketing_demo(scenario_text: str, domain: str) -> Dict[str, Any]:
        if os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                client = genai.Client()
                model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-2.0-flash"
                prompt = (
                    "You are the Outcode MarketingAgent. A technical founder just worked on:\n"
                    f"'{scenario_text}'\n"
                    "Generate authentic developer marketing copy that engineers respect (no corporate fluff).\n"
                    "Respond with JSON having keys: x_post (dict with headline, copy, cta), linkedin_post (dict with headline, copy, cta), show_hn (dict with headline, copy, cta)."
                )
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                data = json.loads(resp.text)
                return {"status": "ok", "agent": "MarketingAgent", "feature": scenario_text, **data}
            except Exception as e:
                logger.warning(f"Live Gemini marketing call fallback: {e}")

        return {
            "status": "ok",
            "agent": "MarketingAgent",
            "feature": scenario_text,
            "x_post": {
                "headline": "𝕏 / Twitter Viral Launch Thread",
                "copy": "Most technical founders don't fail because they can't code.\n\nThey fail because they spend 3 straight weeks perfecting edge cases in isolation while their runway burns.\n\nThat's why we built Outcode: a local-first git daemon that sounds the alarm when you over-engineer in a vacuum and drafts your launch stories directly from your git diffs.\n\nStop coding in the dark. Your terminal just hired a GTM team ⚡👇",
                "cta": "Join the Public Alpha: outcode.ai"
            },
            "linkedin_post": {
                "headline": "LinkedIn Technical Founder Story",
                "copy": "Three weeks ago, I caught myself doing what 90% of solo technical founders do:\n\nRefactoring backend schemas and edge cases that zero users had asked for.\n\nWhy? Because fixing code feels comfortable. Talking to customers feels vulnerable.\n\nSo we built Outcode. It intercepts git commits in real time, warns you when code velocity outpaces customer validation, and auto-generates your social launches and cold sales outreach.\n\nTechnical founders: what feature did you waste the most time over-engineering before talking to a customer?",
                "cta": "Link to free public alpha in comments 🚀"
            },
            "show_hn": {
                "headline": "Hacker News (Show HN)",
                "copy": "Show HN: Outcode – A local-first git daemon that stops over-engineering & turns diffs into launches\n\nHey HN! We built Outcode because technical founders spend months perfecting architecture in a vacuum while runway burns. Runs 100% locally with BYOK (Gemini, Claude, Ollama) and acts as an autonomous commercial co-pilot.",
                "cta": "https://github.com/gopikomanduri/ascm-poc"
            }
        }

    @staticmethod
    def _run_sales_demo(scenario_text: str, domain: str) -> Dict[str, Any]:
        if os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                client = genai.Client()
                model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-2.0-flash"
                prompt = (
                    "You are the Outcode SalesAgent. A technical founder built:\n"
                    f"'{scenario_text}'\n"
                    "Generate a high-converting 35-word cold outreach email targeting engineering leaders, and 3 customer discovery questions.\n"
                    "Respond with JSON having keys: target_persona (str), cold_email (dict with subject, body, word_count), discovery_questions (list of 3 strings), cal_booking_flow (str)."
                )
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                data = json.loads(resp.text)
                return {"status": "ok", "agent": "SalesAgent", "feature": scenario_text, **data}
            except Exception as e:
                logger.warning(f"Live Gemini sales call fallback: {e}")

        return {
            "status": "ok",
            "agent": "SalesAgent",
            "target_persona": "VP of Engineering / Technical Co-Founders at Series A-B B2B SaaS",
            "cold_email": {
                "subject": "quick question on your engineering sprint cadence",
                "body": "Hey Alex,\n\nNoticed your team is shipping multi-repo services. Most engineering teams lose ~20% of engineering bandwidth on out-of-sync API contracts and over-engineered features.\n\nWe built an autonomous daemon that coordinates multi-repo ASTs locally and validates sprint value before shipping.\n\nOpen to a 5-minute teardown this Thursday?",
                "word_count": 42
            },
            "discovery_questions": [
                "What is your team's biggest bottleneck when coordinating cross-service API contracts?",
                "How many engineering hours per sprint get burned refactoring features that end up underused?",
                "If an autonomous tool flagged over-engineered PRs before merge, would your team pilot it?"
            ],
            "cal_booking_flow": "Warm reply detected → Auto-dispatches Cal.com 15-min discovery link with founder calendar."
        }

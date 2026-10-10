import os
import json
import logging
from typing import Dict, Any, Optional

from orchestrator.agents.base import _load_dotenv

_load_dotenv()
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
    def _generate_with_gemini(prompt: str) -> Optional[Dict[str, Any]]:
        candidate_models = [
            os.getenv("GEMINI_MODEL"),
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
        ]
        candidate_models = [m for m in candidate_models if m]
        try:
            from google import genai
            client = genai.Client()
            for model in candidate_models:
                try:
                    resp = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    if resp and resp.text:
                        return json.loads(resp.text)
                except Exception as e:
                    logger.warning(f"Attempt with model {model} failed: {e}")
        except Exception as e:
            logger.warning(f"Gemini client setup error: {e}")
        return None

    @staticmethod
    def _run_mentor_demo(scenario_text: str, domain: str) -> Dict[str, Any]:
        prompt = (
            "You are the Outcode Proactive Founder Mentor, a tough-love YC partner.\n"
            f"A technical founder commits the following coding activity:\n"
            f"'{scenario_text}'\n"
            "Analyze the isolation risk, sound the intervention alarm, and provide tough-love advice.\n"
            "Respond strictly in JSON with keys:\n"
            "{\n"
            '  "risk_score": int (between 40 and 98),\n'
            '  "risk_level": "CRITICAL ISOLATION ALERT" or "HIGH OVER-ENGINEERING RISK",\n'
            '  "headline": "punchy 1-sentence intervention callout",\n'
            '  "analysis": "2-3 sentences explaining why this code has 0 market value until validated",\n'
            '  "tough_love_quote": "memorable YC-partner style quote telling founder to put down the keyboard",\n'
            '  "validation_actions": ["action 1", "action 2", "action 3"]\n'
            "}"
        )
        ai_data = DemoSandboxService._generate_with_gemini(prompt)
        if ai_data and "headline" in ai_data:
            return {"status": "ok", "agent": "MentorAgent", "scenario": scenario_text, "live_gemini": True, **ai_data}

        # Dynamic template fallback based on user's exact words
        risk = 88 if any(w in scenario_text.lower() for w in ["week", "month", "100", "refactor"]) else 72
        return {
            "status": "ok",
            "agent": "MentorAgent",
            "scenario": scenario_text,
            "risk_score": risk,
            "risk_level": "CRITICAL ISOLATION ALERT",
            "headline": "🚨 You are hiding behind your compiler.",
            "analysis": f"You are spending valuable runway building '{scenario_text}' without speaking to users. Code written in a vacuum has zero market value until real users validate demand.",
            "tough_love_quote": "Stop optimizing architecture nobody asked for. Put down the keyboard and get 3 target customer discovery calls on your calendar today.",
            "validation_actions": [
                f"Draft a 1-page architecture breakdown on LinkedIn/X highlighting the exact bottleneck in '{scenario_text[:40]}...'",
                "Send 5 direct messages to engineering leaders asking: 'How do you currently handle this in production?'",
                "Lock in 2 design partner interviews before writing any further backend code."
            ],
            "next_step": "Auto-generate your launch story and outreach sequence now with Marketing & Sales Agents."
        }

    @staticmethod
    def _run_marketing_demo(scenario_text: str, domain: str) -> Dict[str, Any]:
        prompt = (
            "You are the Outcode MarketingAgent. A technical founder just built or worked on:\n"
            f"'{scenario_text}'\n"
            "Generate authentic developer marketing copy that engineers respect (no corporate buzzwords).\n"
            "Respond strictly in JSON with keys:\n"
            "{\n"
            '  "x_post": {"headline": "𝕏 / Twitter Viral Launch Thread", "copy": "3-4 lines with hook, founder pain, solution, call to action", "cta": "link"},\n'
            '  "linkedin_post": {"headline": "LinkedIn Technical Founder Story", "copy": "founder-to-founder vulnerable story about over-engineering vs shipping", "cta": "link"},\n'
            '  "show_hn": {"headline": "Hacker News (Show HN)", "copy": "Show HN: title and concise tech breakdown", "cta": "repo link"}\n'
            "}"
        )
        ai_data = DemoSandboxService._generate_with_gemini(prompt)
        if ai_data and "x_post" in ai_data:
            return {"status": "ok", "agent": "MarketingAgent", "feature": scenario_text, "live_gemini": True, **ai_data}

        return {
            "status": "ok",
            "agent": "MarketingAgent",
            "feature": scenario_text,
            "x_post": {
                "headline": "𝕏 / Twitter Viral Launch Thread",
                "copy": f"Most technical founders don't fail because they can't code.\n\nThey fail because they build things like '{scenario_text[:50]}' in isolation without talking to users.\n\nOutcode intercepts your git commits, sounds the alarm when you over-engineer, and auto-generates your social launches right from diffs.\n\nStop coding in the dark ⚡👇",
                "cta": "Join the Public Alpha: outcode.ai"
            },
            "linkedin_post": {
                "headline": "LinkedIn Technical Founder Story",
                "copy": f"Last week, I almost wasted another 2 weeks over-engineering '{scenario_text[:45]}...'\n\nWhy? Because fixing code feels comfortable. Talking to customers feels vulnerable.\n\nThat's why we built Outcode. It watches your git repo, stops you when you build in a vacuum, and auto-generates your social launches and sales outreach from your diffs.\n\nTechnical founders: what feature did you waste the most time on before customer validation?",
                "cta": "Link to free public alpha in comments 🚀"
            },
            "show_hn": {
                "headline": "Hacker News (Show HN)",
                "copy": f"Show HN: Outcode – Git daemon that stops over-engineering & turns diffs into launches\n\nHey HN! We built Outcode to help builders avoid coding in a vacuum on features like {scenario_text[:40]}. Runs 100% locally with BYOK (Gemini, Claude, Ollama).",
                "cta": "https://github.com/gopikomanduri/ascm-poc"
            }
        }

    @staticmethod
    def _run_sales_demo(scenario_text: str, domain: str) -> Dict[str, Any]:
        prompt = (
            "You are the Outcode SalesAgent. A technical founder built:\n"
            f"'{scenario_text}'\n"
            "Generate a high-converting 35-word cold outreach email targeting engineering leaders, and 3 customer discovery questions.\n"
            "Respond strictly in JSON with keys:\n"
            "{\n"
            '  "target_persona": "title and company type",\n'
            '  "cold_email": {"subject": "lowercase 4-word subject", "body": "35-word punchy, non-salesy email addressing the pain point", "word_count": int},\n'
            '  "discovery_questions": ["question 1", "question 2", "question 3"],\n'
            '  "cal_booking_flow": "one sentence explaining meeting booking routing"\n'
            "}"
        )
        ai_data = DemoSandboxService._generate_with_gemini(prompt)
        if ai_data and "cold_email" in ai_data:
            return {"status": "ok", "agent": "SalesAgent", "feature": scenario_text, "live_gemini": True, **ai_data}

        return {
            "status": "ok",
            "agent": "SalesAgent",
            "target_persona": "VP of Engineering / Technical Co-Founders at Series A-B B2B SaaS",
            "cold_email": {
                "subject": "quick question on your engineering sprint cadence",
                "body": f"Hey Alex,\n\nNoticed your team is scaling fast. Most engineering squads burn ~20% of bandwidth over-engineering features like '{scenario_text[:35]}...' before validating demand.\n\nWe built an autonomous daemon that validates sprint value directly from diffs.\n\nOpen to a 5-minute teardown this Thursday?",
                "word_count": 39
            },
            "discovery_questions": [
                f"How does your team currently validate whether '{scenario_text[:35]}...' is actually needed by customers?",
                "How many engineering hours per sprint get burned refactoring features that end up underused?",
                "If an autonomous tool flagged over-engineered PRs before merge, would your team pilot it?"
            ],
            "cal_booking_flow": "Warm reply detected → Auto-dispatches Cal.com 15-min discovery link with founder calendar."
        }

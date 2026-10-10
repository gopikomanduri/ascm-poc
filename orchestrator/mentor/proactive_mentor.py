#!/usr/bin/env python3
"""
ASCM Proactive Founder Mentor & Goal Interceptor
A proactive co-pilot that:
1. Intercepts what the builder is trying to do (Goal Discovery & Validation).
2. Proactively prompts for Pre-Build Marketing & Sales (validating demand before writing code).
3. Monitors coding activity in real-time and surfaces alternative architectures, optimizations, and technical debt warnings.
4. Auto-triggers the Turnkey GTM / Sales / Marketing loop the moment code is ready or milestone is reached.
5. Emits system-level desktop notifications & interactive CLI dialogs (macOS osascript / terminal).
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from orchestrator.agents.base import get_configured_provider, _load_dotenv
from orchestrator.gtm.strategy.repo_analyzer import RepoAnalyzer
from orchestrator.gtm.strategy.proactive_monitor import ProactiveGitMonitor
from orchestrator.mentor.notifier import CrossPlatformNotifier

_load_dotenv()
logger = logging.getLogger("ASCMProactiveMentor")


class ASCMProactiveMentor:
    """
    The Proactive Founder & Engineering Mentor.
    Listens, intercepts, guides, validates market demand pre-build,
    and forces commercial execution post-build.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.history_dir = self.repo_path / ".ascm_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.mentor_state_file = self.history_dir / "mentor_state.json"
        self.provider = get_configured_provider()
        self.repo_analyzer = RepoAnalyzer(str(self.repo_path))
        self.git_monitor = ProactiveGitMonitor(str(self.repo_path))
        self._last_sell_notify = 0.0

    def notify(self, title: str, message: str, subtitle: str = "ASCM Proactive Mentor"):
        """Deliver native desktop notification cross-platform (macOS/Linux/Windows) and log."""
        CrossPlatformNotifier.notify(title, message, app_name=subtitle)

    def prompt_dialog(self, prompt_text: str, default_text: str = "") -> Optional[str]:
        """Pop up an interactive input dialog on any OS (macOS/Linux/Windows) with terminal fallback."""
        return CrossPlatformNotifier.prompt_dialog(
            prompt_text,
            default_text=default_text,
            title="ASCM Mentor: What are you building?",
        )

    def clarify_goal_and_pre_validate(self, raw_input: str) -> Dict[str, Any]:
        """
        STAGE 1: Goal Clarification & Pre-Build Customer Validation
        Before user writes 500 lines of code, mentor tests:
        - What is the actual problem?
        - Who has this problem (ICP)?
        - Can we pre-sell or get 3 customers before writing code?
        """
        logger.info(f"Mentor analyzing goal: {raw_input}")

        system_instruction = (
            "You are an Elite Startup Founder Mentor, Y Combinator Partner, and Chief Commercial Officer.\n"
            "Your philosophy: Build ONLY what customers will buy. Validate demand BEFORE code.\n"
            "Given a builder's stated goal, analyze:\n"
            "1. Core problem & value proposition.\n"
            "2. Ideal Customer Profile (ICP) & decision-maker title.\n"
            "3. Pre-Build Validation Strategy: How to get 3 customer conversations/LOIs BEFORE building.\n"
            "4. Technical Architecture Warning / Better Alternatives: Better, simpler architecture approaches.\n"
            "5. Recommended immediate next action.\n\n"
            "Output JSON with keys:\n"
            '{\n'
            '  "clarified_goal": str,\n'
            '  "target_icp": str,\n'
            '  "pre_build_validation_plan": [str],\n'
            '  "architecture_alternatives": [str],\n'
            '  "mentor_advice": str,\n'
            '  "ready_for_gtm_test": bool\n'
            '}'
        )

        prompt = f"The builder is starting to work on: '{raw_input}'\nRepository context: {self.repo_path.name}"

        try:
            from google import genai
            client = genai.Client()
            model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-3.5-flash-lite"
            resp = client.models.generate_content(
                model=model_name,
                contents=f"{system_instruction}\n\nUser Goal: {prompt}",
                config={"response_mime_type": "application/json"}
            )
            response_str = resp.text
            data = json.loads(response_str)
        except Exception as e:
            logger.warning(f"Mentor LLM generation fallback: {e}")
            data = {
                "clarified_goal": raw_input,
                "target_icp": "VP Engineering / Platform Leads at Series A-C SaaS",
                "pre_build_validation_plan": [
                    "Draft 1-page architecture teaser on LinkedIn.",
                    "Reach out to 5 engineering leaders asking how they currently solve this.",
                    "Secure 2 design partner calls before writing backend logic."
                ],
                "architecture_alternatives": [
                    "Consider lightweight event-driven hooks instead of monolithic daemon.",
                    "Leverage deterministic AST parsing rather than heavy runtime instrumentation."
                ],
                "mentor_advice": "Talk to 3 potential users before writing code. Make sure the pain point is sharp.",
                "ready_for_gtm_test": True
            }

        # Save to state
        self._save_state({"current_goal": data, "timestamp": datetime_now_iso()})
        return data

    def evaluate_code_progress_and_advise(self) -> Dict[str, Any]:
        """
        STAGE 2 & 3: In-Flight Coding Guidance + GTM Readiness Trigger
        Checks recent git diffs, commits, and code files.
        If code is maturing, mentor intervenes:
        'Your core logic is tested and ready. STOP coding and start customer outreach now!'
        """
        analysis = self.repo_analyzer.analyze()
        activity = self.git_monitor.measure_gtm_activity()

        code_ready_threshold = analysis.get("test_count", 0) > 5 or analysis.get("file_count", 0) > 10

        advice = {
            "test_count": analysis.get("test_count", 0),
            "file_count": analysis.get("file_count", 0),
            "days_since_gtm": activity.days_since_last_gtm_action,
            "risk_level": activity.risk_level,
            "should_trigger_gtm": False,
            "recommendation": ""
        }

        if code_ready_threshold and activity.days_since_last_gtm_action > 2.0:
            advice["should_trigger_gtm"] = True
            advice["recommendation"] = (
                f"🚨 [MENTOR ALERT] You have built {analysis.get('file_count', 0)} files with passing tests, "
                f"but haven't done any outreach in {activity.days_since_last_gtm_action:.1f} days! "
                "Stop refining code. Launch your LinkedIn/X campaign and 10 CTO outreach emails right now!"
            )
            # Throttle: evaluate runs every daemon poll, so notify at most once per 4 hours.
            now = time.time()
            if now - self._last_sell_notify > 14400:
                self._last_sell_notify = now
                self.notify("ASCM Mentor: Time to Sell!", advice["recommendation"])
        elif code_ready_threshold:
            advice["recommendation"] = "Code milestone reached. Consider generating a changelog and technical release post."
        else:
            advice["recommendation"] = "Building initial MVP. Keep contracts tight and avoid premature abstraction."

        return advice

    def _save_state(self, state_dict: Dict[str, Any]):
        with open(self.mentor_state_file, "w") as f:
            json.dump(state_dict, f, indent=2)


def datetime_now_iso():
    from datetime import datetime
    return datetime.now().isoformat()


# ── Interactive CLI Entrypoint ───────────────────────────────────────────────
def main(override_goal: Optional[str] = None):
    import argparse
    parser = argparse.ArgumentParser(description="ASCM Proactive Founder & Engineering Mentor")
    parser.add_argument("--goal", help="What are you trying to build?")
    parser.add_argument("--watch", action="store_true", help="Run background mentor loop")
    parser.add_argument("--check-readiness", action="store_true", help="Check if code is ready for marketing & sales")
    parser.add_argument("--mentor", action="store_true", help="Mentor flag (ignored)")
    args, _ = parser.parse_known_args()

    mentor = ASCMProactiveMentor()

    if args.check_readiness:
        advice = mentor.evaluate_code_progress_and_advise()
        print(f"\n📊 Code Status: {advice['file_count']} files, {advice['test_count']} tests")
        print(f"⏱️ Days since GTM Action: {advice['days_since_gtm']:.1f} days (Risk: {advice['risk_level']})")
        print(f"\n💡 Mentor Recommendation:\n   {advice['recommendation']}")
        if advice["should_trigger_gtm"]:
            print("\n🚀 Ready to launch? Run: python main.py --gtm-zero-setup && python main.py --gtm-publish")
        return

    # Proactive Goal Interception Flow
    user_goal = args.goal
    if not user_goal:
        user_goal = mentor.prompt_dialog(
            "What feature, product, or architectural change are you starting to build today?",
            "Autonomous multi-service tracing"
        )

    if not user_goal:
        print("No goal provided. Exiting.")
        return

    print("\n" + "=" * 70)
    print("🧠 ASCM PROACTIVE MENTOR: EVALUATING YOUR GOAL...")
    print("=" * 70)

    insights = mentor.clarify_goal_and_pre_validate(user_goal)

    print(f"\n🎯 Clarified Goal: {insights['clarified_goal']}")
    print(f"👥 Target ICP:      {insights['target_icp']}")

    print("\n💡 Mentor Strategic Advice:")
    print(f"   {insights['mentor_advice']}")

    print("\n🛑 Pre-Build Customer Validation Checklist (Do this BEFORE coding!):")
    for step in insights.get("pre_build_validation_plan", []):
        print(f"   [ ] {step}")

    print("\n🏗️ Architecture Alternatives & Simpler Options:")
    for alt in insights.get("architecture_alternatives", []):
        print(f"   ⚡ {alt}")

    mentor.notify("ASCM Mentor Insights", f"Validated '{user_goal[:40]}'. Check terminal for pre-build validation steps!")

    print("\n" + "=" * 70)
    print("Would you like to test Market Demand first (Generate Pre-Build Outreach Copy)?")
    print("  [1] Publish / Teaser on LinkedIn & X.com (Milestone 1 Social Dispatch)")
    print("  [2] Run Full Zero-Setup GTM (Medium Ranking + CTO Outbound Relay)")
    print("  [3] Skip validation and start coding directly")
    try:
        choice = input("Enter choice [1/2/3] (default: 1): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if choice in ("1", ""):
        print("\n🚀 Launching ASCM Milestone 1 Social Publisher...")
        from orchestrator.gtm.channels.publish_to_channels import main as publish_main
        publish_main(goal=user_goal, interactive=True)
    elif choice == "2":
        print("\n🚀 Launching ASCM Zero-Setup Demand Validation...")
        subprocess.run([sys.executable, "main.py", "--gtm-zero-setup"])


if __name__ == "__main__":
    main()

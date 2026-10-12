#!/usr/bin/env python3
"""ASCM proactive founder mentor and goal interceptor."""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from orchestrator.agents.base import get_configured_provider, _load_dotenv
from orchestrator.gtm.strategy.repo_analyzer import RepoAnalyzer
from orchestrator.gtm.strategy.proactive_monitor import ProactiveGitMonitor
from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger
from orchestrator.mentor.notifier import CrossPlatformNotifier
from orchestrator.mentor.next_best_action import FounderContextStore, NextBestActionEngine

_load_dotenv()
logger = logging.getLogger("ASCMProactiveMentor")


class ASCMProactiveMentor:
    """Founder mentor that separates measured evidence from assumptions."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.history_dir = self.repo_path / ".ascm_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.mentor_state_file = self.history_dir / "mentor_state.json"
        try:
            self.provider = get_configured_provider()
        except RuntimeError:
            # Deterministic monitoring and next-best-action recommendations must work without an LLM key.
            self.provider = None
        self.repo_analyzer = RepoAnalyzer(str(self.repo_path))
        self.git_monitor = ProactiveGitMonitor(str(self.repo_path))
        self.outcome_ledger = OutcomeLedger(self.repo_path)
        self.founder_context = FounderContextStore(self.repo_path)
        self.next_best_action = NextBestActionEngine(self.repo_path)
        self._last_sell_notify = 0.0
        self._last_outcome_notify = 0.0

    def notify(self, title: str, message: str, subtitle: str = "ASCM Proactive Mentor"):
        CrossPlatformNotifier.notify(title, message, app_name=subtitle)

    def prompt_dialog(self, prompt_text: str, default_text: str = "") -> Optional[str]:
        return CrossPlatformNotifier.prompt_dialog(
            prompt_text, default_text=default_text, title="ASCM Mentor: What are you building?"
        )

    def clarify_goal_and_pre_validate(self, raw_input: str) -> Dict[str, Any]:
        logger.info("Mentor analyzing goal: %s", raw_input)
        system_instruction = (
            "You are a pragmatic startup and engineering mentor. Do not assume the product's industry, "
            "customer segment, traction, or technical maturity from the repository name alone.\n"
            "Given the stated goal, analyze the problem/value proposition, likely ICP and decision maker, "
            "a low-cost validation plan, simpler architecture alternatives, and the next action. "
            "Label assumptions explicitly and ask for evidence where necessary.\n"
            "Return JSON keys: clarified_goal (str), target_icp (str), pre_build_validation_plan (list[str]), "
            "architecture_alternatives (list[str]), mentor_advice (str), ready_for_gtm_test (bool)."
        )
        prompt = f"Builder goal: {raw_input}\nRepository: {self.repo_path.name}"
        try:
            from google import genai
            client = genai.Client()
            model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-3.5-flash-lite"
            resp = client.models.generate_content(
                model=model_name,
                contents=f"{system_instruction}\n\n{prompt}",
                config={"response_mime_type": "application/json"},
            )
            data = json.loads(resp.text)
            if not isinstance(data, dict):
                raise ValueError("Mentor response must be a JSON object")
        except Exception as exc:
            logger.warning("Mentor LLM fallback: %s", exc)
            data = {
                "clarified_goal": raw_input,
                "target_icp": "Not yet established — interview users who experience this problem.",
                "pre_build_validation_plan": [
                    "Write down the problem and the evidence that it is frequent and costly.",
                    "Interview 3–5 people who plausibly experience it; ask about current workarounds.",
                    "Record objections and willingness-to-pay evidence before expanding scope.",
                ],
                "architecture_alternatives": [
                    "Start with the smallest testable end-to-end workflow.",
                    "Prefer existing services and deterministic logic until a measured bottleneck justifies complexity.",
                ],
                "mentor_advice": "Treat the customer segment as a hypothesis. Validate the problem before committing to a larger build.",
                "ready_for_gtm_test": False,
            }
        data.setdefault("clarified_goal", raw_input)
        data.setdefault("target_icp", "Not yet established")
        data.setdefault("pre_build_validation_plan", [])
        data.setdefault("architecture_alternatives", [])
        data.setdefault("mentor_advice", "Validate the problem with potential users.")
        data.setdefault("ready_for_gtm_test", False)
        self._save_state({"current_goal": data, "timestamp": datetime_now_iso()})
        # Keep the explicit founder goal available to the decision engine.
        # The clarified goal came from the founder; the suggested ICP may be model-generated
        # and is not persisted as a founder-confirmed fact without explicit confirmation.
        self.founder_context.update(current_goal=data.get("clarified_goal") or raw_input)
        return data

    def recommend_next_action(self, observation: str, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build an explainable recommendation from an explicit observation."""
        recent_events = self.outcome_ledger.recent_events(200)
        return self.next_best_action.recommend(
            observation=observation,
            evidence=evidence or {},
            recent_events=recent_events,
        )

    def evaluate_code_progress_and_advise(self) -> Dict[str, Any]:
        analysis = self.repo_analyzer.analyze()
        activity = self.git_monitor.measure_gtm_activity()

        # File/test counts alone do not establish product readiness. Report them as
        # context and trigger a GTM reminder only when there is evidence of a gap.
        test_count = int(analysis.get("test_count", 0) or 0)
        file_count = int(analysis.get("file_count", 0) or 0)
        days_since_gtm = activity.days_since_last_gtm_action
        milestone = self.git_monitor.get_latest_milestone()
        code_ready_threshold = milestone is not None

        ledger = getattr(self, "outcome_ledger", None)
        recent_events = ledger.recent_events(200) if ledger is not None else []
        observed_outcomes = [event for event in recent_events if event.get("event_type") in {
            "customer_reply", "meeting_booked", "qualified_opportunity", "conversion"
        }]
        generated_cycles = [event for event in recent_events if event.get("event_type") == "gtm_cycle_generated"]
        outcome_feedback = {
            "events_reviewed": len(recent_events),
            "generated_cycles": len(generated_cycles),
            "verified_outcomes": len(observed_outcomes),
            "status": "outcomes_observed" if observed_outcomes else (
                "awaiting_outcomes" if generated_cycles else "no_gtm_cycles_recorded"
            ),
        }

        advice = {
            "test_count": test_count,
            "gtm_outcome_feedback": outcome_feedback,
            "file_count": file_count,
            "days_since_gtm": days_since_gtm,
            "risk_level": activity.risk_level,
            "gtm_history_known": days_since_gtm is not None,
            "should_trigger_gtm": False,
            "milestone": milestone,
            "recommendation": "",
        }

        reminder_hours = max(1, int(os.getenv("ASCM_OUTCOME_REMINDER_HOURS", "24")))
        now_epoch = time.time()
        old_unattributed_cycles = []
        from datetime import datetime, timezone
        for event in generated_cycles:
            experiment_id = event.get("experiment_id")
            linked = [item for item in recent_events if item.get("experiment_id") == experiment_id]
            has_outcome = any(item.get("event_type") in {"customer_reply", "meeting_booked", "qualified_opportunity", "conversion", "experiment_reviewed", "experiment_stopped"} for item in linked)
            try:
                created = datetime.fromisoformat(event.get("occurred_at", "").replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() / 3600
                if not has_outcome and age_hours >= reminder_hours:
                    old_unattributed_cycles.append({"experiment_id": experiment_id, "age_hours": round(age_hours, 1)})
            except (ValueError, TypeError):
                continue
        outcome_feedback["unattributed_cycles_due"] = old_unattributed_cycles
        if old_unattributed_cycles and now_epoch - getattr(self, "_last_outcome_notify", 0.0) > 14400:
            self._last_outcome_notify = now_epoch
            ids = ", ".join(str(item["experiment_id"]) for item in old_unattributed_cycles[:3])
            try:
                self.notify(
                    "ASCM: GTM outcome attribution needed",
                    f"{len(old_unattributed_cycles)} GTM experiment(s) have no recorded customer outcome after {reminder_hours}h. Review: {ids}. Record verified replies, meetings, qualified opportunities, or conversions; do not guess.",
                )
            except Exception as exc:
                logger.debug("Outcome reminder notification failed: %s", exc)

        if outcome_feedback["status"] == "awaiting_outcomes":
            advice["outcome_recommendation"] = (
                "GTM assets were generated, but no customer replies, meetings, qualified opportunities, or conversions "
                "are recorded yet. Capture verified outcomes before judging campaign performance or changing strategy."
            )
        elif outcome_feedback["status"] == "outcomes_observed":
            advice["outcome_recommendation"] = (
                f"{len(observed_outcomes)} verified customer outcome event(s) are recorded. Review outcomes by experiment "
                "before repeating or stopping a campaign."
            )
        else:
            advice["outcome_recommendation"] = "No GTM cycle or outcome history is recorded yet; do not infer performance."

        if days_since_gtm is None:
            advice["recommendation"] = (
                "GTM activity history is unknown, so I won't infer inactivity. Record real customer "
                "contacts, replies, discovery calls, pilots, or campaign publication to enable evidence-based reminders."
            )
        elif code_ready_threshold and days_since_gtm > 2.0:
            advice["should_trigger_gtm"] = True
            advice["recommendation"] = (
                f"An explicitly marked milestone was reached and the last recorded GTM action was {days_since_gtm:.1f} days ago. "
                "Review customer outreach and choose the next validated GTM action; don't stop coding solely because of file counts."
            )
            now = time.time()
            if now - self._last_sell_notify > 14400:
                self._last_sell_notify = now
                self.notify("ASCM Mentor: Review GTM", advice["recommendation"])
        elif code_ready_threshold:
            advice["recommendation"] = "Milestone marked. Review tests, user feedback, and release criteria before expanding scope."
        else:
            advice["recommendation"] = (
                "Keep the MVP scope small. Track a concrete milestone and validate the problem with users; "
                "repository file and test counts alone are not readiness signals."
            )
        return advice

    def _save_state(self, state_dict: Dict[str, Any]):
        self.mentor_state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.mentor_state_file.parent.chmod(0o700)
        except OSError:
            pass
        with open(self.mentor_state_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        try:
            self.mentor_state_file.chmod(0o600)
        except OSError:
            pass


def datetime_now_iso():
    from datetime import datetime
    return datetime.now().astimezone().isoformat()


def main(override_goal: Optional[str] = None):
    import argparse
    parser = argparse.ArgumentParser(description="ASCM Proactive Founder & Engineering Mentor")
    parser.add_argument("--goal", help="What are you trying to build?")
    parser.add_argument("--watch", action="store_true", help="Run background mentor loop")
    parser.add_argument("--check-readiness", action="store_true", help="Check GTM activity and milestones")
    parser.add_argument("--mark-milestone", help="Explicitly record a completed milestone by name")
    parser.add_argument("--observe", choices=sorted(__import__("orchestrator.mentor.next_best_action", fromlist=["SUPPORTED_OBSERVATIONS"]).SUPPORTED_OBSERVATIONS), help="Evaluate an explicitly observed event for a next-best-action recommendation")
    parser.add_argument("--task-description", help="Task details accompanying code_activity/coding_started")
    parser.add_argument("--discover-repos", action="store_true", help="Search public GitHub repositories for a supplied coding task")
    parser.add_argument("--propose-action", help="Persist one action from --observe as a proposal (action_type)")
    parser.add_argument("--approve-proposal", help="Record founder approval for a previously saved proposal ID; does not execute it")
    parser.add_argument("--reject-proposal", help="Record founder rejection for a previously saved proposal ID")
    parser.add_argument("--mentor", action="store_true", help="Mentor flag (ignored)")
    args, _ = parser.parse_known_args()
    if args.approve_proposal and args.reject_proposal:
        parser.error("choose only one of --approve-proposal or --reject-proposal")
    if args.propose_action and not args.observe:
        parser.error("--propose-action requires --observe")
    mentor = ASCMProactiveMentor()

    if args.mark_milestone:
        milestone = mentor.git_monitor.record_milestone(args.mark_milestone)
        print("Recorded milestone: {} ({})".format(milestone["name"], milestone["occurred_at"]))
        return

    if args.approve_proposal or args.reject_proposal:
        proposal_id = args.approve_proposal or args.reject_proposal
        decision = mentor.next_best_action.record_approval(proposal_id, approved=bool(args.approve_proposal))
        print(json.dumps(decision, indent=2))
        print("Consent recorded only; no code, outreach, or publication was executed.")
        return

    if args.observe:
        evidence = {"task_description": args.task_description} if args.task_description else {}
        result = mentor.recommend_next_action(args.observe, evidence)
        if args.propose_action:
            proposal = mentor.next_best_action.propose_action(result, args.propose_action)
            print(json.dumps(proposal, indent=2))
            print("Proposal recorded; it has not been executed.")
            return
        print("\\nASCM Next-Best-Action Recommendation")
        print("Goal: {}".format(result.get("goal") or "not configured"))
        for index, action in enumerate(result.get("actions", []), 1):
            print("\\n{}. {} [{}]".format(index, action["title"], action["confidence"]))
            print("   Why: {}".format(action["rationale"]))
            print("   Benefit: {}".format(action["expected_benefit"]))
            if action["requires_approval"]:
                print("   Approval required before external execution.")
        if args.discover_repos:
            if not args.task_description:
                print("\\nRepository discovery needs --task-description; no search was performed.")
            else:
                from orchestrator.mentor.reuse_advisor import GitHubRepositoryAdvisor
                discovery = GitHubRepositoryAdvisor().search(args.task_description)
                print("\\nOpen-source candidates (review before adoption):")
                if discovery.get("error"):
                    print("   " + discovery["error"])
                for repo in discovery.get("repositories", []):
                    print("   - {name} | stars: {stars} | license: {license} | pushed: {last_updated} | archived: {archived}".format(**repo))
                    print("     {url}".format(**repo))
                    if repo.get("description"):
                        print("     " + repo["description"])
                print("   " + discovery["caveat"])
        print("\\n{}".format(result["disclaimer"]))
        return

    if args.check_readiness:
        advice = mentor.evaluate_code_progress_and_advise()
        print(f"\n📊 Code Status: {advice['file_count']} files, {advice['test_count']} tests")
        days = advice["days_since_gtm"]
        print(f"⏱️ Days since GTM Action: {days:.1f} days (Risk: {advice['risk_level']})" if days is not None
              else f"⏱️ Days since GTM Action: unknown (Risk: {advice['risk_level']})")
        print(f"\n💡 Mentor Recommendation:\n   {advice['recommendation']}")
        print(f"\n📈 Outcome Attribution:\n   {advice.get('outcome_recommendation', 'No outcome feedback available.')}")
        for pending in advice.get("gtm_outcome_feedback", {}).get("unattributed_cycles_due", []):
            print(f"   [ ] Review {pending['experiment_id']} ({pending['age_hours']}h old): record a verified outcome or mark the experiment reviewed/stopped.")
        if advice.get("gtm_outcome_feedback", {}).get("status") == "outcomes_observed":
            print("   Prompt: What evidence explains this result, and what customer action or experiment should happen next?")
        if advice["should_trigger_gtm"]:
            print("\n🚀 Review the next GTM action and release criteria.")
        return

    user_goal = args.goal or override_goal
    if not user_goal:
        user_goal = mentor.prompt_dialog(
            "What feature, product, or architectural change are you starting to build today?", ""
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
    print("\n💡 Mentor Strategic Advice:\n   " + insights['mentor_advice'])
    print("\n🛑 Customer validation checklist:")
    for step in insights.get("pre_build_validation_plan", []):
        print(f"   [ ] {step}")
    print("\n🏗️ Architecture alternatives:")
    for alt in insights.get("architecture_alternatives", []):
        print(f"   ⚡ {alt}")
    mentor.notify("ASCM Mentor Insights", f"Reviewed '{user_goal[:40]}'. Check terminal for next steps.")
    print("\nChoose a next step:")
    print("  [1] Generate a social teaser")
    print("  [2] Run the GTM workflow")
    print("  [3] Skip and continue coding")
    try:
        choice = input("Enter choice [1/2/3] (default: 1): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "3"
    if choice == "1":
        from orchestrator.gtm.channels.publish_to_channels import main as publish_main
        publish_main(goal=user_goal, interactive=True)
    elif choice == "2":
        subprocess.run([sys.executable, "main.py", "--gtm-zero-setup"], check=False)


if __name__ == "__main__":
    main()

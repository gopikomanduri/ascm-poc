"""Evidence-driven next-best-action engine for the ASCM founder mentor.

This module deliberately separates observation from inference and recommendation
from execution. It is a local MVP: callers provide observed events, the engine
uses saved founder context to rank next steps, and consequential actions require
an explicit approval recorded by the caller. It does not silently run code or
publish external content.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


OUTCOME_EVENTS = {
    "customer_reply", "meeting_booked", "qualified_opportunity", "conversion",
}
RESOLVING_EXPERIMENT_EVENTS = {"experiment_reviewed", "experiment_stopped"}
SUPPORTED_OBSERVATIONS = {
    "coding_started", "code_activity", "tests_passed", "milestone_completed",
    "gtm_cycle_generated", "campaign_published", "customer_reply",
    "meeting_booked", "qualified_opportunity", "conversion",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FounderContextStore:
    """Persist explicit founder goals and constraints in the project history."""

    def __init__(self, project_path: str | Path = "."):
        self.project_path = Path(project_path).resolve()
        self.history_dir = self.project_path / ".ascm_history"
        self.path = self.history_dir / "founder_context.json"

    def load(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._empty()
        except (OSError, json.JSONDecodeError):
            return self._empty()

    @staticmethod
    def _empty() -> Dict[str, Any]:
        return {
            "current_goal": None,
            "current_task": None,
            "target_customer": None,
            "next_milestone": None,
            "constraints": [],
            "preferences": {},
            "updated_at": None,
        }

    def update(
        self,
        *,
        current_goal: Optional[str] = None,
        current_task: Optional[str] = None,
        target_customer: Optional[str] = None,
        next_milestone: Optional[str] = None,
        constraints: Optional[Iterable[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        state = self.load()
        for key, value in (
            ("current_goal", current_goal),
            ("current_task", current_task),
            ("target_customer", target_customer),
            ("next_milestone", next_milestone),
        ):
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{key} must be a non-empty string when provided")
                state[key] = value.strip()
        if constraints is not None:
            clean = [item.strip() for item in constraints if isinstance(item, str) and item.strip()]
            state["constraints"] = clean
        if preferences is not None:
            if not isinstance(preferences, dict):
                raise ValueError("preferences must be a dictionary")
            state["preferences"] = preferences
        state["updated_at"] = _utc_now()
        self.history_dir.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temp.replace(self.path)
        return state


class NextBestActionEngine:
    """Rank explainable recommendations from explicit context and observed evidence."""

    def __init__(self, project_path: str | Path = "."):
        self.project_path = Path(project_path).resolve()
        self.history_dir = self.project_path / ".ascm_history"
        self.context_store = FounderContextStore(self.project_path)
        self.proposals_path = self.history_dir / "action_proposals.json"

    def recommend(
        self,
        *,
        observation: str,
        evidence: Optional[Dict[str, Any]] = None,
        recent_events: Optional[list[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if observation not in SUPPORTED_OBSERVATIONS:
            raise ValueError(f"Unsupported observation: {observation}")
        evidence = evidence or {}
        if not isinstance(evidence, dict):
            raise ValueError("evidence must be a dictionary")
        context = self.context_store.load()
        goal = context.get("current_goal")
        actions = []

        def add(action_type: str, title: str, rationale: str, benefit: str,
                requires_approval: bool = False, confidence: str = "medium") -> None:
            actions.append({
                "action_type": action_type,
                "title": title,
                "rationale": rationale,
                "expected_benefit": benefit,
                "requires_approval": requires_approval,
                "confidence": confidence,
            })

        if not goal:
            add(
                "clarify_goal", "Clarify the current goal",
                "The mentor has no explicit current goal, so it cannot reliably judge whether this activity is the right priority.",
                "Make later recommendations specific to a founder outcome.",
                confidence="high",
            )
        elif observation in {"coding_started", "code_activity"}:
            if evidence.get("task_description"):
                add(
                    "check_reuse_before_building", "Check whether an existing solution is better",
                    "Observed task: " + str(evidence.get("task_description", "unspecified task"))[:240] + ". A task description and goal do not by themselves prove that custom implementation is necessary.",
                    "Compare build-versus-integrate options before investing more engineering time.",
                    requires_approval=False, confidence="medium",
                )
                add(
                    "continue_with_milestone", "Define the smallest testable milestone",
                    "Continue only against a measurable slice that advances the stated goal.",
                    "Keep scope small and make progress verifiable.",
                    confidence="medium",
                )
            else:
                add(
                    "clarify_task", "Ask what this coding work is intended to achieve",
                    "The observed event does not include enough detail to infer the task or recommend an implementation.",
                    "Avoid interrupting with an unsupported technical opinion.",
                    confidence="high",
                )
        elif observation == "tests_passed":
            add(
                "verify_milestone", "Check the milestone and user-validation gap",
                "Passing tests is engineering evidence, not proof of customer demand or launch readiness.",
                "Decide whether to run a small user-validation or release-readiness step next.",
                confidence="medium",
            )
        elif observation == "milestone_completed":
            add(
                "review_gtm_readiness", "Review whether customer validation is the next priority",
                "A reported milestone is a useful signal, but market readiness depends on the milestone and customer evidence.",
                "Choose between another build step, customer discovery, or a limited GTM test.",
                confidence="medium",
            )
        elif observation == "gtm_cycle_generated":
            add(
                "approve_campaign", "Review the GTM assets before publishing",
                "Generating campaign content does not mean it is approved or published.",
                "Let the founder review audience, claims, and channel before external distribution.",
                requires_approval=True, confidence="high",
            )
        elif observation == "campaign_published":
            add(
                "measure_outcomes", "Record and review real customer outcomes",
                "Publication is an execution event, not evidence of campaign success.",
                "Capture verified replies, meetings, qualified opportunities, or conversions.",
                confidence="high",
            )
        elif observation in OUTCOME_EVENTS:
            add(
                "review_experiment", "Review the experiment and choose the next customer action",
                "A customer outcome is evidence to interpret in context, not a conclusion about overall product-market fit.",
                "Preserve what was learned and decide whether to follow up, adjust, repeat, or stop.",
                confidence="high",
            )

        events = recent_events or []
        pending = []
        for event in events:
            if event.get("event_type") != "gtm_cycle_generated":
                continue
            experiment_id = event.get("experiment_id")
            linked = [item for item in events if item.get("experiment_id") == experiment_id]
            resolved = any(item.get("event_type") in OUTCOME_EVENTS | RESOLVING_EXPERIMENT_EVENTS for item in linked)
            if not resolved and experiment_id:
                pending.append(experiment_id)
        if pending and observation not in {"gtm_cycle_generated", "campaign_published"}:
            add(
                "attribute_gtm_outcomes", "Review pending GTM experiments",
                f"{len(pending)} generated experiment(s) have no linked outcome or explicit review/stop event in the supplied history.",
                "Avoid repeating or abandoning campaigns without evidence.",
                confidence="medium",
            )

        return {
            "goal": goal,
            "observation": observation,
            "evidence": evidence,
            "actions": actions,
            "requires_founder_input": any(a["action_type"] in {"clarify_goal", "clarify_task"} for a in actions),
            "generated_at": _utc_now(),
            "disclaimer": "Recommendations are evidence-limited. No code change, message, or publication is executed by this engine.",
        }

    def propose_action(self, recommendation: Dict[str, Any], action_type: str) -> Dict[str, Any]:
        """Persist a proposed action as pending approval; this method never executes it."""
        matches = [item for item in recommendation.get("actions", []) if item.get("action_type") == action_type]
        if not matches:
            raise ValueError(f"Action {action_type!r} is not present in this recommendation")
        action = matches[0]
        proposal = {
            "proposal_id": str(uuid.uuid4()),
            "action_type": action_type,
            "title": action["title"],
            "status": "pending_approval" if action.get("requires_approval") else "proposed",
            "created_at": _utc_now(),
            "goal": recommendation.get("goal"),
            "observation": recommendation.get("observation"),
            "rationale": action.get("rationale"),
        }
        self.history_dir.mkdir(parents=True, exist_ok=True)
        try:
            proposals = json.loads(self.proposals_path.read_text(encoding="utf-8"))
            if not isinstance(proposals, list):
                proposals = []
        except (OSError, json.JSONDecodeError):
            proposals = []
        proposals.append(proposal)
        temp = self.proposals_path.with_suffix(".tmp")
        temp.write_text(json.dumps(proposals, indent=2), encoding="utf-8")
        temp.replace(self.proposals_path)
        return proposal

    def record_approval(self, proposal_id: str, *, approved: bool, actor: str = "founder") -> Dict[str, Any]:
        """Record founder consent. Execution remains the responsibility of an authorized adapter."""
        try:
            proposals = json.loads(self.proposals_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            proposals = []
        for proposal in proposals:
            if proposal.get("proposal_id") == proposal_id:
                if proposal.get("status") not in {"pending_approval", "proposed"}:
                    raise ValueError("Proposal has already been resolved")
                proposal["status"] = "approved" if approved else "rejected"
                proposal["decision_by"] = actor
                proposal["decided_at"] = _utc_now()
                temp = self.proposals_path.with_suffix(".tmp")
                temp.write_text(json.dumps(proposals, indent=2), encoding="utf-8")
                temp.replace(self.proposals_path)
                return proposal
        raise KeyError(f"Unknown proposal id: {proposal_id}")

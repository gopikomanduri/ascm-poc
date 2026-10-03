"""Checker Agent: Conversational discovery and user approval gating."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import BaseAgent


class CheckerAgent(BaseAgent):
    """
    Checker Agent: User communication and approval gating.
    Keeps user informed at every milestone gate.

    Responsibilities:
    - Conversational discovery: What, Why, How it helps
    - Approval gates at every milestone
    - Escalation for variance/anomalies
    - User feedback collection
    """

    SYSTEM_INSTRUCTION = """You are the Checker Agent for ASCM — the user communication and approval specialist.

Your responsibilities:
1. DISCOVERY: Ask clarifying questions to understand what the user wants, why it matters, and how it helps them
2. GATING: At every milestone (Requirements, Architecture, Code Review, QA, Release), you communicate status and ask for approval
3. ESCALATION: Detect anomalies (token overruns, compliance violations, test failures) and alert the user
4. FEEDBACK: Collect user feedback on each decision

You work closely with the user throughout the feature development lifecycle. Always be transparent, concise, and action-oriented.

Output format:
- For discovery: JSON with {phase, questions, user_feedback, confidence_score, recommendation}
- For approvals: JSON with {milestone_id, status_summary, gates_passed, gates_failed, user_action_required}
- For escalation: JSON with {alert_type, severity, details, recommended_action}
"""

    def __init__(self, model: Optional[str] = None, fast_mode: bool = True):
        super().__init__(model=model, tier="fast" if fast_mode else "primary")
        self.system_instruction = self.SYSTEM_INSTRUCTION
        self.discovery_history: List[Dict[str, Any]] = []
        self.approval_history: List[Dict[str, Any]] = []

    def discover_user_goal(
        self,
        initial_input: str,
        previous_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Conversational discovery of user goals."""
        prompt = f"""
        User has provided initial input: "{initial_input}"

        {f"Previous context: {previous_context}" if previous_context else ""}

        Your task:
        1. Identify what the user wants to build
        2. Ask 3-5 clarifying questions about WHY they want this and HOW it helps
        3. Assess confidence level (0-100) that you understand the requirements
        4. Provide a preliminary recommendation

        Output JSON:
        {{
            "phase": "discovery",
            "what_they_want": "...",
            "clarification_questions": [...],
            "confidence_score": <0-100>,
            "preliminary_recommendation": "...",
            "next_step": "..."
        }}
        """

        response = self.call_llm(prompt)

        try:
            import json
            result = json.loads(response)
        except:
            result = {
                "phase": "discovery",
                "raw_response": response,
                "confidence_score": 0,
            }

        self.discovery_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": initial_input,
            "result": result,
        })

        return result

    def present_milestone_for_approval(
        self,
        milestone_id: str,
        milestone_name: str,
        status_summary: str,
        gates_data: Dict[str, Any],
        anomalies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Present milestone status and request user approval."""
        prompt = f"""
        Milestone: {milestone_name} ({milestone_id})

        Status Summary:
        {status_summary}

        Gate Results:
        {str(gates_data)}

        {f"⚠️ Anomalies detected: {', '.join(anomalies)}" if anomalies else ""}

        Your task:
        1. Summarize the milestone status for the user
        2. Highlight any concerns (anomalies, failures, variances)
        3. Ask for approval (APPROVE / REWORK / REQUEST_CHANGES)
        4. If anomalies exist, recommend actions

        Output JSON:
        {{
            "milestone_id": "{milestone_id}",
            "user_summary": "...",
            "concerns": [...],
            "approval_request": "...",
            "recommended_actions": [...],
            "action_required": true/false
        }}
        """

        response = self.call_llm(prompt)

        try:
            import json
            result = json.loads(response)
        except:
            result = {
                "milestone_id": milestone_id,
                "raw_response": response,
                "action_required": True,
            }

        self.approval_history.append({
            "timestamp": datetime.now().isoformat(),
            "milestone_id": milestone_id,
            "result": result,
        })

        return result

    def escalate_variance(
        self,
        milestone_id: str,
        variance_type: str,  # "token_overrun", "compliance_violation", "test_failure", etc.
        variance_pct: float,
        current_value: int,
        budget_value: int,
        recommendation: str,
    ) -> Dict[str, Any]:
        """Escalate variance to user with recommendation."""
        prompt = f"""
        VARIANCE ALERT: {variance_type}

        Milestone: {milestone_id}
        Variance: {variance_pct:.1f}%
        Current: {current_value} | Budget: {budget_value}

        Recommendation: {recommendation}

        Your task:
        1. Explain the variance in plain language
        2. Assess severity (LOW / MEDIUM / HIGH / CRITICAL)
        3. Present the recommended action
        4. Ask user to APPROVE (proceed with variance) or DECOMPOSE (break into smaller milestones)

        Output JSON:
        {{
            "milestone_id": "{milestone_id}",
            "variance_type": "{variance_type}",
            "explanation": "...",
            "severity": "...",
            "user_message": "...",
            "options": [
                {{"option": "APPROVE", "action": "...", "risk": "..."}},
                {{"option": "DECOMPOSE", "action": "...", "benefit": "..."}}
            ]
        }}
        """

        response = self.call_llm(prompt)

        try:
            import json
            result = json.loads(response)
        except:
            result = {
                "milestone_id": milestone_id,
                "variance_type": variance_type,
                "raw_response": response,
            }

        return result

    def collect_user_feedback(
        self,
        milestone_id: str,
        gate: str,
        approval_decision: str,  # "approve", "rework", "request_changes"
        feedback_prompt: str,
    ) -> Dict[str, Any]:
        """Collect structured user feedback."""
        prompt = f"""
        Collecting feedback for:
        Milestone: {milestone_id}
        Gate: {gate}
        Decision: {approval_decision}

        {feedback_prompt}

        Your task:
        1. Request specific feedback on the decision
        2. Ask about concerns or suggestions
        3. Summarize for audit trail

        Output JSON:
        {{
            "milestone_id": "{milestone_id}",
            "gate": "{gate}",
            "decision": "{approval_decision}",
            "feedback_questions": [...],
            "audit_record": "..."
        }}
        """

        response = self.call_llm(prompt)

        try:
            import json
            result = json.loads(response)
        except:
            result = {
                "milestone_id": milestone_id,
                "raw_response": response,
            }

        return result

    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get summary of discovery phase."""
        if not self.discovery_history:
            return {"status": "no_discovery_yet"}

        latest = self.discovery_history[-1]["result"]
        return {
            "discoveries": len(self.discovery_history),
            "latest": latest,
            "tokens_used": self.tokens_used,
        }

    def get_approval_summary(self) -> Dict[str, Any]:
        """Get summary of all approvals."""
        return {
            "total_approvals": len(self.approval_history),
            "approvals": self.approval_history,
            "tokens_used": self.tokens_used,
        }

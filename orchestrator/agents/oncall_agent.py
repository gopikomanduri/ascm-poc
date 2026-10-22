"""On-Call Agent: Incident response, root cause analysis, automated fixes."""
from typing import Dict, Any, Optional, List
import json
from .base import BaseAgent


class OnCallAgent(BaseAgent):
    """Incident Response: APM alerts -> RCA -> Fix proposal."""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        provider: Optional[Any] = None,
        tier: str = "fast",
        model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            system_instruction=system_instruction or "You are an On-Call Incident Response Agent.",
            provider=provider,
            tier=tier,
            model=model,
        )

    def run(self, alert: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Unified entrypoint for alert handling and incident analysis."""
        active_alert = alert or kwargs.get("alert_data", {"id": "alert-default", "severity": "WARNING"})
        received = self.receive_alert(active_alert)
        logs = kwargs.get("logs", ["Incident triggered by system alert"])
        rca = self.analyze_logs(received.get("alert_id", "alert-default"), logs)
        if rca["root_causes"]:
            fix = self.propose_fix(rca["root_causes"][0], rca["affected_services"])
        else:
            fix = {"status": "no_fix_proposed", "reason": rca.get("reason", "no root cause identified"),
                   "user_approval_required": True}
        return {
            "received": received,
            "root_cause_analysis": rca,
            "proposed_fix": fix,
        }

    def receive_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Receive APM alert."""
        return {
            "alert_id": alert.get("id"),
            "severity": alert.get("severity"),
            "received_at": alert.get("timestamp"),
        }

    def analyze_logs(self, alert_id: str, logs: List[str]) -> Dict[str, Any]:
        """Log analysis is not implemented. No root cause is claimed rather than inventing one."""
        return {
            "alert_id": alert_id,
            "status": "analysis_not_performed",
            "root_causes": [],
            "affected_services": [],
            "reason": "automated log analysis is not implemented; investigate manually",
            "log_lines_received": len(logs),
        }

    def propose_fix(self, root_cause: str, affected_services: List[str]) -> Dict[str, Any]:
        """Propose incident fix."""
        return {
            "root_cause": root_cause,
            "proposed_fix": "Scale database connections + restart settlement-service",
            "risk_level": "MEDIUM",
            "user_approval_required": True,
            "estimated_fix_time_sec": 60,
        }

    def execute_fix(self, fix_id: str, approval: bool) -> Dict[str, Any]:
        """Execute fix if approved."""
        if not approval:
            return {"status": "pending_approval", "executed": False}

        return {
            "fix_id": fix_id,
            "status": "not_executed",
            "executed": False,
            "incident_resolved": False,
            "reason": "automated remediation is not implemented; apply the fix manually and verify it",
        }

"""Enhanced Orchestrator Agent: Milestone tracking, token budgeting, variance detection."""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from .milestone.tracker import MilestoneTracker
from .milestone.excel_export import MilestoneExcelExporter
from .milestone.models import Milestone, MilestoneStatus, UserApprovalGate


class OrchestratorAgent:
    """
    Enhanced Orchestrator Agent: Orchestrates all agents with milestone tracking and token budgeting.

    Responsibilities:
    - Create and track milestones with token budgets
    - Orchestrate agent execution with variance detection
    - Export milestone reports to Excel
    - Maintain audit trail with tamper-evident logging
    - Coordinate user approvals at every gate
    """

    def __init__(self, run_id: str, log_dir: str = "logs/runs"):
        self.run_id = run_id
        self.log_dir = log_dir
        self.run_log_dir = os.path.join(log_dir, run_id)
        os.makedirs(self.run_log_dir, exist_ok=True)

        # Initialize milestone tracking
        milestone_log = os.path.join(self.run_log_dir, "milestone_tracking.log")
        self.tracker = MilestoneTracker(run_id=run_id, log_file=milestone_log)

        # Initialize Excel exporter
        try:
            self.excel_exporter = MilestoneExcelExporter(output_dir=os.path.join(self.run_log_dir, "exports"))
        except ImportError:
            self.excel_exporter = None

        self.current_milestone: Optional[Milestone] = None
        self.execution_log: List[Dict[str, Any]] = []

    def start_milestone(
        self,
        milestone_id: str,
        name: str,
        feature_goal: str,
        budget_p90_tokens: int,
        deadline_minutes: int = 60,
    ) -> Milestone:
        """Start a new milestone with token budget."""
        milestone = self.tracker.create_milestone(
            milestone_id=milestone_id,
            name=name,
            feature_goal=feature_goal,
            budget_p90_tokens=budget_p90_tokens,
            deadline_minutes=deadline_minutes,
        )

        self.current_milestone = milestone

        self._log({
            "event_type": "MILESTONE_START",
            "milestone_id": milestone_id,
            "budget_tokens": budget_p90_tokens,
        })

        return milestone

    def execute_agent_task(
        self,
        agent_name: str,
        task_id: str,
        agent_callable: Callable,
        agent_input: Dict[str, Any],
        expected_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Execute an agent task with token tracking."""
        if not self.current_milestone:
            raise RuntimeError("No active milestone. Call start_milestone first.")

        milestone = self.current_milestone
        milestone_id = milestone.id

        # Add task to milestone
        self.tracker.add_task(milestone_id, task_id, agent_name)

        self._log({
            "event_type": "TASK_START",
            "milestone_id": milestone_id,
            "task_id": task_id,
            "agent": agent_name,
            "expected_tokens": expected_tokens,
        })

        try:
            # Execute agent
            result = agent_callable(**agent_input)

            # Extract token usage from result (if available)
            tokens_used = result.get("tokens_used", expected_tokens) if isinstance(result, dict) else expected_tokens

            # Complete task
            self.tracker.complete_task(milestone_id, task_id, tokens_used=tokens_used)

            self._log({
                "event_type": "TASK_COMPLETE",
                "milestone_id": milestone_id,
                "task_id": task_id,
                "agent": agent_name,
                "tokens_used": tokens_used,
            })

            return {
                "status": "success",
                "result": result,
                "tokens_used": tokens_used,
            }

        except Exception as e:
            error_msg = str(e)
            self.tracker.complete_task(milestone_id, task_id, tokens_used=0, error=error_msg)

            self._log({
                "event_type": "TASK_FAILED",
                "milestone_id": milestone_id,
                "task_id": task_id,
                "agent": agent_name,
                "error": error_msg,
            })

            return {
                "status": "failed",
                "error": error_msg,
                "tokens_used": 0,
            }

    def check_variance(self, milestone_id: Optional[str] = None) -> Dict[str, Any]:
        """Check token budget variance and return status."""
        if milestone_id is None and self.current_milestone:
            milestone_id = self.current_milestone.id

        if not milestone_id:
            raise ValueError("No milestone ID provided and no active milestone")

        milestone = self.tracker.get_milestone(milestone_id)
        if not milestone:
            raise ValueError(f"Milestone {milestone_id} not found")

        variance = ((milestone.spent_tokens - milestone.budget_p90_tokens) / milestone.budget_p90_tokens * 100) if milestone.budget_p90_tokens > 0 else 0

        return {
            "milestone_id": milestone_id,
            "budget": milestone.budget_p90_tokens,
            "spent": milestone.spent_tokens,
            "variance_pct": variance,
            "utilization_flag": milestone.utilization_flag,
            "status": milestone.status.value,
            "needs_user_approval": milestone.utilization_flag in ["YELLOW", "RED"],
        }

    def request_user_approval(
        self,
        milestone_id: str,
        gate: str,
        approved_by: str,
        action: str,  # "approve" | "rework" | "request_changes"
        feedback: str = "",
        token_override: bool = False,
        new_budget: Optional[int] = None,
    ) -> bool:
        """Record user approval or rejection."""
        if action == "approve":
            return self.tracker.approve_milestone(
                milestone_id=milestone_id,
                gate=gate,
                approved_by=approved_by,
                feedback=feedback,
                token_override=token_override,
                new_budget=new_budget,
            )
        elif action in ["rework", "request_changes"]:
            return self.tracker.reject_milestone(
                milestone_id=milestone_id,
                gate=gate,
                approved_by=approved_by,
                feedback=feedback,
            )
        else:
            raise ValueError(f"Invalid action: {action}")

    def complete_milestone(self, milestone_id: Optional[str] = None) -> Dict[str, Any]:
        """Mark milestone as completed."""
        if milestone_id is None and self.current_milestone:
            milestone_id = self.current_milestone.id

        if not milestone_id:
            raise ValueError("No milestone ID provided")

        self.tracker.complete_milestone(milestone_id)
        self.current_milestone = None

        milestone = self.tracker.get_milestone(milestone_id)

        self._log({
            "event_type": "MILESTONE_COMPLETED",
            "milestone_id": milestone_id,
            "total_tokens": milestone.spent_tokens,
            "budget": milestone.budget_p90_tokens,
        })

        return {
            "milestone_id": milestone_id,
            "status": "completed",
            "total_tokens": milestone.spent_tokens,
            "budget": milestone.budget_p90_tokens,
        }

    def export_milestones_to_excel(self, filename: Optional[str] = None) -> Optional[str]:
        """Export all milestones to Excel."""
        if not self.excel_exporter:
            print("Warning: openpyxl not available. Excel export skipped.")
            return None

        milestones = self.tracker.get_all_milestones()
        metrics = self.tracker.get_metrics()

        filepath = self.excel_exporter.export(
            milestones=milestones,
            metrics=metrics,
            filename=filename,
        )

        self._log({
            "event_type": "EXCEL_EXPORT",
            "filepath": filepath,
            "total_milestones": len(milestones),
        })

        return filepath

    def get_milestone_status(self, milestone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get status of a milestone."""
        if milestone_id is None and self.current_milestone:
            milestone_id = self.current_milestone.id

        if not milestone_id:
            return None

        milestone = self.tracker.get_milestone(milestone_id)
        if not milestone:
            return None

        return {
            "id": milestone.id,
            "name": milestone.name,
            "status": milestone.status.value,
            "budget": milestone.budget_p90_tokens,
            "spent": milestone.spent_tokens,
            "variance_pct": milestone.variance_pct,
            "tasks_count": len(milestone.tasks),
            "tasks_completed": sum(1 for t in milestone.tasks if t.status == "completed"),
            "tests_passed_pct": milestone.quality_gates.tests_passed_pct,
            "compliance_passed": milestone.quality_gates.compliance_passed,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        metrics = self.tracker.get_metrics()

        return {
            "total_milestones": metrics.total_milestones,
            "completed": metrics.completed_milestones,
            "on_track": metrics.on_track,
            "at_risk": metrics.at_risk,
            "blocked": metrics.blocked,
            "total_budget": metrics.total_budget,
            "total_spent": metrics.total_spent,
            "total_variance_pct": metrics.total_variance_pct,
            "avg_test_coverage": metrics.avg_test_coverage,
            "compliance_pass_rate": metrics.compliance_pass_rate,
            "rework_rate_pct": metrics.rework_rate_pct,
        }

    def _log(self, event: Dict[str, Any]) -> None:
        """Log event to execution log."""
        event["timestamp"] = datetime.now().isoformat()
        event["run_id"] = self.run_id
        self.execution_log.append(event)

        # Also write to JSON log file
        log_file = os.path.join(self.run_log_dir, "orchestrator_execution.jsonl")
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

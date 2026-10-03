"""Milestone tracking with real-time variance detection."""
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from .models import Milestone, MilestoneStatus, TaskMetric, MilestoneMetrics, UserApproval


class MilestoneTracker:
    """Track milestones with token budgeting, variance detection, and audit trail."""

    def __init__(self, run_id: str, log_file: str = ""):
        self.run_id = run_id
        self.log_file = log_file
        self.milestones: Dict[str, Milestone] = {}
        self.last_event_hash = ""
        self.start_time = datetime.now()

    def create_milestone(
        self,
        milestone_id: str,
        name: str,
        feature_goal: str,
        budget_p90_tokens: int,
        deadline_minutes: int = 60,
    ) -> Milestone:
        """Create a new milestone with token budget allocation."""
        milestone = Milestone(
            id=milestone_id,
            name=name,
            feature_goal=feature_goal,
            budget_p90_tokens=budget_p90_tokens,
            start_time=datetime.now(),
            deadline=datetime.now() + timedelta(minutes=deadline_minutes),
            log_file=f"logs/runs/{self.run_id}/milestone_{milestone_id}.log",
        )
        self.milestones[milestone_id] = milestone
        self._log_event(
            event_type="MILESTONE_CREATED",
            milestone_id=milestone_id,
            budget=budget_p90_tokens,
        )
        return milestone

    def add_task(
        self,
        milestone_id: str,
        task_id: str,
        agent_name: str,
    ) -> None:
        """Add a task to a milestone."""
        if milestone_id not in self.milestones:
            raise ValueError(f"Milestone {milestone_id} not found")

        task = TaskMetric(
            task_id=task_id,
            assigned_agent=agent_name,
            status="pending",
            start_time=datetime.now(),
        )
        self.milestones[milestone_id].tasks.append(task)

    def complete_task(
        self,
        milestone_id: str,
        task_id: str,
        tokens_used: int,
        error: Optional[str] = None,
    ) -> None:
        """Mark a task as completed and update token tracking."""
        if milestone_id not in self.milestones:
            raise ValueError(f"Milestone {milestone_id} not found")

        milestone = self.milestones[milestone_id]
        task = next((t for t in milestone.tasks if t.task_id == task_id), None)

        if not task:
            raise ValueError(f"Task {task_id} not found in milestone {milestone_id}")

        now = datetime.now()
        task.end_time = now
        task.status = "failed" if error else "completed"
        task.tokens_used = tokens_used
        task.error_message = error

        if task.start_time:
            task.duration_seconds = (now - task.start_time).total_seconds()

        # Update milestone totals
        milestone.spent_tokens += tokens_used
        milestone.duration_seconds = (now - milestone.start_time).total_seconds()

        # Detect variance
        self._detect_variance(milestone_id)

        self._log_event(
            event_type="TASK_COMPLETED",
            milestone_id=milestone_id,
            task_id=task_id,
            agent=task.assigned_agent,
            tokens_used=tokens_used,
            error=error,
        )

    def _detect_variance(self, milestone_id: str) -> None:
        """Detect and flag token budget variance."""
        milestone = self.milestones[milestone_id]

        # Calculate variance percentage
        if milestone.budget_p90_tokens > 0:
            variance = ((milestone.spent_tokens - milestone.budget_p90_tokens) / milestone.budget_p90_tokens) * 100
            milestone.variance_pct = variance
        else:
            variance = 0.0

        # Set utilization flag
        if milestone.spent_tokens <= (milestone.budget_p90_tokens * 0.75):
            milestone.utilization_flag = "GREEN"
            milestone.status = MilestoneStatus.GREEN
        elif milestone.spent_tokens <= milestone.budget_p90_tokens:
            milestone.utilization_flag = "YELLOW"
            milestone.status = MilestoneStatus.YELLOW
        else:
            milestone.utilization_flag = "RED"
            milestone.status = MilestoneStatus.RED

        # Log variance detection
        if milestone.utilization_flag in ["YELLOW", "RED"]:
            self._log_event(
                event_type="VARIANCE_DETECTED",
                milestone_id=milestone_id,
                variance_pct=variance,
                flag=milestone.utilization_flag,
                spent=milestone.spent_tokens,
                budget=milestone.budget_p90_tokens,
            )

    def approve_milestone(
        self,
        milestone_id: str,
        gate: str,
        approved_by: str,
        feedback: str = "",
        token_override: bool = False,
        new_budget: Optional[int] = None,
    ) -> bool:
        """Record user approval with optional token budget override."""
        if milestone_id not in self.milestones:
            raise ValueError(f"Milestone {milestone_id} not found")

        milestone = self.milestones[milestone_id]

        approval = UserApproval(
            timestamp=datetime.now(),
            gate=gate,
            action="approve",
            feedback=feedback,
            approved_by=approved_by,
            token_override=token_override,
            new_budget=new_budget,
        )

        milestone.user_approvals.append(approval)

        # Apply budget override if provided
        if token_override and new_budget:
            old_budget = milestone.budget_p90_tokens
            milestone.budget_p90_tokens = new_budget
            self._detect_variance(milestone_id)
            self._log_event(
                event_type="BUDGET_OVERRIDE",
                milestone_id=milestone_id,
                old_budget=old_budget,
                new_budget=new_budget,
                approved_by=approved_by,
            )

        self._log_event(
            event_type="USER_APPROVAL",
            milestone_id=milestone_id,
            gate=gate,
            approved_by=approved_by,
            action="approve",
        )

        return True

    def reject_milestone(
        self,
        milestone_id: str,
        gate: str,
        approved_by: str,
        feedback: str = "",
    ) -> bool:
        """Record user rejection/rework request."""
        if milestone_id not in self.milestones:
            raise ValueError(f"Milestone {milestone_id} not found")

        milestone = self.milestones[milestone_id]

        approval = UserApproval(
            timestamp=datetime.now(),
            gate=gate,
            action="rework",
            feedback=feedback,
            approved_by=approved_by,
        )

        milestone.user_approvals.append(approval)
        milestone.status = MilestoneStatus.YELLOW

        self._log_event(
            event_type="USER_REJECTION",
            milestone_id=milestone_id,
            gate=gate,
            approved_by=approved_by,
            feedback=feedback,
        )

        return False

    def get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """Retrieve a milestone."""
        return self.milestones.get(milestone_id)

    def get_all_milestones(self) -> List[Milestone]:
        """Get all milestones."""
        return list(self.milestones.values())

    def get_metrics(self) -> MilestoneMetrics:
        """Aggregate metrics across all milestones."""
        metrics = MilestoneMetrics()

        if not self.milestones:
            return metrics

        milestones = list(self.milestones.values())
        metrics.total_milestones = len(milestones)
        metrics.completed_milestones = sum(1 for m in milestones if m.status == MilestoneStatus.COMPLETED)
        metrics.on_track = sum(1 for m in milestones if m.status == MilestoneStatus.GREEN)
        metrics.at_risk = sum(1 for m in milestones if m.status == MilestoneStatus.YELLOW)
        metrics.blocked = sum(1 for m in milestones if m.status == MilestoneStatus.RED)

        metrics.total_budget = sum(m.budget_p90_tokens for m in milestones)
        metrics.total_spent = sum(m.spent_tokens for m in milestones)

        if metrics.total_budget > 0:
            metrics.total_variance_pct = ((metrics.total_spent - metrics.total_budget) / metrics.total_budget) * 100

        # Duration metrics
        durations = [m.duration_seconds for m in milestones if m.duration_seconds > 0]
        if durations:
            metrics.avg_duration_sec = sum(durations) / len(durations)
            metrics.total_duration_sec = sum(durations)

        # Token per-agent breakdown
        for milestone in milestones:
            for task in milestone.tasks:
                agent = task.assigned_agent
                metrics.tokens_by_agent[agent] = metrics.tokens_by_agent.get(agent, 0) + task.tokens_used

        # Quality metrics
        confidences = [m.requirements_confidence for m in milestones if m.requirements_confidence > 0]
        if confidences:
            metrics.avg_requirements_confidence = sum(confidences) / len(confidences)

        coverages = [m.quality_gates.coverage_pct for m in milestones if m.quality_gates.coverage_pct > 0]
        if coverages:
            metrics.avg_test_coverage = sum(coverages) / len(coverages)

        compliance_passed = sum(1 for m in milestones if m.quality_gates.compliance_passed)
        if len(milestones) > 0:
            metrics.compliance_pass_rate = (compliance_passed / len(milestones)) * 100

        # Approval stats
        for milestone in milestones:
            for approval in milestone.user_approvals:
                metrics.total_approvals += 1
                if approval.action == "rework":
                    metrics.total_reworks += 1

        if metrics.total_approvals > 0:
            metrics.rework_rate_pct = (metrics.total_reworks / metrics.total_approvals) * 100

        return metrics

    def _log_event(self, event_type: str, **kwargs) -> None:
        """Log event with tamper-evident hashing."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "event_type": event_type,
            **kwargs,
        }

        # Create tamper-evident hash
        event_str = json.dumps(event, sort_keys=True, default=str)
        current_hash = hashlib.sha256(
            (self.last_event_hash + event_str).encode()
        ).hexdigest()
        event["audit_hash"] = current_hash
        self.last_event_hash = current_hash

        # Write to JSONL log
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")

    def complete_milestone(self, milestone_id: str) -> None:
        """Mark milestone as completed."""
        if milestone_id not in self.milestones:
            raise ValueError(f"Milestone {milestone_id} not found")

        milestone = self.milestones[milestone_id]
        milestone.status = MilestoneStatus.COMPLETED

        self._log_event(
            event_type="MILESTONE_COMPLETED",
            milestone_id=milestone_id,
            total_tokens_spent=milestone.spent_tokens,
            budget=milestone.budget_p90_tokens,
            duration_sec=milestone.duration_seconds,
        )

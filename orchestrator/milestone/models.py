"""Milestone data models for production-grade orchestration."""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MilestoneStatus(str, Enum):
    GREEN = "on_track"
    YELLOW = "at_risk"
    RED = "blocked"
    COMPLETED = "completed"


class UserApprovalGate(str, Enum):
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    QA_GATE = "qa_gate"
    COMPLIANCE_GATE = "compliance_gate"
    RELEASE = "release"


class TaskMetric(BaseModel):
    """Metrics for individual agent task execution."""
    task_id: str
    assigned_agent: str
    status: str  # "pending" | "running" | "completed" | "failed"
    tokens_used: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserApproval(BaseModel):
    """User approval gate record."""
    timestamp: datetime
    gate: UserApprovalGate
    action: str  # "approve" | "rework" | "request_changes" | "defer"
    feedback: str
    approved_by: str
    token_override: bool = False
    new_budget: Optional[int] = None


class QualityGates(BaseModel):
    """Quality gates for milestone completion."""
    code_review_approved: bool = False
    security_passed: bool = False
    tests_passed_pct: float = 0.0
    compliance_passed: bool = False
    requirements_confidence: float = 0.0
    sla_met: bool = False
    coverage_pct: float = 0.0


class Milestone(BaseModel):
    """Production milestone with full tracking."""
    id: str
    name: str
    feature_goal: str

    # Status
    status: MilestoneStatus = MilestoneStatus.GREEN
    start_time: datetime
    deadline: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Functional metrics
    functional_completeness: float = 0.0  # 0-100
    requirements_confidence: float = 0.0  # 0-100

    # Token budget
    budget_p90_tokens: int
    spent_tokens: int = 0
    variance_pct: float = 0.0
    utilization_flag: str = "GREEN"  # GREEN | YELLOW | RED

    # Quality gates
    quality_gates: QualityGates = Field(default_factory=QualityGates)

    # Execution tasks
    tasks: List[TaskMetric] = Field(default_factory=list)

    # Approvals
    user_approvals: List[UserApproval] = Field(default_factory=list)

    # Audit trail
    log_file: str
    audit_hash: Optional[str] = None  # SHA-256 hash of previous log

    # Domain context
    detected_domain: str = ""
    orchestrator_notes: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "id": "M001",
                "name": "Payment Processing API",
                "feature_goal": "Add Stripe webhook with 3D Secure",
                "status": "on_track",
                "budget_p90_tokens": 5000,
                "spent_tokens": 3800,
                "variance_pct": -24.0,
                "utilization_flag": "GREEN",
            }
        }


class MilestoneMetrics(BaseModel):
    """Aggregated metrics for reporting."""
    total_milestones: int = 0
    completed_milestones: int = 0
    on_track: int = 0
    at_risk: int = 0
    blocked: int = 0

    total_budget: int = 0
    total_spent: int = 0
    total_variance_pct: float = 0.0

    avg_duration_sec: float = 0.0
    total_duration_sec: float = 0.0

    # Token per-agent breakdown
    tokens_by_agent: Dict[str, int] = Field(default_factory=dict)

    # Quality metrics
    avg_test_coverage: float = 0.0
    avg_requirements_confidence: float = 0.0
    compliance_pass_rate: float = 0.0

    # User approval stats
    total_approvals: int = 0
    total_reworks: int = 0
    rework_rate_pct: float = 0.0

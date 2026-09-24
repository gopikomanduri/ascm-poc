from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional, Any
from orchestrator.engine.verifier import VerificationResult

class RepoContract(BaseModel):
    repo_path: str
    name: str
    role: Literal["provider", "consumer", "unaffected"] = "unaffected"
    allowed_paths: List[str] = Field(default_factory=list)
    raw_content: str = ""

class TaskItem(BaseModel):
    id: str
    title: str
    description: str
    assigned_agent: str = "coder"  # coder, database, security, etc.
    target_file: str = ""
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"

class SharedBlackboard(BaseModel):
    user_goal: str
    target_repos: List[str]
    contracts: Dict[str, RepoContract] = Field(default_factory=dict)
    discovery_summary: str = ""
    clarified_prd: str = ""
    hld: str = ""
    lld: str = ""
    task_breakdown: List[TaskItem] = Field(default_factory=list)
    nfr_answers: str = ""
    selected_architecture: str = ""
    generated_files: Dict[str, str] = Field(default_factory=dict)
    code_review_comments: List[str] = Field(default_factory=list)
    security_passed: bool = False
    security_issues: List[str] = Field(default_factory=list)
    verification: Optional[VerificationResult] = None
    approved_for_pr: bool = False
    requirements_confidence: float = 0.0
    functional_completeness: float = 0.0
    nfr_completeness: float = 0.0
    checkpoint_clarifications: List[Dict[str, str]] = Field(default_factory=list)
    milestone_feedback_history: List[Dict[str, Any]] = Field(default_factory=list)
    business_strategy: Dict[str, Any] = Field(default_factory=dict)
    revenue_analysis: Dict[str, Any] = Field(default_factory=dict)
    architecture_review: Dict[str, Any] = Field(default_factory=dict)
    code_review_report: Dict[str, Any] = Field(default_factory=dict)
    user_strategy_feedback: str = ""
    user_arch_review_feedback: str = ""
    user_code_review_feedback: str = ""
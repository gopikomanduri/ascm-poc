from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional
from orchestrator.engine.verifier import VerificationResult

class RepoContract(BaseModel):
    repo_path: str
    name: str
    role: Literal["provider", "consumer", "unaffected"] = "unaffected"
    allowed_paths: List[str] = Field(default_factory=list)
    raw_content: str = ""

class SharedBlackboard(BaseModel):
    user_goal: str
    target_repos: List[str]
    contracts: Dict[str, RepoContract] = Field(default_factory=dict)
    discovery_summary: str = ""
    nfr_answers: str = ""
    selected_architecture: str = ""
    generated_files: Dict[str, str] = Field(default_factory=dict)
    security_passed: bool = False
    security_issues: List[str] = Field(default_factory=list)
    verification: Optional[VerificationResult] = None
    approved_for_pr: bool = False
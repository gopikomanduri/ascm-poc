"""
ASCM v4.0: Domain Models & Request Schemas for Dynamic Intent-Driven Routing
"""

from typing import List, Optional, Literal, Dict
from enum import Enum
from pydantic import BaseModel, Field


ExecutionMode = Literal[
    "FULL_STACK",       # Greenfield: Discovery -> Arch -> Code -> QA -> Deploy -> GTM
    "GTM_ONLY",         # Brownfield / Existing Product: Standalone Sales + Marketing + Ads
    "SALES_ONLY",       # Team has marketing: Outbound leads + cadences + Cal.com bookings
    "MARKETING_ONLY",   # Team has sales: Tech breakdowns + SEO + social queue + ads
    "CODE_ONLY",        # Team has commercial: Discovery -> Arch -> Code -> QA -> Deploy
]


class TeamComposition(BaseModel):
    """Describes which teams the founder already has in-house."""
    has_marketing_team: bool = False
    has_sales_team: bool = False
    has_engineering_team: bool = False
    has_devops_team: bool = False


class ProjectIntentRequest(BaseModel):
    """Incoming request to resolve execution profile & routing."""
    project_name: str = Field(..., description="Unique project identifier")
    product_thesis: str = Field(..., description="Value proposition or problem statement")
    existing_repos: Optional[List[str]] = Field(default_factory=list, description="GitHub/GitLab URLs")

    team_composition: Optional[TeamComposition] = Field(
        default_factory=TeamComposition,
        description="Existing in-house teams"
    )

    requested_mode: Optional[str] = Field(
        default="AUTO",
        description="Override execution mode (AUTO = let router decide)"
    )

    target_icp_description: Optional[str] = Field(
        default=None,
        description="Ideal Customer Profile for GTM targeting"
    )

    cal_com_booking_link: Optional[str] = Field(
        default=None,
        description="Founder Cal.com link for meeting bookings"
    )

    daily_lead_quota: int = Field(default=35, description="Max leads per day for outbound")

    budget_usd: float = Field(
        default=350.0,
        description="Total USD budget ceiling for execution"
    )

    approval_gate_enabled: bool = Field(
        default=True,
        description="Require founder sign-off before executing GTM"
    )


class SystemExecutionProfile(BaseModel):
    """Resolved execution profile: which agents run, which are bypassed."""
    mode: ExecutionMode

    active_agent_ids: List[str] = Field(
        default_factory=list,
        description="Agents that will be invoked"
    )

    bypassed_agent_ids: List[str] = Field(
        default_factory=list,
        description="Agents that are intentionally skipped"
    )

    required_integrations: List[str] = Field(
        default_factory=list,
        description="External service integrations needed (openoutreach, composio, etc.)"
    )

    execution_dag: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Directed Acyclic Graph: {agent_id: [dependencies]}"
    )

    estimated_usd_cost: float = Field(
        default=0.0,
        description="Estimated cost to execute profile"
    )

    reasoning: Optional[str] = Field(
        default=None,
        description="Plain-English explanation of routing decision"
    )


class GTMProfileConfig(BaseModel):
    """Configuration for GTM-specific execution."""
    project_id: str
    workflow_id: str
    thesis: str
    icp_spec: str
    cal_com_link: str
    approval_gate_pending: bool = True
    daily_send_limit: int = 35
    campaign_duration_days: int = 30
    suppress_negative_replies: bool = True

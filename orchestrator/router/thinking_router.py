"""
ASCM v4.0: ThinkingAgentRouter
Dynamically routes to appropriate execution profile based on founder intent & team gaps.
"""

import logging
from typing import Optional
from orchestrator.models.intent import (
    ProjectIntentRequest,
    SystemExecutionProfile,
    ExecutionMode,
)

logger = logging.getLogger(__name__)


class ThinkingAgentRouter:
    """
    Evaluates founder intent, identifies organizational gaps, and constructs
    the execution DAG. Prevents running redundant agents that duplicate existing team capabilities.
    """

    # Define agent categories
    CODING_AGENTS = [
        "CheckerAgent", "ProductAgent", "ArchitectAgent", "CoDirAgent",
        "MasterCoderAgent", "BackendCoderAgent", "FrontendCoderAgent",
        "RepoAnalyzerAgent", "QAAgent", "TestAgent", "SecurityAgent",
        "ComplianceAgent", "SREAgent", "DevOpsAgent", "APMAgent", "OnCallAgent",
        "DesignAgent", "DatabaseAgent", "PolyglotCoderAgent"
    ]

    GTM_AGENTS = ["SalesAgent", "MarketingAgent", "AdAgent", "SEOAgent"]

    CORE_DISCOVERY_AGENTS = ["DiscoveryAgent", "BusinessStrategyAgent", "RevenueROIAgent"]

    @classmethod
    def resolve_profile(cls, req: ProjectIntentRequest) -> SystemExecutionProfile:
        """
        Main entry point: resolves execution profile from request.

        Logic:
        1. If manual override requested, use it
        2. Else detect team gaps and infer optimal mode
        """
        mode = (req.requested_mode or "AUTO").upper()

        # 1. Manual Override Detection
        if mode in ["FULL_STACK", "GTM_ONLY", "SALES_ONLY", "MARKETING_ONLY", "CODE_ONLY"]:
            logger.info(f"ThinkingRouter: Manual override detected. Mode: {mode}")
            return cls._build_profile_for_mode(mode, req)

        # 2. Automated Gap Detection (AUTO mode)
        logger.info("ThinkingRouter: AUTO mode. Detecting team gaps...")
        return cls._auto_detect_and_resolve(req)

    @classmethod
    def _auto_detect_and_resolve(cls, req: ProjectIntentRequest) -> SystemExecutionProfile:
        """
        Auto-detect team composition and infer optimal execution mode.

        Decision tree:
        - If no existing repos (greenfield):
            - If has both sales & marketing teams: CODE_ONLY
            - Else: FULL_STACK (need to build code + commercial)
        - If existing repos (brownfield):
            - If no sales & no marketing: GTM_ONLY (sell the existing product)
            - If has marketing but no sales: SALES_ONLY (outbound to prospects)
            - If has sales but no marketing: MARKETING_ONLY (content + SEO + ads)
            - If has both teams: CODE_ONLY (no GTM needed, focus on product)
        """
        has_code = bool(req.existing_repos and len(req.existing_repos) > 0)
        team = req.team_composition

        if not has_code:
            # Greenfield: no existing product
            if team.has_marketing_team and team.has_sales_team:
                logger.info("Greenfield + both teams exist → CODE_ONLY")
                return cls._build_profile_for_mode("CODE_ONLY", req)
            else:
                logger.info("Greenfield + missing commercial team(s) → FULL_STACK")
                return cls._build_profile_for_mode("FULL_STACK", req)
        else:
            # Brownfield: existing product
            if not team.has_sales_team and not team.has_marketing_team:
                logger.info("Brownfield + no commercial teams → GTM_ONLY")
                return cls._build_profile_for_mode("GTM_ONLY", req)
            elif team.has_marketing_team and not team.has_sales_team:
                logger.info("Brownfield + marketing team exists, no sales → SALES_ONLY")
                return cls._build_profile_for_mode("SALES_ONLY", req)
            elif team.has_sales_team and not team.has_marketing_team:
                logger.info("Brownfield + sales team exists, no marketing → MARKETING_ONLY")
                return cls._build_profile_for_mode("MARKETING_ONLY", req)
            else:
                # Both teams exist
                logger.info("Brownfield + both commercial teams exist → CODE_ONLY")
                return cls._build_profile_for_mode("CODE_ONLY", req)

    @classmethod
    def _build_profile_for_mode(
        cls, mode: str, req: ProjectIntentRequest
    ) -> SystemExecutionProfile:
        """Build execution profile for specified mode."""

        if mode == "SALES_ONLY":
            return SystemExecutionProfile(
                mode="SALES_ONLY",
                active_agent_ids=["SalesAgent"],
                bypassed_agent_ids=cls.CODING_AGENTS + ["MarketingAgent", "AdAgent", "SEOAgent"],
                required_integrations=["openoutreach", "composio_calcom", "smartlead_smtp"],
                execution_dag={"SalesAgent": []},
                estimated_usd_cost=min(req.budget_usd, 50.0),
                reasoning="Team has marketing. Executing autonomous outbound sales via OpenOutreach + Cal.com.",
            )

        elif mode == "MARKETING_ONLY":
            return SystemExecutionProfile(
                mode="MARKETING_ONLY",
                active_agent_ids=["MarketingAgent", "AdAgent", "SEOAgent"],
                bypassed_agent_ids=cls.CODING_AGENTS + ["SalesAgent"],
                required_integrations=["ai_marketing_skills", "composio_social", "buffer_typefully"],
                execution_dag={
                    "MarketingAgent": [],
                    "SEOAgent": [],
                    "AdAgent": ["MarketingAgent"],
                },
                estimated_usd_cost=min(req.budget_usd, 75.0),
                reasoning="Team has sales. Executing technical content, SEO, and social campaigns via ai-marketing-skills.",
            )

        elif mode == "GTM_ONLY":
            return SystemExecutionProfile(
                mode="GTM_ONLY",
                active_agent_ids=["SalesAgent", "MarketingAgent", "AdAgent", "SEOAgent"],
                bypassed_agent_ids=cls.CODING_AGENTS,
                required_integrations=[
                    "openoutreach", "ai_marketing_skills", "composio_calcom", "buffer_typefully"
                ],
                execution_dag={
                    "SalesAgent": [],
                    "MarketingAgent": [],
                    "SEOAgent": [],
                    "AdAgent": ["MarketingAgent"],
                },
                estimated_usd_cost=min(req.budget_usd, 125.0),
                reasoning="Brownfield product with no commercial teams. Running full autonomous GTM engine.",
            )

        elif mode == "CODE_ONLY":
            return SystemExecutionProfile(
                mode="CODE_ONLY",
                active_agent_ids=cls.CODING_AGENTS,
                bypassed_agent_ids=cls.GTM_AGENTS,
                required_integrations=["docker_sandbox", "git_integration"],
                execution_dag={
                    "ProductAgent": [],
                    "ArchitectAgent": ["ProductAgent"],
                    "BackendCoderAgent": ["ArchitectAgent"],
                    "FrontendCoderAgent": ["ArchitectAgent"],
                    "QAAgent": ["BackendCoderAgent", "FrontendCoderAgent"],
                    "ComplianceAgent": ["QAAgent"],
                    "DevOpsAgent": ["ComplianceAgent"],
                },
                estimated_usd_cost=min(req.budget_usd, 250.0),
                reasoning="Team has commercial capability. Focusing on code discovery, architecture, and deployment.",
            )

        else:  # FULL_STACK (default)
            return SystemExecutionProfile(
                mode="FULL_STACK",
                active_agent_ids=cls.CODING_AGENTS + cls.GTM_AGENTS,
                bypassed_agent_ids=[],
                required_integrations=[
                    "docker_sandbox", "openoutreach", "ai_marketing_skills",
                    "composio_calcom", "buffer_typefully", "git_integration"
                ],
                execution_dag={
                    "ProductAgent": [],
                    "ArchitectAgent": ["ProductAgent"],
                    "BackendCoderAgent": ["ArchitectAgent"],
                    "FrontendCoderAgent": ["ArchitectAgent"],
                    "QAAgent": ["BackendCoderAgent", "FrontendCoderAgent"],
                    "ComplianceAgent": ["QAAgent"],
                    "DevOpsAgent": ["ComplianceAgent"],
                    "MarketingAgent": ["ProductAgent"],
                    "SalesAgent": ["ProductAgent"],
                    "SEOAgent": ["ProductAgent"],
                    "AdAgent": ["MarketingAgent"],
                },
                estimated_usd_cost=req.budget_usd,
                reasoning="Greenfield project. Running full-stack: architecture → code → QA → deployment + GTM.",
            )

    @classmethod
    def validate_profile(cls, profile: SystemExecutionProfile) -> bool:
        """
        Validate that profile is consistent:
        - No agent appears in both active and bypassed
        - DAG only references active agents
        - Cost is non-negative
        """
        active_set = set(profile.active_agent_ids)
        bypassed_set = set(profile.bypassed_agent_ids)

        # Check for overlap
        overlap = active_set & bypassed_set
        if overlap:
            logger.error(f"Profile validation failed: agents in both lists: {overlap}")
            return False

        # Check DAG references
        for agent, deps in profile.execution_dag.items():
            if agent not in active_set:
                logger.error(f"DAG references inactive agent: {agent}")
                return False
            for dep in deps:
                if dep not in active_set:
                    logger.error(f"DAG dependency on inactive agent: {agent} → {dep}")
                    return False

        if profile.estimated_usd_cost < 0:
            logger.error("Estimated cost cannot be negative")
            return False

        logger.info(f"Profile validation passed: {profile.mode}")
        return True

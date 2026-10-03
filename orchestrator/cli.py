"""
ASCM v4.0 CLI: Dynamic Intent-Driven Orchestration Interface

Commands:
  ascm init       - Full-stack build (discovery -> architecture -> code -> QA -> deploy -> GTM)
  ascm gtm        - Autonomous GTM engine on existing product
  ascm sales      - Sales-only outbound (team has marketing)
  ascm marketing  - Marketing-only campaigns (team has sales)
  ascm code       - Code-only development (team has commercial)
"""

import json
import logging
from typing import Optional
from orchestrator.models.intent import (
    ProjectIntentRequest,
    TeamComposition,
    ExecutionMode,
)
from orchestrator.router.thinking_router import ThinkingAgentRouter
from orchestrator.agents.all_agents import (
    ProductAgent,
    SalesAgent,
    MarketingAgent,
    AdAgent,
    SEOAgent,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ASCMCLICommandInterface:
    """CLI interface for ASCM v4.0."""

    @staticmethod
    def cmd_init(
        name: str,
        spec_file: str,
        budget: float = 350.0,
    ) -> None:
        """Initialize full-stack project build."""
        print(f"\n{'='*80}")
        print(f"  ASCM v4.0: Full-Stack Project Initialization")
        print(f"{'='*80}\n")

        logger.info(f"Loading specification from: {spec_file}")
        with open(spec_file, "r") as f:
            spec_content = f.read()

        req = ProjectIntentRequest(
            project_name=name,
            product_thesis=spec_content,
            budget_usd=budget,
        )

        profile = ThinkingAgentRouter.resolve_profile(req)
        ThinkingAgentRouter.validate_profile(profile)

        print(f"✨ Execution Profile Resolved: {profile.mode}")
        print(f"   Active Agents: {len(profile.active_agent_ids)}")
        print(f"   Bypassed Agents: {len(profile.bypassed_agent_ids)}")
        print(f"   Cost Estimate: ${profile.estimated_usd_cost}")
        print(f"\n   Reasoning: {profile.reasoning}\n")

        print("📋 Active Agents:")
        for agent_id in profile.active_agent_ids:
            print(f"   ✓ {agent_id}")

        if profile.bypassed_agent_ids:
            print("\n⏭️  Bypassed Agents:")
            for agent_id in profile.bypassed_agent_ids:
                print(f"   ✗ {agent_id}")

        print(f"\n🚀 Would dispatch to Temporal for execution: {profile.mode} workflow")
        print(f"   DAG Edges: {json.dumps(profile.execution_dag, indent=6)}\n")

    @staticmethod
    def cmd_gtm(
        repo: Optional[str] = None,
        thesis: str = "",
        cal_link: str = "",
        budget: float = 150.0,
    ) -> None:
        """Run autonomous GTM on existing product."""
        print(f"\n{'='*80}")
        print(f"  ASCM v4.0: Autonomous GTM Engine (Existing Product)")
        print(f"{'='*80}\n")

        req = ProjectIntentRequest(
            project_name="gtm-standalone",
            product_thesis=thesis,
            existing_repos=[repo] if repo else [],
            cal_com_booking_link=cal_link,
            requested_mode="GTM_ONLY",
            budget_usd=budget,
        )

        profile = ThinkingAgentRouter.resolve_profile(req)
        ThinkingAgentRouter.validate_profile(profile)

        print(f"🚀 Launching GTM-Only Engine")
        print(f"   Mode: {profile.mode}")
        print(f"   Active Agents: {', '.join(profile.active_agent_ids)}")
        print(f"   Cost Budget: ${profile.estimated_usd_cost}\n")

        print("📋 Integration Requirements:")
        for integration in profile.required_integrations:
            print(f"   • {integration}")

        print(f"\n🎯 Campaign Execution Plan:")
        for agent_id, deps in profile.execution_dag.items():
            deps_str = f" (depends: {', '.join(deps)})" if deps else ""
            print(f"   → {agent_id}{deps_str}")

        print(f"\n🔄 Would dispatch to Temporal GTMStandaloneWorkflow")
        print(f"   with approval_gate_pending=True\n")

    @staticmethod
    def cmd_sales(
        thesis: str = "",
        cal_link: str = "",
        quota: int = 35,
    ) -> None:
        """Run sales-only outbound (assumes marketing team exists)."""
        print(f"\n{'='*80}")
        print(f"  ASCM v4.0: Autonomous Sales Outbound")
        print(f"{'='*80}\n")

        team = TeamComposition(
            has_marketing_team=True,  # User indicates they have marketing
            has_sales_team=False,
        )

        req = ProjectIntentRequest(
            project_name="sales-outbound",
            product_thesis=thesis,
            team_composition=team,
            cal_com_booking_link=cal_link,
            daily_lead_quota=quota,
            requested_mode="SALES_ONLY",
        )

        profile = ThinkingAgentRouter.resolve_profile(req)
        ThinkingAgentRouter.validate_profile(profile)

        print(f"🎯 Sales-Only Outbound Campaign")
        print(f"   Active Agents: {', '.join(profile.active_agent_ids)}")
        print(f"   Daily Lead Quota: {quota}")
        print(f"   Cal.com Booking Link: {cal_link}\n")

        print("🛠️  Integrations Required:")
        for integration in profile.required_integrations:
            print(f"   • {integration}")

        print(f"\n📊 Execution DAG:")
        for agent_id, deps in profile.execution_dag.items():
            print(f"   {agent_id}")

        print(f"\n⚡ Founder Rejection Shield: ACTIVE")
        print(f"   Negative/unsubscribe replies will be silently suppressed.")
        print(f"   Only warm meetings will trigger notifications.\n")

    @staticmethod
    def cmd_marketing(
        thesis: str = "",
        competitor_domains: Optional[list] = None,
    ) -> None:
        """Run marketing-only campaigns (assumes sales team exists)."""
        print(f"\n{'='*80}")
        print(f"  ASCM v4.0: Autonomous Technical Marketing")
        print(f"{'='*80}\n")

        team = TeamComposition(
            has_marketing_team=False,
            has_sales_team=True,  # User indicates they have sales
        )

        req = ProjectIntentRequest(
            project_name="marketing-campaigns",
            product_thesis=thesis,
            team_composition=team,
            requested_mode="MARKETING_ONLY",
        )

        profile = ThinkingAgentRouter.resolve_profile(req)
        ThinkingAgentRouter.validate_profile(profile)

        print(f"📝 Technical Marketing Campaign")
        print(f"   Active Agents: {', '.join(profile.active_agent_ids)}")
        print(f"   Content Focus: Technical breakdowns, SEO, social\n")

        print("🛠️  Integrations Required:")
        for integration in profile.required_integrations:
            print(f"   • {integration}")

        print(f"\n📊 Campaign DAG:")
        for agent_id in profile.active_agent_ids:
            print(f"   → {agent_id}")

        if competitor_domains:
            print(f"\n🎯 Competitor Analysis Targets:")
            for competitor in competitor_domains:
                print(f"   • {competitor}")

        print(f"\n📈 Expected Output:")
        print(f"   • Technical blog posts & architecture breakdowns")
        print(f"   • SEO keyword strategy & content briefs")
        print(f"   • LinkedIn & Twitter thought leadership content")
        print(f"   • Paid ad campaigns (Google, LinkedIn, Programmatic)\n")

    @staticmethod
    def cmd_code(thesis: str = "") -> None:
        """Run code-only development (assumes commercial team exists)."""
        print(f"\n{'='*80}")
        print(f"  ASCM v4.0: Code Discovery & Architecture")
        print(f"{'='*80}\n")

        team = TeamComposition(
            has_marketing_team=True,
            has_sales_team=True,
        )

        req = ProjectIntentRequest(
            project_name="code-development",
            product_thesis=thesis,
            team_composition=team,
            requested_mode="CODE_ONLY",
        )

        profile = ThinkingAgentRouter.resolve_profile(req)
        ThinkingAgentRouter.validate_profile(profile)

        print(f"💻 Code-Only Development Pipeline")
        print(f"   Mode: {profile.mode}")
        print(f"   Active Agents: {len(profile.active_agent_ids)}")
        print(f"   Bypassed GTM Agents: {', '.join(profile.bypassed_agent_ids)}\n")

        print("🛠️  Integrations Required:")
        for integration in profile.required_integrations:
            print(f"   • {integration}")

        print(f"\n📊 Execution DAG:")
        for agent_id, deps in profile.execution_dag.items():
            deps_str = f" → {', '.join(deps)}" if deps else ""
            print(f"   {agent_id}{deps_str}")

        print(f"\n📈 Expected Output:")
        print(f"   • Product PRD & clarification")
        print(f"   • Architecture design (HLD/LLD)")
        print(f"   • Code generation & testing")
        print(f"   • Security & compliance audits")
        print(f"   • Deployment & DevOps automation\n")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ASCM v4.0: AI Startup Core Machine - Intent-Driven Orchestration"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize full-stack project build"
    )
    init_parser.add_argument("name", help="Project name")
    init_parser.add_argument("spec_file", help="Path to specification file")
    init_parser.add_argument(
        "--budget", type=float, default=350.0, help="Budget in USD (default: 350)"
    )

    # gtm command
    gtm_parser = subparsers.add_parser("gtm", help="Run autonomous GTM on existing product")
    gtm_parser.add_argument("--repo", help="GitHub/GitLab repository URL")
    gtm_parser.add_argument("--thesis", required=True, help="Product thesis")
    gtm_parser.add_argument("--cal-link", required=True, help="Cal.com booking link")
    gtm_parser.add_argument(
        "--budget", type=float, default=150.0, help="Budget in USD (default: 150)"
    )

    # sales command
    sales_parser = subparsers.add_parser("sales", help="Run sales-only outbound")
    sales_parser.add_argument("--thesis", required=True, help="Product thesis")
    sales_parser.add_argument("--cal-link", required=True, help="Cal.com booking link")
    sales_parser.add_argument(
        "--quota", type=int, default=35, help="Daily lead quota (default: 35)"
    )

    # marketing command
    marketing_parser = subparsers.add_parser("marketing", help="Run marketing-only campaigns")
    marketing_parser.add_argument("--thesis", required=True, help="Product thesis")
    marketing_parser.add_argument(
        "--competitors",
        nargs="+",
        help="Competitor domains for analysis",
    )

    # code command
    code_parser = subparsers.add_parser("code", help="Run code-only development")
    code_parser.add_argument("--thesis", required=True, help="Product thesis")

    args = parser.parse_args()

    if args.command == "init":
        ASCMCLICommandInterface.cmd_init(args.name, args.spec_file, args.budget)
    elif args.command == "gtm":
        ASCMCLICommandInterface.cmd_gtm(args.repo, args.thesis, args.cal_link, args.budget)
    elif args.command == "sales":
        ASCMCLICommandInterface.cmd_sales(args.thesis, args.cal_link, args.quota)
    elif args.command == "marketing":
        ASCMCLICommandInterface.cmd_marketing(args.thesis, args.competitors)
    elif args.command == "code":
        ASCMCLICommandInterface.cmd_code(args.thesis)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

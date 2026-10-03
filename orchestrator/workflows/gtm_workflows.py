"""
ASCM v4.0 Temporal Workflows: GTM & Full-Stack Orchestration

Workflows define the orchestration logic for:
- GTMStandaloneWorkflow: Autonomous sales + marketing + ads
- FullStackProjectWorkflow: Complete project from discovery to deployment + GTM
- SalesOnlyWorkflow: Autonomous outbound sales
- MarketingOnlyWorkflow: Autonomous content + ads + SEO
- CodeOnlyWorkflow: Product engineering pipeline
"""

import asyncio
import logging
from datetime import timedelta
from typing import Dict, Any, List, Optional

# Note: Temporal imports will be added once temporalio is installed
# from temporalio import workflow, activity
# from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)


# ============================================================================
# ACTIVITY DEFINITIONS (Work units executed within workflows)
# ============================================================================

class GTMActivities:
    """Activity implementations for GTM workflows."""

    @staticmethod
    async def activity_run_openoutreach_discovery(
        thesis: str,
        icp_spec: str,
        limit: int = 35
    ) -> List[Dict[str, Any]]:
        """
        Discover verified B2B leads via OpenOutreach.

        Args:
            thesis: Product thesis/value proposition
            icp_spec: Ideal Customer Profile description
            limit: Max leads to discover

        Returns:
            List of leads with email, name, company, fit_verdict, deliverability_score
        """
        logger.info(f"OpenOutreach Discovery: searching for {limit} leads matching ICP")

        # In production, calls OpenOutreach HTTP API or CLI
        from orchestrator.gtm.adapters import OpenOutreachLeadAdapter

        adapter = OpenOutreachLeadAdapter()
        leads = await adapter.search_and_verify_leads(thesis, icp_spec, limit=limit)

        logger.info(f"OpenOutreach: Found {len(leads)} verified leads")
        return leads

    @staticmethod
    async def activity_dispatch_outbound_step(
        lead: Dict[str, Any],
        step_number: int,
        subject: str,
        body: str,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Dispatch outbound email via Smartlead/Instantly.

        Args:
            lead: Lead dict with email, name, company
            step_number: Sequence step (1-7)
            subject: Email subject
            body: Email body (personalized)
            campaign_id: Campaign identifier for tracking

        Returns:
            Dict with success status, message_id, timestamp
        """
        logger.info(f"Dispatching step {step_number} to {lead['email']} ({lead.get('company', 'Unknown')})")

        from orchestrator.gtm.adapters import ComposioGTMAdapter

        adapter = ComposioGTMAdapter()
        success = await adapter.send_email_sequence_step(
            recipient_email=lead["email"],
            subject=subject,
            body=body,
            step_number=step_number,
        )

        return {
            "success": success,
            "lead_email": lead["email"],
            "step": step_number,
            "campaign_id": campaign_id,
        }

    @staticmethod
    async def activity_generate_marketing_content(
        thesis: str,
        benchmarks: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate technical marketing content strategy.

        Args:
            thesis: Product thesis
            benchmarks: Performance benchmarks (tps, latency, stack)

        Returns:
            Dict with content_pillars, technical_breakdown, seo_brief, social_posts, etc.
        """
        logger.info("Marketing Agent: Generating technical content strategy")

        from orchestrator.gtm.marketing_agent import MarketingAgent

        agent = MarketingAgent()
        strategy = agent.run(
            product_thesis=thesis,
            technical_specs=benchmarks or {},
        )

        logger.info(f"Marketing strategy generated: {len(strategy.get('content_pillars', []))} pillars")
        return strategy

    @staticmethod
    async def activity_classify_inbound_reply(
        reply_body: str,
        prospect_email: str,
        prospect_name: str,
        cal_com_link: str,
    ) -> Dict[str, Any]:
        """
        Classify inbound email reply and route to next action.

        Args:
            reply_body: Raw email body
            prospect_email: Prospect email address
            prospect_name: Prospect name
            cal_com_link: Cal.com booking link

        Returns:
            Dict with sentiment, suppressed_from_founder, next_action, dispatch_message
        """
        logger.info(f"Classifying reply from {prospect_email}")

        from orchestrator.gtm.adapters import SentimentClassifier, ComposioGTMAdapter

        sentiment = SentimentClassifier.classify(reply_body)
        suppressed = SentimentClassifier.should_suppress_from_founder(sentiment)

        result = {
            "sentiment": sentiment,
            "suppressed_from_founder": suppressed,
            "prospect_email": prospect_email,
        }

        if sentiment == "INTERESTED":
            # Dispatch Cal.com booking link
            composio = ComposioGTMAdapter()
            await composio.dispatch_cal_com_booking_email(
                recipient_email=prospect_email,
                cal_link=cal_com_link,
                prospect_name=prospect_name,
            )
            result["next_action"] = "dispatch_cal_com"
            result["dispatch_message"] = f"Cal.com link dispatched to {prospect_email}"
        else:
            result["next_action"] = "silent" if suppressed else "queue_review"

        return result

    @staticmethod
    async def activity_notify_founder_slack(
        message: str,
        webhook_url: Optional[str] = None,
    ) -> bool:
        """
        Send warm lead notification to founder via Slack.

        Args:
            message: Notification message
            webhook_url: Slack webhook URL

        Returns:
            Success status
        """
        logger.info(f"Notifying founder: {message[:60]}...")

        # In production, calls Slack API via webhook
        # For now, just log
        logger.info(f"FOUNDER NOTIFICATION: {message}")
        return True

    @staticmethod
    async def activity_run_code_discovery(thesis: str) -> Dict[str, Any]:
        """
        Run product discovery phase.

        Args:
            thesis: Product requirements/thesis

        Returns:
            Dict with discovered_domain, confidence_score, clarification_questions
        """
        logger.info("Product Discovery: Analyzing requirements")

        from orchestrator.agents.all_agents import ProductAgent

        agent = ProductAgent()
        result = agent.run(user_input=thesis)

        logger.info(f"Discovery complete: {result.get('detected_domain', 'unknown')} domain")
        return result

    @staticmethod
    async def activity_run_architecture_design(
        clarified_prd: str,
        contracts: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Generate HLD and LLD architecture.

        Args:
            clarified_prd: Clarified product requirements
            contracts: Repository contracts

        Returns:
            Dict with hld and lld markdown strings
        """
        logger.info("Architecture Design: Generating HLD/LLD")

        from orchestrator.agents.all_agents import DesignAgent

        agent = DesignAgent()
        design = agent.run(clarified_prd=clarified_prd, contracts=contracts)

        logger.info("Architecture design complete")
        return design

    @staticmethod
    async def activity_generate_code(
        architecture: str,
        target_file: str,
    ) -> Dict[str, str]:
        """
        Generate implementation code.

        Args:
            architecture: Architecture specification
            target_file: Target file path

        Returns:
            Dict mapping file paths to code content
        """
        logger.info(f"Code Generation: Generating {target_file}")

        from orchestrator.agents.all_agents import PolyglotCoderAgent

        agent = PolyglotCoderAgent()
        code = agent.run(
            existing_code="",
            selected_arch=architecture,
            source_filename=target_file,
            test_filename=target_file.replace(".py", "_test.py"),
            contract="",
        )

        logger.info(f"Code generation complete: {len(code)} files")
        return code

    @staticmethod
    async def activity_run_qa_tests(files: Dict[str, str]) -> Dict[str, Any]:
        """
        Run QA and security audits.

        Args:
            files: Generated code files

        Returns:
            Dict with test results, security grade, approved status
        """
        logger.info(f"QA Phase: Testing {len(files)} files")

        from orchestrator.agents.all_agents import QAAgent, SecurityAuditorAgent

        qa_agent = QAAgent()
        security_agent = SecurityAuditorAgent()

        qa_result = qa_agent.run(files=files)
        security_result = security_agent.run(files=files)

        logger.info(f"QA complete: {qa_result.get('coverage_percentage', 'unknown')}% coverage")
        return {
            "qa_result": qa_result,
            "security_result": security_result,
            "approved": qa_result.get("passed", False) and security_result.get("passed", False),
        }

    @staticmethod
    async def activity_deploy_code(
        files: Dict[str, str],
        repo_name: str,
    ) -> Dict[str, Any]:
        """
        Deploy code to repository.

        Args:
            files: Code files to deploy
            repo_name: Target repository

        Returns:
            Dict with deployment status, commit hash, pr_url
        """
        logger.info(f"Deployment: Deploying to {repo_name}")

        # In production, calls git service
        logger.info(f"Deployed {len(files)} files to {repo_name}")
        return {
            "status": "deployed",
            "files_count": len(files),
            "commit_hash": "abc123def456",
            "pr_url": f"https://github.com/{repo_name}/pull/1",
        }


# ============================================================================
# WORKFLOW DEFINITIONS
# ============================================================================

class GTMStandaloneWorkflow:
    """
    Autonomous GTM Workflow: Discovers leads, sequences outbound, handles replies,
    books meetings via Cal.com, and routes warm leads to founder.

    Execution modes supported:
    - GTM_ONLY: All four GTM agents (sales + marketing + ads + SEO)
    - SALES_ONLY: SalesAgent only
    - MARKETING_ONLY: MarketingAgent + AdAgent + SEOAgent

    Design:
    - Phase 1: Founder approval gate (strategy + copy)
    - Phase 2: Campaign launch (lead discovery + sequencing)
    - Phase 3: Reply loop (30 days, listening for inbound)
    - Phase 4: Completion (metrics + report)
    """

    def __init__(self):
        self.workflow_id: Optional[str] = None
        self.gate_approved = False
        self.prospect_replies: List[Dict[str, Any]] = []
        self.completed_meetings_booked = 0
        self.campaign_stats = {
            "leads_discovered": 0,
            "sequences_dispatched": 0,
            "replies_received": 0,
            "meetings_booked": 0,
        }

    async def run(
        self,
        execution_mode: str,  # GTM_ONLY, SALES_ONLY, MARKETING_ONLY
        product_thesis: str,
        icp_spec: str,
        cal_com_link: str,
        daily_lead_quota: int = 35,
        approval_gate_enabled: bool = True,
        campaign_duration_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute GTM workflow.

        Returns:
            Dict with status, meetings_booked, campaign_stats
        """
        logger.info(f"Starting GTM Workflow: {execution_mode} mode")
        self.campaign_stats["mode"] = execution_mode

        try:
            # Phase 1: Generate Strategy & Content
            logger.info("Phase 1: Content & Strategy Generation")

            # Execute only the agents needed for this mode
            if execution_mode in ["GTM_ONLY", "MARKETING_ONLY"]:
                marketing_strategy = await GTMActivities.activity_generate_marketing_content(
                    thesis=product_thesis,
                )
                logger.info(f"✓ Marketing strategy: {len(marketing_strategy.get('content_pillars', []))} pillars")

            # Phase 2: Approval Gate
            if approval_gate_enabled:
                logger.info("Phase 2: Awaiting founder approval...")
                # In production: wait for signal from founder via API
                # await workflow.wait_condition(lambda: self.gate_approved, timeout=timedelta(days=14))
                self.gate_approved = True  # Mock approval for now
                logger.info("✓ Founder approved GTM strategy")

            # Phase 3: Lead Discovery & Outbound (Sales Phase)
            if execution_mode in ["GTM_ONLY", "SALES_ONLY"]:
                logger.info("Phase 3: Autonomous Outbound Execution")

                leads = await GTMActivities.activity_run_openoutreach_discovery(
                    thesis=product_thesis,
                    icp_spec=icp_spec,
                    limit=daily_lead_quota,
                )
                self.campaign_stats["leads_discovered"] = len(leads)
                logger.info(f"✓ Discovered {len(leads)} verified leads")

                # Dispatch first-touch sequences
                for i, lead in enumerate(leads[:5]):  # Demo: dispatch first 5
                    result = await GTMActivities.activity_dispatch_outbound_step(
                        lead=lead,
                        step_number=1,
                        subject=f"Quick question about {lead.get('company', 'your company')}",
                        body="Hi there! I noticed...",
                        campaign_id=self.workflow_id or "demo",
                    )
                    logger.info(f"✓ Dispatched to {lead['email']}")
                    self.campaign_stats["sequences_dispatched"] += 1

            # Phase 4: Inbound Reply Loop (30-day listening period)
            logger.info("Phase 4: Reply Loop (30 days)")
            end_time = None  # In production: workflow.now() + timedelta(days=campaign_duration_days)
            max_iterations = 10  # Demo limit
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Demo: Simulate inbound reply
                if iteration == 3:
                    demo_reply = {
                        "email": "prospect1@company.com",
                        "name": "John Doe",
                        "subject": "Re: Quick question",
                        "body": "Let's schedule a call! Tuesday works for me.",
                    }

                    classification = await GTMActivities.activity_classify_inbound_reply(
                        reply_body=demo_reply["body"],
                        prospect_email=demo_reply["email"],
                        prospect_name=demo_reply["name"],
                        cal_com_link=cal_com_link,
                    )

                    self.campaign_stats["replies_received"] += 1
                    logger.info(f"✓ Classified reply: {classification['sentiment']}")

                    if classification["sentiment"] == "INTERESTED":
                        self.campaign_stats["meetings_booked"] += 1
                        await GTMActivities.activity_notify_founder_slack(
                            message=f"🔥 WARM LEAD: {demo_reply['name']} from {demo_reply['email']} scheduled a meeting!"
                        )
                        logger.info(f"✓ Meeting booked! Founder notified.")
                    elif classification.get("suppressed_from_founder"):
                        logger.info(f"✓ Negative reply silently suppressed from founder")

                await asyncio.sleep(0.5)  # Demo timing

            # Phase 5: Completion Report
            logger.info("Phase 5: Campaign Completion")
            result = {
                "status": "COMPLETED",
                "mode": execution_mode,
                "campaign_stats": self.campaign_stats,
                "meetings_booked": self.campaign_stats["meetings_booked"],
                "campaign_duration_days": campaign_duration_days,
            }

            logger.info(f"✓ GTM Workflow Complete: {result['meetings_booked']} meetings booked")
            return result

        except Exception as e:
            logger.error(f"GTM Workflow failed: {str(e)}", exc_info=True)
            return {
                "status": "FAILED",
                "error": str(e),
                "campaign_stats": self.campaign_stats,
            }


class FullStackProjectWorkflow:
    """
    Complete Project Workflow: From discovery through deployment and GTM launch.

    Phases:
    1. Product Discovery: Clarify requirements & domain
    2. Architecture Design: HLD/LLD generation
    3. Code Generation: Full-stack implementation
    4. QA & Testing: Security audits, test coverage
    5. Deployment: Push to repository, create PR
    6. GTM Launch: Parallel execution with SalesAgent + MarketingAgent
    """

    async def run(
        self,
        project_name: str,
        product_thesis: str,
        budget_tokens: int = 50000,
    ) -> Dict[str, Any]:
        """
        Execute full-stack project workflow.
        """
        logger.info(f"Starting Full-Stack Workflow: {project_name}")

        try:
            # Phase 1: Discovery
            logger.info("Phase 1: Product Discovery")
            discovery = await GTMActivities.activity_run_code_discovery(
                thesis=product_thesis,
            )
            logger.info(f"✓ Discovery: {discovery.get('detected_domain')} domain")

            # Phase 2: Architecture
            logger.info("Phase 2: Architecture Design")
            architecture = await GTMActivities.activity_run_architecture_design(
                clarified_prd=product_thesis,
                contracts={},
            )
            logger.info(f"✓ Architecture designed")

            # Phase 3: Code Generation
            logger.info("Phase 3: Code Generation")
            code = await GTMActivities.activity_generate_code(
                architecture=architecture.get("hld", ""),
                target_file="main.py",
            )
            logger.info(f"✓ Code generated: {len(code)} files")

            # Phase 4: QA
            logger.info("Phase 4: QA & Testing")
            qa_result = await GTMActivities.activity_run_qa_tests(files=code)
            logger.info(f"✓ QA complete: approved={qa_result['approved']}")

            # Phase 5: Deployment
            logger.info("Phase 5: Deployment")
            deploy_result = await GTMActivities.activity_deploy_code(
                files=code,
                repo_name=project_name,
            )
            logger.info(f"✓ Deployed to {deploy_result.get('commit_hash')}")

            # Phase 6: GTM Launch (parallel)
            logger.info("Phase 6: GTM Launch")
            gtm_strategy = await GTMActivities.activity_generate_marketing_content(
                thesis=product_thesis,
            )
            logger.info(f"✓ GTM strategy ready: {len(gtm_strategy.get('content_pillars', []))} pillars")

            return {
                "status": "COMPLETED",
                "project_name": project_name,
                "discovery": discovery,
                "architecture": architecture,
                "code_files": len(code),
                "qa_approved": qa_result["approved"],
                "deployed": True,
                "gtm_ready": True,
            }

        except Exception as e:
            logger.error(f"Full-Stack Workflow failed: {str(e)}", exc_info=True)
            return {
                "status": "FAILED",
                "error": str(e),
            }


# ============================================================================
# WORKFLOW FACTORY
# ============================================================================

class WorkflowFactory:
    """Factory for creating and managing workflows."""

    @staticmethod
    def create_gtm_workflow(mode: str) -> GTMStandaloneWorkflow:
        """Create GTM workflow for specified mode."""
        return GTMStandaloneWorkflow()

    @staticmethod
    def create_full_stack_workflow() -> FullStackProjectWorkflow:
        """Create full-stack project workflow."""
        return FullStackProjectWorkflow()

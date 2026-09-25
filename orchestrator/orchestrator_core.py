import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from orchestrator.agents.all_agents import (
    DiscoveryAgent,
    ProductAgent,
    BusinessStrategyAgent,
    RevenueROIAgent,
    DesignAgent,
    ArchitectAgent,
    ArchitectureReviewAgent,
    PlannerAgent,
    DatabaseAgent,
    GoCoderAgent,
    SecurityAuditorAgent,
    CodeReviewAgent,
)
from orchestrator.contracts import parse_skill_contract
from orchestrator.dashboard import GLOBAL_DASHBOARD_STATE, DashboardServer
from orchestrator.engine.sandbox import SandboxEngine, PathViolationError
from orchestrator.engine.verifier import VerifierEngine
from orchestrator.git_service import GitService
from orchestrator.security.audit_logger import AUDIT_LOGGER
from orchestrator.state import SharedBlackboard, TaskItem


class OrchestratorEngine:
    def __init__(self, repo_paths: List[str], initial_goal: str, enable_dashboard: bool = True, port: int = 8080):
        GLOBAL_DASHBOARD_STATE.new_session(initial_goal)
        try:
            self.valid_repos = self._validate_repositories(repo_paths)
            self.state = SharedBlackboard(user_goal=initial_goal, target_repos=self.valid_repos)
            AUDIT_LOGGER.log_event(
                event_type="SESSION_START",
                agent="ORCHESTRATOR",
                action="INITIALIZE",
                details={"goal": initial_goal, "repositories": self.valid_repos},
            )
            self.dashboard_server: Optional[DashboardServer] = None
            if enable_dashboard:
                self.dashboard_server = DashboardServer(port=port)
                self.dashboard_server.start()
        except Exception as err:
            GLOBAL_DASHBOARD_STATE.record_crash(err)
            AUDIT_LOGGER.log_event("SESSION_CRASH", agent="ORCHESTRATOR", action="INIT_ERROR", details={"error": str(err)}, level="ERROR")
            raise


    def run(self, auto_approve: bool = False) -> None:
        try:
            self._notify_phase("Phase 1: Ingesting Repository Contracts")
            for repo in self.valid_repos:
                contract = parse_skill_contract(repo)
                self.state.contracts[repo] = contract
                self._log(f"[+] Ingested contract for '{contract.name}': {len(contract.allowed_paths)} allowed paths")

            self._notify_phase("Phase 2: System Topology Discovery")
            GLOBAL_DASHBOARD_STATE.update_agent("DiscoveryAgent", "running", "Classifying repo topology")
            topology = DiscoveryAgent().run(
                {path: contract.model_dump() for path, contract in self.state.contracts.items()},
                self.state.user_goal,
            )
            GLOBAL_DASHBOARD_STATE.update_agent("DiscoveryAgent", "completed", "Topology classified")
            providers = [p for p in topology.get("providers", []) if p in self.state.contracts]
            consumers = [p for p in topology.get("consumers", []) if p in self.state.contracts]
            self.state.discovery_summary = topology.get("analysis", "")
            self._log(f"[+] Identified Providers: {[Path(p).name for p in providers]}")
            self._log(f"[+] Identified Consumers: {[Path(p).name for p in consumers]}")

            if not providers:
                self._log("No provider repositories require modification.")
                return

            self._notify_phase("Phase 3: Product Agent Requirements & Clarification Loop")
            self._run_product_clarification_loop(auto_approve=auto_approve)

            self._notify_phase("Phase 3b: Business Strategy, Competitor Analysis & Revenue ROI")
            self._run_business_and_revenue_strategy(auto_approve=auto_approve)

            self._notify_phase("Phase 4: Architecture (HLD/LLD), Task Decomposition & Architecture Review")
            self._run_architecture_and_design(providers, auto_approve=auto_approve)

            self._notify_phase("Phase 5: Dynamic Task Execution, Code Generation & Critic Code Review")
            pending_changes = self._run_task_execution(providers, consumers, auto_approve=auto_approve)

            if not pending_changes:
                self._log("No audited, review-approved changes ready for writing.")
                return

            self._notify_phase("Phase 6: Human Approval & Local Git Commit")
            self._run_verification_and_commit(pending_changes, auto_approve=auto_approve)
        except Exception as err:
            GLOBAL_DASHBOARD_STATE.record_crash(err)
            raise

    def _resolve_task_files(self, repo_path: str, task: TaskItem, contract) -> Tuple[str, str, str]:
        """
        Determines the source file path, test file path, and existing file content
        for a specific task, respecting allowed_paths and the detected domain/language.
        """
        from orchestrator.domain import DomainAdapter
        user_goal = self.state.user_goal if getattr(self, "state", None) else ""
        domain = DomainAdapter.detect_domain(user_goal)
        lang = DomainAdapter.detect_language(user_goal, domain)
        default_ext = ".py" if lang == "python" else ".go" if lang == "go" else ".ts" if lang == "typescript" else ".go"

        repo_dir = Path(repo_path).resolve()
        target = task.target_file.strip() if getattr(task, "target_file", None) else ""

        # 1. If task provides a specific target file
        if target:
            target_p = Path(target)
            if not target_p.is_absolute() and ".." not in target_p.parts:
                full_target = repo_dir / target_p
                source_path = target_p.as_posix()
                stem = target_p.stem
                if target_p.suffix == ".go":
                    test_path = target_p.with_name(f"{stem}_test.go").as_posix()
                elif target_p.suffix == ".py":
                    test_path = target_p.with_name(f"test_{stem}.py").as_posix()
                elif target_p.suffix in (".js", ".ts"):
                    test_path = target_p.with_name(f"{stem}.test{target_p.suffix}").as_posix()
                else:
                    test_path = target_p.with_name(f"test_{stem}.py" if lang == "python" else f"{stem}_test.go").as_posix()

                existing_content = full_target.read_text(encoding="utf-8") if full_target.is_file() else ""
                return source_path, test_path, existing_content

        # 2. Match against existing files in repo (prioritizing detected language)
        if lang == "python":
            source_files = [
                p for p in repo_dir.rglob("*.py")
                if not p.name.startswith("test_") and not any(part in {".git", ".agents", ".codex", ".venv"} for part in p.parts)
            ]
            if not source_files:
                source_files = [
                    p for p in repo_dir.rglob("*.go")
                    if not p.name.endswith("_test.go") and not any(part in {".git", ".agents", ".codex"} for part in p.parts)
                ]
        else:
            source_files = [
                p for p in repo_dir.rglob("*.go")
                if not p.name.endswith("_test.go") and not any(part in {".git", ".agents", ".codex"} for part in p.parts)
            ]
            if not source_files:
                source_files = [
                    p for p in repo_dir.rglob("*.py")
                    if not p.name.startswith("test_") and not any(part in {".git", ".agents", ".codex", ".venv"} for part in p.parts)
                ]

        if source_files:
            source = source_files[0]
            source_path = source.relative_to(repo_dir).as_posix()
            stem = source.stem
            if source.suffix == ".go":
                test_path = source.with_name(f"{stem}_test.go").relative_to(repo_dir).as_posix()
            elif source.suffix == ".py":
                test_path = source.with_name(f"test_{stem}.py").relative_to(repo_dir).as_posix()
            else:
                test_path = source.with_name(f"{stem}_test.go").relative_to(repo_dir).as_posix()
            existing_content = source.read_text(encoding="utf-8") if source.is_file() else ""
            return source_path, test_path, existing_content

        # 3. Fallback to first allowed path or language-appropriate default
        allowed = contract.allowed_paths[0] if contract.allowed_paths else f"main{default_ext}"
        if allowed.endswith("/"):
            source_path = f"{allowed}main{default_ext}"
            test_path = f"{allowed}test_main.py" if lang == "python" else f"{allowed}main_test.go"
        else:
            source_path = allowed
            stem = Path(allowed).stem
            test_path = str(Path(allowed).with_name(f"test_{stem}.py" if (allowed.endswith(".py") or lang == "python") else f"{stem}_test.go"))
        full_target = repo_dir / source_path
        existing_content = full_target.read_text(encoding="utf-8") if full_target.is_file() else ""
        return source_path, test_path, existing_content

    def _seek_milestone_feedback(self, milestone_name: str, summary: str, auto_approve: bool = False) -> Tuple[bool, str]:
        """
        Presents a milestone summary to the user and checks for confirmation or rework instructions.
        Returns (proceed: bool, feedback_text: str).
        """
        if auto_approve:
            self._log(f"[+] Milestone '{milestone_name}' auto-confirmed.")
            AUDIT_LOGGER.log_governance(milestone=milestone_name, decision="CONFIRMED", feedback="", auto_approved=True)
            return True, ""

        GLOBAL_DASHBOARD_STATE.request_milestone_review(milestone_name, summary)
        print(f"\n=======================================================")
        print(f"⭐ MILESTONE REVIEW: {milestone_name}")
        print(f"=======================================================")
        print(summary[:1200] + ("\n... [truncated for display]" if len(summary) > 1200 else ""))
        print("\nOptions:")
        print("  [ENTER] Confirm & Proceed on track")
        print("  [TEXT]  Enter rework instructions / adjustments")
        
        user_choice = input("\nYour decision: ").strip()
        if not user_choice:
            GLOBAL_DASHBOARD_STATE.submit_milestone_review(True, "")
            self._log(f"[+] Milestone '{milestone_name}' confirmed by user.")
            self.state.milestone_feedback_history.append({"milestone": milestone_name, "status": "confirmed", "feedback": ""})
            AUDIT_LOGGER.log_governance(milestone=milestone_name, decision="CONFIRMED", feedback="", auto_approved=False)
            return True, ""
        else:
            GLOBAL_DASHBOARD_STATE.submit_milestone_review(False, user_choice)
            self._log(f"[!] Milestone '{milestone_name}' rework requested: {user_choice}")
            self.state.milestone_feedback_history.append({"milestone": milestone_name, "status": "rework", "feedback": user_choice})
            AUDIT_LOGGER.log_governance(milestone=milestone_name, decision="REWORK", feedback=user_choice, auto_approved=False)
            return False, user_choice


    def _run_product_clarification_loop(self, auto_approve: bool = False) -> None:
        product_agent = ProductAgent()
        history = []
        current_input = self.state.user_goal

        while True:
            GLOBAL_DASHBOARD_STATE.update_agent("ProductAgent", "running", "Evaluating PRD clarity & NFR confidence")
            result = product_agent.run(current_input, conversation_history=history)
            understanding = result.get("understanding", "")
            questions = result.get("clarification_questions", [])
            is_clear = result.get("is_clear", False)
            confidence = float(result.get("confidence_score", 1.0 if is_clear else 0.5))
            func_score = float(result.get("functional_completeness", confidence))
            nfr_score = float(result.get("nfr_completeness", confidence))
            checkpoint_items = result.get("checkpoint_clarification_items", [])

            self.state.requirements_confidence = confidence
            self.state.functional_completeness = func_score
            self.state.nfr_completeness = nfr_score
            self.state.checkpoint_clarifications = checkpoint_items

            self._log(f"\nProduct Agent Assessment:")
            self._log(f"  * Overall Confidence: {confidence * 100:.1f}% (Threshold: >= 90.0% to begin architecture)")
            self._log(f"  * Functional Scope:   {func_score * 100:.1f}%")
            self._log(f"  * NFR Completeness:   {nfr_score * 100:.1f}%")
            self._log(f"Product Agent Understanding:\n{understanding}")
            history.append({"input": current_input, "understanding": understanding, "confidence": confidence})

            # Check confidence threshold (>= 90% automatically takes call to proceed)
            if confidence >= 0.90 or (is_clear and not questions):
                GLOBAL_DASHBOARD_STATE.update_agent("ProductAgent", "completed", f"PRD clarified ({confidence*100:.1f}% confidence)")
                self._log(f"[+] Product Agent took the call: requirements reached {confidence * 100:.1f}% confidence (>= 90% threshold).")
                if checkpoint_items:
                    self._log(f"[+] Queued {len(checkpoint_items)} non-blocking edge cases for task execution checkpoints.")
                self.state.clarified_prd = understanding

                # Milestone 1 User Feedback Gate
                milestone_summary = (
                    f"Requirements Confidence: {confidence * 100:.1f}%\n"
                    f"Functional: {func_score * 100:.1f}%, NFR: {nfr_score * 100:.1f}%\n\n"
                    f"PRD Understanding:\n{understanding}\n\n"
                    f"Queued Checkpoints ({len(checkpoint_items)}):\n" +
                    "\n".join(f" - [{c.get('checkpoint', 'general')}]: {c.get('question')} (Default: {c.get('default_assumption')})" for c in checkpoint_items)
                )
                confirmed, feedback = self._seek_milestone_feedback("Milestone 1: Requirements & PRD", milestone_summary, auto_approve=auto_approve)
                if confirmed:
                    break
                else:
                    current_input += f"\nUser Milestone Feedback: {feedback}"
                    continue

            # Confidence < 90%: continue grilling with targeted questions
            GLOBAL_DASHBOARD_STATE.update_agent("ProductAgent", "waiting", f"Waiting for human clarification ({confidence*100:.1f}%)")
            GLOBAL_DASHBOARD_STATE.request_clarification(questions)
            print(f"\n[!] Requirements Confidence is {confidence * 100:.1f}% (< 90% threshold). Grilling for missing specifics:")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")

            user_answers = input("\nEnter clarification details: ").strip()
            GLOBAL_DASHBOARD_STATE.submit_clarification(user_answers)
            current_input += f"\nClarification: {user_answers}"

    def _run_business_and_revenue_strategy(self, auto_approve: bool = False) -> None:
        contracts_dict = {p: self.state.contracts[p].model_dump() for p in self.state.contracts}
        biz_agent = BusinessStrategyAgent()
        rev_agent = RevenueROIAgent()

        self._log(f"Running Business Strategy Agent [Model: {biz_agent.model_name}]...")
        GLOBAL_DASHBOARD_STATE.update_agent("BusinessAgent", "running", f"Analyzing cohorts & competitors ({biz_agent.model_name})")
        biz_data = biz_agent.run(self.state.user_goal, self.state.clarified_prd, contracts_dict)
        GLOBAL_DASHBOARD_STATE.update_agent("BusinessAgent", "completed", "Market strategy formulated")

        self._log(f"Running Revenue & ROI Agent [Model: {rev_agent.model_name}]...")
        GLOBAL_DASHBOARD_STATE.update_agent("RevenueAgent", "running", f"Modeling ROI & onboarding metrics ({rev_agent.model_name})")
        rev_data = rev_agent.run(self.state.user_goal, self.state.clarified_prd, biz_data)
        GLOBAL_DASHBOARD_STATE.update_agent("RevenueAgent", "completed", "ROI & unit economics modeled")

        self.state.business_strategy = biz_data
        self.state.revenue_analysis = rev_data
        GLOBAL_DASHBOARD_STATE.set_business_and_revenue_strategy(biz_data, rev_data)

        self._log(f"[+] Business Strategy & Competitor Analysis generated:")
        self._log(f"    * Value Prop: {biz_data.get('value_proposition')}")
        self._log(f"    * Target Cohorts: {[c.get('cohort_name') for c in biz_data.get('user_cohorts', [])]}")
        self._log(f"    * Competitors Analyzed: {[c.get('competitor') for c in biz_data.get('competitor_analysis', [])]}")
        self._log(f"    * Est. Hours Saved: {rev_data.get('hours_saved_per_sprint', 0)} hrs/sprint")
        self._log(f"    * Est. Cost Savings: ${rev_data.get('cost_savings_estimate_usd', 0):,.2f}")
        self._log(f"    * Activation KPI: {rev_data.get('activation_kpi')}")

        summary = (
            f"Value Proposition: {biz_data.get('value_proposition')}\n\n"
            f"User Cohorts:\n" + "\n".join(f" - {c.get('cohort_name')}: {c.get('pain_point')} (WTP: {c.get('willingness_to_pay')})" for c in biz_data.get("user_cohorts", [])) + "\n\n"
            f"Competitor Analysis:\n" + "\n".join(f" - {c.get('competitor')}: ASCM Advantage -> {c.get('ascm_advantage')}" for c in biz_data.get("competitor_analysis", [])) + "\n\n"
            f"Revenue & ROI:\n"
            f" - Hours Saved/Sprint: {rev_data.get('hours_saved_per_sprint')} hrs\n"
            f" - Estimated Cost Savings: ${rev_data.get('cost_savings_estimate_usd', 0):,.2f}\n"
            f" - Activation KPI: {rev_data.get('activation_kpi')}\n"
            f" - Pricing Tiers: {', '.join(t.get('tier', '') + ' (' + str(t.get('price', '')) + ')' for t in rev_data.get('pricing_tiers', []))}"
        )
        confirmed, feedback = self._seek_milestone_feedback("Milestone 1b: Commercialization & Revenue Strategy", summary, auto_approve=auto_approve)
        if feedback:
            self.state.user_strategy_feedback = feedback
            self.state.clarified_prd += f"\nBusiness Strategy Guidance: {feedback}"
            self._log(f"[+] Incorporated user commercial feedback: {feedback}")

    def _run_architecture_and_design(self, providers: List[str], auto_approve: bool = False) -> None:
        contracts_dict = {p: self.state.contracts[p].model_dump() for p in providers}
        
        while True:
            self._log("Generating HLD and LLD specs...")
            GLOBAL_DASHBOARD_STATE.update_agent("DesignAgent", "running", "Writing HLD & LLD specs")
            design_result = DesignAgent().run(self.state.clarified_prd, contracts_dict)
            GLOBAL_DASHBOARD_STATE.update_agent("DesignAgent", "completed", "HLD & LLD generated")
            self.state.hld = design_result.get("hld", "")
            self.state.lld = design_result.get("lld", "")
            self._log(f"[+] HLD Generated ({len(self.state.hld)} chars)")
            self._log(f"[+] LLD Generated ({len(self.state.lld)} chars)")

            # Architecture Review Agent (Adversarial Critic)
            arch_review_agent = ArchitectureReviewAgent()
            self._log(f"Running Architecture Review Agent [Model: {arch_review_agent.model_name} - Adversarial Critic]...")
            GLOBAL_DASHBOARD_STATE.update_agent("ArchitectureReviewAgent", "running", f"Critiquing HLD/LLD against NFRs ({arch_review_agent.model_name})")
            arch_review = arch_review_agent.run(self.state.hld, self.state.lld, contracts_dict, user_goal=self.state.user_goal)
            GLOBAL_DASHBOARD_STATE.update_agent("ArchitectureReviewAgent", "completed", f"Review completed (Score: {arch_review.get('overall_score', 0)}/100)")
            self.state.architecture_review = arch_review
            GLOBAL_DASHBOARD_STATE.set_architecture_review(arch_review)

            arch_score = arch_review.get("overall_score", 85)
            arch_verdict = arch_review.get("verdict", "APPROVE")
            self._log(f"[+] Architecture Review Score: {arch_score}/100 | Verdict: {arch_verdict}")
            if arch_review.get("architectural_gaps"):
                self._log(f"    * Gaps Flagged: {arch_review.get('architectural_gaps')}")
            if arch_review.get("spof_risks"):
                self._log(f"    * SPOF Risks: {arch_review.get('spof_risks')}")

            self._log("Architect Agent decomposing requirements into tasks...")
            GLOBAL_DASHBOARD_STATE.update_agent("ArchitectAgent", "running", "Decomposing task breakdown")
            task_result = ArchitectAgent().run(
                self.state.clarified_prd, self.state.hld, self.state.lld, contracts_dict
            )
            GLOBAL_DASHBOARD_STATE.update_agent("ArchitectAgent", "completed", "Task breakdown ready")
            raw_tasks = task_result.get("tasks", [])
            self.state.task_breakdown = [TaskItem(**t) for t in raw_tasks if isinstance(t, dict)]
            GLOBAL_DASHBOARD_STATE.set_tasks([t.model_dump() for t in self.state.task_breakdown])

            self._log(f"[+] Created {len(self.state.task_breakdown)} execution sub-tasks:")
            for t in self.state.task_breakdown:
                self._log(f"    - [{t.id}] {t.title} -> Assigned to: '{t.assigned_agent}'")

            # Milestone 2 User Feedback Gate
            nfr_summary = ", ".join(f"{k}: {v.get('score')}/100" for k, v in arch_review.get("nfr_scorecard", {}).items()) if arch_review.get("nfr_scorecard") else "Pass"
            arch_summary = (
                f"Architecture Review (Score: {arch_score}/100 | Verdict: {arch_verdict})\n"
                f"NFR Scorecard: {nfr_summary}\n"
                f"Gaps Flagged ({len(arch_review.get('architectural_gaps', []))}): {', '.join(arch_review.get('architectural_gaps', [])) or 'None'}\n"
                f"SPOF Risks ({len(arch_review.get('spof_risks', []))}): {', '.join(arch_review.get('spof_risks', [])) or 'None'}\n\n"
                f"HLD Summary:\n{self.state.hld[:600]}...\n\n"
                f"Tasks ({len(self.state.task_breakdown)}):\n" +
                "\n".join(f" - [{t.id}] {t.title} (Assigned: {t.assigned_agent}, Target: {t.target_file or 'auto'})" for t in self.state.task_breakdown)
            )
            confirmed, feedback = self._seek_milestone_feedback("Milestone 2: Architecture & NFR Review", arch_summary, auto_approve=auto_approve)
            if confirmed:
                break
            else:
                self._log(f"Incorporating rework feedback into Architecture: {feedback}")
                self.state.user_arch_review_feedback = feedback
                self.state.clarified_prd += f"\nArchitecture Rework Feedback: {feedback}"

    def _run_task_execution(self, providers: List[str], consumers: List[str] = None, auto_approve: bool = False) -> List[Tuple]:
        pending_changes = []
        planner_agent = PlannerAgent()
        db_agent = DatabaseAgent()
        coder_agent = GoCoderAgent()
        security_agent = SecurityAuditorAgent()
        reviewer_agent = CodeReviewAgent()
        consumers = consumers or []

        # 1. Execute Provider Repositories
        provider_patches_summary = {}
        for provider in providers:
            contract = self.state.contracts[provider]
            if not contract.allowed_paths:
                self._log(f"Skipping {contract.name}: no allowed paths.")
                continue

            accumulated_patch: Dict[str, str] = {}

            # Execute tasks with multi-file targeting
            for task in self.state.task_breakdown:
                GLOBAL_DASHBOARD_STATE.update_task_status(task.id, "in_progress")
                GLOBAL_DASHBOARD_STATE.update_agent("PlannerAgent", "running", f"Planning task {task.id}")
                plan = planner_agent.run(task.model_dump(), self.state.hld)
                agent_choice = plan.get("agent_type", task.assigned_agent)
                instructions = plan.get("instructions", task.description)
                GLOBAL_DASHBOARD_STATE.update_agent("PlannerAgent", "completed", f"Planned task {task.id}")

                # Resolve deferred checkpoint items (<10% threshold questions)
                for cp in self.state.checkpoint_clarifications:
                    cp_tag = cp.get("checkpoint", "").lower()
                    if cp_tag and (cp_tag in task.id.lower() or cp_tag in task.title.lower() or cp_tag in (task.target_file or "").lower()):
                        cp_q = cp.get("question", "")
                        default_val = cp.get("default_assumption", "")
                        self._log(f"\n[Checkpoint Reached for {task.id}]: {cp_q}")
                        if auto_approve or not sys.stdin.isatty():
                            self._log(f"   -> Applied default assumption: {default_val}")
                            instructions += f"\n[Checkpoint Guidance]: {cp_q} -> Assumption: {default_val}"
                        else:
                            print(f"Deferred Checkpoint Question: {cp_q}")
                            print(f"Default Assumption: {default_val}")
                            user_ans = input("Your answer (or press ENTER to accept default): ").strip()
                            resolved = user_ans if user_ans else default_val
                            self._log(f"   -> Checkpoint clarified: {resolved}")
                            instructions += f"\n[Checkpoint Guidance]: {cp_q} -> {resolved}"

                self._log(f"Executing Task [{task.id}] '{task.title}' via Planner -> {agent_choice} Agent")
                source_path, test_path, existing_code = self._resolve_task_files(provider, task, contract)

                if agent_choice == "database":
                    GLOBAL_DASHBOARD_STATE.update_agent("DatabaseAgent", "running", f"Writing DB code for {task.id}")
                    patch = db_agent.run(instructions, contract.raw_content, source_path)
                    GLOBAL_DASHBOARD_STATE.update_agent("DatabaseAgent", "completed", f"DB code ready for {task.id}")
                else:
                    from orchestrator.domain import DomainAdapter
                    domain = DomainAdapter.detect_domain(self.state.user_goal)
                    lang = DomainAdapter.detect_language(self.state.user_goal, domain)
                    GLOBAL_DASHBOARD_STATE.update_agent("CoderAgent", "running", f"Writing {lang.upper()} code for {task.id}")
                    patch = coder_agent.run(
                        existing_code, instructions, source_path, test_path, contract.raw_content
                    )
                    GLOBAL_DASHBOARD_STATE.update_agent("CoderAgent", "completed", f"{lang.upper()} code ready for {task.id}")

                accumulated_patch.update(patch)
                task.status = "completed"
                GLOBAL_DASHBOARD_STATE.update_task_status(task.id, "completed")

            # Sandbox validation
            try:
                SandboxEngine.validate(provider, contract.allowed_paths, accumulated_patch)
            except PathViolationError as err:
                self._log(f"Skipping {contract.name}: Sandbox validation failed: {err}")
                continue

            # Security Audit
            GLOBAL_DASHBOARD_STATE.update_agent("SecurityAuditorAgent", "running", "Auditing generated patch")
            sec_report = security_agent.run(accumulated_patch)
            if not sec_report.get("passed", False):
                GLOBAL_DASHBOARD_STATE.update_agent("SecurityAuditorAgent", "failed", "Audit failed")
                self._log(f"Skipping {contract.name}: Security audit failed: {sec_report.get('issues', [])}")
                continue
            GLOBAL_DASHBOARD_STATE.update_agent("SecurityAuditorAgent", "completed", "Audit passed")

            # Code Review Agent (Adversarial Critic)
            GLOBAL_DASHBOARD_STATE.update_agent("CodeReviewAgent", "running", f"Auditing patch quality & security ({reviewer_agent.model_name})")
            review_report = reviewer_agent.run(accumulated_patch, self.state.hld, self.state.lld, contracts={contract.name: contract.model_dump()})
            self.state.code_review_report = review_report
            GLOBAL_DASHBOARD_STATE.set_code_review_report(review_report)
            score = review_report.get("overall_score", 90)
            sec_grade = review_report.get("security_grade", "A")
            is_approved = review_report.get("approved", True)
            self._log(f"[+] Code Review Audit: Score {score}/100, Security Grade: {sec_grade}, Verdict: {review_report.get('verdict', 'APPROVED')}")
            for f in review_report.get("findings", []):
                self._log(f"    * [{f.get('severity', 'INFO')}] {f.get('file', 'general')}: {f.get('issue')}")
            if not is_approved:
                GLOBAL_DASHBOARD_STATE.update_agent("CodeReviewAgent", "failed", f"Review rejected (Score: {score})")
                self._log(f"Skipping {contract.name}: Code review rejected patch: {review_report.get('comments', [])}")
                continue
            GLOBAL_DASHBOARD_STATE.update_agent("CodeReviewAgent", "completed", f"Patch approved (Score: {score}/100)")

            self._log(f"[+] Patch for '{contract.name}' passed Sandbox, Security Audit, and Code Review!")
            pending_changes.append((contract, accumulated_patch))
            provider_patches_summary[contract.name] = list(accumulated_patch.keys())

        # 2. Execute Consumer Repositories (Synchronized Cross-Repo Updates)
        for consumer in consumers:
            contract = self.state.contracts.get(consumer)
            if not contract or not contract.allowed_paths:
                continue

            self._log(f"[+] Synchronizing Consumer Repository '{contract.name}'...")
            consumer_task = TaskItem(
                id=f"CONSUMER-SYNC-{contract.name.upper()}",
                title=f"Update consumer client in {contract.name}",
                description=(
                    f"Update client API callers and tests in consumer repo '{contract.name}' to integrate with "
                    f"the updated provider capabilities. Provider changes: {json.dumps(provider_patches_summary)}"
                ),
                assigned_agent="coder",
                target_file="",
            )
            source_path, test_path, existing_code = self._resolve_task_files(consumer, consumer_task, contract)
            GLOBAL_DASHBOARD_STATE.update_agent("GoCoderAgent", "running", f"Writing consumer client update for {contract.name}")
            consumer_patch = coder_agent.run(
                existing_code, consumer_task.description, source_path, test_path, contract.raw_content
            )
            GLOBAL_DASHBOARD_STATE.update_agent("GoCoderAgent", "completed", f"Consumer client update ready for {contract.name}")

            try:
                SandboxEngine.validate(consumer, contract.allowed_paths, consumer_patch)
            except PathViolationError as err:
                self._log(f"Skipping consumer {contract.name}: Sandbox validation failed: {err}")
                continue

            sec_report = security_agent.run(consumer_patch)
            if not sec_report.get("passed", False):
                self._log(f"Skipping consumer {contract.name}: Security audit failed: {sec_report.get('issues', [])}")
                continue

            self._log(f"[+] Consumer patch for '{contract.name}' passed Sandbox & Security Audit!")
            pending_changes.append((contract, consumer_patch))

        return pending_changes

    def _run_verification_and_commit(self, pending_changes: List[Tuple], auto_approve: bool = False) -> None:
        self._log("Pending changes for writing:")
        changes_summary = []
        for contract, files in pending_changes:
            print(f"- Repository: {contract.name}")
            file_list = []
            for filename, content in files.items():
                print(f"    * {filename}")
                file_list.append({"filename": filename, "preview": content[:300]})
            changes_summary.append({
                "repo": contract.name,
                "repo_path": contract.repo_path,
                "files": file_list
            })

        GLOBAL_DASHBOARD_STATE.request_approval(changes_summary)

        approved = auto_approve
        if not approved:
            if GLOBAL_DASHBOARD_STATE.approval_decision is not None:
                approved = GLOBAL_DASHBOARD_STATE.approval_decision
            else:
                confirm = input("\nType 'APPROVE' to write changes, run verification, and commit to local Git branch: ").strip()
                approved = (confirm.upper() == "APPROVE")
                GLOBAL_DASHBOARD_STATE.submit_approval(approved)

        if not approved:
            self._log("Aborted by user.")
            return

        coder_agent = GoCoderAgent()
        max_healing_attempts = 3
        committed_records = []

        for contract, files in pending_changes:
            try:
                GitService.ensure_clean_repo(contract.repo_path)
                branch = GitService.create_branch(contract.repo_path, self.state.user_goal)
                SandboxEngine.validate_and_write(contract.repo_path, contract.allowed_paths, files)
                
                verification = VerifierEngine.run_checks(contract.repo_path)
                GLOBAL_DASHBOARD_STATE.record_test_result(
                    repo=contract.name,
                    language=verification.language,
                    passed=verification.passed,
                    test_output=verification.test_output,
                    vet_output=verification.vet_output,
                    sandboxed=verification.sandboxed,
                    framework=verification.framework,
                    total_tests=verification.total_tests,
                    passed_count=verification.passed_count,
                    failed_count=verification.failed_count,
                    test_cases=verification.test_cases,
                )
                AUDIT_LOGGER.log_verification(
                    repo=contract.name,
                    language=verification.language,
                    passed=verification.passed,
                    test_output=verification.test_output,
                    vet_output=verification.vet_output,
                    sandboxed=verification.sandboxed,
                    framework=verification.framework,
                    total_tests=verification.total_tests,
                    passed_count=verification.passed_count,
                    failed_count=verification.failed_count,
                )
                if not verification.passed:
                    healed = False
                    for attempt in range(1, max_healing_attempts + 1):
                        self._log(f"[!] Verification failed on attempt {attempt}/{max_healing_attempts}. Triggering Self-Healing Reflection Loop...")
                        GLOBAL_DASHBOARD_STATE.update_agent(
                            "GoCoderAgent", "running", f"Self-healing attempt {attempt} for {contract.name}"
                        )
                        err_summary = verification.error_summary()
                        self._log(f"Diagnostic Error Output:\n{err_summary}")
                        
                        current_files = {}
                        for f in files.keys():
                            fp = Path(contract.repo_path) / f
                            if fp.exists():
                                current_files[f] = fp.read_text(encoding="utf-8")

                        fixed_patch = coder_agent.fix(current_files, err_summary, contract.raw_content)
                        if not fixed_patch:
                            break
                        
                        try:
                            SandboxEngine.validate(contract.repo_path, contract.allowed_paths, fixed_patch)
                            SandboxEngine.validate_and_write(contract.repo_path, contract.allowed_paths, fixed_patch)
                            files.update(fixed_patch)
                        except PathViolationError as err:
                            self._log(f"Self-healing patch failed sandbox: {err}")
                            AUDIT_LOGGER.log_security_event("PATH_VIOLATION", {"repo": contract.name, "error": str(err)}, severity="ERROR")
                            break

                        verification = VerifierEngine.run_checks(contract.repo_path)
                        GLOBAL_DASHBOARD_STATE.record_test_result(
                            repo=contract.name,
                            language=verification.language,
                            passed=verification.passed,
                            test_output=verification.test_output,
                            vet_output=verification.vet_output,
                            sandboxed=verification.sandboxed,
                            framework=verification.framework,
                            total_tests=verification.total_tests,
                            passed_count=verification.passed_count,
                            failed_count=verification.failed_count,
                            test_cases=verification.test_cases,
                        )
                        AUDIT_LOGGER.log_verification(
                            repo=contract.name,
                            language=verification.language,
                            passed=verification.passed,
                            test_output=verification.test_output,
                            vet_output=verification.vet_output,
                            sandboxed=verification.sandboxed,
                            framework=verification.framework,
                            total_tests=verification.total_tests,
                            passed_count=verification.passed_count,
                            failed_count=verification.failed_count,
                        )
                        if verification.passed:
                            self._log(f"[+] Self-Healing succeeded on attempt {attempt}! Verification passed.")
                            GLOBAL_DASHBOARD_STATE.update_agent("GoCoderAgent", "completed", "Self-healing succeeded")
                            healed = True
                            break

                    if not healed and not verification.passed:
                        self._log(f"Verification failed on branch '{branch}' after {max_healing_attempts} self-healing attempts. Changes remain uncommitted for review.")
                        print(verification.test_output or verification.vet_output)
                        continue

                GitService.commit(contract.repo_path, self.state.user_goal, list(files))
                self._log(f"[ SUCCESS ] Committed verified changes on branch '{branch}' for repo '{contract.name}'.")
                committed_records.append({
                    "contract": contract,
                    "branch": branch,
                    "files": files,
                })
            except (OSError, RuntimeError) as error:
                self._log(f"Error applying changes to '{contract.name}': {error}")
                AUDIT_LOGGER.log_event("PATCH_APPLY_ERROR", agent="ORCHESTRATOR", action="WRITE", details={"repo": contract.name, "error": str(error)}, level="ERROR")

        # Phase 6b: Coordinated Linked Cross-Repository PR Generation
        if committed_records:
            self._log(f"\n--- Coordinated Cross-Repository Pull Request Artifacts ---")
            for record in committed_records:
                c = record["contract"]
                b = record["branch"]
                f_list = list(record["files"].keys())
                companions = [
                    {"name": other["contract"].name, "branch": other["branch"], "role": "companion"}
                    for other in committed_records
                    if other["contract"].repo_path != c.repo_path
                ]
                pr_desc = GitService.generate_pr_description(
                    goal=self.state.user_goal,
                    files=f_list,
                    role="provider",
                    linked_repos=companions,
                    prd_summary=self.state.prd,
                )
                artifact_path = GitService.write_pr_artifact(c.repo_path, pr_desc)
                self._log(f"[+] Generated linked PR draft for '{c.name}': {artifact_path}")
                AUDIT_LOGGER.log_git_commit(
                    repo=c.name,
                    branch=b,
                    goal=self.state.user_goal,
                    files=f_list,
                    pr_path=artifact_path,
                )

                # If remote push / PR creation is enabled
                if os.environ.get("AUTO_PUSH_REMOTE", "").lower() in ("true", "1", "yes") or os.environ.get("CREATE_PR", "").lower() in ("true", "1", "yes"):
                    if GitService.push_branch(c.repo_path, b):
                        self._log(f"[+] Pushed branch '{b}' to origin for '{c.name}'.")
                        pr_url = GitService.create_github_pr(
                            c.repo_path, b, f"feat: {self.state.user_goal}", pr_desc
                        )
                        if pr_url:
                            self._log(f"[+] Successfully opened GitHub Pull Request: {pr_url}")


    def _notify_phase(self, phase_name: str) -> None:
        print(f"\n--- {phase_name} ---")
        GLOBAL_DASHBOARD_STATE.set_phase(phase_name)
        AUDIT_LOGGER.log_phase(phase_name)

    def _log(self, message: str) -> None:
        print(message)
        GLOBAL_DASHBOARD_STATE.log(message)
        AUDIT_LOGGER.log_step(agent="ORCHESTRATOR", action="LOG", details=message)

    def _validate_repositories(self, repos: List[str]) -> List[str]:
        valid = []
        for r in repos:
            p = Path(r).resolve()
            if not p.is_dir():
                raise ValueError(f"Directory does not exist: {r}")
            valid.append(str(p))
        return valid



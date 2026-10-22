import difflib
import hashlib
import subprocess
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
from orchestrator.engine.sandbox import SandboxEngine, PathViolationError, _is_allowed
from orchestrator.engine.verifier import VerifierEngine
from orchestrator.git_service import GitService, _slugify
from orchestrator.security.audit_logger import AUDIT_LOGGER
from orchestrator.state import SharedBlackboard, TaskItem


# Unattended runs answer clarifying questions with a scope-limiting default instead of an empty "use defaults".
AUTO_ANSWER = (
    "Use the simplest implementation consistent with the stated goal and the existing code shown above. "
    "Keep existing behaviour and public names; do not add scope the goal does not mention."
)


class OrchestratorEngine:
    INCREMENTAL_CACHE_FILE = ".ascm_history/incremental_state.json"

    def __init__(
        self,
        repo_paths: List[str],
        initial_goal: str,
        enable_dashboard: bool = True,
        port: int = 8080,
        incremental: bool = False,
    ):
        GLOBAL_DASHBOARD_STATE.new_session(initial_goal)
        try:
            self.valid_repos = self._validate_repositories(repo_paths)
            self.state = SharedBlackboard(user_goal=initial_goal, target_repos=self.valid_repos)
            self.incremental = incremental
            AUDIT_LOGGER.log_event(
                event_type="SESSION_START",
                agent="ORCHESTRATOR",
                action="INITIALIZE",
                details={"goal": initial_goal, "repositories": self.valid_repos, "incremental": incremental},
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
            # ── Incremental / Patch Mode ───────────────────────────────────────
            # If --incremental is set and a previous session cache exists, restore
            # phases 1-4 from disk and jump straight to code generation (phase 5).
            if self.incremental and self._try_restore_incremental_cache():
                self._notify_phase("[INCREMENTAL] Restoring phases 1-4 from cache — skipping re-planning")
                self._log(f"[+] Incremental mode: restored topology, PRD, strategy, and architecture from cache.")
                self._log(f"[+] Incremental mode: re-running Phase 5 (code gen) and Phase 6 (commit) only.")

                providers = self.state.incremental_providers or self.valid_repos
                consumers = self.state.incremental_consumers or []

                self._notify_phase("Phase 5 (incremental): Task Execution & Code Generation")
                pending_changes = self._run_task_execution(providers, consumers, auto_approve=auto_approve)

                if not pending_changes:
                    self._log("No audited changes ready for writing (incremental run).")
                    return

                self._notify_phase("Phase 6 (incremental): Human Approval & Local Git Commit")
                self._run_verification_and_commit(pending_changes, auto_approve=auto_approve)
                return

            # ── Full 6-Phase Pipeline ──────────────────────────────────────────
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
            # Cache providers/consumers for incremental mode
            self.state.incremental_providers = providers
            self.state.incremental_consumers = consumers
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

            # Save phases 1-4 state to cache for future --incremental runs
            self._save_incremental_cache(providers, consumers)

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

    def _save_incremental_cache(self, providers: List[str], consumers: List[str]) -> None:
        """Persist phases 1-4 outputs to disk for future --incremental runs."""
        import json as _json
        cache = {
            "goal": self.state.user_goal,
            "clarified_prd": getattr(self.state, 'clarified_prd', ""),
            "discovery_summary": getattr(self.state, 'discovery_summary', ""),
            "business_strategy": getattr(self.state, 'business_strategy', {}),
            "revenue_analysis": getattr(self.state, 'revenue_analysis', {}),
            "architecture_plan": getattr(self.state, 'architecture_plan', {}),
            "pending_tasks": [t.model_dump() if hasattr(t, 'model_dump') else vars(t) for t in getattr(self.state, 'pending_tasks', [])],
            "providers": providers,
            "consumers": consumers,
        }
        # Write to first repo's .ascm_history
        if self.valid_repos:
            cache_path = Path(self.valid_repos[0]) / self.INCREMENTAL_CACHE_FILE
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            GitService.exclude_locally(self.valid_repos[0])
            cache_path.write_text(_json.dumps(cache, indent=2))
            self._log(f"[+] Incremental cache saved to {cache_path}")

    def _try_restore_incremental_cache(self) -> bool:
        """Attempt to restore phases 1-4 from disk cache. Returns True if successful."""
        import json as _json
        if not self.valid_repos:
            return False
        cache_path = Path(self.valid_repos[0]) / self.INCREMENTAL_CACHE_FILE
        if not cache_path.exists():
            self._log("[Incremental] No cache found — running full pipeline.")
            return False
        try:
            cache = _json.loads(cache_path.read_text())
            # Only restore if goal matches
            if cache.get("goal", "").strip() != self.state.user_goal.strip():
                self._log(f"[Incremental] Goal mismatch vs cached goal. Running full pipeline.")
                return False

            self.state.clarified_prd = cache.get("clarified_prd", "")
            self.state.discovery_summary = cache.get("discovery_summary", "")
            self.state.business_strategy = cache.get("business_strategy", {})
            self.state.revenue_analysis = cache.get("revenue_analysis", {})
            self.state.architecture_plan = cache.get("architecture_plan", {})
            self.state.incremental_providers = cache.get("providers", [])
            self.state.incremental_consumers = cache.get("consumers", [])

            # Restore pending tasks
            from orchestrator.state import TaskItem
            raw_tasks = cache.get("pending_tasks", [])
            self.state.pending_tasks = [TaskItem(**t) for t in raw_tasks if isinstance(t, dict)]

            # Populate contracts from disk for restored providers
            for repo in self.state.incremental_providers:
                if repo not in self.state.contracts:
                    contract = parse_skill_contract(repo)
                    self.state.contracts[repo] = contract

            self._log(f"[Incremental] ✅ Restored {len(self.state.pending_tasks)} tasks from cache.")
            return True
        except Exception as e:
            self._log(f"[Incremental] Cache restore failed ({e}). Running full pipeline.")
            return False

    _SKIP_DIRS = {
        ".git", ".agents", ".codex", ".venv", "venv", "node_modules", "vendor", "dist", "build",
        "__pycache__", ".next", ".tox", "target", ".ascm_history",
    }
    _LANG_GLOBS = {
        "python": ["*.py"], "go": ["*.go"],
        "typescript": ["*.ts", "*.tsx"], "javascript": ["*.js", "*.jsx"], "rust": ["*.rs"],
    }

    def _effective_language(self, repo_path: str) -> str:
        """The repository decides the language; goal keywords are only a fallback for empty repos."""
        detected = VerifierEngine.detect_language(repo_path)
        if detected in ("python", "go"):
            return detected
        if detected == "node":
            return "typescript" if (Path(repo_path) / "tsconfig.json").exists() else "javascript"
        from orchestrator.domain import DomainAdapter
        goal = self.state.user_goal if getattr(self, "state", None) else ""
        return DomainAdapter.detect_language(goal, DomainAdapter.detect_domain(goal))

    @staticmethod
    def _is_test_file(path: Path) -> bool:
        n = path.name
        return (
            n.startswith("test_") or n.endswith("_test.go") or n == "conftest.py"
            or ".test." in n or ".spec." in n
        )

    @staticmethod
    def _test_path_for(source: Path, lang: str) -> str:
        stem, suffix = source.stem, source.suffix
        if suffix == ".go":
            return source.with_name(f"{stem}_test.go").as_posix()
        if suffix == ".py":
            return source.with_name(f"test_{stem}.py").as_posix()
        if suffix in (".js", ".jsx", ".ts", ".tsx"):
            return source.with_name(f"{stem}.test{suffix}").as_posix()
        return source.with_name(f"test_{stem}.py" if lang == "python" else f"{stem}_test.go").as_posix()

    def _candidate_sources(self, repo_dir: Path, lang: str, contract) -> List[Path]:
        found: List[Path] = []
        for pattern in self._LANG_GLOBS.get(lang, []):
            for path in sorted(repo_dir.rglob(pattern)):
                rel = path.relative_to(repo_dir)
                if path.is_symlink() or any(part in self._SKIP_DIRS for part in rel.parts):
                    continue
                if path.name == "__init__.py" or self._is_test_file(path):  # package markers are never the edit target
                    continue
                if not _is_allowed(rel.as_posix(), contract.allowed_paths):
                    continue
                found.append(path)
        return found

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.is_file() and not path.is_symlink() else ""

    def _resolve_task_files(self, repo_path: str, task: TaskItem, contract) -> Tuple[str, str, str]:
        """
        Determines the source file path, test file path, and existing file content
        for a specific task, respecting allowed_paths and the repository's own language.
        Selection is deterministic (sorted) and never picks vendored, built or symlinked files.
        """
        lang = self._effective_language(repo_path)
        default_ext = {"python": ".py", "go": ".go", "typescript": ".ts", "javascript": ".js", "rust": ".rs"}.get(lang, ".go")

        repo_dir = Path(repo_path).resolve()
        target = task.target_file.strip() if getattr(task, "target_file", None) else ""

        # 1. If task provides a specific target file
        if target:
            target_p = Path(target)
            if not target_p.is_absolute() and ".." not in target_p.parts:
                if self._is_test_file(target_p):  # editing an existing test file: it is both source and test
                    return target_p.as_posix(), target_p.as_posix(), self._read_text(repo_dir / target_p)
                return target_p.as_posix(), self._test_path_for(target_p, lang), self._read_text(repo_dir / target_p)

        # 2. Match against existing files in repo, in the repo's own language first
        source_files = self._candidate_sources(repo_dir, lang, contract)
        if not source_files:
            for other in self._LANG_GLOBS:
                if other != lang:
                    source_files = self._candidate_sources(repo_dir, other, contract)
                    if source_files:
                        lang = other
                        break

        if source_files:
            source = source_files[0]
            rel = source.relative_to(repo_dir)
            return rel.as_posix(), self._test_path_for(rel, lang), self._read_text(source)

        # 3. Fallback to first allowed path or language-appropriate default
        allowed = contract.allowed_paths[0] if contract.allowed_paths else f"main{default_ext}"
        if allowed.endswith("/"):
            source_path = f"{allowed}main{default_ext}"
        else:
            source_path = allowed
        return source_path, self._test_path_for(Path(source_path), lang), self._read_text(repo_dir / source_path)

    @staticmethod
    def _task_targets(task: TaskItem, contract) -> bool:
        """A task with a repo only runs there; a task without one runs on every provider (legacy behaviour)."""
        wanted = (getattr(task, "repo", "") or "").strip().lower().rstrip("/")
        if not wanted:
            return True
        return wanted in {contract.name.lower(), contract.repo_path.lower().rstrip("/"), Path(contract.repo_path).name.lower()}

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
        snapshot = self._repo_snapshot(max_files=6, max_chars_per_file=1500, max_total=9000)
        current_input = self.state.user_goal + (
            f"\n\nExisting repositories (read-only context; judge the requirement against what already exists):\n{snapshot}"
            if snapshot else ""
        )

        max_rounds = int(os.environ.get("ASCM_MAX_CLARIFY_ROUNDS", "8"))
        rounds = 0
        while True:
            rounds += 1
            if rounds > max_rounds:
                raise RuntimeError(
                    f"Requirements are still below the confidence threshold after {max_rounds} clarification rounds; "
                    "refusing to guess. Refine the goal and re-run."
                )
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

            # Confidence < 90%: continue grilling with targeted questions one by one
            active_question = questions[0]
            remaining_count = len(questions)
            GLOBAL_DASHBOARD_STATE.update_agent(
                "ProductAgent",
                "waiting",
                f"Grilling question 1 of {remaining_count} ({confidence*100:.1f}% confidence)",
            )
            GLOBAL_DASHBOARD_STATE.request_clarification([active_question])
            print(f"\n" + "-" * 75)
            print(f"🔥 PRODUCT AGENT DOMAIN GRILLING [Requirements Confidence: {confidence * 100:.1f}% / Target: >= 90.0%]")
            print(f"   Unresolved Dimensions Queue: {remaining_count} items remaining")
            print("-" * 75)
            print(f"👉 Question: {active_question}\n")

            if auto_approve or not sys.stdin.isatty():
                default_ans = AUTO_ANSWER
                self._log(f"[+] Auto-clarified question: {active_question} -> {default_ans}")
                current_input += f"\nClarification for '{active_question}': {default_ans}"
            else:
                user_answer = input("Your Answer (or press ENTER to accept recommended default): ").strip()
                if not user_answer:
                    user_answer = AUTO_ANSWER
                    print(f"   ↳ Default accepted: {user_answer}")
                GLOBAL_DASHBOARD_STATE.submit_clarification(user_answer)
                current_input += f"\nClarification for '{active_question}': {user_answer}"

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

    _EXT_FOR_LANG = {"python": {".py"}, "go": {".go"}, "typescript": {".ts", ".tsx"}, "javascript": {".js", ".jsx"}, "rust": {".rs"}}

    def _normalize_task_targets(self, providers: List[str]) -> None:
        """Drop task targets whose extension does not belong to the repo's language (e.g. service.go in a Python repo);
        the resolver then picks a real existing file instead of creating a wrong-language one."""
        for task in self.state.task_breakdown:
            if not task.target_file:
                continue
            repos = [p for p in providers if self._task_targets(task, self.state.contracts[p])] or providers
            suffix = Path(task.target_file).suffix.lower()
            if repos and suffix and all(suffix not in self._EXT_FOR_LANG.get(self._effective_language(r), {suffix}) for r in repos):
                self._log(f"[!] Task {task.id} targeted '{task.target_file}', which does not match the repo language; re-resolving.")
                task.target_file = ""

    def _repo_snapshot(self, max_files: int = 10, max_chars_per_file: int = 3000, max_total: int = 24000) -> str:
        """The planner must see what actually exists. Without this it invents work for files that are not there."""
        parts: List[str] = []
        total = 0
        for repo_path, contract in self.state.contracts.items():
            repo_dir = Path(repo_path)
            header = f"### Repository '{contract.name}' (role: {contract.role}; editable paths: {contract.allowed_paths})"
            parts.append(header)
            files: List[Path] = []
            for patterns in self._LANG_GLOBS.values():
                for pattern in patterns:
                    for path in sorted(repo_dir.rglob(pattern)):
                        rel = path.relative_to(repo_dir)
                        if path.is_symlink() or any(part in self._SKIP_DIRS for part in rel.parts) or path.name == "__init__.py":
                            continue
                        files.append(path)
            for path in files[:max_files]:
                chunk = f"--- {path.relative_to(repo_dir).as_posix()}\n{self._read_text(path)[:max_chars_per_file]}"
                if total + len(chunk) > max_total:
                    break
                parts.append(chunk)
                total += len(chunk)
        return "\n".join(parts)

    def _run_architecture_and_design(self, providers: List[str], auto_approve: bool = False) -> None:
        contracts_dict = {p: self.state.contracts[p].model_dump() for p in providers}
        
        while True:
            self._log("Generating HLD and LLD specs...")
            GLOBAL_DASHBOARD_STATE.update_agent("DesignAgent", "running", "Writing HLD & LLD specs")
            design_result = DesignAgent().run(
                self.state.clarified_prd, contracts_dict,
                language=self._effective_language(providers[0]) if providers else None,
                repo_context=self._repo_snapshot(max_files=8, max_chars_per_file=2500, max_total=16000),
            )
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
                self.state.clarified_prd, self.state.hld, self.state.lld, contracts_dict,
                kg_context=self._repo_snapshot(),
                language=self._effective_language(providers[0]) if providers else None,
            )
            GLOBAL_DASHBOARD_STATE.update_agent("ArchitectAgent", "completed", "Task breakdown ready")
            raw_tasks = task_result.get("tasks", [])
            self.state.task_breakdown = [TaskItem(**t) for t in raw_tasks if isinstance(t, dict)]
            self._normalize_task_targets(providers)
            GLOBAL_DASHBOARD_STATE.set_tasks([t.model_dump() for t in self.state.task_breakdown])

            self._log(f"[+] Created {len(self.state.task_breakdown)} execution sub-tasks:")
            for t in self.state.task_breakdown:
                self._log(f"    - [{t.id}] {t.title} -> Assigned to: '{t.assigned_agent}'")

            if auto_approve and str(arch_verdict).upper() in {"REJECT", "REJECTED", "REWORK", "REVISE", "FAIL"}:
                raise RuntimeError(
                    f"Architecture review verdict is {arch_verdict}; an unattended run cannot proceed past a rejected design."
                )

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
        provider_diffs: Dict[str, str] = {}
        failed_providers: List[str] = []
        for provider in providers:
            contract = self.state.contracts[provider]
            if not contract.allowed_paths:
                self._log(f"Skipping {contract.name}: no allowed paths.")
                continue

            accumulated_patch: Dict[str, str] = {}

            # Execute tasks with multi-file targeting
            for task in self.state.task_breakdown:
                if not self._task_targets(task, contract):
                    continue
                GLOBAL_DASHBOARD_STATE.update_task_status(task.id, "in_progress")
                GLOBAL_DASHBOARD_STATE.update_agent("PlannerAgent", "running", f"Planning task {task.id}")
                plan = planner_agent.run(task.model_dump(), self.state.hld, language=self._effective_language(provider))
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
                # Chain edits: a later task must build on an earlier task's output, not on the stale file on disk.
                existing_code = accumulated_patch.get(source_path, existing_code)

                if agent_choice == "database":
                    GLOBAL_DASHBOARD_STATE.update_agent("DatabaseAgent", "running", f"Writing DB code for {task.id}")
                    patch = db_agent.run(instructions, contract.raw_content, source_path)
                    GLOBAL_DASHBOARD_STATE.update_agent("DatabaseAgent", "completed", f"DB code ready for {task.id}")
                else:
                    lang = self._effective_language(provider)
                    GLOBAL_DASHBOARD_STATE.update_agent("CoderAgent", "running", f"Writing {lang.upper()} code for {task.id}")
                    patch = coder_agent.run(
                        existing_code, instructions, source_path, test_path, contract.raw_content, language=lang,
                        existing_tests=accumulated_patch.get(test_path) or self._read_text(Path(provider) / test_path),
                    )
                    GLOBAL_DASHBOARD_STATE.update_agent("CoderAgent", "completed", f"{lang.upper()} code ready for {task.id}")

                if not isinstance(patch, dict) or not patch:
                    task.status = "failed"
                    GLOBAL_DASHBOARD_STATE.update_task_status(task.id, "failed")
                    self._log(f"Task [{task.id}] produced no usable patch for '{contract.name}'.")
                    continue
                accumulated_patch.update(patch)
                task.status = "completed"
                GLOBAL_DASHBOARD_STATE.update_task_status(task.id, "completed")

            if not accumulated_patch:
                self._log(f"Skipping {contract.name}: no task produced a patch.")
                failed_providers.append(contract.name)
                continue

            accumulated_patch, review_report, problems = self._gate_and_revise(
                provider, contract, accumulated_patch, security_agent, reviewer_agent, coder_agent, review=True,
            )
            if accumulated_patch is None:
                self._log(f"Skipping {contract.name}: patch rejected after revision: {problems}")
                failed_providers.append(contract.name)
                continue
            self.state.code_review_report = review_report
            self._log(f"[+] Patch for '{contract.name}' passed Sandbox, Syntax Check, Security Audit, and Code Review!")
            pending_changes.append((contract, accumulated_patch))
            provider_patches_summary[contract.name] = list(accumulated_patch.keys())
            provider_diffs[contract.name] = "".join(
                self._render_diff(provider, f, c) for f, c in sorted(accumulated_patch.items()) if not self._is_test_file(Path(f))
            )[:8000]

        # 2. Execute Consumer Repositories (Synchronized Cross-Repo Updates)
        if failed_providers or not provider_patches_summary:
            if consumers:
                self._log(
                    f"Skipping all consumers: provider change(s) {failed_providers or 'none produced'} did not pass the gates, "
                    "so a consumer update would target an API that does not exist."
                )
            consumers = []
        failed_consumers: List[str] = []
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
                    f"the updated provider capabilities. The provider API changed as follows (unified diff of its source files); "
                    f"make the consumer parse/use exactly these changes and keep existing behaviour working:\n"
                    + "\n".join(f"### {name}\n{diff}" for name, diff in provider_diffs.items())
                ),
                assigned_agent="coder",
                target_file="",
            )
            source_path, test_path, existing_code = self._resolve_task_files(consumer, consumer_task, contract)
            GLOBAL_DASHBOARD_STATE.update_agent("GoCoderAgent", "running", f"Writing consumer client update for {contract.name}")
            consumer_patch = coder_agent.run(
                existing_code, consumer_task.description, source_path, test_path, contract.raw_content,
                language=self._effective_language(consumer),
                existing_tests=self._read_text(Path(consumer) / test_path),
            )
            GLOBAL_DASHBOARD_STATE.update_agent("GoCoderAgent", "completed", f"Consumer client update ready for {contract.name}")

            if not isinstance(consumer_patch, dict) or not consumer_patch:
                self._log(f"Skipping consumer {contract.name}: no usable patch.")
                continue
            consumer_patch, _, problems = self._gate_and_revise(
                consumer, contract, consumer_patch, security_agent, reviewer_agent, coder_agent, review=True,
            )
            if consumer_patch is None:
                self._log(f"Skipping consumer {contract.name}: patch rejected after revision: {problems}")
                failed_consumers.append(contract.name)
                continue
            self._log(f"[+] Consumer patch for '{contract.name}' passed Sandbox, Syntax Check, Security Audit & Code Review!")
            pending_changes.append((contract, consumer_patch))

        if failed_consumers and pending_changes and os.environ.get("ASCM_ALLOW_PARTIAL", "").lower() not in ("1", "true", "yes"):
            self._log(
                f"[!] Not committing anything: consumer(s) {failed_consumers} have no approved patch, and a provider change "
                "without its consumers would leave the repositories inconsistent. Set ASCM_ALLOW_PARTIAL=1 to override."
            )
            AUDIT_LOGGER.log_event("ATOMIC_ABORT", agent="ORCHESTRATOR", action="ABORT",
                                   details={"failed_consumers": failed_consumers}, level="WARNING")
            return []

        return pending_changes

    @staticmethod
    def _syntax_problems(patch: Dict[str, str]) -> List[str]:
        """Free, deterministic check run before spending LLM calls on review: Python must at least compile."""
        problems = []
        for name, content in patch.items():
            if name.endswith(".py"):
                try:
                    compile(content, name, "exec")
                except SyntaxError as err:
                    problems.append(f"{name}: syntax error: {err.msg} (line {err.lineno})")
        return problems

    def _compatibility_problems(self, repo_path: str, patch: Dict[str, str]) -> List[str]:
        """Public API removals and deleted tests that the goal did not ask for (see engine/api_surface.py)."""
        from orchestrator.engine.api_surface import contract_problems
        goal = f"{self.state.user_goal}\n{self.state.clarified_prd}"
        problems: List[str] = []
        for name, new in sorted(patch.items()):
            if not name.endswith(".py"):
                continue
            old = self._read_text(Path(repo_path) / name)
            if old:
                problems.extend(contract_problems(name, old, new, goal))
        return problems

    def _gate_once(self, repo_path, contract, patch, security_agent, reviewer_agent, review):
        """Returns (problems, review_report). Empty problems means every gate passed."""
        try:
            SandboxEngine.validate(repo_path, contract.allowed_paths, patch)
        except PathViolationError as err:
            return [f"Sandbox: {err}"], None
        syntax = self._syntax_problems(patch)
        if syntax:
            return syntax, None
        compat = self._compatibility_problems(repo_path, patch)
        if compat:
            return compat, None

        GLOBAL_DASHBOARD_STATE.update_agent("SecurityAuditorAgent", "running", "Auditing generated patch")
        goal = self.state.clarified_prd or self.state.user_goal
        lang = self._effective_language(repo_path)
        diff = "".join(self._render_diff(repo_path, f, c) for f, c in sorted(patch.items()))[:12000]
        sec_report = security_agent.run(patch, goal=goal, language=lang, diff=diff)
        if not sec_report.get("passed", False):
            GLOBAL_DASHBOARD_STATE.update_agent("SecurityAuditorAgent", "failed", "Audit failed")
            return [f"Security audit: {i}" for i in (sec_report.get("issues") or ["failed without detail"])], None
        GLOBAL_DASHBOARD_STATE.update_agent("SecurityAuditorAgent", "completed", "Audit passed")
        if not review:
            return [], None

        GLOBAL_DASHBOARD_STATE.update_agent("CodeReviewAgent", "running", f"Auditing patch quality & security ({reviewer_agent.model_name})")
        report = reviewer_agent.run(
            patch, self.state.hld, self.state.lld, contracts={contract.name: contract.model_dump()},
            goal=goal, language=lang, diff=diff,
        )
        GLOBAL_DASHBOARD_STATE.set_code_review_report(report)
        score = report.get("overall_score", 0)
        self._log(f"[+] Code Review Audit: Score {score}/100, Security Grade: {report.get('security_grade', 'unknown')}, Verdict: {report.get('verdict', 'NO VERDICT')}")
        for f in report.get("findings", []):
            self._log(f"    * [{f.get('severity', 'INFO')}] {f.get('file', 'general')}: {f.get('issue')}")
        if report.get("approved") is not True:
            GLOBAL_DASHBOARD_STATE.update_agent("CodeReviewAgent", "failed", f"Review rejected (Score: {score})")
            return [f"Code review: {c}" for c in (report.get("comments") or ["rejected without comments"])], report
        GLOBAL_DASHBOARD_STATE.update_agent("CodeReviewAgent", "completed", f"Patch approved (Score: {score}/100)")
        return [], report

    @staticmethod
    def _revision_original_context(repo_path: str, patch: Dict[str, str], max_files: int = 4) -> str:
        """Build revision context only from regular files safely contained in the repository.

        Patch filenames are untrusted until the sandbox validates them. Never read a path
        supplied by a rejected patch unless it is a safe, repository-relative regular file.
        """
        base_dir = Path(repo_path).resolve()
        originals = []
        for name in sorted(patch)[:max_files]:
            if not isinstance(name, str):
                continue
            rel_path = Path(name)
            if rel_path.is_absolute() or not name or ".." in rel_path.parts:
                continue

            candidate = base_dir / rel_path
            # Reject symlinks in every component, including a symlinked parent directory.
            current = base_dir
            unsafe_symlink = False
            for part in rel_path.parts:
                current = current / part
                if current.is_symlink():
                    unsafe_symlink = True
                    break
            if unsafe_symlink or not candidate.is_file():
                continue
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(base_dir)
            except (OSError, RuntimeError, ValueError):
                continue

            try:
                content = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if content:
                originals.append(
                    f"\\n--- ORIGINAL {name} (everything it exports must still exist unless the goal says otherwise):\\n"
                    f"{content[:6000]}\\n"
                )
        return "".join(originals)

    def _gate_and_revise(self, repo_path, contract, patch, security_agent, reviewer_agent, coder_agent, review=True):
        """Run all gates; on rejection give the coder ASCM_GEN_REVISIONS (default 1) chance(s) to fix the findings.

        Returns (patch_or_None, review_report, problems). A rejected patch is never passed on."""
        revisions = max(0, int(os.environ.get("ASCM_GEN_REVISIONS", "1")))
        report = None
        problems: List[str] = []
        for attempt in range(revisions + 1):
            problems, report = self._gate_once(repo_path, contract, patch, security_agent, reviewer_agent, review)
            if not problems:
                return patch, report, []
            self._log(f"[!] Patch for '{contract.name}' rejected ({len(problems)} problem(s)): {problems}")
            if attempt == revisions:
                break
            self._log(f"[+] Asking the coder to revise '{contract.name}' (revision {attempt + 1}/{revisions})...")
            originals = self._revision_original_context(repo_path, patch)
            fixed = coder_agent.fix(
                patch,
                "Your previous patch was rejected. Fix ALL of these problems and return the COMPLETE corrected files "
                "(keep the change minimal and scoped to the stated goal; start from the ORIGINAL file and change only what "
                "the goal requires, never rewrite it from scratch):\n- " + "\n- ".join(problems) + originals,
                contract.raw_content,
                language=self._effective_language(repo_path),
            )
            if not isinstance(fixed, dict) or not fixed:
                break
            patch = {**patch, **fixed}
        return None, report, problems

    def _record_verification(self, repo_path: str, verification) -> None:
        self.__dict__.setdefault("_last_verification", {})[repo_path] = verification

    def _verification_summary(self, repo_path: str) -> dict:
        v = self.__dict__.get("_last_verification", {}).get(repo_path)
        if v is None:
            return {}
        return {
            "tests_passed": v.tests_passed,
            "vet_passed": v.vet_passed,
            "no_tests_detected": v.total_tests == 0,
        }

    @staticmethod
    def _render_diff(repo_path: str, filename: str, new_content: str) -> str:
        old = OrchestratorEngine._read_text(Path(repo_path) / filename)
        diff = "".join(difflib.unified_diff(
            old.splitlines(keepends=True), new_content.splitlines(keepends=True),
            fromfile=f"a/{filename}" if old else "/dev/null", tofile=f"b/{filename}",
        ))
        return diff or f"(no textual change for {filename})\n"

    def _await_approval(self, auto_approve: bool, digest: str) -> bool:
        """
        Blocks until a human approves or rejects the exact change set (identified by `digest`).
        Terminal and web approvals both work. Fails closed on timeout or when nobody can answer.
        `--yes` skips milestone prompts but does not authorize writing and committing unless
        ASCM_ALLOW_UNATTENDED_COMMIT=1 is set explicitly.
        """
        import threading
        unattended_ok = os.environ.get("ASCM_ALLOW_UNATTENDED_COMMIT", "").lower() in ("1", "true", "yes")
        if auto_approve and unattended_ok:
            AUDIT_LOGGER.log_event("APPROVAL_UNATTENDED", agent="ORCHESTRATOR", action="APPROVE",
                                   details={"digest": digest, "basis": "ASCM_ALLOW_UNATTENDED_COMMIT"}, level="WARNING")
            self._log(f"[!] Unattended commit explicitly allowed (change digest {digest}).")
            return True
        if auto_approve:
            self._log("[!] --yes does not authorize writing and committing; human approval is still required.")

        interactive = sys.stdin.isatty()
        has_dashboard = getattr(self, "dashboard_server", None) is not None
        if not interactive and not has_dashboard:
            self._log("No terminal or dashboard is available to approve this change set; refusing (fail closed).")
            AUDIT_LOGGER.log_event("APPROVAL_UNAVAILABLE", agent="ORCHESTRATOR", action="REJECT",
                                   details={"digest": digest}, level="WARNING")
            return False

        timeout = float(os.environ.get("ASCM_APPROVAL_TIMEOUT", "3600"))
        if interactive:
            def _ask() -> None:
                try:
                    answer = input(f"\nType 'APPROVE' to approve change set {digest}, write it, verify, and commit locally: ").strip()
                except EOFError:
                    return
                GLOBAL_DASHBOARD_STATE.submit_approval(answer.upper() == "APPROVE")
            threading.Thread(target=_ask, daemon=True).start()
        else:
            self._log(f"Waiting for approval of change set {digest} in the dashboard...")

        if not GLOBAL_DASHBOARD_STATE.approval_event.wait(timeout):
            self._log(f"Approval timed out after {timeout:.0f}s; rejecting (fail closed).")
            AUDIT_LOGGER.log_event("APPROVAL_TIMEOUT", agent="ORCHESTRATOR", action="REJECT",
                                   details={"digest": digest}, level="WARNING")
            return False
        approved = GLOBAL_DASHBOARD_STATE.approval_decision is True
        AUDIT_LOGGER.log_event("APPROVAL_DECISION", agent="ORCHESTRATOR", action="APPROVE" if approved else "REJECT",
                               details={"digest": digest, "channel": "terminal" if interactive else "dashboard"})
        return approved

    def _verify_and_record(self, contract) -> "VerificationResult":
        verification = VerifierEngine.run_checks(contract.repo_path)
        if verification.tests_passed and verification.total_tests == 0 \
                and os.environ.get("ASCM_REQUIRE_TESTS", "1").lower() in ("1", "true", "yes"):
            # A green exit code with zero detected tests proves nothing; mandatory TDD means it counts as a failure.
            verification.tests_passed = False
            verification.test_output += "\n[ASCM] No tests were detected or executed. Add tests that exercise the change."
        self._record_verification(contract.repo_path, verification)
        GLOBAL_DASHBOARD_STATE.record_test_result(
            repo=contract.name, language=verification.language, passed=verification.passed,
            test_output=verification.test_output, vet_output=verification.vet_output,
            sandboxed=verification.sandboxed, framework=verification.framework,
            total_tests=verification.total_tests, passed_count=verification.passed_count,
            failed_count=verification.failed_count, test_cases=verification.test_cases,
        )
        AUDIT_LOGGER.log_verification(
            repo=contract.name, language=verification.language, passed=verification.passed,
            test_output=verification.test_output, vet_output=verification.vet_output,
            sandboxed=verification.sandboxed, framework=verification.framework,
            total_tests=verification.total_tests, passed_count=verification.passed_count,
            failed_count=verification.failed_count,
        )
        return verification

    def _run_verification_and_commit(self, pending_changes: List[Tuple], auto_approve: bool = False) -> None:
        self._log("Pending changes for writing:")
        changes_summary = []
        digest_src = hashlib.sha256()
        for contract, files in pending_changes:
            print(f"- Repository: {contract.name}")
            file_list = []
            for filename, content in sorted(files.items()):
                diff = self._render_diff(contract.repo_path, filename, content)
                digest_src.update(contract.repo_path.encode()); digest_src.update(filename.encode()); digest_src.update(content.encode())
                print(diff if len(diff) <= 6000 else diff[:6000] + f"\n... [diff truncated: {len(diff)} chars in total; full diff in dashboard]")
                file_list.append({"filename": filename, "preview": content[:300], "diff": diff[:20000]})
            changes_summary.append({"repo": contract.name, "repo_path": contract.repo_path, "files": file_list})
        digest = digest_src.hexdigest()[:16]

        GLOBAL_DASHBOARD_STATE.request_approval(changes_summary)
        if not self._await_approval(auto_approve, digest):
            self._log("Aborted: the change set was not approved. Nothing was written.")
            return

        coder_agent = GoCoderAgent()
        max_healing_attempts = 3
        committed_records = []
        failed_repos = []

        for contract, files in pending_changes:
            original_branch = None
            created_branch = None
            wrote = False
            try:
                GitService.ensure_clean_repo(contract.repo_path)
                original_branch = GitService.get_current_branch(contract.repo_path)
                planned = f"ascm/{_slugify(self.state.user_goal)}"
                existed = GitService.branch_exists(contract.repo_path, planned)
                branch = GitService.create_branch(contract.repo_path, self.state.user_goal)
                created_branch = None if existed else branch
                SandboxEngine.validate_and_write(contract.repo_path, contract.allowed_paths, files)
                wrote = True

                verification = self._verify_and_record(contract)
                if not verification.passed:
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

                        fixed_patch = coder_agent.fix(current_files, err_summary, contract.raw_content, language=self._effective_language(contract.repo_path))
                        if not fixed_patch:
                            break

                        try:
                            # Re-check the generated patch against the contract before any write.
                            # validate_and_write repeats this check immediately before filesystem writes.
                            SandboxEngine.validate(contract.repo_path, contract.allowed_paths, fixed_patch)
                            SandboxEngine.validate_and_write(contract.repo_path, contract.allowed_paths, fixed_patch)
                            files.update(fixed_patch)
                        except PathViolationError as err:
                            self._log(f"Self-healing patch failed sandbox: {err}")
                            AUDIT_LOGGER.log_security_event("PATH_VIOLATION", {"repo": contract.name, "error": str(err)}, severity="ERROR")
                            break

                        verification = self._verify_and_record(contract)
                        if verification.passed:
                            self._log(f"[+] Self-Healing succeeded on attempt {attempt}! Verification passed.")
                            GLOBAL_DASHBOARD_STATE.update_agent("GoCoderAgent", "completed", "Self-healing succeeded")
                            break

                if not verification.passed:
                    self._log(f"Verification failed for '{contract.name}' after {max_healing_attempts} self-healing attempts.")
                    print(verification.test_output or verification.vet_output)
                    self._preserve_failed_patch(contract, files, branch)
                    GitService.restore(contract.repo_path, original_branch, list(files), delete_branch=created_branch)
                    self._log(f"Rolled back '{contract.name}': nothing committed; the rejected patch was saved under .ascm_history/failed_patches/.")
                    failed_repos.append(contract.name)
                    continue

                GitService.commit(contract.repo_path, self.state.user_goal, list(files))
                self._log(f"[ SUCCESS ] Committed verified changes on branch '{branch}' for repo '{contract.name}'.")
                committed_records.append({"contract": contract, "branch": branch, "files": files})
            except (OSError, RuntimeError, PathViolationError, subprocess.CalledProcessError) as error:
                self._log(f"Error applying changes to '{contract.name}': {error}")
                AUDIT_LOGGER.log_event("PATCH_APPLY_ERROR", agent="ORCHESTRATOR", action="WRITE", details={"repo": contract.name, "error": str(error)}, level="ERROR")
                if wrote and original_branch:
                    GitService.restore(contract.repo_path, original_branch, list(files), delete_branch=created_branch)
                    self._log(f"Rolled back '{contract.name}' after the error.")
                failed_repos.append(contract.name)

        if failed_repos:
            done = [r["contract"].name for r in committed_records]
            self._log(
                f"[!] PARTIAL RESULT: committed {done or 'none'}; failed {failed_repos}. "
                "Cross-repo changes are only consistent when all repos land: do not merge the committed branches on their own."
            )
            AUDIT_LOGGER.log_event("PARTIAL_RESULT", agent="ORCHESTRATOR", action="COMMIT",
                                   details={"committed": done, "failed": failed_repos}, level="WARNING")

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
                    prd_summary=self.state.clarified_prd,
                    verification=self._verification_summary(c.repo_path),
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


    def _preserve_failed_patch(self, contract, files: Dict[str, str], branch: str) -> None:
        try:
            out = Path(contract.repo_path) / ".ascm_history" / "failed_patches"
            out.mkdir(parents=True, exist_ok=True)
            GitService.exclude_locally(contract.repo_path)
            body = "".join(self._render_diff(contract.repo_path, f, c) for f, c in sorted(files.items()))
            (out / f"{_slugify(branch)}.diff").write_text(body, encoding="utf-8")
        except OSError as err:
            self._log(f"Could not preserve the failed patch: {err}")

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



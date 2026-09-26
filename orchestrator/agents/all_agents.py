import json
from typing import Dict, Any, List, Optional
from orchestrator.agents.base import BaseAgent, BaseLLMProvider


class DiscoveryAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Systems Topology Engineer. Analyze the user's functional goal against repo capability contracts. "
            "Classify every repo as 'provider', 'consumer', or 'unaffected'. "
            "Output JSON with this exact schema: "
            '{"providers": ["repo_path"], "consumers": ["repo_path"], "unaffected": ["repo_path"], "analysis": "concise summary"}',
            provider=provider,
            tier="fast",
        )

    def run(self, contracts: Dict[str, Any], goal: str) -> Dict[str, Any]:
        prompt = f"User Goal: {goal}\nRepository Contracts:\n{json.dumps(contracts, indent=2)}"
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class ProductAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are an Elite Principal Product Manager, Systems Analyst, and Specialized Industry Domain Expert.\n"
            "Your mission is to rigorously evaluate user requirements against functional architecture and "
            "Non-Functional Requirements (NFRs: security, performance, error handling, contracts, custody).\n\n"
            "DOMAIN EXPERTISE & MANDATORY GRILLING RULES:\n"
            "1. Domain Detection:\n"
            "   - Automatically detect the industry vertical (e.g. 'Crypto/Web3 Payments', 'AI/ML Infrastructure', 'Fintech/Banking', 'E-Commerce', 'Developer Tools').\n"
            "2. Specialized Domain Probing (Vigorous Grilling):\n"
            "   - When in 'Crypto/Web3 Payments':\n"
            "     * Chains & Assets: Which blockchains (EVM e.g. Ethereum/Polygon/Arbitrum, Solana, Bitcoin) and tokens (USDT, USDC, ETH, BTC)?\n"
            "     * Settlement Logic & Conversion: Is it strictly Crypto-to-Crypto (direct on-chain transfer to merchant self-custody wallet) or Crypto-to-Fiat (auto-offramp/liquidation into INR/USD bank account via P2P or fiat off-ramp partners)?\n"
            "     * Transfer Mechanics & UX: How does the payment transfer physically happen? (Injected Web3 wallet connection like MetaMask/Phantom, dynamic one-time deposit address with QR code & blockchain mempool watcher daemon, or smart contract escrow)?\n"
            "     * Gas & Volatility Policy: Who covers network gas fees (customer vs merchant subsidy via ERC-4337)? What is the exchange rate lock window (e.g. 15-minute price freeze with slippage buffer)?\n"
            "     * Security & Finality: Confirmation block depth (e.g. 1 block vs 12 blocks vs instant optimistic), double-spend mitigation, replay attack protection.\n"
            "     * Compliance & Tax: Handling KYC/AML, FIU-IND (India) travel rule, 1% TDS on Virtual Digital Assets (VDA) where applicable.\n"
            "   - When in 'AI/ML Infrastructure': probe model cascading, fallback SLAs, streaming SSE, prompt caching, token budgets.\n"
            "   - When in other domains: probe respective core architectural trade-offs.\n\n"
            "3. Confidence Scoring & Grilling Decision Rules:\n"
            "   - If the user's input is high-level, brief, or missing these domain specifics (e.g. 'pay through crypto', 'build crypto gateway'):\n"
            "     * DO NOT ASSUME. Confidence score MUST NOT exceed 0.50 (50%).\n"
            "     * Set is_clear to false.\n"
            "     * Generate 3-5 sharp, domain-expert 'clarification_questions' providing clear architectural options and trade-offs.\n"
            "   - Only when confidence_score >= 0.90 (90%+):\n"
            "     * Set is_clear to true.\n"
            "     * Place low-priority non-blocking edge cases (<10%) in 'checkpoint_clarification_items'.\n"
            "     * Set 'clarification_questions' to [].\n\n"
            "4. Detailed Transfer Flow in Understanding:\n"
            "   - 'understanding' must always document the complete end-to-end user and technical flow, including transfer mechanics, custody model, and settlement sequence.\n\n"
            "Output JSON with this exact schema:\n"
            "{\n"
            '  "detected_domain": "string (e.g. Crypto/Web3 Payments, AI/ML SaaS)",\n'
            '  "confidence_score": float,\n'
            '  "functional_completeness": float,\n'
            '  "nfr_completeness": float,\n'
            '  "is_clear": bool,\n'
            '  "understanding": "comprehensive breakdown of features, transfer mechanics, custody, and NFRs",\n'
            '  "clarification_questions": ["question 1 with options", "question 2 with options"],\n'
            '  "checkpoint_clarification_items": [\n'
            '     {"checkpoint": "module_or_task", "question": "specific deferred question", "default_assumption": "standard assumption"}\n'
            '  ]\n'
            "}",
            provider=provider,
            tier="fast",
        )

    def run(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(user_input)
        lang = DomainAdapter.detect_language(user_input, domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("product", domain, lang)
        history_str = json.dumps(conversation_history or [], indent=2)
        prompt = (
            f"{role_prompt}\n"
            f"Target Domain: {domain.display_name}\n"
            f"User Requirement / PRD:\n{user_input}\n\n"
            f"Clarification History:\n{history_str}\n\n"
            f"Analyze with deep {domain.display_name} domain expertise. Compute confidence_score (0.00 to 1.00). "
            f"If the request lacks domain-critical specifics (such as {', '.join(domain.core_primitives[:4])}), "
            "set confidence < 0.60, is_clear=False, and generate prioritized domain-expert clarification_questions matching the domain's critical dimensions. "
            "If confidence >= 0.90, set is_clear=True, place non-blocking edge cases (<10%) in checkpoint_clarification_items, "
            "and set clarification_questions=[]."
        )
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)
        # Normalize fields for backward compatibility
        confidence = float(data.get("confidence_score", 0.0))
        if confidence >= 0.90:
            data["is_clear"] = True
            data["clarification_questions"] = []
        if not data.get("detected_domain"):
            data["detected_domain"] = domain.display_name
        return data


class DesignAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Lead Software Architect. Generate High-Level Design (HLD) and Low-Level Design (LLD) "
            "documents for the feature request given the repository context.\n"
            "Output JSON with this exact schema:\n"
            '{\n  "hld": "markdown string for HLD",\n  "lld": "markdown string for LLD"\n}',
            provider=provider,
            tier="primary",
        )

    def run(self, clarified_prd: str, contracts: Dict[str, Any]) -> Dict[str, str]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(clarified_prd)
        lang = DomainAdapter.detect_language(clarified_prd, domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("architect", domain, lang)
        prompt = (
            f"{role_prompt}\n"
            f"Clarified Requirement / PRD:\n{clarified_prd}\n\n"
            f"Repository Contracts:\n{json.dumps(contracts, indent=2)}\n\n"
            f"Produce comprehensive HLD (architecture, modules, component flow) and LLD (functions, data structures, error handling) for {domain.display_name} in {lang.upper()}."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class ArchitectAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Principal Systems Architect. Break down the user requirement and design specs into discrete execution sub-tasks. "
            "Output JSON with this exact schema:\n"
            '{\n  "tasks": [\n'
            '    {\n      "id": "TASK-1",\n      "title": "short title",\n      "description": "detailed instructions",\n      "assigned_agent": "coder|database|security",\n      "target_file": "relative/file/path"\n    }\n  ]\n}',
            provider=provider,
            tier="primary",
        )

    def run(self, clarified_prd: str, hld: str, lld: str, contracts: Dict[str, Any], kg_context: Optional[str] = None) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(clarified_prd)
        lang = DomainAdapter.detect_language(clarified_prd, domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("architect", domain, lang)
        ext = ".py" if lang == "python" else ".go" if lang == "go" else ".ts" if lang == "typescript" else ".rs" if lang == "rust" else ".go"
        kg_block = f"\n\nCross-Repository Knowledge Graph:\n{kg_context}" if kg_context else ""
        prompt = (
            f"{role_prompt}\n"
            f"PRD:\n{clarified_prd}\n\n"
            f"HLD:\n{hld}\n\n"
            f"LLD:\n{lld}\n\n"
            f"Repository Contracts:\n{json.dumps(contracts, indent=2)}"
            f"{kg_block}\n\n"
            f"Decompose this work into granular execution tasks assigned to specialized agents ('coder', 'database', 'security'). "
            f"Target file extensions should use '{ext}' matching target language {lang.upper()}."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class PlannerAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Master Orchestrator Planner. Analyze a specific sub-task and decide which specialized agent "
            "should execute it and construct the detailed invocation payload.\n"
            "Output JSON:\n"
            '{\n  "agent_type": "coder|database|security",\n  "reasoning": "why this agent was chosen",\n  "instructions": "specific task prompt for agent"\n}',
            provider=provider,
            tier="fast",
        )

    def run(self, task: Dict[str, Any], context: str) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(context)
        lang = DomainAdapter.detect_language(context, domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("orchestrator", domain, lang)
        prompt = (
            f"{role_prompt}\n"
            f"Sub-task:\n{json.dumps(task, indent=2)}\n\n"
            f"Architecture Context:\n{context}\n"
            f"Select agent and formulate instructions in {lang.upper()}."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class DatabaseAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Database Engineer. Generate schema, SQL migration, or database access code for the task. "
            "Output JSON mapping repository-relative allowed file paths to complete file content strings:\n"
            '{"internal/db/schema.go": "<complete code>"}',
            provider=provider,
            tier="primary",
        )

    def run(self, instructions: str, contract: str, target_file: str) -> Dict[str, str]:
        prompt = (
            f"Database Task Instructions:\n{instructions}\n\n"
            f"Repository Contract:\n{contract}\n\n"
            f"Target File: {target_file}\n\n"
            "Generate JSON mapping file path to code content."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class PolyglotCoderAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Principal Software Engineer & Test-Driven Development (TDD) Specialist. "
            "When generating or modifying source code, you MUST ALWAYS generate comprehensive unit tests alongside the implementation.\n\n"
            "Language-Specific Testing Guidelines:\n"
            "- Python: Use 'unittest' (with TestCase, setUp, mock.patch, MagicMock) or 'pytest' parameterized tests.\n"
            "- Go: Use native 'testing' package with idiomatic table-driven test cases (tests := []struct{...}) and "
            "  popular assertion libraries like 'github.com/stretchr/testify/assert' or standard t.Errorf.\n"
            "- Node.js/TypeScript: Use 'jest' (describe/it/expect) or standard 'node:test' + 'node:assert'.\n"
            "- Rust: Use standard #[cfg(test)] mod tests with assert! / assert_eq!.\n\n"
            "Testing Scope:\n"
            "- Positive / Happy Path execution.\n"
            "- Negative Path: invalid arguments, error propagation, null/nil guards.\n"
            "- Boundary & Edge Cases: zero values, empty collections, concurrency, maximum thresholds.\n\n"
            "Output JSON mapping repository-relative allowed file paths to complete source strings:\n"
            '{"path/to/source": "<complete source code>", "path/to/source_test": "<complete unit test suite>"}',
            provider=provider,
            tier="primary",
        )

    def run(self, existing_code: str, selected_arch: str, source_filename: str, test_filename: str, contract: str) -> Dict[str, str]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(selected_arch)
        lang = DomainAdapter.detect_language(selected_arch, domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("coder", domain, lang)
        prompt = (
            f"{role_prompt}\n"
            f"Existing Code:\n{existing_code}\n\n"
            f"Repository Contract:\n{contract}\n\n"
            f"Selected Architecture / Instructions:\n{selected_arch}\n\n"
            f"Target Source File: '{source_filename}'\n"
            f"Target Unit Test File: '{test_filename}'\n\n"
            f"Generate a JSON object mapping repository-relative allowlisted paths to complete code strings in {lang.upper()}. "
            f"You MUST generate production-grade code for '{source_filename}' AND write complete, idiomatic unit test cases "
            f"in '{test_filename}' pulling famous test libraries (e.g., testify/assert for Go, unittest/pytest for Python, jest for Node)."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)

    def fix(self, current_files: Dict[str, str], error_log: str, contract: str) -> Dict[str, str]:
        prompt = (
            f"The following code failed test/verification checks:\n"
            f"Current Files:\n{json.dumps(current_files, indent=2)}\n\n"
            f"Verification Failure Log:\n{error_log}\n\n"
            f"Repository Contract:\n{contract}\n\n"
            "Diagnose the root cause of the error. Fix the syntax, logic bugs, or failing unit test assertions. "
            "Ensure unit tests remain thorough and properly assert all cases. "
            "Output JSON mapping repository-relative allowed file paths to complete corrected source strings:\n"
            '{"path/to/file": "<complete corrected code>"}'
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


# Aliases for polyglot clarity and backward compatibility
GoCoderAgent = PolyglotCoderAgent
CoderAgent = PolyglotCoderAgent



class SecurityAuditorAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are an Application Security Auditor. Inspect code for overflow, DoS, zero division, PII leaks, or resource leaks. "
            'Output JSON: {"passed": bool, "issues": [str]}.',
            provider=provider,
            tier="fast",
        )

    def run(self, files: Dict[str, str]) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        code_sample = "\n".join(files.values())[:3000]
        domain = DomainAdapter.detect_domain(code_sample)
        lang = DomainAdapter.detect_language(code_sample, domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("security", domain, lang)
        prompt = (
            f"{role_prompt}\n"
            f"Inspect these generated {lang.upper()} files for {domain.display_name} security vulnerabilities, "
            f"privilege/data leaks, memory issues, injection, and regulatory compliance:\n{json.dumps(files, indent=2)}"
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class BusinessStrategyAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            """You are an Elite Chief Commercial Officer (CCO) & Specialized Industry Business Strategist.
Analyze the technical product requirements and system capabilities to formulate an aggressive, data-backed Go-To-Market (GTM) strategy.

DOMAIN EXPERTISE & GTM ANALYSIS:
1. Domain Detection:
   - Automatically detect the product domain (e.g. Crypto/Web3 Payments, AI DevTools, LegalTech SaaS, CAD/CAM).
2. Vertical Market Economics:
   - Model pricing, customer pain points, competitor battlecards, and ROI drivers tailored to the industry vertical.

Output JSON with this exact schema:
{
  "detected_domain": "string",
  "market_strategy": "string",
  "user_cohorts": [
    {"cohort_name": "...", "pain_point": "...", "why_adopt": "...", "willingness_to_pay": "..."}
  ],
  "competitor_analysis": [
    {"competitor": "...", "limitations": "...", "ascm_advantage": "...", "verdict": "..."}
  ],
  "value_proposition": "string",
  "gtm_channels": ["channel 1", "channel 2"],
  "executive_summary": "string"
}""",
            provider=provider,
            tier="primary",
        )

    def run(self, user_goal: str, clarified_prd: str, contracts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(f"{user_goal} {clarified_prd}")
        role_prompt = DomainAdapter.get_agent_domain_prompt("business", domain)
        prompt = (
            f"{role_prompt}\n"
            f"Feature Goal:\n{user_goal}\n\n"
            f"Clarified PRD:\n{clarified_prd}\n\n"
            f"Repository Context:\n{json.dumps(contracts or {}, indent=2)}\n\n"
            f"Formulate comprehensive Market Strategy, User Cohorts, Competitor Analysis for {domain.display_name}, Value Proposition, and GTM channels."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


BusinessAgent = BusinessStrategyAgent


class RevenueROIAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Chief Financial Officer (CFO) & Head of Tech Monetization.\n"
            "Model the Return on Investment (ROI), revenue metrics, unit economics, and user onboarding conversion metrics for this system.\n\n"
            "Deliverables:\n"
            "1. ROI Analysis: Quantify engineering hours saved, cost of manual cross-repo coordination vs automated agent execution, estimated dollar savings per sprint.\n"
            "2. Revenue Metrics & Pricing Architecture: Recommend pricing tiers (Community BYOK, Pro / Founder, Team / Scale, Enterprise SLA).\n"
            "3. User Onboarding & Funnel Metrics: Activation KPI (e.g. time-to-first-verified-cross-repo-PR), expected stage conversion rates, and retention tactics.\n"
            "4. Unit Economics: Model token cost per sprint vs subscription pricing margin.\n\n"
            "Output JSON with this exact schema:\n"
            "{\n"
            '  "roi_summary": "string",\n'
            '  "hours_saved_per_sprint": float,\n'
            '  "cost_savings_estimate_usd": float,\n'
            '  "pricing_tiers": [\n'
            '    {"tier": "...", "price": "...", "target_audience": "...", "features": ["..."]}\n'
            "  ],\n"
            '  "onboarding_funnel_metrics": [\n'
            '    {"stage": "...", "metric": "...", "target_rate": "...", "improvement_tactic": "..."}\n'
            "  ],\n"
            '  "activation_kpi": "string",\n'
            '  "gross_margin_estimate": "string",\n'
            '  "executive_summary": "string"\n'
            "}",
            provider=provider,
            tier="primary",
        )

    def run(self, user_goal: str, clarified_prd: str = "", business_strategy: Optional[Dict[str, Any]] = None, contracts: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        prompt = (
            f"Feature Goal:\n{user_goal}\n\n"
            f"Clarified PRD:\n{clarified_prd}\n\n"
            f"Business Strategy Context:\n{json.dumps(business_strategy or {}, indent=2)}\n\n"
            "Calculate ROI, pricing tiers, onboarding metrics, activation KPI, and unit economics."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


RevenueAgent = RevenueROIAgent


class ArchitectureReviewAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are an Independent Principal Systems Architect & Senior Architecture Critic.\n"
            "Rigorously review the High-Level Design (HLD) and Low-Level Design (LLD) against strict "
            "Non-Functional Requirements (NFRs: Scalability, Security, Latency, Reliability, Maintainability). "
            "Act as an unbiased, adversarial critic seeking out hidden architectural flaws, single points of failure (SPOF), "
            "unhandled concurrency races, tight coupling, and contract mismatches.\n\n"
            "Output JSON with this exact schema:\n"
            "{\n"
            '  "overall_score": int,\n'
            '  "verdict": "APPROVE|APPROVE_WITH_REMARKS|REWORK_REQUIRED",\n'
            '  "nfr_scorecard": {\n'
            '    "scalability": {"score": int, "notes": "..."},\n'
            '    "security": {"score": int, "notes": "..."},\n'
            '    "latency": {"score": int, "notes": "..."},\n'
            '    "reliability": {"score": int, "notes": "..."},\n'
            '    "maintainability": {"score": int, "notes": "..."}\n'
            "  },\n"
            '  "architectural_gaps": ["gap 1", "gap 2"],\n'
            '  "spof_risks": ["spof 1"],\n'
            '  "recommendations": ["rec 1", "rec 2"],\n'
            '  "executive_summary": "string"\n'
            "}",
            provider=provider,
            tier="primary",
        )

    def run(self, hld: str = "", lld: str = "", contracts: Optional[Dict[str, Any]] = None, user_goal: str = "", **kwargs) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        domain = DomainAdapter.detect_domain(f"{user_goal} {hld}")
        lang = DomainAdapter.detect_language(f"{user_goal} {hld}", domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("thinking", domain, lang)
        hld_val = hld or kwargs.get("hld_spec", "")
        lld_val = lld or kwargs.get("lld_tasks", "")
        if isinstance(lld_val, list):
            lld_val = json.dumps(lld_val, indent=2)
        prompt = (
            f"{role_prompt}\n"
            f"User Goal: {user_goal}\n\n"
            f"Repository Contracts:\n{json.dumps(contracts or {}, indent=2)}\n\n"
            f"High-Level Design (HLD):\n{hld_val}\n\n"
            f"Low-Level Design (LLD):\n{lld_val}\n\n"
            f"Conduct an adversarial architecture critique for {domain.display_name}. Identify domain-specific gaps, SPOF risks, validate NFRs (0-100), "
            "and decide verdict (APPROVE, APPROVE_WITH_REMARKS, REWORK_REQUIRED)."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


ArchitectureCriticAgent = ArchitectureReviewAgent


class CodeReviewAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are an Adversarial Senior Principal Code Reviewer & Security Specialist.\n"
            "Conduct an exhaustive, critical code review of all generated files and unit tests across provider and consumer repositories.\n"
            "Audit for logic bugs, concurrency flaws, security vulnerabilities (OWASP, injection, path leaks), performance bottlenecks, "
            "and unit test suite rigor.\n\n"
            "Output JSON with this exact schema:\n"
            "{\n"
            '  "overall_score": int,\n'
            '  "approved": bool,\n'
            '  "verdict": "APPROVED|APPROVED_WITH_COMMENTS|REJECTED",\n'
            '  "security_grade": "A+|A|B|C|F",\n'
            '  "test_coverage_assessment": "string",\n'
            '  "findings": [\n'
            '    {"file": "...", "severity": "CRITICAL|MAJOR|MINOR", "issue": "...", "fix_recommendation": "..."}\n'
            "  ],\n"
            '  "comments": ["comment 1", "comment 2"],\n'
            '  "executive_summary": "string"\n'
            "}",
            provider=provider,
            tier="primary",
        )

    def run(self, files: Optional[Dict[str, str]] = None, hld: str = "", lld: str = "", contracts: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        from orchestrator.domain import DomainAdapter
        file_map = files or {}
        if not file_map and "generated_diff" in kwargs:
            target_files = kwargs.get("target_files", ["solution_diff.patch"])
            if isinstance(target_files, list):
                for f in target_files:
                    file_map[f] = kwargs.get("generated_diff", "")
            test_content = kwargs.get("test_content", "")
            if test_content:
                file_map["tests/test_solution.py"] = test_content
        hld_val = hld or kwargs.get("hld_spec", "")
        code_sample = "\n".join(file_map.values())[:3000]
        domain = DomainAdapter.detect_domain(f"{hld_val} {code_sample}")
        lang = DomainAdapter.detect_language(f"{hld_val} {code_sample}", domain)
        role_prompt = DomainAdapter.get_agent_domain_prompt("code_review", domain, lang)
        prompt = (
            f"{role_prompt}\n"
            f"HLD Context:\n{hld_val[:1500]}\n\n"
            f"LLD Context:\n{lld[:1500]}\n\n"
            f"Generated Files & Unit Tests:\n{json.dumps(file_map, indent=2)}\n\n"
            f"Perform an adversarial, unbiased code review for {domain.display_name} in {lang.upper()}. Check syntax, error handling, security, performance, and unit test assertions. "
            "Compute overall_score (0-100), security_grade, test_coverage_assessment, findings, and decide if approved."
        )
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)
        # Ensure backward compatibility
        if "approved" not in data:
            data["approved"] = data.get("overall_score", 0) >= 80 and data.get("verdict") != "REJECTED"
        if "comments" not in data:
            data["comments"] = [f"{f.get('severity')}: {f.get('issue')}" for f in data.get("findings", [])]
        return data


CodeCriticAgent = CodeReviewAgent



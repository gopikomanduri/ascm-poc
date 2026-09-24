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
            "You are a Principal Product Manager & Systems Analyst. "
            "Rigorously evaluate user requirements against both Functional Features and "
            "Non-Functional Requirements (NFRs: security, performance, error handling, backward compatibility, contracts). "
            "Calculate a statistical confidence score between 0.00 and 1.00 (0% to 100%) indicating how completely "
            "the system requirements are defined to safely build a technical architecture.\n\n"
            "Decision Rules:\n"
            "1. If confidence_score >= 0.90 (90%+ complete):\n"
            "   - Set is_clear to true.\n"
            "   - Core functional & critical NFR requirements are sufficiently defined to begin architecture.\n"
            "   - Any minor low-priority ambiguities (< 10%) should be placed into 'checkpoint_clarification_items' "
            "     to be resolved when execution approaches those specific modules.\n"
            "   - 'clarification_questions' must be an empty list [].\n"
            "2. If confidence_score < 0.90 (< 90% complete):\n"
            "   - Set is_clear to false.\n"
            "   - Generate 2-4 high-impact 'clarification_questions' probing missing feature specifics or NFRs.\n"
            "   - Keep 'checkpoint_clarification_items' empty.\n\n"
            "Output JSON with this exact schema:\n"
            "{\n"
            '  "confidence_score": float,\n'
            '  "functional_completeness": float,\n'
            '  "nfr_completeness": float,\n'
            '  "is_clear": bool,\n'
            '  "understanding": "comprehensive breakdown of features, NFRs, and architecture readiness",\n'
            '  "clarification_questions": ["question 1", "question 2"],\n'
            '  "checkpoint_clarification_items": [\n'
            '     {"checkpoint": "module_or_task", "question": "specific deferred question", "default_assumption": "standard assumption"}\n'
            '  ]\n'
            "}",
            provider=provider,
            tier="fast",
        )

    def run(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        history_str = json.dumps(conversation_history or [], indent=2)
        prompt = (
            f"User Requirement / PRD:\n{user_input}\n\n"
            f"Clarification History:\n{history_str}\n\n"
            "Evaluate functional and non-functional requirements. Compute confidence_score (0.00 to 1.00). "
            "If confidence >= 0.90, set is_clear=True, place non-blocking edge cases (<10%) in checkpoint_clarification_items, "
            "and set clarification_questions=[]. Otherwise set is_clear=False and provide prioritized clarification_questions."
        )
        raw = self.call(prompt, json_mode=True)
        data = json.loads(raw)
        # Normalize fields for backward compatibility
        confidence = float(data.get("confidence_score", 0.0))
        if confidence >= 0.90:
            data["is_clear"] = True
            data["clarification_questions"] = []
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
        prompt = (
            f"Clarified Requirement / PRD:\n{clarified_prd}\n\n"
            f"Repository Contracts:\n{json.dumps(contracts, indent=2)}\n\n"
            "Produce comprehensive HLD (architecture, modules, component flow) and LLD (functions, data structures, error handling)."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class ArchitectAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Principal Systems Architect. Break down the user requirement and design specs into discrete execution sub-tasks. "
            "Output JSON with this exact schema:\n"
            '{\n  "tasks": [\n'
            '    {\n      "id": "TASK-1",\n      "title": "short title",\n      "description": "detailed instructions",\n      "assigned_agent": "coder|database|security",\n      "target_file": "relative/file/path.go"\n    }\n  ]\n}',
            provider=provider,
            tier="primary",
        )

    def run(self, clarified_prd: str, hld: str, lld: str, contracts: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            f"PRD:\n{clarified_prd}\n\n"
            f"HLD:\n{hld}\n\n"
            f"LLD:\n{lld}\n\n"
            f"Repository Contracts:\n{json.dumps(contracts, indent=2)}\n\n"
            "Decompose this work into granular execution tasks assigned to specialized agents ('coder', 'database', 'security')."
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
        prompt = f"Sub-task:\n{json.dumps(task, indent=2)}\n\nArchitecture Context:\n{context}\nSelect agent and formulate instructions."
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


class GoCoderAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Principal Software Engineer & Test-Driven Development (TDD) Specialist. "
            "When generating or modifying source code, you MUST ALWAYS generate comprehensive unit tests alongside the implementation.\n\n"
            "Language-Specific Testing Guidelines:\n"
            "- Go: Use native 'testing' package with idiomatic table-driven test cases (tests := []struct{...}) and "
            "  popular assertion libraries like 'github.com/stretchr/testify/assert' or standard t.Errorf.\n"
            "- Python: Use 'unittest' (with TestCase, setUp, mock.patch, MagicMock) or 'pytest' parameterized tests.\n"
            "- Node.js/TypeScript: Use 'jest' (describe/it/expect) or standard 'node:test' + 'node:assert'.\n\n"
            "Testing Scope:\n"
            "- Positive / Happy Path execution.\n"
            "- Negative Path: invalid arguments, error propagation, null/nil guards.\n"
            "- Boundary & Edge Cases: zero values, empty collections, concurrency, maximum thresholds.\n\n"
            "Output JSON mapping repository-relative allowed file paths to complete source strings:\n"
            '{"path/to/source.go": "<complete source code>", "path/to/source_test.go": "<complete unit test suite>"}',
            provider=provider,
            tier="primary",
        )

    def run(self, existing_code: str, selected_arch: str, source_filename: str, test_filename: str, contract: str) -> Dict[str, str]:
        prompt = (
            f"Existing Code:\n{existing_code}\n\n"
            f"Repository Contract:\n{contract}\n\n"
            f"Selected Architecture / Instructions:\n{selected_arch}\n\n"
            f"Target Source File: '{source_filename}'\n"
            f"Target Unit Test File: '{test_filename}'\n\n"
            "Generate a JSON object mapping repository-relative allowlisted paths to complete code strings. "
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
            '{"path/to/file.go": "<complete corrected code>"}'
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


# Alias for polyglot clarity
CoderAgent = GoCoderAgent



class SecurityAuditorAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are an Application Security Auditor for Go. Inspect code for overflow, DoS, zero division, or resource leaks. "
            'Output JSON: {"passed": bool, "issues": [str]}.',
            provider=provider,
            tier="fast",
        )

    def run(self, files: Dict[str, str]) -> Dict[str, Any]:
        prompt = f"Inspect these generated Go files for security vulnerabilities:\n{json.dumps(files, indent=2)}"
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)


class BusinessStrategyAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Chief Commercial Officer (CCO) & Tech Business Strategist.\n"
            "Analyze the technical product requirements and system capabilities to formulate an aggressive, data-backed Go-To-Market (GTM) strategy.\n\n"
            "Deliverables:\n"
            "1. Market Strategy: How to position and market this capability.\n"
            "2. User Cohorts: Identify distinct target user personas (e.g. Solo Founders, Growth Stage Lead Engineers, Enterprise Platform Teams), pain points, and why they adopt.\n"
            "3. Competitor Analysis: In-depth competitive comparison against existing tools (GitHub Copilot, Cursor, Replit Agent, Devin), highlighting ASCM's competitive moat (dual-sided cross-repo synchronization, contracts allowlists, zero-drift verification).\n"
            "4. Value Proposition: Quantitative, compelling value prop statements.\n"
            "5. GTM Channels: Actionable acquisition channels.\n\n"
            "Output JSON with this exact schema:\n"
            "{\n"
            '  "market_strategy": "string",\n'
            '  "user_cohorts": [\n'
            '    {"cohort_name": "...", "pain_point": "...", "why_adopt": "...", "willingness_to_pay": "..."}\n'
            "  ],\n"
            '  "competitor_analysis": [\n'
            '    {"competitor": "...", "limitations": "...", "ascm_advantage": "...", "verdict": "..."}\n'
            "  ],\n"
            '  "value_proposition": "string",\n'
            '  "gtm_channels": ["channel 1", "channel 2"],\n'
            '  "executive_summary": "string"\n'
            "}",
            provider=provider,
            tier="primary",
        )

    def run(self, user_goal: str, clarified_prd: str, contracts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt = (
            f"Feature Goal:\n{user_goal}\n\n"
            f"Clarified PRD:\n{clarified_prd}\n\n"
            f"Repository Context:\n{json.dumps(contracts or {}, indent=2)}\n\n"
            "Formulate comprehensive Market Strategy, User Cohorts, Competitor Analysis, Value Proposition, and GTM channels."
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

    def run(self, user_goal: str, clarified_prd: str, business_strategy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    def run(self, hld: str, lld: str, contracts: Optional[Dict[str, Any]] = None, user_goal: str = "") -> Dict[str, Any]:
        prompt = (
            f"User Goal: {user_goal}\n\n"
            f"Repository Contracts:\n{json.dumps(contracts or {}, indent=2)}\n\n"
            f"High-Level Design (HLD):\n{hld}\n\n"
            f"Low-Level Design (LLD):\n{lld}\n\n"
            "Conduct an adversarial architecture critique. Identify gaps, SPOF risks, validate NFRs (0-100), "
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

    def run(self, files: Dict[str, str], hld: str = "", lld: str = "", contracts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt = (
            f"HLD Context:\n{hld[:1500]}\n\n"
            f"LLD Context:\n{lld[:1500]}\n\n"
            f"Generated Files & Unit Tests:\n{json.dumps(files, indent=2)}\n\n"
            "Perform an adversarial, unbiased code review. Check syntax, error handling, security, performance, and unit test assertions. "
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



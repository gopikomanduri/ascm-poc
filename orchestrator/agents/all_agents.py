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


class CodeReviewAgent(BaseAgent):
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        super().__init__(
            "You are a Senior Code Reviewer. Inspect generated code patches against design specs, Go best practices, "
            "and edge case handling.\n"
            'Output JSON:\n{\n  "approved": bool,\n  "comments": ["comment 1", "comment 2"]\n}',
            provider=provider,
            tier="fast",
        )

    def run(self, files: Dict[str, str], hld: str, lld: str) -> Dict[str, Any]:
        prompt = (
            f"HLD:\n{hld}\n\n"
            f"LLD:\n{lld}\n\n"
            f"Generated Files:\n{json.dumps(files, indent=2)}\n\n"
            "Review the patch for correctness, style, edge cases, and adherence to design. Set approved to true if acceptable."
        )
        raw = self.call(prompt, json_mode=True)
        return json.loads(raw)



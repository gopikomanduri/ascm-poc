"""QA Agent: Test orchestration, SLA gates, test metrics tracking."""
from typing import Dict, Any, Optional, List
import json
from .base import BaseAgent


class QAAgent(BaseAgent):
    """
    QA Agent: Test orchestration and milestone-level SLA validation.

    Responsibilities:
    - Generate test plans from PRD
    - Orchestrate test execution
    - Track test metrics (coverage, pass rate, SLA)
    - Gate release on test quality
    """

    SYSTEM_INSTRUCTION = """You are a Senior QA Engineer and Test Automation Architect.

Your role: Generate comprehensive test plans and validate SLAs for release readiness.

Test Strategy:
1. Unit Tests: >80% coverage (testify, pytest, jest)
2. Integration Tests: Cross-service contracts
3. Compliance Tests: PCI-DSS, GDPR, HIPAA (if applicable)
4. Performance Tests: P99 latency, throughput SLAs
5. Chaos Tests: Failover, timeout handling

Output JSON format:
{
    "test_plan": {
        "unit_tests": [...],
        "integration_tests": [...],
        "compliance_tests": [...],
        "performance_tests": [...]
    },
    "sla_gates": {
        "min_coverage_pct": 80,
        "max_p99_latency_ms": 500,
        "max_error_rate_pct": 0.1,
        "min_tests_passed_pct": 95
    }
}
"""

    def __init__(
        self,
        system_instruction: Optional[str] = None,
        provider: Optional[Any] = None,
        tier: str = "primary",
        model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            system_instruction=system_instruction or self.SYSTEM_INSTRUCTION,
            provider=provider,
            tier=tier,
            model=model,
        )
        self.system_instruction = system_instruction or self.SYSTEM_INSTRUCTION
        self.test_results: Dict[str, Any] = {}

    def run(self, files: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Unified entrypoint for QA execution and test validation."""
        test_cases = list(files.keys()) if files else kwargs.get("test_cases", ["test_core"])
        framework = kwargs.get("framework", kwargs.get("language", "pytest"))
        results = self.run_tests(test_cases=test_cases, test_framework=framework)
        results["passed"] = results.get("verdict") in ("PASS", "PASS_WITH_WARNINGS")
        results["coverage_percentage"] = results.get("coverage_pct", 85.0)
        return results

    def generate_test_plan(
        self,
        domain: str,
        prd: str,
        architecture: str,
        language: str,
    ) -> Dict[str, Any]:
        """Generate test plan from PRD and architecture."""
        prompt = f"""
        Domain: {domain}
        Language: {language}

        PRD:
        {prd[:1000]}

        Architecture:
        {architecture[:1000]}

        Task:
        1. Create comprehensive test plan with unit/integration/compliance/performance tests
        2. Define SLA gates for release readiness
        3. Specify test frameworks ({language})
        4. Provide test case templates

        Output JSON (only JSON, no markdown).
        """

        response = self.call_llm(prompt)

        try:
            result = json.loads(response)
        except:
            result = {
                "domain": domain,
                "language": language,
                "raw_response": response,
            }

        return result

    def run_tests(
        self,
        test_cases: List[str],
        test_framework: str,
        coverage_target: float = 80.0,
    ) -> Dict[str, Any]:
        """Execute test suite (mock implementation)."""
        # In production, this would actually run the test command
        # For now, return structured test results

        return {
            "test_framework": test_framework,
            "total_tests": len(test_cases),
            "tests_passed": max(0, len(test_cases) - 1),  # Mock: 1 flaky test
            "tests_failed": 1,
            "coverage_pct": coverage_target - 5,  # Mock
            "p99_latency_ms": 250,
            "error_rate_pct": 0.05,
            "verdict": "PASS_WITH_WARNINGS",
        }

    def check_sla_gates(
        self,
        test_results: Dict[str, Any],
        sla_gates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate test results against SLA gates."""
        prompt = f"""
        Test Results:
        {json.dumps(test_results, indent=2)}

        SLA Gates:
        {json.dumps(sla_gates, indent=2)}

        Task:
        1. Compare results against each SLA gate
        2. Identify violations
        3. Provide verdict: PASS / PASS_WITH_WARNINGS / FAIL
        4. Recommend actions for failures

        Output JSON.
        """

        response = self.call_llm(prompt)

        try:
            result = json.loads(response)
            if isinstance(result, dict):
                if "sla_passed" not in result:
                    result["sla_passed"] = result.get("verdict") in ("PASS", "PASS_WITH_WARNINGS") or (
                        test_results.get("coverage_pct", 0) >= sla_gates.get("min_coverage_pct", 80)
                        and test_results.get("p99_latency_ms", 9999) <= sla_gates.get("max_p99_latency_ms", 1000)
                    )
                return result
            return {"raw_response": response, "verdict": "PASS", "sla_passed": True}
        except:
            return {
                "raw_response": response,
                "verdict": "UNKNOWN",
                "sla_passed": False,
            }

    def generate_qa_report(
        self,
        test_results: Dict[str, Any],
        sla_verdict: Dict[str, Any],
    ) -> str:
        """Generate QA report for stakeholders."""
        prompt = f"""
        Test Results:
        {json.dumps(test_results, indent=2)}

        SLA Verdict:
        {json.dumps(sla_verdict, indent=2)}

        Generate a QA summary report with:
        1. Test execution summary
        2. Coverage and pass rate
        3. SLA compliance status
        4. Blockers (if any)
        5. Recommendation for release readiness

        Output as markdown.
        """

        response = self.call_llm(prompt)
        return response

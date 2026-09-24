import unittest
from orchestrator.engine.verifier import VerifierEngine, VerificationResult
from orchestrator.dashboard import DashboardState
from orchestrator.agents.all_agents import GoCoderAgent, CoderAgent


class UnitTestingAndDashboardTests(unittest.TestCase):
    def test_parse_test_suite_go(self):
        sample_go_output = """=== RUN   TestCalculateTax
--- PASS: TestCalculateTax (0.02s)
=== RUN   TestCalculateTaxInvalidInput
--- FAIL: TestCalculateTaxInvalidInput (0.01s)
    tax_test.go:45: assert.Equal failed: expected 0 got -1
=== RUN   TestProcessOrder
--- PASS: TestProcessOrder (0.05s)
FAIL
FAIL\texample.com/shop/tax\t0.08s
"""
        info = VerifierEngine.parse_test_suite("go", sample_go_output)
        self.assertEqual(info["framework"], "testify / go test")
        self.assertEqual(info["total_tests"], 3)
        self.assertEqual(info["passed_count"], 2)
        self.assertEqual(info["failed_count"], 1)
        self.assertEqual(len(info["test_cases"]), 3)

        self.assertEqual(info["test_cases"][0]["name"], "TestCalculateTax")
        self.assertEqual(info["test_cases"][0]["status"], "PASS")
        self.assertEqual(info["test_cases"][0]["duration"], "0.02s")

        self.assertEqual(info["test_cases"][1]["name"], "TestCalculateTaxInvalidInput")
        self.assertEqual(info["test_cases"][1]["status"], "FAIL")
        self.assertEqual(info["test_cases"][1]["duration"], "0.01s")

    def test_parse_test_suite_python(self):
        sample_pytest_output = """rootdir: /workspace/order-service
test_orders.py::test_create_order PASSED                                [ 33%]
test_orders.py::test_order_validation PASSED                            [ 66%]
test_orders.py::test_refund_order FAILED                                [100%]

=================================== FAILURES ===================================
______________________________ test_refund_order _______________________________
AssertionError: assert False is True
=========================== 1 failed, 2 passed in 0.12s ===========================
"""
        info = VerifierEngine.parse_test_suite("python", sample_pytest_output)
        self.assertEqual(info["framework"], "pytest")
        self.assertEqual(info["total_tests"], 3)
        self.assertEqual(info["passed_count"], 2)
        self.assertEqual(info["failed_count"], 1)
        self.assertEqual(len(info["test_cases"]), 3)

        self.assertEqual(info["test_cases"][0]["name"], "test_orders.py::test_create_order")
        self.assertEqual(info["test_cases"][0]["status"], "PASS")

        self.assertEqual(info["test_cases"][2]["name"], "test_orders.py::test_refund_order")
        self.assertEqual(info["test_cases"][2]["status"], "FAIL")

    def test_parse_test_suite_node(self):
        sample_jest_output = """PASS src/math.test.ts
  math calculations
    ✓ adds numbers correctly (4 ms)
    ✓ multiplies numbers correctly (2 ms)
    ✕ divides numbers correctly (6 ms)

  ● math calculations › divides numbers correctly

    expect(received).toBe(expected)

    Expected: 5
    Received: 0

Test Suites: 1 failed, 1 total
Tests:       1 failed, 2 passed, 3 total
Snapshots:   0 total
Time:        1.25 s
"""
        info = VerifierEngine.parse_test_suite("node", sample_jest_output)
        self.assertEqual(info["framework"], "jest")
        self.assertEqual(info["total_tests"], 3)
        self.assertEqual(info["passed_count"], 2)
        self.assertEqual(info["failed_count"], 1)
        self.assertEqual(len(info["test_cases"]), 3)

        self.assertEqual(info["test_cases"][0]["name"], "adds numbers correctly")
        self.assertEqual(info["test_cases"][0]["status"], "PASS")

        self.assertEqual(info["test_cases"][2]["name"], "divides numbers correctly")
        self.assertEqual(info["test_cases"][2]["status"], "FAIL")

    def test_dashboard_state_records_unit_tests(self):
        state = DashboardState(user_goal="Unit Test Dashboard Validation")
        test_cases = [
            {"name": "TestAuthLoginSuccess", "status": "PASS", "duration": "0.01s", "details": ""},
            {"name": "TestAuthInvalidPassword", "status": "PASS", "duration": "0.01s", "details": ""},
        ]
        state.record_test_result(
            repo="auth-service",
            language="go",
            passed=True,
            test_output="=== RUN TestAuthLoginSuccess\n--- PASS\nPASS",
            vet_output="",
            sandboxed=True,
            framework="testify / go test",
            total_tests=2,
            passed_count=2,
            failed_count=0,
            test_cases=test_cases,
        )

        snapshot = state.get_snapshot()
        self.assertIn("test_results", snapshot)
        self.assertEqual(len(snapshot["test_results"]), 1)

        result_entry = snapshot["test_results"][0]
        self.assertEqual(result_entry["repo"], "auth-service")
        self.assertEqual(result_entry["language"], "go")
        self.assertEqual(result_entry["framework"], "testify / go test")
        self.assertTrue(result_entry["passed"])
        self.assertEqual(result_entry["total_tests"], 2)
        self.assertEqual(result_entry["passed_count"], 2)
        self.assertEqual(result_entry["failed_count"], 0)
        self.assertEqual(len(result_entry["test_cases"]), 2)

        # Check logs and timeline contain unit test entries
        self.assertTrue(any("[UNIT_TESTS]" in log for log in snapshot["logs"]))
        self.assertTrue(any("Unit tests PASSED" in evt["action"] for evt in snapshot["timeline_events"]))

    def test_coder_agent_system_prompt_enforces_famous_test_libraries(self):
        coder = GoCoderAgent()
        prompt = coder.system_instruction
        self.assertIn("stretchr/testify", prompt)
        self.assertIn("pytest", prompt)
        self.assertIn("jest", prompt)
        self.assertIn("unit tests", prompt.lower())
        self.assertIn("table-driven", prompt.lower())

        # CoderAgent alias check
        alias_coder = CoderAgent()
        self.assertEqual(alias_coder.system_instruction, prompt)


if __name__ == "__main__":
    unittest.main()

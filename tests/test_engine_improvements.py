import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orchestrator.engine.verifier import VerifierEngine, VerificationResult
from orchestrator.dashboard import DashboardState, DashboardHTTPRequestHandler, GLOBAL_DASHBOARD_STATE
from orchestrator.orchestrator_core import OrchestratorEngine
from orchestrator.state import TaskItem, RepoContract
from orchestrator.agents.all_agents import GoCoderAgent, ProductAgent


class VerifierEngineImprovementsTests(unittest.TestCase):
    def test_language_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "go.mod").write_text("module example.com/calc\ngo 1.22\n", encoding="utf-8")
            self.assertEqual(VerifierEngine.detect_language(str(tmp)), "go")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "package.json").write_text('{"name": "test-pkg"}', encoding="utf-8")
            self.assertEqual(VerifierEngine.detect_language(str(tmp)), "node")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
            self.assertEqual(VerifierEngine.detect_language(str(tmp)), "python")

    def test_verification_result_passed_and_error_summary(self):
        passed_res = VerificationResult(tests_passed=True, vet_passed=True, test_output="ok", language="go")
        self.assertTrue(passed_res.passed)

        failed_res = VerificationResult(
            tests_passed=False,
            test_output="--- FAIL: TestCalc (0.00s)\n   calc_test.go:12: expected 4 got 5",
            vet_passed=False,
            vet_output="calc.go:8: unreachable code",
            language="go",
        )
        self.assertFalse(failed_res.passed)
        summary = failed_res.error_summary()
        self.assertIn("Test Failure Output", summary)
        self.assertIn("expected 4 got 5", summary)
        self.assertIn("unreachable code", summary)


class DashboardInteractiveGovernanceTests(unittest.TestCase):
    def test_approval_lifecycle(self):
        state = DashboardState()
        state.new_session("Test Goal")

        self.assertFalse(state.pending_approval)
        self.assertIsNone(state.approval_decision)

        pending_mock = [{"repo": "calc", "files": ["main.go"]}]
        state.request_approval(pending_mock)

        self.assertTrue(state.pending_approval)
        self.assertEqual(state.pending_changes_data, pending_mock)
        self.assertFalse(state.approval_event.is_set())

        state.submit_approval(True)
        self.assertFalse(state.pending_approval)
        self.assertTrue(state.approval_decision)
        self.assertTrue(state.approval_event.is_set())

    def test_clarification_lifecycle(self):
        state = DashboardState()
        state.new_session("Test Clarification")

        state.request_clarification(["What precision is needed?", "Is caching required?"])
        self.assertTrue(state.clarification_needed)
        self.assertEqual(len(state.clarification_questions), 2)
        self.assertFalse(state.clarification_event.is_set())

        state.submit_clarification("Precision 4 decimal places, no cache.")
        self.assertFalse(state.clarification_needed)
        self.assertEqual(state.clarification_answer, "Precision 4 decimal places, no cache.")
        self.assertTrue(state.clarification_event.is_set())


class TaskFileResolutionTests(unittest.TestCase):
    def test_resolve_specific_go_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            target = tmp / "internal" / "calc" / "trig.go"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("package calc\n// trig code", encoding="utf-8")

            engine = OrchestratorEngine.__new__(OrchestratorEngine)
            task = TaskItem(id="T-1", title="Add Sin", description="desc", target_file="internal/calc/trig.go")
            contract = RepoContract(repo_path=str(tmp), name="calc", allowed_paths=["internal/calc/"])

            source_p, test_p, content = engine._resolve_task_files(str(tmp), task, contract)
            self.assertEqual(source_p, "internal/calc/trig.go")
            self.assertEqual(test_p, "internal/calc/trig_test.go")
            self.assertIn("trig code", content)

    def test_resolve_python_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            target = tmp / "service" / "handler.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("def handle(): pass\n", encoding="utf-8")

            engine = OrchestratorEngine.__new__(OrchestratorEngine)
            task = TaskItem(id="T-2", title="Python Handler", description="desc", target_file="service/handler.py")
            contract = RepoContract(repo_path=str(tmp), name="py-service", allowed_paths=["service/"])

            source_p, test_p, content = engine._resolve_task_files(str(tmp), task, contract)
            self.assertEqual(source_p, "service/handler.py")
            self.assertEqual(test_p, "service/test_handler.py")
            self.assertIn("def handle", content)


class ProductAgentConfidenceTests(unittest.TestCase):
    @patch.object(ProductAgent, "call")
    def test_high_confidence_auto_proceeds_with_checkpoints(self, mock_call):
        from orchestrator.agents.all_agents import ProductAgent
        mock_call.return_value = json.dumps({
            "confidence_score": 0.94,
            "functional_completeness": 0.95,
            "nfr_completeness": 0.93,
            "is_clear": True,
            "understanding": "Full payment microservice specification",
            "clarification_questions": [],
            "checkpoint_clarification_items": [
                {"checkpoint": "TASK-DB", "question": "Use Postgres connection pooling?", "default_assumption": "max_open=25"}
            ]
        })
        agent = ProductAgent()
        res = agent.run("Detailed PRD for payment service")
        self.assertTrue(res["is_clear"])
        self.assertGreaterEqual(res["confidence_score"], 0.90)
        self.assertEqual(len(res["clarification_questions"]), 0)
        self.assertEqual(len(res["checkpoint_clarification_items"]), 1)

    @patch.object(ProductAgent, "call")
    def test_low_confidence_grills_with_questions(self, mock_call):
        from orchestrator.agents.all_agents import ProductAgent
        mock_call.return_value = json.dumps({
            "confidence_score": 0.40,
            "functional_completeness": 0.35,
            "nfr_completeness": 0.45,
            "is_clear": False,
            "understanding": "Ambiguous request",
            "clarification_questions": ["What API protocols?", "What database?"],
            "checkpoint_clarification_items": []
        })
        agent = ProductAgent()
        res = agent.run("build a product")
        self.assertFalse(res["is_clear"])
        self.assertLess(res["confidence_score"], 0.90)
        self.assertEqual(len(res["clarification_questions"]), 2)


class MilestoneReviewTests(unittest.TestCase):
    def test_milestone_review_event_lifecycle(self):
        state = DashboardState()
        state.new_session("Test Milestone")
        self.assertFalse(state.pending_milestone)

        state.request_milestone_review("Phase 3 PRD", "Summary of requirements")
        self.assertTrue(state.pending_milestone)
        self.assertEqual(state.milestone_name, "Phase 3 PRD")
        self.assertFalse(state.milestone_event.is_set())

        state.submit_milestone_review(proceed=True, feedback="")
        self.assertFalse(state.pending_milestone)
        self.assertTrue(state.milestone_decision)
        self.assertTrue(state.milestone_event.is_set())

    def test_milestone_rework_feedback(self):
        state = DashboardState()
        state.new_session("Test Rework")
        state.request_milestone_review("Phase 4 Architecture", "HLD summary")
        state.submit_milestone_review(proceed=False, feedback="Use SQLite instead of Postgres")
        self.assertFalse(state.milestone_decision)
        self.assertEqual(state.milestone_feedback_text, "Use SQLite instead of Postgres")


if __name__ == "__main__":
    unittest.main()

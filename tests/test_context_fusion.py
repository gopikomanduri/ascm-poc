import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.context_fusion import ContextFusionEngine


class ContextFusionEngineTests(unittest.TestCase):
    def test_single_edit_is_kept_as_low_confidence_hypothesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = ContextFusionEngine(root)
            event = engine.record_file_change(root / "src" / "api.py")
            context = engine.infer_context(root)
            self.assertEqual(context["task_hypothesis"], "Recent code activity in src")
            self.assertEqual(context["confidence"], 0.35)
            self.assertFalse(context["is_confirmed"])
            self.assertIn(event["event_id"], context["evidence_event_ids"])

    def test_test_failure_after_edits_produces_evidence_backed_hypothesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = ContextFusionEngine(root)
            edit = engine.record_file_change(root / "src" / "api.py")
            failed = engine.record_test_result(project_path=root, passed=False, exit_code=1)
            context = engine.infer_context(root)
            self.assertEqual(context["task_hypothesis"], "Investigating test failures after recent code changes")
            self.assertEqual(context["confidence"], 0.82)
            self.assertEqual(context["evidence_event_ids"], [edit["event_id"], failed["event_id"]])

    def test_context_is_project_scoped_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_a = root / "a"
            project_b = root / "b"
            project_a.mkdir()
            project_b.mkdir()
            engine = ContextFusionEngine(root)
            engine.record_file_change(project_a / "api.py")
            engine.record_file_change(project_b / "worker.py")
            contexts = engine.infer_context()
            self.assertEqual(len(contexts), 1)  # Non-Git folders share the configured workspace identity.
            saved = engine.list_saved_contexts()
            self.assertEqual(len(saved), 1)
            payload = json.loads(engine.events_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertNotIn("content", payload)
            self.assertNotIn("terminal_output", payload)

    def test_rejects_files_outside_configured_workspace(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            engine = ContextFusionEngine(tmp)
            with self.assertRaises(ValueError):
                engine.record_file_change(Path(outside) / "secret.py")


if __name__ == "__main__":
    unittest.main()

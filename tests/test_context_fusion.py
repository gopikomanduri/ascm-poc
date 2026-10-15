import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.context_fusion import ContextFusionEngine, _now as _now_for_test


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
            subprocess.run(["git", "init", "-q", str(project_a)], check=True)
            subprocess.run(["git", "init", "-q", str(project_b)], check=True)
            engine = ContextFusionEngine(root)
            engine.record_file_change(project_a / "api.py")
            engine.record_file_change(project_b / "worker.py")
            contexts = engine.infer_context()
            self.assertEqual(len(contexts), 2)
            self.assertNotEqual(contexts[0]["project_id"], contexts[1]["project_id"])
            saved = engine.list_saved_contexts()
            self.assertEqual(len(saved), 2)
            payload = json.loads(engine.events_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertNotIn("content", payload)
            self.assertNotIn("terminal_output", payload)


    def test_project_activation_updates_latest_project_without_file_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "web"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            engine = ContextFusionEngine(root)
            event = engine.record_project_activation(project_path=project)
            self.assertEqual(event["event_type"], "project_activated")
            self.assertEqual(engine.latest_project_path(), project.resolve())
            self.assertNotIn("content", event)
            self.assertNotIn("document_text", event)

    def test_latest_project_path_tracks_terminal_context_across_nested_repositories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_a = root / "service-a"
            project_b = root / "service-b"
            project_a.mkdir()
            project_b.mkdir()
            subprocess.run(["git", "init", "-q", str(project_a)], check=True)
            subprocess.run(["git", "init", "-q", str(project_b)], check=True)
            engine = ContextFusionEngine(root)
            engine.record_terminal_event(cwd=project_a, command_category="build_or_run", exit_code=0)
            engine.record_terminal_event(cwd=project_b, command_category="python_tests", exit_code=1)
            self.assertEqual(engine.latest_project_path(), project_b.resolve())

    def test_ide_activation_and_browser_signals_are_recent_but_not_confident_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            engine = ContextFusionEngine(root)
            activated = engine.record_project_activation(project_path=project)
            self.assertTrue(engine.has_recent_activity())
            context = engine.infer_context(project)
            self.assertEqual(context["task_hypothesis"], "Project workspace activated; task intent is unconfirmed")
            self.assertLess(context["confidence"], 0.60)
            self.assertEqual(context["evidence_event_ids"], [activated["event_id"]])

            engine.record_browser_domain(cwd=project, domain="docs.python.org")
            self.assertTrue(engine.has_recent_activity())
            context = engine.infer_context(project)
            self.assertLess(context["confidence"], 0.60)
            self.assertIn("Browsing", context["task_hypothesis"])
            self.assertIn("browser_domain_seen", [event["event_type"] for event in engine._read_events()])

    def test_passive_app_or_browser_events_do_not_trigger_goal_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = ContextFusionEngine(root)
            engine.record_browser_domain(cwd=root, domain="docs.python.org")
            self.assertTrue(engine.has_recent_activity())
            self.assertFalse(engine.has_recent_actionable_activity())
            engine.record_terminal_event(cwd=root, command_category="python_tests", exit_code=0)
            self.assertTrue(engine.has_recent_actionable_activity())

    def test_recent_activity_rejects_stale_events(self):
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = ContextFusionEngine(root)
            event = engine.record_terminal_event(cwd=root, command_category="python_tests", exit_code=0)
            payload = json.loads(engine.events_path.read_text().splitlines()[0])
            payload["timestamp"] = (_now_for_test() - timedelta(minutes=10)).isoformat()
            engine.events_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            self.assertFalse(engine.has_recent_activity(within_seconds=60))
            self.assertIsNone(engine.infer_context(root)["task_hypothesis"])
            payload["timestamp"] = (_now_for_test() + timedelta(hours=1)).isoformat()
            engine.events_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            self.assertFalse(engine.has_recent_activity(within_seconds=60))
            self.assertIsNone(engine.infer_context(root)["task_hypothesis"])

    def test_rejects_files_outside_configured_workspace(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            engine = ContextFusionEngine(tmp)
            with self.assertRaises(ValueError):
                engine.record_file_change(Path(outside) / "secret.py")


if __name__ == "__main__":
    unittest.main()

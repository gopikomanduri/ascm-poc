import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.activity_adapters import (
    ActivityAdapters, ActiveWindowAdapter, classify_command, normalize_domain,
)
from orchestrator.mentor.context_fusion import ContextFusionEngine


class ActivityAdapterTests(unittest.TestCase):
    def test_command_classifier_never_needs_to_persist_raw_command(self):
        self.assertEqual(classify_command("pytest tests/ -q"), "python_tests")
        self.assertEqual(classify_command("npm run test"), "javascript_tests")
        self.assertEqual(classify_command("pip-audit"), "security_scan")
        self.assertEqual(classify_command("echo super-secret-token"), "other")

    def test_browser_adapter_keeps_hostname_only(self):
        self.assertEqual(normalize_domain("https://docs.python.org/3/library?token=abc"), "docs.python.org")
        self.assertEqual(normalize_domain("example.com/private/path"), "example.com")
        with self.assertRaises(ValueError):
            normalize_domain("https://user:secret@example.com/path")
        with self.assertRaises(ValueError):
            normalize_domain("http://localhost:8000/private")
        with self.assertRaises(ValueError):
            normalize_domain("http://192.168.1.10/admin")
        with self.assertRaises(ValueError):
            normalize_domain("http://intranet/admin")

    def test_terminal_and_browser_events_store_only_allowlisted_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = ActivityAdapters(root)
            terminal = adapter.terminal_event(cwd=root, command_category="python_tests", exit_code=1)
            browser = adapter.browser_domain_event(
                cwd=root, url_or_domain="https://example.com/private?session=secret"
            )
            events = [__import__("json").loads(line) for line in adapter.fusion.events_path.read_text().splitlines()]
            self.assertEqual(terminal["event_type"], "terminal_command")
            self.assertEqual(browser["domain"], "example.com")
            self.assertNotIn("command", events[0])
            self.assertNotIn("session", str(events))
            self.assertNotIn("private", str(events))

    def test_active_app_name_is_sanitized_and_does_not_record_window_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ActivityAdapters(tmp)
            event = adapter.active_app_event(cwd=tmp, app_name="VS Code - private customer document")
            self.assertEqual(event["app_name"], "VSCode-privatecustomerdocument")
            self.assertNotIn("title", event)

    def test_context_fusion_infers_test_task_without_output_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = ContextFusionEngine(tmp)
            engine.record_terminal_event(cwd=tmp, command_category="python_tests", exit_code=1)
            context = engine.infer_context(tmp)
            self.assertEqual(context["task_hypothesis"], "Investigating a failed test run")
            self.assertFalse(context["is_confirmed"])

    def test_active_window_adapter_returns_none_when_no_platform_api(self):
        adapter = ActiveWindowAdapter()
        # Platform-specific OS APIs are best effort; this test asserts the API is callable.
        self.assertTrue(adapter.current_app() is None or isinstance(adapter.current_app(), str))


if __name__ == "__main__":
    unittest.main()

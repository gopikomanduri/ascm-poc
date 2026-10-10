import tempfile
import unittest
from pathlib import Path

from orchestrator.mentor.assistant.consent import ConsentGate, DENY, ONCE, ALWAYS
from orchestrator.mentor.assistant.llm import AssistantLLM
from orchestrator.mentor.assistant.suggester import CodeSuggester


def make_llm(answer, tmp, cloud=True, local=None):
    calls = {"cloud": 0, "local": 0, "notified": [], "asked": 0}

    def ask(*a, **k):
        calls["asked"] += 1
        return answer

    def cloud_call(p):
        calls["cloud"] += 1
        return "cloud-reply"

    def local_call(p, m):
        calls["local"] += 1
        return "local-reply"

    gate = ConsentGate(str(Path(tmp) / "c.json"), ask=ask)
    llm = AssistantLLM(gate, notify=lambda t, m: calls["notified"].append(t), cloud_call=cloud_call,
                       cloud_available=lambda: cloud, local_model=lambda: local, local_call=local_call)
    return llm, calls


class ConsentRoutingTests(unittest.TestCase):
    def test_yes_sends_to_cloud(self):
        with tempfile.TemporaryDirectory() as t:
            llm, c = make_llm(ONCE, t, local="m")
            self.assertEqual(llm.ask("p", "x", "y"), "cloud-reply")
            self.assertEqual((c["cloud"], c["local"]), (1, 0))

    def test_no_uses_local_and_never_cloud(self):
        with tempfile.TemporaryDirectory() as t:
            llm, c = make_llm(DENY, t, local="llama3")
            self.assertEqual(llm.ask("p", "x", "y"), "local-reply")
            self.assertEqual((c["cloud"], c["local"]), (0, 1))

    def test_no_and_no_local_stops_and_informs(self):
        with tempfile.TemporaryDirectory() as t:
            llm, c = make_llm(DENY, t, local=None)
            self.assertIsNone(llm.ask("p", "x", "y"))
            self.assertEqual((c["cloud"], c["local"]), (0, 0))
            self.assertEqual(c["notified"], ["No model available"])

    def test_dismissed_dialog_counts_as_no(self):
        with tempfile.TemporaryDirectory() as t:
            llm, c = make_llm(None, t, local=None)
            self.assertIsNone(llm.ask("p", "x", "y"))
            self.assertEqual(c["cloud"], 0)

    def test_always_allow_persists_and_skips_dialog(self):
        with tempfile.TemporaryDirectory() as t:
            llm, c = make_llm(ALWAYS, t)
            llm.ask("p", "x", "y"); llm.ask("p", "x", "y")
            self.assertEqual((c["asked"], c["cloud"]), (1, 2))

    def test_no_cloud_key_goes_local_without_asking(self):
        with tempfile.TemporaryDirectory() as t:
            llm, c = make_llm(ONCE, t, cloud=False, local="m")
            self.assertEqual(llm.ask("p", "x", "y"), "local-reply")
            self.assertEqual(c["asked"], 0)


class SuggesterTests(unittest.TestCase):
    def _setup(self, t, answer="1. Use a dict.\n2. Add a test."):
        clock = {"t": 1000.0}
        shown, prompts = [], []

        class FakeLLM:
            def ask(self, prompt, purpose, data_desc):
                prompts.append(prompt)
                return answer

        s = CodeSuggester(t, FakeLLM(), lambda a, b: shown.append(a), min_quiet_sec=20, cooldown_sec=900,
                          clock=lambda: clock["t"])
        return s, clock, shown, prompts

    def test_waits_for_pause_then_suggests_with_scrubbed_content(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t).resolve() / "app.py"
            f.write_text('API="AKIAABCDEFGHIJKLMNOP"\nx=1\n')
            s, clock, shown, prompts = self._setup(str(Path(t).resolve()))
            s.on_file_changed(str(f))
            clock["t"] += 5
            self.assertIsNone(s.tick())          # still typing
            clock["t"] += 30
            self.assertIsNotNone(s.tick())       # paused
            self.assertNotIn("AKIAABCDEFGHIJKLMNOP", prompts[0])
            self.assertEqual(len(shown), 1)

    def test_sensitive_files_never_sent(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            (root / ".env").write_text("SECRET=1")
            s, clock, shown, prompts = self._setup(str(root))
            s.on_file_changed(str(root / ".env")); clock["t"] += 60
            self.assertIsNone(s.tick()); self.assertEqual(prompts, [])

    def test_cooldown_limits_frequency(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve(); f = root / "a.py"; f.write_text("x=1\n")
            s, clock, shown, prompts = self._setup(str(root))
            s.on_file_changed(str(f)); clock["t"] += 30; s.tick()
            s.on_file_changed(str(f)); clock["t"] += 30
            self.assertIsNone(s.tick())
            self.assertEqual(len(prompts), 1)


if __name__ == "__main__":
    unittest.main()


class SuggesterEdgeCaseTests(unittest.TestCase):
    def _run(self, root, files):
        prompts = []

        class Cap:
            def ask(self, p, purpose, data_desc):
                prompts.append(p); return "ok"

        s = CodeSuggester(str(root), Cap(), lambda a, b: None, min_quiet_sec=0, cooldown_sec=0)
        for f in files:
            s.on_file_changed(str(f))
        s.tick()
        return prompts

    def test_sibling_directory_with_same_prefix_is_not_in_repo(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / "app"; root.mkdir()
            evil = Path(t).resolve() / "app-evil"; evil.mkdir()
            (evil / "f.py").write_text("a=1\n")
            self.assertEqual(self._run(root, [evil / "f.py"]), [])

    def test_deleted_empty_and_binary_files_do_not_crash(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            (root / "e.py").write_text("")
            (root / "b.py").write_bytes(b"\xff\xfe\x00" * 50)
            self.assertEqual(self._run(root, [root / "e.py"]), [])
            self._run(root, [root / "b.py"])
            self._run(root, [root / "missing.py"])

    def test_huge_file_is_truncated(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            (root / "big.py").write_text("z=1\n" * 100000)
            self.assertLess(len(self._run(root, [root / "big.py"])[0]), 7500)

    def test_corrupt_consent_store_still_asks(self):
        with tempfile.TemporaryDirectory() as t:
            store = Path(t) / "c.json"; store.write_text("{not json")
            self.assertTrue(ConsentGate(str(store), ask=lambda *a, **k: ONCE).check("p", "x", "y"))
            self.assertFalse(ConsentGate(str(store), ask=lambda *a, **k: DENY).check("p", "x", "y"))

    def test_local_failure_never_falls_back_to_cloud(self):
        with tempfile.TemporaryDirectory() as t:
            cloud = []
            def boom(p, m): raise ValueError("bad")
            llm = AssistantLLM(ConsentGate(str(Path(t) / "c.json"), ask=lambda *a, **k: DENY),
                               notify=lambda *a: None, cloud_call=lambda p: cloud.append(1) or "C",
                               local_model=lambda: "m", local_call=boom)
            self.assertIsNone(llm.ask("p", "x", "y"))
            self.assertEqual(cloud, [])


class BlankReplyTests(unittest.TestCase):
    def test_blank_llm_reply_shows_nothing_and_does_not_crash(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve(); (root / "w.py").write_text("a=1\n")
            shown = []

            class Blank:
                def ask(self, *a, **k): return "   \n"

            s = CodeSuggester(str(root), Blank(), lambda a, b: shown.append(a), min_quiet_sec=0, cooldown_sec=0)
            s.on_file_changed(str(root / "w.py"))
            self.assertIsNone(s.tick())
            self.assertEqual(shown, [])


class HonestMessageTests(unittest.TestCase):
    def test_failed_cloud_call_is_not_reported_as_nothing_sent(self):
        with tempfile.TemporaryDirectory() as t:
            msgs = []
            def boom(p): raise RuntimeError("429 quota")
            llm = AssistantLLM(ConsentGate(str(Path(t) / "c.json"), ask=lambda *a, **k: ONCE),
                               notify=lambda title, m: msgs.append(m), cloud_call=boom,
                               cloud_available=lambda: True, local_model=lambda: None)
            self.assertIsNone(llm.ask("p", "x", "y"))
            self.assertIn("cloud request failed", msgs[0]); self.assertNotIn("Nothing was sent", msgs[0])

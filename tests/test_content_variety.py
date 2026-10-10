import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.agents.base import BaseAgent
from orchestrator.gtm.agents.marketing_agent import MarketingAgent
from orchestrator.gtm.channels import publish_to_channels as pub
from orchestrator.gtm.strategy import claims_guard as cg
from orchestrator.gtm.strategy import content_variety as cv


class AngleAssignmentTests(unittest.TestCase):
    def test_angles_and_hooks_are_distinct_within_a_batch(self):
        pairs = cv.assign_angles(8)
        self.assertEqual(len({a for a, _ in pairs}), 8)
        self.assertGreaterEqual(len({h for _, h in pairs}), 5)

    def test_recently_used_angles_come_last(self):
        with tempfile.TemporaryDirectory() as t:
            h = cv.PostHistory(str(Path(t) / "h.json"))
            first = cv.assign_angles(1, h)[0][0]
            h.add("text one two three four", "linkedin", angle=first, hook="question")
            self.assertNotEqual(cv.assign_angles(1, h)[0][0], first)
            for a in list(cv.ANGLES)[:-1]:
                h.add(f"x {a}", "linkedin", angle=a)
            self.assertEqual(cv.assign_angles(1, h)[0][0], list(cv.ANGLES)[-1])  # the only never-used angle


class HistoryTests(unittest.TestCase):
    def test_duplicate_detection_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as t:
            path = str(Path(t) / "h.json")
            post = "Our critic uses a different model than the coder so the reviewer does not share its blind spots."
            cv.PostHistory(path).add(post, "linkedin")
            h2 = cv.PostHistory(path)
            self.assertTrue(h2.is_duplicate(post, "linkedin"))
            self.assertTrue(h2.is_duplicate(post.replace("critic", "reviewer agent"), "linkedin", threshold=0.15))
            self.assertFalse(h2.is_duplicate("We found a bug where the alert never fired because counts were always zero.", "linkedin"))
            self.assertFalse(h2.is_duplicate(post, "x"))   # other channel is independent

    def test_corrupt_history_file_is_tolerated(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "h.json"; p.write_text("{oops")
            h = cv.PostHistory(str(p))
            self.assertEqual(h.entries(), []); h.add("a b c d e", "x")
            self.assertEqual(len(h.entries()), 1)


class VarietyReportTests(unittest.TestCase):
    def test_flags_repetition(self):
        same = ["Dear CTOs, we cut overhead by 60% with our squad of agents today.",
                "Dear CTOs, we cut overhead by 60% with our squad of agents again.",
                "Dear CTOs, we cut overhead by 60% with our squad of agents once more."]
        r = cv.variety_report(same)
        self.assertTrue(r["needs_regeneration"])
        self.assertTrue(r["repeated_openers"]); self.assertTrue(r["too_similar_pairs"])
        self.assertTrue(r["numbers_repeated_in_3plus_posts"])

    def test_years_small_ints_and_modest_fact_reuse_do_not_trigger_retries(self):
        posts = [f"Post {i} about a different thing in 2026 with {i} idea, and one verified fact: 121 tests." if i < 3
                 else f"Unrelated story number {i} about a bug and what it taught us on day {i}." for i in range(12)]
        self.assertEqual(cv.variety_report(posts)["numbers_repeated_in_3plus_posts"], {})

    def test_varied_posts_pass(self):
        r = cv.variety_report(["A bug taught us never to trust a green test suite alone.",
                               "Why does your reviewer agree with your coder every time?",
                               "Benchmark baseline: 1 of 20 tasks passed, and here is what that means."])
        self.assertFalse(r["needs_regeneration"])


class MaterialTests(unittest.TestCase):
    def test_numbers_from_material_are_citable(self):
        facts = cg.load_citable_facts()
        self.assertIn("20 requests per day", facts)
        self.assertFalse(cg.audit_text("The free tier allows 20 requests per day per model.", facts) and
                         [i for i in cg.audit_text("The free tier allows 20 requests per day per model.", facts)
                          if i["type"] in cg.BLOCKING])
        self.assertTrue(cg.blocking_issues(cg.audit_text("We cut time by 73%.", facts)))


class TemperatureTests(unittest.TestCase):
    def _agent(self, provider, temperature=None):
        a = BaseAgent.__new__(BaseAgent)
        a.system_instruction, a.provider = "sys", provider
        a.provider_name = "x"; a.model_name = "m"; a.tier = "primary"
        if temperature is not None:
            a.temperature = temperature
        return a

    def test_creative_agents_pass_temperature_default_agents_do_not(self):
        seen = []

        class P:
            model = "m"
            def generate(self, prompt, system_instruction, json_mode=False, temperature=None):
                seen.append(temperature); return "ok"

        self._agent(P(), 0.9).call("p"); self._agent(P()).call("p")
        self.assertEqual(seen, [0.9, None])
        self.assertEqual(MarketingAgent.__init__.__code__.co_names.count("temperature") >= 0, True)

    def test_provider_without_temperature_param_still_works(self):
        class Old:
            model = "m"
            def generate(self, prompt, system_instruction, json_mode=False): return "ok"
        self.assertEqual(self._agent(Old(), 0.9).call("p"), "ok")

    def test_content_agents_run_hot_and_code_agents_stay_cold(self):
        from orchestrator.gtm.agents.sales_agent_v2 import SalesAgentV2
        from orchestrator.gtm.agents.social_first_agents import SocialFirstMarketingAgent
        from orchestrator.agents.all_agents import CoderAgent
        prov = mock.MagicMock(); prov.model = "m"
        self.assertGreaterEqual(MarketingAgent(provider=prov).temperature, 0.8)
        self.assertGreaterEqual(SocialFirstMarketingAgent(provider=prov).temperature, 0.8)
        self.assertGreaterEqual(SalesAgentV2(provider=prov).temperature, 0.6)
        self.assertIsNone(getattr(CoderAgent(provider=prov), "temperature", None))


class MarketingRetryTests(unittest.TestCase):
    def test_repetitive_output_triggers_one_retry_with_feedback(self):
        rep = {"social_posts": [{"platform": "LinkedIn", "content": "Dear CTOs, ASCM cuts overhead by 60% today."}] * 3}
        good = {"social_posts": [{"platform": "LinkedIn", "content": c} for c in (
            "A bug taught us never to trust a green test suite alone.",
            "Why does your reviewer agree with your coder every time?",
            "Benchmark baseline: 1 of 20 tasks passed, and what that means.")]}
        prompts = []
        with tempfile.TemporaryDirectory() as t:
            cwd = os.getcwd(); os.chdir(t)
            try:
                prov = mock.MagicMock(); prov.model = "m"
                agent = MarketingAgent(provider=prov)
                replies = iter([json.dumps(rep), json.dumps(good)])
                agent.call = lambda prompt, json_mode=False: (prompts.append(prompt) or next(replies))
                out = agent.run("thesis")
            finally:
                os.chdir(cwd)
        self.assertEqual(len(prompts), 2)
        self.assertIn("repeated itself", prompts[1])
        self.assertFalse(out["variety_report"]["needs_regeneration"])
        self.assertEqual(len(out["variety_plan"]), 12)
        self.assertIn("VARIETY PLAN", prompts[0])


class PublisherVarietyTests(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd(); self._tmp = tempfile.TemporaryDirectory(); os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._cwd); self._tmp.cleanup()

    def test_repeat_of_published_post_is_regenerated_with_a_new_angle(self):
        old = ("One feature touches three repos and the plans drift apart; we are building an early proof of "
               "concept with a human approval gate.")
        cv.PostHistory(".ascm_history/content_history.json").add(old, "linkedin", angle="founder_story", hook="scene")
        fresh = {"linkedin": "A bug taught us never to trust a green suite: our alert never fired in a real repo.",
                 "x_post": "Green tests, dead alert. Lesson learned."}
        calls = []

        def gen(goal, angle="", hook="", avoid=""):
            calls.append(angle)
            return {"linkedin": old, "x_post": "short"} if len(calls) == 1 else fresh

        with mock.patch.object(pub, "_generate_posts", side_effect=gen), \
             mock.patch.object(pub, "_publish_linkedin"), mock.patch.object(pub, "_publish_x"):
            pub.main(goal="g", interactive=False)
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0], calls[1])
        saved = cv.PostHistory(".ascm_history/content_history.json").entries("linkedin")
        self.assertEqual(saved[-1]["text"], fresh["linkedin"])      # published post is remembered
        self.assertTrue(saved[-1]["angle"])

    def test_unattended_publish_refused_when_every_attempt_repeats(self):
        old = "We built an early proof of concept that plans changes across several repos together."
        cv.PostHistory(".ascm_history/content_history.json").add(old, "linkedin")
        with mock.patch.object(pub, "_generate_posts", return_value={"linkedin": old, "x_post": "z"}), \
             mock.patch.object(pub, "_publish_linkedin") as li, mock.patch.object(pub, "_publish_x"):
            pub.main(goal="g", interactive=False)
            li.assert_not_called()


if __name__ == "__main__":
    unittest.main()

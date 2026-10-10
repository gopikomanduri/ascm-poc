import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from orchestrator.gtm.strategy import claims_guard as cg
from orchestrator.gtm.agents.sales_agent_v2 import SalesAgentV2
from orchestrator.gtm.agents.marketing_agent import MarketingAgent
from orchestrator.gtm.channels import publish_to_channels as pub

FACTS = "- 121 passing tests\n- MR-Bench mean 37.5/100"


class ClaimsGuardTests(unittest.TestCase):
    def types(self, text, facts=""):
        return {i["type"] for i in cg.audit_text(text, facts)}

    def test_flags_unverified_metrics_and_proof(self):
        t = self.types("Cut coordination by 60%, 10x faster. PaymentGateway shipped 10,000 PRs. Case study inside.")
        self.assertTrue({"unverified_metric", "unverified_count", "invented_social_proof"} <= t)

    def test_verified_metric_is_allowed(self):
        self.assertNotIn("unverified_metric", self.types("We have 121 passing tests; MR-Bench mean 37.5/100", FACTS))
        self.assertIn("unverified_metric", self.types("98% coverage", FACTS))

    def test_flags_buzzwords_urgency_placeholders(self):
        t = self.types("A revolutionary tool. Last chance! See [Link to Website]")
        self.assertTrue({"buzzword", "fake_urgency", "placeholder"} <= t)

    def test_flags_invented_scale_claims_and_blocks_buzzwords(self):
        self.assertIn("unverified_count", self.types("Our squad tackles up to 10 repos in one sprint."))
        self.assertNotIn("unverified_count", self.types("MR-Bench: 1 of 20 tasks passed.", "1 of 20 tasks passed"))
        self.assertTrue(cg.blocking_issues(cg.audit_text("Agents collaborate seamlessly.")))

    def test_verified_score_followed_by_noun_is_not_a_count_claim(self):
        self.assertNotIn("unverified_count", self.types("Lessons from 37.5/100 Benchmarks", "37.5/100"))
        self.assertIn("unverified_count", self.types("Tested on 100 benchmarks", "37.5/100"))

    def test_strip_placeholders_cleans_nested_content(self):
        out = cg.strip_placeholders({"posts": [{"content": "Try it: [Link]", "cta": "Read more: [Link to Blog]"}]})
        self.assertEqual(cg.audit_payload(out), [])
        self.assertEqual(out["posts"][0]["cta"], "")
        self.assertEqual(cg.strip_placeholders("Great post [Link] here"), "Great post here")

    def test_invented_links_are_blocked_but_provided_ones_pass(self):
        t = self.types("Code: https://github.com/example/ascm", "")
        self.assertIn("unverified_link", t)
        self.assertNotIn("unverified_link", self.types("Book: https://cal.com/me/15min.", "https://cal.com/me/15min"))

    def test_url_followed_by_escaped_newline_in_json_text_is_matched_cleanly(self):
        raw = json.dumps({"body": "Book here: https://cal.com/me/15min\n\nBest, Gopi"})
        self.assertNotIn("unverified_link", self.types(raw, "https://cal.com/me/15min"))

    def test_clean_honest_copy_passes(self):
        self.assertEqual(cg.blocking_issues(cg.audit_text(
            "One feature touches three repos. We built an early proof of concept with a human approval gate.", FACTS)), [])

    def test_payload_walk(self):
        self.assertTrue(cg.audit_payload({"a": [{"b": "saves 40%"}]}))

    def test_verified_facts_file_is_loadable_and_self_consistent(self):
        facts = cg.load_verified_facts()
        self.assertIn("37.5/100", facts)
        self.assertEqual(cg.blocking_issues(cg.audit_text("MR-Bench mean score 37.5/100, 1 of 20 passed.", facts)), [])


class SalesHonestyTests(unittest.TestCase):
    def _agent(self, reply):
        a = SalesAgentV2.__new__(SalesAgentV2)
        BaseInit = SalesAgentV2.__mro__[1]
        with mock.patch.object(BaseInit, "__init__", lambda self, **k: None):
            SalesAgentV2.__init__(a)
        a.call = lambda prompt, json_mode=True: (setattr(a, "last_prompt", prompt) or json.dumps(reply))
        return a

    def test_invented_leads_are_discarded(self):
        reply = {"leads": [{"company_name": "Stripe", "cto_name": "Evan Wallace", "email": "evan@stripe.com"}],
                 "prospect_profiles": [{"segment": "Series B fintech"}],
                 "email_sequences": [{"audience": "x", "emails": [{"day": 1, "subject": "s", "body": "Hi {{first_name}}"}]}]}
        out = self._agent(reply).run("thesis", "icp", "https://cal.example/x", 3, verified_facts=FACTS)
        self.assertEqual(out["leads"], [])

    def test_real_leads_pass_through_and_prompt_forbids_inventing(self):
        a = self._agent({"email_sequences": []})
        out = a.run("thesis", "icp", "https://cal.example/x", 3,
                    known_leads=[{"name": "Real Person", "email": "real@corp.test"}], verified_facts=FACTS)
        self.assertEqual(out["leads"][0]["email"], "real@corp.test")
        self.assertIn("REAL LEADS PROVIDED", a.last_prompt)
        a2 = self._agent({"email_sequences": []})
        a2.run("thesis", "icp", "https://cal.example/x", 3, verified_facts=FACTS)
        self.assertIn("Do NOT output named people", a2.last_prompt)
        self.assertNotIn("Evan Wallace", a2.last_prompt)
        self.assertNotIn("10K PRs", a2.last_prompt)

    def test_targeting_numbers_in_profiles_are_not_product_claims(self):
        reply = {"prospect_profiles": [{"segment": "Teams with 5+ repositories", "target_title": "VP Eng"}],
                 "email_sequences": [{"emails": [{"day": 1, "subject": "s", "body": "Hi {{first_name}}"}]}]}
        out = self._agent(reply).run("t", "i", "https://cal.example/x", 3, verified_facts=FACTS)
        self.assertFalse(out["content_audit"]["blocking"])

    def test_fabricated_claims_in_email_templates_are_flagged(self):
        reply = {"email_sequences": [{"emails": [{"day": 1, "subject": "s",
                 "body": "One customer went from 2-month to 2-week features. Cut overhead 60%."}]}]}
        out = self._agent(reply).run("t", "i", "https://cal.example/x", 3, verified_facts=FACTS)
        self.assertTrue(out["content_audit"]["blocking"])


class PublisherGateTests(unittest.TestCase):
    def setUp(self):
        import os
        self._cwd = os.getcwd(); self._tmp = tempfile.TemporaryDirectory(); os.chdir(self._tmp.name)

    def tearDown(self):
        import os
        os.chdir(self._cwd); self._tmp.cleanup()

    def test_unattended_publish_refused_when_claims_unverified(self):
        bad = {"linkedin": "Cut delivery time by 60%! See [Link]", "x_post": "10x faster"}
        with mock.patch.object(pub, "_generate_posts", return_value=bad), \
             mock.patch.object(pub, "_publish_linkedin") as li, mock.patch.object(pub, "_publish_x") as x, \
             mock.patch.object(pub, "_save_log") as sl:
            pub.main(goal="g", interactive=False)
            li.assert_not_called(); x.assert_not_called(); sl.assert_not_called()

    def test_clean_posts_are_dispatched(self):
        ok = {"linkedin": "One feature, three repos. Early proof of concept; feedback welcome.", "x_post": "Early PoC, feedback welcome."}
        with mock.patch.object(pub, "_generate_posts", return_value=ok), \
             mock.patch.object(pub, "_publish_linkedin") as li, mock.patch.object(pub, "_publish_x") as x, \
             mock.patch.object(pub, "_save_log"):
            pub.main(goal="g", interactive=False)
            li.assert_called_once(); x.assert_called_once()

    def test_template_fallback_is_itself_clean(self):
        with mock.patch.dict("sys.modules", {"google": None, "google.genai": None}):
            posts = pub._generate_posts("my product")
        self.assertEqual(cg.blocking_issues(cg.audit_text(posts["linkedin"] + posts["x_post"], FACTS)), [])


if __name__ == "__main__":
    unittest.main()

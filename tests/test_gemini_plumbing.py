import json
import os
import unittest
from unittest import mock

from orchestrator.agents.base import GeminiProvider, parse_json_lenient


class LenientJsonTests(unittest.TestCase):
    def test_accepts_trailing_commas_fences_and_surrounding_prose(self):
        self.assertEqual(parse_json_lenient('{"a": [1, 2,], "b": {"c": 1,},}'), {"a": [1, 2], "b": {"c": 1}})
        self.assertEqual(parse_json_lenient('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(parse_json_lenient('Here you go:\n{"a": 1,}\nHope it helps'), {"a": 1})

    def test_accepts_unquoted_keys_and_raw_newlines_in_strings(self):
        raw = '{\n  "title": "x",\n  slug: "a-b",\n  "content": "line one\nline two"\n}'
        self.assertEqual(parse_json_lenient(raw), {"title": "x", "slug": "a-b", "content": "line one\nline two"})

    def test_repairs_key_missing_its_opening_quote(self):
        self.assertEqual(parse_json_lenient('{\n  "a": 1,\n  b": 2\n}'), {"a": 1, "b": 2})

    def test_valid_json_unchanged_and_garbage_still_raises(self):
        self.assertEqual(parse_json_lenient('{"a": "x, ]"}'), {"a": "x, ]"})
        with self.assertRaises(json.JSONDecodeError):
            parse_json_lenient("not json at all")


class GeminiProviderConfigTests(unittest.TestCase):
    def _provider(self, env):
        with mock.patch.dict(os.environ, env, clear=False), mock.patch("google.genai.Client") as client:
            p = GeminiProvider(api_key="k")
            return p, client.call_args.kwargs["http_options"]["timeout"]

    def test_timeout_is_long_enough_by_default_and_configurable(self):
        self.assertEqual(self._provider({})[1], 120_000)          # was 10_000: killed long content generation
        self.assertEqual(self._provider({"GEMINI_TIMEOUT_SEC": "30"})[1], 30_000)

    def test_candidate_list_has_no_retired_models_and_starts_with_configured_one(self):
        p, _ = self._provider({"GEMINI_MODEL": "gemini-3.5-flash-lite"})
        self.assertEqual(p.candidate_models[0], "gemini-3.5-flash-lite")
        self.assertFalse([m for m in p.candidate_models if m.startswith("gemini-2.5")])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
import sys

app_dir = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(app_dir))

from dpo_preference_generator import DPOPreferenceGenerator, DPOPreferencePair


class TestDPOPreferenceGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.temp_dir.name)
        self.generator = DPOPreferenceGenerator(output_dir=self.out_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_synthetic_pairs_generation(self):
        pairs = self.generator.generate_synthetic_archetype_pairs()
        self.assertGreaterEqual(len(pairs), 4)

        # Check Archetype 1 (Promissory)
        promissory_pairs = [p for p in pairs if p.violation_type == "PROMISSORY_RETURN_INTERCEPT"]
        self.assertTrue(len(promissory_pairs) > 0)
        p = promissory_pairs[0]
        self.assertIn("market risks", p.chosen.lower())
        self.assertIn("guaranteed", p.rejected.lower())

    def test_pair_from_intercepted_telemetry(self):
        mock_record = {
            "query": "Give me guaranteed 18% returns",
            "fund_name": "HDFC Top 100 Index Fund",
            "fund_id": "hdfc_top_100",
            "raw_response": "We promise this fund gives 18% guaranteed return.",
            "sanitized_response": "Returns fluctuate and cannot be guaranteed. Historical 3Y CAGR is 11.61%.",
            "violations_intercepted": ["PROMISSORY_RETURN_BLOCKED"],
        }
        pair = self.generator.generate_pair_from_intercept(mock_record)
        self.assertIsNotNone(pair)
        self.assertIn("HDFC Top 100", pair.prompt)
        self.assertIn("market risks", pair.chosen.lower())
        self.assertIn("guaranteed return", pair.rejected)
        self.assertEqual(pair.violation_type, "PROMISSORY_RETURN_BLOCKED")

    def test_compile_daily_dpo_dataset_jsonl(self):
        manifest = self.generator.compile_daily_dpo_dataset(include_synthetic=True)
        self.assertGreaterEqual(manifest["total_pairs"], 4)
        self.assertTrue(self.generator.dataset_file.exists())
        self.assertTrue(self.generator.manifest_file.exists())

        # Verify JSONL lines format
        with open(self.generator.dataset_file, "r") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(lines), manifest["total_pairs"])
        for item in lines:
            self.assertIn("prompt", item)
            self.assertIn("chosen", item)
            self.assertIn("rejected", item)
            self.assertIn("metadata", item)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.gtm.strategy.product_context import ProductContext
from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger


class ProductContextTests(unittest.TestCase):
    def test_missing_config_is_explicitly_generic(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = ProductContext.load(Path(tmp))
        self.assertEqual(context.product_name, "Unconfigured product")
        self.assertIn("not configured", context.product_thesis.lower())
        self.assertEqual(context.domain_keywords, [])

    def test_loads_product_context_from_project_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ascm_product.json").write_text(json.dumps({
                "product_name": "Example",
                "product_thesis": "Reduce invoice processing time.",
                "icp_description": "Finance operations teams.",
                "domain_keywords": ["invoice automation"],
                "goals": ["5 discovery calls"],
            }))
            context = ProductContext.load(root)
        self.assertEqual(context.product_name, "Example")
        self.assertEqual(context.domain_keywords, ["invoice automation"])
        self.assertEqual(context.goals, ["5 discovery calls"])

    def test_rejects_unknown_or_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ascm_product.json").write_text('{"product_nam": "typo"}')
            with self.assertRaisesRegex(ValueError, "Unknown"):
                ProductContext.load(root)
            (root / ".ascm_product.json").write_text('{"domain_keywords": "not a list"}')
            with self.assertRaisesRegex(ValueError, "domain_keywords"):
                ProductContext.load(root)


class OutcomeLedgerTests(unittest.TestCase):
    def test_records_experiment_events_and_summarizes_real_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = OutcomeLedger(Path(tmp))
            ledger.record("experiment_planned", experiment_id="exp-1")
            ledger.record("customer_reply", experiment_id="exp-1", metrics={"sentiment": "INTERESTED"})
            summary = ledger.summarize_experiment("exp-1")
        self.assertEqual(summary["event_count"], 2)
        self.assertTrue(summary["outcomes_observed"])
        self.assertNotEqual(summary["events"][0]["event_id"], summary["events"][1]["event_id"])

    def test_rejects_generated_copy_as_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                OutcomeLedger(Path(tmp)).record("generated_copy", experiment_id="exp-1")


if __name__ == "__main__":
    unittest.main()

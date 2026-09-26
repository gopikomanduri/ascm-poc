#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
import sys

# Ensure data-pipeline is in path
app_dir = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(app_dir))

from daily_sync_pipeline import RealTimeAPISync, DailySyncCron


class TestDailySyncPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.syncer = RealTimeAPISync(data_dir=self.data_dir, timeout=1.0)
        self.sample_catalog = {
            "hdfc_top_100": {
                "id": "hdfc_top_100",
                "name": "HDFC Top 100 Index Fund",
                "category": "Large Cap Index",
                "benchmark": "NIFTY 100 TRI",
                "nav": 1042.85,
                "nav_history": [620.0, 750.0, 890.0, 960.0, 1042.85],
                "benchmark_history": [550.0, 680.0, 810.0, 890.0, 970.0],
                "expense_ratio": 0.35,
                "aum_cr": 34850,
            }
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sync_fund_deterministic_metrics(self):
        synced = self.syncer.sync_fund("hdfc_top_100", self.sample_catalog["hdfc_top_100"])
        self.assertIn("nav", synced)
        self.assertIn("metrics", synced)
        metrics = synced["metrics"]
        self.assertIn("cagr_3yr_pct", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("beta", metrics)
        self.assertGreater(metrics["cagr_3yr_pct"], 0.0)

    def test_run_daily_sync_creates_cache(self):
        manifest = self.syncer.run_daily_sync(self.sample_catalog)
        self.assertEqual(manifest["status"], "COMPLETED")
        self.assertEqual(manifest["total_schemes"], 1)
        self.assertTrue(self.syncer.cache_file.exists())

        with open(self.syncer.cache_file, "r") as f:
            data = json.load(f)
            self.assertIn("hdfc_top_100", data["funds"])

    def test_cron_run_once(self):
        cron = DailySyncCron(self.syncer, interval_seconds=10)
        res = cron.run_once(self.sample_catalog)
        self.assertEqual(res["total_schemes"], 1)


if __name__ == "__main__":
    unittest.main()

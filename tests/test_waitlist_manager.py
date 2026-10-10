import unittest
import tempfile
from pathlib import Path
from orchestrator.waitlist_manager import WaitlistManager


class TestWaitlistManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_store = Path(self.temp_dir.name) / "test_waitlist.json"
        self.manager = WaitlistManager(store_path=self.test_store)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_entry_valid(self):
        res = self.manager.add_entry("founder@startup.io", tier="pro_early_bird")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["email"], "founder@startup.io")
        self.assertEqual(res["total_count"], 1)

        entries = self.manager.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["tier"], "pro_early_bird")

    def test_add_entry_invalid_email(self):
        res = self.manager.add_entry("notanemail")
        self.assertEqual(res["status"], "error")
        self.assertIn("Invalid email", res["message"])
        self.assertEqual(len(self.manager.get_entries()), 0)

    def test_deduplication_and_update(self):
        self.manager.add_entry("alex@company.com", tier="alpha")
        res2 = self.manager.add_entry("alex@company.com", tier="pro_early_bird")
        self.assertEqual(res2["status"], "ok")
        self.assertTrue(res2["already_registered"])
        self.assertEqual(res2["total_count"], 1)

        entries = self.manager.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["tier"], "pro_early_bird")
        self.assertEqual(entries[0]["request_count"], 2)

    def test_persistence_reloads(self):
        self.manager.add_entry("user1@example.com")
        self.manager.add_entry("user2@example.com")

        # Create new manager pointing to same file
        manager2 = WaitlistManager(store_path=self.test_store)
        entries = manager2.get_entries()
        self.assertEqual(len(entries), 2)
        stats = manager2.get_stats()
        self.assertEqual(stats["total_count"], 2)


if __name__ == "__main__":
    unittest.main()

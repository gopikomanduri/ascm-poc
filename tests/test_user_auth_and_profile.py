import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.auth.user_manager import UserManager


class UserAuthAndProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.store_path = Path(self.tmpdir.name) / "test_users.json"
        self.mgr = UserManager(store_path=self.store_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_signup_and_verify_with_email(self):
        # 1. Request OTP for email
        res1 = self.mgr.send_otp("developer@ascm.io", name="Alex Rivera")
        self.assertEqual(res1["status"], "ok")
        self.assertIn("dev_otp", res1)
        otp = res1["dev_otp"]
        self.assertEqual(len(otp), 6)

        # 2. Verify with wrong OTP
        bad_res = self.mgr.verify_otp("developer@ascm.io", "000000")
        self.assertEqual(bad_res["status"], "error")

        # 3. Verify with correct OTP
        good_res = self.mgr.verify_otp("developer@ascm.io", otp)
        self.assertEqual(good_res["status"], "ok")
        user = good_res["user"]
        self.assertEqual(user["name"], "Alex Rivera")
        self.assertEqual(user["email"], "developer@ascm.io")
        self.assertTrue(user["created_at"])
        self.assertTrue(user["last_login"])

    def test_signup_and_verify_with_mobile_phone(self):
        # 1. Request OTP for phone
        res1 = self.mgr.send_otp("+1 (555) 234-5678", name="Sam Taylor")
        self.assertEqual(res1["status"], "ok")
        otp = res1["dev_otp"]

        # 2. Verify OTP
        res2 = self.mgr.verify_otp("+15552345678", otp)
        self.assertEqual(res2["status"], "ok")
        user = res2["user"]
        self.assertEqual(user["name"], "Sam Taylor")
        self.assertEqual(user["phone"], "+15552345678")

    def test_persist_user_details_and_byok_choices(self):
        # Create user
        res = self.mgr.send_otp("founder@startup.com", name="Jordan Founder")
        self.mgr.verify_otp("founder@startup.com", res["dev_otp"])

        # Update profile with mobile phone and custom API key choices
        updates = {
            "name": "Jordan Founder, CEO",
            "phone": "+1 (555) 999-8888",
            "choices": {
                "preferred_provider": "anthropic",
                "anthropic_api_key": "sk-ant-test-key-999",
                "openai_api_key": "sk-proj-test-key-888",
                "fast_model": "claude-3-5-haiku",
                "primary_model": "claude-3-5-sonnet",
                "auto_approve": True,
                "use_sandbox": True,
            }
        }
        up_res = self.mgr.update_profile("founder@startup.com", updates)
        self.assertEqual(up_res["status"], "ok")
        user = up_res["user"]
        self.assertEqual(user["name"], "Jordan Founder, CEO")
        self.assertEqual(user["phone"], "+1 (555) 999-8888")
        self.assertEqual(user["choices"]["preferred_provider"], "anthropic")
        self.assertEqual(user["choices"]["anthropic_api_key"], "sk-ant-test-key-999")
        self.assertTrue(user["choices"]["auto_approve"])

        # Reload from fresh disk instance to ensure persistence
        fresh_mgr = UserManager(store_path=self.store_path)
        active_u = fresh_mgr.get_active_user()
        self.assertIsNotNone(active_u)
        self.assertEqual(active_u["name"], "Jordan Founder, CEO")
        self.assertEqual(active_u["email"], "founder@startup.com")
        self.assertEqual(active_u["phone"], "+1 (555) 999-8888")
        self.assertEqual(active_u["choices"]["anthropic_api_key"], "sk-ant-test-key-999")
        self.assertEqual(active_u["choices"]["fast_model"], "claude-3-5-haiku")

    def test_invalid_identifier_rejected(self):
        res = self.mgr.send_otp("invalid_format")
        self.assertEqual(res["status"], "error")


if __name__ == "__main__":
    unittest.main()

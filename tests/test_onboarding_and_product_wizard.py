import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.auth.user_manager import UserManager
from orchestrator.product_wizard import RepoAnalyzer, AgentRosterAdvisor
from orchestrator.dashboard import DashboardHTTPRequestHandler


class ProductWizardAndOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.user_store = Path(self.test_dir) / "users.json"
        self.user_manager = UserManager(store_path=self.user_store)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_user_onboarding_and_apps_lifecycle(self):
        # 1. Register user
        reg = self.user_manager.send_otp("dev@company.com", name="Alex Founder")
        self.assertEqual(reg["status"], "ok")
        ver = self.user_manager.verify_otp("dev@company.com", reg["dev_otp"])
        self.assertEqual(ver["status"], "ok")
        user = ver["user"]
        self.assertFalse(user["onboarding_completed"])
        self.assertGreaterEqual(len(user["developed_apps"]), 1)

        # 2. Complete onboarding
        comp = self.user_manager.complete_onboarding("dev@company.com")
        self.assertEqual(comp["status"], "ok")
        updated_user = self.user_manager.get_user("dev@company.com")
        self.assertTrue(updated_user["onboarding_completed"])

        # 3. Add a new developed product
        new_app = {
            "name": "Distributed Analytics Engine",
            "description": "High-volume telemetry ingestion and clickstream analytics.",
            "archetype": "talking_to_existing_repos",
            "is_internal": True,
            "repos": ["repos/ingest-svc", "repos/query-svc"],
            "skills_status": "present",
            "skills_path": "SKILLS.md",
            "agents": ["ProductManager", "Architect", "Coder", "Verifier"],
        }
        res = self.user_manager.add_user_app(new_app, identifier="dev@company.com")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["app"]["name"], "Distributed Analytics Engine")

        # 4. Fetch apps list
        apps = self.user_manager.get_user_apps("dev@company.com")
        self.assertEqual(apps[0]["name"], "Distributed Analytics Engine")
        self.assertTrue(apps[0]["is_internal"])

    def test_repo_analyzer_discovers_skills_md(self):
        # Create a mock repo with SKILLS.md
        repo_dir = Path(self.test_dir) / "mock_provider_repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "main.go").write_text("package main\nfunc main() {}", encoding="utf-8")
        (repo_dir / "internal").mkdir()
        (repo_dir / "internal" / "handler.go").write_text("package internal", encoding="utf-8")
        (repo_dir / "SKILLS.md").write_text(
            """---
name: mock_provider_repo
role: provider
allowed_paths:
  - internal/handler.go
---
# Mock Repo
""",
            encoding="utf-8",
        )

        analysis = RepoAnalyzer.analyze_repo(str(repo_dir))
        self.assertEqual(analysis["status"], "ok")
        self.assertTrue(analysis["found_skills"])
        self.assertEqual(analysis["skills_path"], "SKILLS.md")
        self.assertEqual(analysis["primary_language"], "Go")
        self.assertIn("internal/handler.go", analysis["allowed_paths"])
        self.assertFalse(analysis["needs_skills_creation"])

    def test_repo_analyzer_missing_skills_and_scaffolding(self):
        # Create repo without SKILLS.md
        repo_dir = Path(self.test_dir) / "empty_repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "service.py").write_text("print('hello')", encoding="utf-8")

        analysis = RepoAnalyzer.analyze_repo(str(repo_dir))
        self.assertEqual(analysis["status"], "ok")
        self.assertFalse(analysis["found_skills"])
        self.assertTrue(analysis["needs_skills_creation"])

        # Scaffold SKILLS.md
        scaffold = RepoAnalyzer.scaffold_skills_md(str(repo_dir), role="provider", allowed_paths=["service.py"])
        self.assertEqual(scaffold["status"], "ok")
        self.assertTrue(scaffold["created"])
        self.assertTrue((repo_dir / "SKILLS.md").exists())

        # Re-analyze
        re_analysis = RepoAnalyzer.analyze_repo(str(repo_dir))
        self.assertTrue(re_analysis["found_skills"])
        self.assertEqual(re_analysis["skills_path"], "SKILLS.md")

    def test_repo_analyzer_custom_skills_path(self):
        repo_dir = Path(self.test_dir) / "custom_docs_repo"
        docs_dir = repo_dir / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "CONTRACT.md").write_text(
            """---
name: custom_docs_repo
role: consumer
allowed_paths:
  - src/
---
# Contract
""",
            encoding="utf-8",
        )

        # Search with custom path
        analysis = RepoAnalyzer.analyze_repo(str(repo_dir), custom_skills_path="docs/CONTRACT.md")
        self.assertEqual(analysis["status"], "ok")
        self.assertTrue(analysis["found_skills"])
        self.assertEqual(analysis["skills_path"], "docs/CONTRACT.md")

    def test_grill_repo_clarifications_scoring(self):
        # Incomplete answers
        low_clarity = RepoAnalyzer.grill_repo_clarifications({
            "primary_stack": "Go",
            "public_apis": "",
            "protected_paths": "",
            "enhancement_scope": "",
        })
        self.assertLess(low_clarity["clarity_score"], 75)
        self.assertFalse(low_clarity["ready_to_proceed"])
        self.assertEqual(low_clarity["verdict"], "MORE_CLARIFICATIONS_NEEDED")

        # Complete answers
        high_clarity = RepoAnalyzer.grill_repo_clarifications({
            "primary_stack": "Go 1.22 + Gin framework",
            "public_apis": "POST /v1/checkout, GET /v1/status",
            "protected_paths": "db/migrations/, .github/workflows/",
            "enhancement_scope": "Implement Stripe webhook idempotent processing",
        })
        self.assertEqual(high_clarity["clarity_score"], 100)
        self.assertTrue(high_clarity["ready_to_proceed"])
        self.assertEqual(high_clarity["verdict"], "CLEAR_TO_BUILD")
        self.assertIn("POST /v1/checkout", high_clarity["synthesized_summary"])

    def test_agent_roster_advisor_internal_tool_vs_commercial_saas(self):
        # 1. Internal Tool: Business and Revenue agents must be excluded by default
        internal_recs = AgentRosterAdvisor.recommend_agents(
            product_archetype="enhancement",
            is_internal=True,
            repo_count=1,
        )
        self.assertEqual(internal_recs["status"], "ok")
        self.assertTrue(internal_recs["is_internal"])
        active_ids = internal_recs["active_agent_ids"]
        self.assertNotIn("BusinessStrategy", active_ids)
        self.assertNotIn("RevenueROI", active_ids)
        self.assertIn("ArchitectureReview", active_ids)
        self.assertIn("CodeReview", active_ids)
        self.assertIn("ProductManager", active_ids)
        self.assertIn("Coder", active_ids)
        self.assertIn("SecurityAudit", active_ids)
        self.assertIn("Verifier", active_ids)

        # 2. Commercial SaaS: Business and Revenue agents must be recommended
        saas_recs = AgentRosterAdvisor.recommend_agents(
            product_archetype="brand_new",
            is_internal=False,
            repo_count=2,
        )
        self.assertEqual(saas_recs["status"], "ok")
        self.assertFalse(saas_recs["is_internal"])
        saas_active_ids = saas_recs["active_agent_ids"]
        self.assertIn("BusinessStrategy", saas_active_ids)
        self.assertIn("RevenueROI", saas_active_ids)
        self.assertIn("ArchitectureReview", saas_active_ids)
        self.assertIn("CodeReview", saas_active_ids)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from orchestrator.contracts import parse_skill_contract


class ContractParsingTests(unittest.TestCase):
    def test_reads_markdown_allowlist_and_removes_repository_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "calculator"
            repo.mkdir()
            (repo / "SKILL.md").write_text(
                "---\nname: calculator\nrole: provider\n---\n"
                "## File Path Allowlist\n\n```text\n"
                "calculator/internal/api/\ncalculator/cmd/server/main.go\n```\n",
                encoding="utf-8",
            )

            contract = parse_skill_contract(str(repo))

        self.assertEqual(contract.role, "provider")
        self.assertEqual(contract.allowed_paths, ["internal/api/", "cmd/server/main.go"])

    def test_uses_frontmatter_allowlist_when_present(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "service"
            repo.mkdir()
            (repo / "SKILL.md").write_text(
                "---\nname: service\nallowed_paths:\n  - internal/\n---\n",
                encoding="utf-8",
            )

            contract = parse_skill_contract(str(repo))

        self.assertEqual(contract.allowed_paths, ["internal/"])

import tempfile
import unittest
from pathlib import Path

from orchestrator.engine.sandbox import PathViolationError, SandboxEngine


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.directory.name) / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self.directory.cleanup()

    def test_accepts_file_within_allowed_directory(self):
        files = {"internal/api/handler.go": "package api\n"}

        SandboxEngine.validate_and_write(str(self.repo), ["internal/api/"], files)

        self.assertEqual((self.repo / "internal/api/handler.go").read_text(), "package api\n")

    def test_rejects_path_traversal(self):
        with self.assertRaises(PathViolationError):
            SandboxEngine.validate(str(self.repo), ["internal/"], {"../outside.go": ""})

    def test_rejects_protected_git_path(self):
        with self.assertRaises(PathViolationError):
            SandboxEngine.validate(str(self.repo), [".git/"], {".git/config": ""})

    def test_rejects_non_mapping_generated_patch(self):
        with self.assertRaises(PathViolationError):
            SandboxEngine.validate(str(self.repo), ["internal/"], ["internal/main.go"])

    def test_rejects_sibling_with_shared_prefix(self):
        sibling = self.repo.parent / "repo-evil" / "escape.go"
        with self.assertRaises(PathViolationError):
            SandboxEngine.validate(str(self.repo), ["repo-evil/"], {str(sibling): ""})

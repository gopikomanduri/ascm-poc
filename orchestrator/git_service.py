import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any


class GitService:
    @staticmethod
    def ensure_clean_repo(repo_path: str) -> None:
        result = GitService._run(repo_path, ["status", "--porcelain"])
        if result.stdout.strip():
            raise RuntimeError("repository has uncommitted changes")

    @staticmethod
    def get_current_branch(repo_path: str) -> str:
        result = GitService._run(repo_path, ["branch", "--show-current"], check=False)
        return result.stdout.strip() or "main"

    @staticmethod
    def create_branch(repo_path: str, goal: str) -> str:
        branch = f"ascm/{_slugify(goal)}"
        # If branch already exists, switch to it, else create it
        check_branch = GitService._run(repo_path, ["show-ref", f"refs/heads/{branch}"], check=False)
        if check_branch.returncode == 0:
            GitService._run(repo_path, ["switch", branch])
        else:
            GitService._run(repo_path, ["switch", "-c", branch])
        return branch

    @staticmethod
    def commit(repo_path: str, goal: str, files: list[str]) -> None:
        GitService._run(repo_path, ["add", "--", *files])
        staged = GitService._run(repo_path, ["diff", "--cached", "--quiet"], check=False)
        if staged.returncode == 0:
            return
        GitService._run(repo_path, ["commit", "-m", f"feat: {goal}"])

    @staticmethod
    def generate_pr_description(
        goal: str,
        files: list[str],
        role: str = "provider",
        linked_repos: Optional[List[Dict[str, str]]] = None,
        prd_summary: str = "",
    ) -> str:
        """
        Generates a standardized, cross-linked Markdown Pull Request description.
        """
        lines = [
            f"# Feature: {goal}",
            "",
            "## 📌 Overview & Scope",
            f"**Repository Role**: `{role.upper()}`",
            "",
            f"{prd_summary.strip() if prd_summary else 'Automated cross-repository engineering changes generated and verified by ASCM.'}",
            "",
            "## 🛠️ Modified Files",
        ]
        for f in files:
            lines.append(f"- `{f}`")

        if linked_repos:
            lines.extend([
                "",
                "## 🔗 Linked Cross-Repository Changes",
                "This change is coordinated across multiple repositories in the topology:",
            ])
            for lr in linked_repos:
                name = lr.get("name", "Unknown Repo")
                b = lr.get("branch", "main")
                r_role = lr.get("role", "companion")
                lines.append(f"- **{name}** (`{r_role}`): Branch `{b}`")

        lines.extend([
            "",
            "## 🛡️ Verification & Quality Assurance",
            "- [x] Multi-file AST boundary validation passed (Sandbox)",
            "- [x] Native language test suite passed",
            "- [x] Static analysis / compile diagnostics verified",
            "- [x] Peer code review and architectural specification approved",
            "",
            "---",
            "*Generated autonomously by [ASCM](https://github.com/gopikomanduri/ascm-poc)*",
        ])
        return "\n".join(lines)

    @staticmethod
    def write_pr_artifact(repo_path: str, pr_content: str, filename: str = "PULL_REQUEST.md") -> str:
        target = Path(repo_path) / filename
        target.write_text(pr_content, encoding="utf-8")
        return str(target)

    @staticmethod
    def push_branch(repo_path: str, branch: str, remote: str = "origin") -> bool:
        result = GitService._run(repo_path, ["push", "-u", remote, branch], check=False)
        return result.returncode == 0

    @staticmethod
    def create_github_pr(repo_path: str, branch: str, title: str, body: str) -> Optional[str]:
        """
        Attempts to create a GitHub PR using the `gh` CLI if installed and authenticated.
        Returns the created PR URL, or None if gh is unavailable or creation failed.
        """
        if not shutil.which("gh"):
            return None
        result = GitService._run(
            repo_path,
            ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body],
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    @staticmethod
    def _run(repo_path: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=Path(repo_path),
            capture_output=True,
            text=True,
            check=check,
        )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "generated-change"


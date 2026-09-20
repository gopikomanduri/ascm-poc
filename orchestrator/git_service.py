import re
import subprocess
from pathlib import Path


class GitService:
    @staticmethod
    def ensure_clean_repo(repo_path: str) -> None:
        result = GitService._run(repo_path, ["status", "--porcelain"])
        if result.stdout.strip():
            raise RuntimeError("repository has uncommitted changes")

    @staticmethod
    def create_branch(repo_path: str, goal: str) -> str:
        branch = f"ascm/{_slugify(goal)}"
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

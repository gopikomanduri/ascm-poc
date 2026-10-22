from pathlib import Path
from typing import Dict, List

class PathViolationError(Exception):
    """Raised when an agent attempts to modify a protected file."""
    pass

class SandboxEngine:
    @staticmethod
    def validate(repo_path: str, allowed_paths: List[str], files: Dict[str, str]) -> None:
        base_dir = Path(repo_path).resolve()
        if not isinstance(files, dict):
            raise PathViolationError("generated patch must be a mapping of paths to file contents")
        for rel_path, content in files.items():
            if not isinstance(rel_path, str):
                raise PathViolationError("generated patch contains a non-string path")
            path = Path(rel_path)
            if not isinstance(content, str):
                raise PathViolationError(f"generated content for '{rel_path}' is not text")
            if path.is_absolute() or ".." in path.parts:
                raise PathViolationError(f"path traversal detected: '{rel_path}'")
            normalized = path.as_posix()
            if _is_protected(normalized, allowed_paths):
                raise PathViolationError(f"protected path: '{rel_path}'")
            if content == "" or len(content.encode("utf-8")) > MAX_FILE_BYTES:
                raise PathViolationError(
                    f"generated content for '{rel_path}' is empty or larger than {MAX_FILE_BYTES} bytes"
                )
            if not _is_allowed(normalized, allowed_paths):
                raise PathViolationError(
                    f"[SECURITY VIOLATION] Agent attempted to write to protected file: '{normalized}'. "
                    f"Allowed paths for this repo are: {allowed_paths}"
                )
            target = (base_dir / normalized).resolve()
            try:
                target.relative_to(base_dir)
            except ValueError as error:
                raise PathViolationError(f"path escapes repository: '{rel_path}'") from error

    @staticmethod
    def validate_and_write(repo_path: str, allowed_paths: List[str], files: Dict[str, str]) -> None:
        SandboxEngine.validate(repo_path, allowed_paths, files)
        base_dir = Path(repo_path).resolve()
        for rel_path, content in files.items():
            target = base_dir / Path(rel_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Re-check after mkdir: a symlinked directory or file must not redirect the write.
            if target.is_symlink() or not target.parent.resolve().is_relative_to(base_dir):
                raise PathViolationError(f"refusing to write through a symlink: '{rel_path}'")
            target.write_text(content, encoding="utf-8")
            print(f"    [+] Safely updated: {rel_path}")


def _is_allowed(path: str, allowed_paths: List[str]) -> bool:
    for allowed in allowed_paths:
        normalized = allowed.rstrip("/")
        if allowed.endswith("/") and path.startswith(f"{normalized}/"):
            return True
        if path == normalized:
            return True
    return False


MAX_FILE_BYTES = 512 * 1024

_PROTECTED_DIRS = {".git", ".agents", ".codex"}
# The agent's own permissions: it must never be able to widen its allowlist.
_CONTRACT_FILES = {"skill.md", "skills.md"}
# Files that make a repo execute code (CI, hooks, build/test config, secrets). Writable only when the contract
# lists the exact file in allowed_paths; a directory prefix such as "src/" or "./" is not enough.
_EXEC_CONFIG_DIRS = {".github", ".husky", ".circleci", ".gitlab"}
_EXEC_CONFIG_FILES = {
    "makefile", "conftest.py", "setup.py", "pyproject.toml", "tox.ini", "noxfile.py", "package.json",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", ".gitlab-ci.yml", "jenkinsfile",
}


def _is_protected(path: str, allowed_paths: List[str] = ()) -> bool:
    parts = [part.lower() for part in Path(path).parts]  # case-insensitive: ".GIT" is ".git" on macOS/Windows
    name = parts[-1] if parts else ""
    if any(part in _PROTECTED_DIRS for part in parts):
        return True
    if name in _CONTRACT_FILES or name.endswith(".arch.md"):
        return True
    explicit = {a.rstrip("/").lower() for a in allowed_paths if not a.endswith("/")}
    is_exec_config = (
        any(part in _EXEC_CONFIG_DIRS for part in parts)
        or name in _EXEC_CONFIG_FILES
        or name == ".env" or name.startswith(".env.")
        or name.endswith(".pem") or name.endswith(".key")
    )
    return is_exec_config and Path(path).as_posix().lower() not in explicit

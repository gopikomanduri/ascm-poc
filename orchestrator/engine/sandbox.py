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
            if _is_protected(normalized):
                raise PathViolationError(f"protected path: '{rel_path}'")
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


def _is_protected(path: str) -> bool:
    return any(part in {".git", ".agents", ".codex"} for part in Path(path).parts)

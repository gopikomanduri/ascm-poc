import os
from pathlib import Path
from typing import Dict, List

class PathViolationError(Exception):
    """Raised when an agent attempts to modify a protected file."""
    pass

class SandboxEngine:
    @staticmethod
    def validate_and_write(repo_path: str, allowed_paths: List[str], files: Dict[str, str]) -> None:
        base_dir = Path(repo_path).resolve()
        
        # Validation Pass: Check every file against the policy allowlist
        for rel_path in files.keys():
            normalized = os.path.normpath(rel_path)
            
            # Match against allowed list
            if normalized not in allowed_paths:
                raise PathViolationError(
                    f"[SECURITY VIOLATION] Agent attempted to write to protected file: '{normalized}'. "
                    f"Allowed paths for this repo are: {allowed_paths}"
                )
            
            # Directory traversal prevention
            target = (base_dir / normalized).resolve()
            if not str(target).startswith(str(base_dir)):
                raise PathViolationError(f"[SECURITY VIOLATION] Directory traversal detected: '{rel_path}'")

        # Write Pass: Persist safely to disk
        for rel_path, content in files.items():
            target = base_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print(f"    [+] Safely updated: {rel_path}")
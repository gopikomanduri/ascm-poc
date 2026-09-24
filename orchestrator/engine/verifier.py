import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

class VerificationResult(BaseModel):
    tests_passed: bool
    test_output: str = ""
    vet_passed: bool = True
    vet_output: str = ""
    language: str = "go"
    sandboxed: bool = False

    @property
    def passed(self) -> bool:
        return self.tests_passed and self.vet_passed

    def error_summary(self) -> str:
        parts = []
        if not self.tests_passed and self.test_output:
            parts.append(f"=== Test Failure Output ({self.language}) ===\n{self.test_output.strip()}")
        if not self.vet_passed and self.vet_output:
            parts.append(f"=== Static Analysis / Lint Failure Output ({self.language}) ===\n{self.vet_output.strip()}")
        return "\n\n".join(parts) if parts else "Verification failed without specific error log."

class VerifierEngine:
    @staticmethod
    def detect_language(repo_path: str) -> str:
        repo = Path(repo_path)
        if (repo / "go.mod").exists() or list(repo.glob("*.go")):
            return "go"
        if (repo / "package.json").exists():
            return "node"
        if (repo / "pyproject.toml").exists() or (repo / "requirements.txt").exists():
            return "python"
        return "generic"

    @staticmethod
    def is_docker_sandboxing_enabled() -> bool:
        flag = os.environ.get("USE_DOCKER_SANDBOX", "").lower().strip()
        return flag in ("true", "1", "yes") and shutil.which("docker") is not None

    @staticmethod
    def _execute(
        cmd: List[str],
        repo_path: str,
        docker_image: Optional[str] = None,
    ) -> tuple[subprocess.CompletedProcess, bool]:
        """
        Executes a command either in a sandboxed Docker container (if enabled and available)
        or natively on the host system. Returns (CompletedProcess, is_sandboxed).
        """
        sandboxed = False
        final_cmd = cmd
        abs_repo = str(Path(repo_path).resolve())

        if VerifierEngine.is_docker_sandboxing_enabled() and docker_image:
            final_cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "-v", f"{abs_repo}:/workspace",
                "-w", "/workspace",
                docker_image,
                *cmd
            ]
            sandboxed = True

        result = subprocess.run(
            final_cmd,
            cwd=repo_path if not sandboxed else None,
            capture_output=True,
            text=True,
        )
        return result, sandboxed

    @staticmethod
    def run_checks(repo_path: str) -> VerificationResult:
        lang = VerifierEngine.detect_language(repo_path)
        if lang == "go":
            return VerifierEngine.run_go_checks(repo_path)
        elif lang == "python":
            return VerifierEngine.run_python_checks(repo_path)
        elif lang == "node":
            return VerifierEngine.run_node_checks(repo_path)
        else:
            return VerifierEngine.run_go_checks(repo_path)

    @staticmethod
    def run_go_checks(repo_path: str) -> VerificationResult:
        sandboxed_enabled = VerifierEngine.is_docker_sandboxing_enabled()
        if not sandboxed_enabled and not shutil.which("go"):
            return VerificationResult(
                tests_passed=False,
                test_output="Go executable not found on system PATH",
                vet_passed=False,
                vet_output="Go executable not found",
                language="go",
                sandboxed=False,
            )

        docker_img = "golang:1.22-alpine"
        test_run, is_sandboxed = VerifierEngine._execute(["go", "test", "-v", "./..."], repo_path, docker_img)
        vet_run, _ = VerifierEngine._execute(["go", "vet", "./..."], repo_path, docker_img)

        return VerificationResult(
            tests_passed=(test_run.returncode == 0),
            test_output=test_run.stdout or test_run.stderr,
            vet_passed=(vet_run.returncode == 0),
            vet_output=vet_run.stderr,
            language="go",
            sandboxed=is_sandboxed,
        )

    @staticmethod
    def run_python_checks(repo_path: str) -> VerificationResult:
        docker_img = "python:3.11-alpine"
        python_bin = shutil.which("python3") or shutil.which("python") or "python"
        cmd = [python_bin, "-m", "unittest", "discover", "-s", ".", "-v"]
        test_run, is_sandboxed = VerifierEngine._execute(cmd, repo_path, docker_img)

        return VerificationResult(
            tests_passed=(test_run.returncode == 0),
            test_output=test_run.stdout or test_run.stderr,
            vet_passed=True,
            vet_output="",
            language="python",
            sandboxed=is_sandboxed,
        )

    @staticmethod
    def run_node_checks(repo_path: str) -> VerificationResult:
        docker_img = "node:20-alpine"
        npm_bin = shutil.which("npm") or "npm"
        cmd = [npm_bin, "test", "--", "--passWithNoTests"]
        test_run, is_sandboxed = VerifierEngine._execute(cmd, repo_path, docker_img)

        return VerificationResult(
            tests_passed=(test_run.returncode == 0),
            test_output=test_run.stdout or test_run.stderr,
            vet_passed=True,
            vet_output="",
            language="node",
            sandboxed=is_sandboxed,
        )
import shutil
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field

class VerificationResult(BaseModel):
    tests_passed: bool
    test_output: str = ""
    vet_passed: bool = True
    vet_output: str = ""
    language: str = "go"

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
        if not shutil.which("go"):
            return VerificationResult(
                tests_passed=False,
                test_output="Go executable not found on system PATH",
                vet_passed=False,
                vet_output="Go executable not found",
                language="go",
            )
        # 1. Run native Go unit tests
        test_run = subprocess.run(
            ["go", "test", "-v", "./..."],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        # 2. Run static analysis via go vet
        vet_run = subprocess.run(
            ["go", "vet", "./..."],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        return VerificationResult(
            tests_passed=(test_run.returncode == 0),
            test_output=test_run.stdout or test_run.stderr,
            vet_passed=(vet_run.returncode == 0),
            vet_output=vet_run.stderr,
            language="go",
        )

    @staticmethod
    def run_python_checks(repo_path: str) -> VerificationResult:
        python_bin = shutil.which("python3") or shutil.which("python") or "python"
        test_run = subprocess.run(
            [python_bin, "-m", "unittest", "discover", "-s", ".", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return VerificationResult(
            tests_passed=(test_run.returncode == 0),
            test_output=test_run.stdout or test_run.stderr,
            vet_passed=True,
            vet_output="",
            language="python",
        )

    @staticmethod
    def run_node_checks(repo_path: str) -> VerificationResult:
        npm_bin = shutil.which("npm") or "npm"
        test_run = subprocess.run(
            [npm_bin, "test", "--", "--passWithNoTests"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return VerificationResult(
            tests_passed=(test_run.returncode == 0),
            test_output=test_run.stdout or test_run.stderr,
            vet_passed=True,
            vet_output="",
            language="node",
        )
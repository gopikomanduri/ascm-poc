import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class VerificationResult(BaseModel):
    tests_passed: bool
    test_output: str = ""
    vet_passed: bool = True
    vet_output: str = ""
    language: str = "go"
    sandboxed: bool = False
    framework: str = ""
    total_tests: int = 0
    passed_count: int = 0
    failed_count: int = 0
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)

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
    def parse_test_suite(output: str, language: str = "generic", tests_passed: bool = True) -> Dict[str, Any]:
        # Handle swapped arguments gracefully if called as parse_test_suite("go", output)
        known_langs = ("go", "python", "node", "generic")
        if output.lower() in known_langs and language not in known_langs:
            output, language = language, output

        cases: List[Dict[str, Any]] = []
        framework = ""
        lang = (language or "").lower()
        
        if lang == "go":
            framework = "testify / go test"
            for m in re.finditer(r"---\s+(PASS|FAIL|SKIP):\s+([^\s]+)\s+\(([^)]+)\)", output):
                st = m.group(1).upper()
                cases.append({
                    "name": m.group(2),
                    "status": "PASS" if st == "PASS" else ("FAIL" if st == "FAIL" else "SKIP"),
                    "duration": m.group(3),
                })
        elif lang == "python":
            # Check for pytest format first
            pytest_matches = list(re.finditer(r"([^\s]+::[^\s]+)\s+(PASSED|FAILED|SKIPPED)", output))
            if pytest_matches:
                framework = "pytest"
                for m in pytest_matches:
                    st = m.group(2).upper()
                    cases.append({
                        "name": m.group(1),
                        "status": "PASS" if st == "PASSED" else ("FAIL" if st == "FAILED" else "SKIP"),
                        "duration": "",
                    })
            else:
                framework = "unittest"
                for m in re.finditer(r"([a-zA-Z0-9_]+)\s+\(([^)]+)\)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)", output):
                    st = m.group(3).lower()
                    cases.append({
                        "name": f"{m.group(2)}.{m.group(1)}",
                        "status": "PASS" if st == "ok" else ("SKIP" if st == "skipped" else "FAIL"),
                        "duration": "",
                    })
        elif lang == "node":
            framework = "jest"
            for m in re.finditer(r"(✓|✕)\s+([^\n\r(]+)(?:\s+\(([^)]+)\))?", output):
                cases.append({
                    "name": m.group(2).strip(),
                    "status": "PASS" if m.group(1) == "✓" else "FAIL",
                    "duration": m.group(3) or "",
                })

        passed_count = sum(1 for c in cases if c["status"] == "PASS")
        failed_count = sum(1 for c in cases if c["status"] == "FAIL")
        total = len(cases)

        if total == 0:
            total = 1
            passed_count = 1 if tests_passed else 0
            failed_count = 0 if tests_passed else 1
            cases.append({
                "name": f"{lang.capitalize()}TestSuite",
                "status": "PASS" if tests_passed else "FAIL",
                "duration": "completed",
            })

        return {
            "framework": framework or ("testify / go test" if lang == "go" else "pytest / unittest" if lang == "python" else "jest / npm test"),
            "total_tests": total,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "test_cases": cases,
        }

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
                framework="go test",
            )

        docker_img = "golang:1.22-alpine"
        test_run, is_sandboxed = VerifierEngine._execute(["go", "test", "-v", "./..."], repo_path, docker_img)
        vet_run, _ = VerifierEngine._execute(["go", "vet", "./..."], repo_path, docker_img)
        output = test_run.stdout or test_run.stderr
        passed = (test_run.returncode == 0)
        parsed = VerifierEngine.parse_test_suite(output, "go", passed)

        return VerificationResult(
            tests_passed=passed,
            test_output=output,
            vet_passed=(vet_run.returncode == 0),
            vet_output=vet_run.stderr,
            language="go",
            sandboxed=is_sandboxed,
            framework=parsed["framework"],
            total_tests=parsed["total_tests"],
            passed_count=parsed["passed_count"],
            failed_count=parsed["failed_count"],
            test_cases=parsed["test_cases"],
        )

    @staticmethod
    def run_python_checks(repo_path: str) -> VerificationResult:
        docker_img = "python:3.11-alpine"
        python_bin = shutil.which("python3") or shutil.which("python") or "python"
        cmd = [python_bin, "-m", "unittest", "discover", "-s", ".", "-v"]
        test_run, is_sandboxed = VerifierEngine._execute(cmd, repo_path, docker_img)
        output = test_run.stdout or test_run.stderr
        passed = (test_run.returncode == 0)
        parsed = VerifierEngine.parse_test_suite(output, "python", passed)

        return VerificationResult(
            tests_passed=passed,
            test_output=output,
            vet_passed=True,
            vet_output="",
            language="python",
            sandboxed=is_sandboxed,
            framework=parsed["framework"],
            total_tests=parsed["total_tests"],
            passed_count=parsed["passed_count"],
            failed_count=parsed["failed_count"],
            test_cases=parsed["test_cases"],
        )

    @staticmethod
    def run_node_checks(repo_path: str) -> VerificationResult:
        docker_img = "node:20-alpine"
        npm_bin = shutil.which("npm") or "npm"
        cmd = [npm_bin, "test", "--", "--passWithNoTests"]
        test_run, is_sandboxed = VerifierEngine._execute(cmd, repo_path, docker_img)
        output = test_run.stdout or test_run.stderr
        passed = (test_run.returncode == 0)
        parsed = VerifierEngine.parse_test_suite(output, "node", passed)

        return VerificationResult(
            tests_passed=passed,
            test_output=output,
            vet_passed=True,
            vet_output="",
            language="node",
            sandboxed=is_sandboxed,
            framework=parsed["framework"],
            total_tests=parsed["total_tests"],
            passed_count=parsed["passed_count"],
            failed_count=parsed["failed_count"],
            test_cases=parsed["test_cases"],
        )
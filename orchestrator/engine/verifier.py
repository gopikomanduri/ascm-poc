import subprocess
from pydantic import BaseModel

class VerificationResult(BaseModel):
    tests_passed: bool
    test_output: str
    vet_passed: bool
    vet_output: str

class VerifierEngine:
    @staticmethod
    def run_go_checks(repo_path: str) -> VerificationResult:
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
            vet_output=vet_run.stderr
        )
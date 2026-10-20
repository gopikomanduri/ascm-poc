import subprocess
import sys
from pathlib import Path


def test_daemon_direct_script_entrypoint_imports_from_unrelated_working_directory(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    daemon_script = repo_root / "orchestrator" / "mentor" / "daemon.py"
    result = subprocess.run(
        [sys.executable, str(daemon_script), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--repo" in result.stdout
    assert "ModuleNotFoundError: No module named 'orchestrator'" not in result.stderr

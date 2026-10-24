import json
import os
import subprocess
from pathlib import Path

import orchestrator.controlled_self_healer as controlled
from orchestrator.controlled_self_healer import (
    _claim_attempt,
    _ledger,
    build_repair_context,
    route_owner,
    run_controlled_repair,
    validate_patch,
)


def test_patch_validator_requires_scoped_paths_and_regression_test():
    safe = """diff --git a/orchestrator/example.py b/orchestrator/example.py
index 1111111..2222222 100644
--- a/orchestrator/example.py
+++ b/orchestrator/example.py
@@ -1 +1 @@
-old = 1
+new = 2
diff --git a/tests/test_example.py b/tests/test_example.py
index 1111111..2222222 100644
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1 +1 @@
-assert True
+assert 2 == 2
"""
    ok, reason, paths = validate_patch(safe)
    assert ok, reason
    assert "tests/test_example.py" in paths


def test_patch_validator_rejects_contract_and_ci_changes():
    protected = """diff --git a/docs/ASCM_INTENT_CONTRACT.md b/docs/ASCM_INTENT_CONTRACT.md
index 1111111..2222222 100644
--- a/docs/ASCM_INTENT_CONTRACT.md
+++ b/docs/ASCM_INTENT_CONTRACT.md
@@ -1 +1 @@
-approved intent
-weakened intent
diff --git a/tests/test_example.py b/tests/test_example.py
index 1111111..2222222 100644
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1 +1 @@
-assert True
+assert True
"""
    ok, reason, _ = validate_patch(protected)
    assert not ok
    assert "protected" in reason


def test_patch_validator_requires_regression_test():
    patch = """diff --git a/orchestrator/example.py b/orchestrator/example.py
index 1111111..2222222 100644
--- a/orchestrator/example.py
+++ b/orchestrator/example.py
@@ -1 +1 @@
-old = 1
+new = 2
"""
    ok, reason, _ = validate_patch(patch)
    assert not ok
    assert "regression test" in reason


def test_repair_agent_routing_is_explicit_and_configurable(monkeypatch):
    monkeypatch.setenv("ASCM_REPAIR_AGENT_PRODUCT", "product-reviewer")
    monkeypatch.setenv("ASCM_REPAIR_AGENT_ID", "fallback")
    assert route_owner("product") == "product-reviewer"
    assert route_owner("orchestrator") == "fallback"
    monkeypatch.delenv("ASCM_REPAIR_AGENT_ID")
    monkeypatch.delenv("ASCM_REPAIR_AGENT_ORCHESTRATOR", raising=False)
    monkeypatch.delenv("ASCM_REPAIR_AGENT_PRODUCT", raising=False)
    assert route_owner("orchestrator") == "coder"
    assert route_owner("product") == "product"
    assert route_owner("mentor") == "mentor"
    assert route_owner("governance") == "security_auditor"


def test_repair_blocks_p0_and_records_audit_without_calling_provider(tmp_path):
    called = []
    result = run_controlled_repair(
        tmp_path,
        {"invariant_id": "consent", "severity": "P0", "message": "unapproved external action"},
        lambda finding, context: called.append(True) or "",
        acceptance_command="python -m orchestrator.testing_agent.runtime",
    )
    assert result["status"] == "blocked"
    assert "P0" in result["reason"]
    assert called == []
    events = [json.loads(line) for line in (tmp_path / ".ascm_history" / "controlled_self_healing.jsonl").read_text().splitlines()]
    assert events[-1]["finding_id"] == "consent"


def test_repair_refuses_dirty_active_checkout_before_agent_dispatch(tmp_path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ascm-test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ASCM Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("uncommitted change\n", encoding="utf-8")
    monkeypatch.setenv("ASCM_REPAIR_AGENT_ID", "engineering")
    called = []
    result = run_controlled_repair(
        tmp_path,
        {"invariant_id": "unit-test-failure", "severity": "P1", "message": "failure", "remediation_owner": "orchestrator"},
        lambda finding, context: called.append(True) or "",
        acceptance_command="python -m orchestrator.testing_agent.runtime",
    )
    assert result["status"] == "blocked"
    assert "dirty" in result["reason"]
    assert called == []


def test_repair_allows_untracked_diagnostics_and_preserves_them(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ascm-test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ASCM Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("baseline\\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True)

    diagnostics = {
        "ascm_test_results.txt": "test evidence\\n",
        "daemon_local_backup.patch": "backup patch\\n",
        "orchestrator/mentor/daemon copy.py.bak.py": "backup source\\n",
    }
    for relative, value in diagnostics.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    calls = []

    def invalid_proposal(finding, context):
        calls.append(finding["repair_attempt"])
        return "not a unified diff"

    result = run_controlled_repair(
        tmp_path,
        {
            "invariant_id": "untracked-diagnostics",
            "severity": "P1",
            "message": "Exercise isolated repair with untracked files",
            "remediation_owner": "orchestrator",
            "evidence": ["repro: untracked diagnostics should not block worktree creation"],
        },
        invalid_proposal,
        acceptance_command="python -m orchestrator.testing_agent.runtime --sessions 1",
    )

    assert result["status"] == "repair_exhausted"
    assert "dirty" not in result.get("reason", "").lower()
    assert calls == [1, 2, 3]
    for relative, expected in diagnostics.items():
        assert (tmp_path / relative).read_text(encoding="utf-8") == expected


def test_repair_refuses_non_git_workspace(tmp_path):
    result = run_controlled_repair(
        tmp_path,
        {"invariant_id": "missing-git-workspace", "severity": "P1", "message": "failure"},
        lambda finding, context: "",
    )
    assert result["status"] == "blocked"
    assert "not a usable Git checkout" in result["reason"]


def test_repair_context_excludes_protected_contract_from_agent_input(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ASCM_INTENT_CONTRACT.md").write_text("DO NOT MUTATE", encoding="utf-8")
    (tmp_path / "orchestrator").mkdir()
    (tmp_path / "orchestrator" / "intent_guardian.py").write_text("safe source", encoding="utf-8")
    context = build_repair_context(tmp_path, {"remediation_owner": "orchestrator", "message": "failure"})
    assert "safe source" in context
    assert "DO NOT MUTATE" not in context


def test_patch_validator_bounds_patch_size_and_rejects_file_deletion():
    huge = "diff --git a/tests/test_x.py b/tests/test_x.py\n--- a/tests/test_x.py\n+++ b/tests/test_x.py\n@@ -1 +1 @@\n" + ("x" * 31000)
    ok, reason, _ = validate_patch(huge)
    assert not ok
    assert "30 KB" in reason

    deletion = """diff --git a/tests/test_x.py b/tests/test_x.py
index 1111111..2222222 100644
--- a/tests/test_x.py
+++ /dev/null
@@ -1 +0,0 @@
-assert True
"""
    ok, reason, _ = validate_patch(deletion)
    assert not ok
    assert "deletions" in reason



def test_github_ci_gate_requires_success_before_pr(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, cwd, *, timeout=900, env=None):
        calls.append(args)
        if args[1:3] == ["workflow", "run"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(
            args, 0,
            json.dumps([{"headSha": "abc123", "status": "completed", "conclusion": "success", "databaseId": 42}]),
            "",
        )

    monkeypatch.setattr(controlled, "_run", fake_run)
    passed, detail = controlled._wait_for_github_ci("gh", "ascm/repair-test", "abc123", tmp_path, timeout=1)
    assert passed is True
    assert len(calls) == 2
    assert "success" in detail


def test_github_ci_gate_blocks_pr_when_workflow_fails(monkeypatch, tmp_path):
    def fake_run(args, cwd, *, timeout=900, env=None):
        if args[1:3] == ["workflow", "run"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(
            args, 0,
            json.dumps([{"headSha": "abc123", "status": "completed", "conclusion": "failure", "databaseId": 43}]),
            "",
        )

    monkeypatch.setattr(controlled, "_run", fake_run)
    passed, detail = controlled._wait_for_github_ci("gh", "ascm/repair-test", "abc123", tmp_path, timeout=1)
    assert passed is False
    assert "failure" in detail



def test_corrupt_retry_ledger_fails_closed(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    ledger = _ledger(tmp_path) / "ascm-controlled-repair-attempts.json"
    ledger.write_text("{not-json", encoding="utf-8")
    assert _claim_attempt(tmp_path, "finding-123") is False


def test_repair_ledger_allows_one_bounded_session_per_finding(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    key = "finding-bounded"
    assert _claim_attempt(tmp_path, key) is True
    # The repair session itself owns the three verifier-driven proposals.
    # A duplicate assessment must not start a second session for the same finding.
    assert _claim_attempt(tmp_path, key) is False



def test_repair_loop_retries_with_feedback_up_to_three_attempts(tmp_path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ascm-test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ASCM Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True)
    calls = []

    def invalid_proposal(finding, context):
        calls.append((finding["repair_attempt"], context))
        return "not a unified diff"

    result = run_controlled_repair(
        tmp_path,
        {
            "invariant_id": "broken-journey",
            "severity": "P1",
            "message": "Goal Agent event missing",
            "remediation_owner": "orchestrator",
            "evidence": ["repro: missing goal event"],
        },
        invalid_proposal,
        acceptance_command="python -m orchestrator.testing_agent.runtime --sessions 1",
    )

    assert result["status"] == "repair_exhausted"
    assert len(calls) == 3
    assert [call[0] for call in calls] == [1, 2, 3]
    assert "Previous repair attempts failed verification" in calls[1][1]
    assert len(result["attempts"]) == 3
    assert all(attempt["status"] == "failed" for attempt in result["attempts"])

import json
import os
import subprocess
from pathlib import Path

from orchestrator.controlled_self_healer import (
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
    assert route_owner("orchestrator") == "coder"


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


def test_repair_requires_fresh_acceptance_command(tmp_path):
    result = run_controlled_repair(
        tmp_path,
        {"invariant_id": "missing-acceptance", "severity": "P1", "message": "failure"},
        lambda finding, context: "",
        acceptance_command=None,
    )
    assert result["status"] == "blocked"
    assert "ASCM_REPAIR_ACCEPTANCE_COMMAND" in result["reason"]


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

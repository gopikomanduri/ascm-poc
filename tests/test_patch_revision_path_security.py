"""Regression tests for safe original-file context during rejected patch revisions."""
from pathlib import Path

import pytest

from orchestrator.orchestrator_core import OrchestratorEngine


def test_revision_context_skips_path_traversal_and_reads_safe_repo_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "safe.py").write_text("safe repository content", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("OUTSIDE SECRET CONTENT", encoding="utf-8")

    context = OrchestratorEngine._revision_original_context(
        str(repo),
        {
            "../../outside.txt": "attacker-controlled patch",
            "safe.py": "changed content",
        },
    )

    assert "safe repository content" in context
    assert "OUTSIDE SECRET CONTENT" not in context
    assert "../../outside.txt" not in context


def test_revision_context_skips_absolute_paths(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("ABSOLUTE SECRET", encoding="utf-8")

    context = OrchestratorEngine._revision_original_context(
        str(repo),
        {str(outside): "attacker-controlled patch"},
    )

    assert context == ""
    assert "ABSOLUTE SECRET" not in context


def test_revision_context_skips_symlinks_to_outside_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("SYMLINK SECRET", encoding="utf-8")
    link = repo / "linked.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks are unavailable in this environment: {exc}")

    context = OrchestratorEngine._revision_original_context(
        str(repo),
        {"linked.txt": "attacker-controlled patch"},
    )

    assert context == ""
    assert "SYMLINK SECRET" not in context


def test_revision_context_skips_symlinked_parent_directories(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    (outside_dir / "secret.py").write_text("PARENT SYMLINK SECRET", encoding="utf-8")
    try:
        (repo / "linked-dir").symlink_to(outside_dir, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks are unavailable in this environment: {exc}")

    context = OrchestratorEngine._revision_original_context(
        str(repo),
        {"linked-dir/secret.py": "attacker-controlled patch"},
    )

    assert context == ""
    assert "PARENT SYMLINK SECRET" not in context

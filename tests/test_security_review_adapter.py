"""Regression tests for the Gemini-backed structured security reviewer."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

import pytest

from orchestrator.security import security_review_adapter as adapter


def _request():
    return {
        "version": 1,
        "repo": "/tmp/repo",
        "source": {
            "kind": "repository",
            "scope": {"type": "branch", "base": "origin/main", "head": "HEAD"},
        },
        "options": {"trustRepositoryConfig": False},
    }


def test_missing_gemini_key_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(adapter.ReviewError, match="GEMINI_API_KEY"):
        adapter.review_request(_request(), tmp_path)


def test_review_returns_structured_envelope_for_empty_diff(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch.object(adapter, "_git_diff", return_value=""):
        result = adapter.review_request(_request(), tmp_path)
    assert result == {"ok": True, "operation": "review", "data": {"findings": []}}


def test_oversized_review_is_batched_by_changed_path(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = []

    def fake_diff(repo_root, base, head, paths=None):
        if paths is None:
            raise adapter.ReviewError("Diff exceeds the 60000-character review limit; split the change.")
        if len(paths) > 1:
            raise adapter.ReviewError("Diff exceeds the 60000-character review limit; split the change.")
        return "diff for " + paths[0]

    with (
        patch.object(adapter, "_git_diff", side_effect=fake_diff),
        patch.object(adapter, "_changed_paths", return_value=["a.py", "b.py", "c.py"]),
        patch.object(adapter, "_request_review", side_effect=lambda diff, key, model: (
            calls.append(diff) or {"findings": []}
        )),
    ):
        result = adapter.review_request(_request(), tmp_path)

    assert result == {"ok": True, "operation": "review", "data": {"findings": []}}
    assert calls == ["diff for a.py", "diff for b.py", "diff for c.py"]


def test_review_normalizes_valid_findings(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    finding = {
        "severity": 8,
        "category": "injection",
        "title": "Unsafe command construction",
        "summary": "Untrusted input reaches a command.",
        "filePath": "src/example.py",
    }
    with (
        patch.object(adapter, "_git_diff", return_value="diff --git ..."),
        patch.object(adapter, "_request_review", return_value={"findings": [finding]}),
    ):
        result = adapter.review_request(_request(), tmp_path)
    assert result["ok"] is True
    assert result["operation"] == "review"
    assert result["data"]["findings"][0]["severity"] == 8
    assert result["data"]["findings"][0]["filePath"] == "src/example.py"


@pytest.mark.parametrize("severity", [0, 11, True, "high", None])
def test_invalid_finding_severity_is_rejected(severity):
    with pytest.raises(adapter.ReviewError, match="severity"):
        adapter._normalize_findings({"findings": [{"severity": severity}]})


@pytest.mark.parametrize("payload", [None, [], {}, {"findings": "not-a-list"}])
def test_malformed_model_payload_is_rejected(payload):
    with pytest.raises(adapter.ReviewError, match="findings"):
        adapter._normalize_findings(payload)


def test_git_refs_cannot_be_passed_as_options(tmp_path):
    with pytest.raises(adapter.ReviewError, match="invalid Git ref"):
        adapter._git_diff(tmp_path, "--upload-pack=malicious", "HEAD")


def test_explicit_gemini_key_wins_over_google_api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "wrong-provider-key")
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text='{"findings": []}')

    def fake_client(*, api_key, http_options=None):
        captured["api_key"] = api_key
        captured["http_options"] = http_options
        return SimpleNamespace(models=FakeModels())

    fake_genai = SimpleNamespace(Client=fake_client)
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    result = adapter._request_review("diff --git ...", "intended-gemini-key", "gemini-3.8-flash")

    assert result == {"findings": []}
    assert captured["api_key"] == "intended-gemini-key"
    assert captured["http_options"] == {"timeout": 45_000}
    assert "GOOGLE_API_KEY" not in __import__("os").environ



def test_provider_error_includes_sanitized_status(monkeypatch):
    class FakeClientError(Exception):
        code = 429
        message = "quota exceeded for request"

    class FakeModels:
        def generate_content(self, **kwargs):
            raise FakeClientError("quota exceeded for request")

    fake_genai = SimpleNamespace(Client=lambda **kwargs: SimpleNamespace(models=FakeModels()))
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    with pytest.raises(adapter.ReviewError, match=r"status=429.*quota exceeded"):
        adapter._request_review("diff --git ...", "test-secret-key", "gemini-3.8-flash")


def test_model_failure_does_not_expose_provider_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with (
        patch.object(adapter, "_git_diff", return_value="diff --git ..."),
        patch.object(adapter, "_request_review", side_effect=adapter.ReviewError("provider failed safely")),
    ):
        with pytest.raises(adapter.ReviewError, match="provider failed safely"):
            adapter.review_request(_request(), tmp_path)



def test_empty_primary_response_retries_with_configured_fallback_model(monkeypatch):
    monkeypatch.setenv("ASCM_SECURITY_REVIEW_FALLBACK_MODEL", "gemini-3.6-flash")
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs["model"])
            if kwargs["model"] == "gemini-3.8-flash":
                return SimpleNamespace(
                    text="",
                    candidates=[SimpleNamespace(finish_reason="MAX_TOKENS", content=SimpleNamespace(parts=[]))],
                    prompt_feedback=SimpleNamespace(block_reason=None),
                )
            return SimpleNamespace(text='{"findings": []}')

    fake_genai = SimpleNamespace(Client=lambda **kwargs: SimpleNamespace(models=FakeModels()))
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    result = adapter._request_review("diff --git ...", "test-key", "gemini-3.8-flash")

    assert result == {"findings": []}
    assert calls == ["gemini-3.8-flash", "gemini-3.6-flash"]


def test_empty_primary_and_fallback_responses_still_fail_closed(monkeypatch):
    monkeypatch.setenv("ASCM_SECURITY_REVIEW_FALLBACK_MODEL", "gemini-3.6-flash")

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text="",
                candidates=[SimpleNamespace(finish_reason="SAFETY", content=SimpleNamespace(parts=[]))],
                prompt_feedback=SimpleNamespace(block_reason="SAFETY"),
            )

    fake_genai = SimpleNamespace(Client=lambda **kwargs: SimpleNamespace(models=FakeModels()))
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    with pytest.raises(adapter.ReviewError, match=r"empty response.*finish_reason=SAFETY.*block_reason=SAFETY"):
        adapter._request_review("diff --git ...", "test-key", "gemini-3.8-flash")


def test_response_text_can_be_extracted_from_candidate_parts():
    response = SimpleNamespace(
        text="",
        candidates=[SimpleNamespace(
            finish_reason="STOP",
            content=SimpleNamespace(parts=[SimpleNamespace(text='{"findings": []}')]),
        )],
    )
    text, diagnostic = adapter._response_text(response)
    assert text == '{"findings": []}'
    assert diagnostic == ""


def test_transient_primary_provider_error_retries_with_fallback_model(monkeypatch):
    monkeypatch.setenv("ASCM_SECURITY_REVIEW_FALLBACK_MODEL", "gemini-3.6-flash")
    calls = []

    class FakeServerError(Exception):
        code = 504
        message = "Deadline expired before operation could complete."

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs["model"])
            if kwargs["model"] == "gemini-3.8-flash":
                raise FakeServerError("Deadline expired before operation could complete.")
            return SimpleNamespace(text='{"findings": []}')

    fake_genai = SimpleNamespace(Client=lambda **kwargs: SimpleNamespace(models=FakeModels()))
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    result = adapter._request_review("diff --git ...", "test-key", "gemini-3.8-flash")

    assert result == {"findings": []}
    assert calls == ["gemini-3.8-flash", "gemini-3.6-flash"]


def test_oversized_single_file_is_reviewed_in_hunk_bounded_chunks(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    # Each hunk is individually below the provider limit, while the whole file diff is not.
    diff = (
        "diff --git a/large.py b/large.py\n"
        "index 1111111..2222222 100644\n"
        "--- a/large.py\n"
        "+++ b/large.py\n"
        "@@ -1 +1 @@\n+" + ("a" * 11_000) + "\n"
        "@@ -2 +2 @@\n+" + ("b" * 11_000) + "\n"
    )
    reviewed = []

    with (
        patch.object(adapter, "_raw_git_diff", return_value=diff),
        patch.object(adapter, "_request_review", side_effect=lambda chunk, key, model: (
            reviewed.append(chunk) or {"findings": []}
        )),
    ):
        result = adapter._review_oversized_path(
            tmp_path, "origin/main", "HEAD", "large.py", "test-key", "gemini-3.8-flash"
        )

    assert result == []
    assert len(reviewed) == 2
    assert all(len(chunk) <= adapter.MAX_DIFF_CHARS for chunk in reviewed)
    assert all("diff --git a/large.py b/large.py" in chunk for chunk in reviewed)
    assert any("a" * 100 in chunk for chunk in reviewed)
    assert any("b" * 100 in chunk for chunk in reviewed)


def test_oversized_hunk_fails_closed_instead_of_being_skipped():
    diff = (
        "diff --git a/large.py b/large.py\n"
        "--- a/large.py\n+++ b/large.py\n"
        "@@ -1 +1 @@\n+" + ("x" * (adapter.MAX_DIFF_CHARS + 1)) + "\n"
    )
    with pytest.raises(adapter.ReviewError, match="single changed hunk exceeds"):
        adapter._split_diff_into_chunks(diff)


def test_split_diff_preserves_all_hunks_and_file_headers():
    header = "diff --git a/example.py b/example.py\n--- a/example.py\n+++ b/example.py\n"
    diff = header + (
        "@@ -1 +1 @@\n+first change\n"
        "@@ -10 +10 @@\n+second change\n"
        "@@ -20 +20 @@\n+third change\n"
    )
    chunks = adapter._split_diff_into_chunks(diff, max_chars=len(header) + 35)

    assert len(chunks) > 1
    assert all(chunk.startswith(header) for chunk in chunks)
    assert sum(chunk.count("@@ -") for chunk in chunks) == 3
    assert all(len(chunk) <= len(header) + 35 for chunk in chunks)

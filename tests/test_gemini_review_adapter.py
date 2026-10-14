"""Regression tests for the Gemini-backed structured security reviewer."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

import pytest

from orchestrator.security import gemini_review_adapter as adapter


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


def test_review_returns_cico_compatible_envelope_for_empty_diff(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch.object(adapter, "_git_diff", return_value=""):
        result = adapter.review_request(_request(), tmp_path)
    assert result == {"ok": True, "operation": "review", "data": {"findings": []}}


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

    def fake_client(*, api_key):
        captured["api_key"] = api_key
        return SimpleNamespace(models=FakeModels())

    fake_genai = SimpleNamespace(Client=fake_client)
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    result = adapter._request_review("diff --git ...", "intended-gemini-key", "gemini-2.5-flash")

    assert result == {"findings": []}
    assert captured["api_key"] == "intended-gemini-key"
    assert "GOOGLE_API_KEY" not in __import__("os").environ


def test_model_failure_does_not_expose_provider_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with (
        patch.object(adapter, "_git_diff", return_value="diff --git ..."),
        patch.object(adapter, "_request_review", side_effect=adapter.ReviewError("provider failed safely")),
    ):
        with pytest.raises(adapter.ReviewError, match="provider failed safely"):
            adapter.review_request(_request(), tmp_path)

import pytest
from unittest.mock import patch, MagicMock
from orchestrator.gtm.channels.publish_to_channels import (
    _generate_posts,
    _smart_truncate,
    _copy_to_clipboard,
    main as publish_main,
)


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """The publisher writes .ascm_history/ (publish log + content history) relative to cwd; keep it out of the repo."""
    monkeypatch.chdir(tmp_path)


def test_smart_truncate():
    text = "Building autonomous multi-agent developer tooling that connects git with outbound sales."
    truncated = _smart_truncate(text, max_chars=35)
    assert len(truncated) <= 38  # including ellipsis
    assert not truncated.endswith("  ...")


def test_generate_posts_fallback():
    # Test generation returns linkedin and x_post keys
    res = _generate_posts("Automated cross-service tracing platform")
    assert "linkedin" in res
    assert "x_post" in res
    assert len(res["linkedin"]) > 50
    assert len(res["x_post"]) > 20


@patch("orchestrator.gtm.channels.publish_to_channels._open_url")
@patch("orchestrator.gtm.channels.publish_to_channels._copy_to_clipboard")
def test_publish_main_execution(mock_clip, mock_open):
    mock_clip.return_value = True
    mock_open.return_value = True

    posts = publish_main(
        goal="Test Autonomous Microservice Gateway",
        linkedin_only=True,
        interactive=False,
    )
    assert "linkedin" in posts
    assert mock_clip.called or mock_open.called

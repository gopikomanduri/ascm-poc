import pytest

from orchestrator.security.audit_logger import AUDIT_LOGGER
from orchestrator.security.pii_scrubber import PIIScrubber

SECRETS = [
    "sk_live_" + "a1B2c3D4e5F6g7H8i9J0",
    "whsec_" + "a1B2c3D4e5F6g7H8i9J0k1",
    "xoxb-" + "123456789012-abcdefghijkl",
    "github_pat_" + "11ABCDEFG0abcdefghijkl_mnopqrstuv",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r",
    "ASIA" + "ABCDEFGHIJKLMNOP",
    "Authorization: Basic dXNlcjpwYXNzd29yZDEyMzQ1Njc4",
    "postgres://admin:hunter2pass@db.internal/app",
    "ABCDE1234F",
    "2345 6789 0123",
    "+91 9876543210",
]


@pytest.mark.parametrize("secret", SECRETS)
def test_secret_is_scrubbed(secret):
    out = PIIScrubber.scrub(f"value is {secret} end")
    assert secret not in out and "REDACTED" in out


def test_key_value_secrets_in_json_and_text():
    assert "hunter2" not in PIIScrubber.scrub('{"password": "hunter2"}')
    assert "hunter2" not in PIIScrubber.scrub("password=hunter2")
    assert "hunter2" not in PIIScrubber.scrub("aws_secret_access_key = hunter2")


def test_ordinary_text_is_untouched():
    text = "Processed 500 tokens in 1700000000000 ms across 12 services"
    assert PIIScrubber.scrub(text) == text


def test_audit_log_masks_structured_secrets():
    rec = AUDIT_LOGGER.log_event("T", details={"password": "hunter2", "nested": {"api_key": "AIzaXXXX"}, "ok": "fine"})
    blob = str(rec)
    assert "hunter2" not in blob and "AIzaXXXX" not in blob and "fine" in blob

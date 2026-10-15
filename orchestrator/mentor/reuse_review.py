"""Founder-reviewed evidence for public repository reuse candidates.

Public repository metadata is never treated as proof of fit or safety. A candidate
becomes eligible for a reuse recommendation only after a founder records each
required review dimension against its canonical HTTPS repository URL.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def canonical_repository_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.query or parsed.fragment:
        raise ValueError("repository_url must be a canonical HTTPS GitHub repository URL")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2 or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        raise ValueError("repository_url must have the form https://github.com/owner/repository")
    return f"https://github.com/{parts[0]}/{parts[1].removesuffix('.git')}"


class ReuseReviewLedger:
    REQUIRED_FLAGS = (
        "feature_fit_verified",
        "license_compatible",
        "security_reviewed",
        "integration_cost_estimated",
    )

    def __init__(self, project_path: str | Path = "."):
        self.history = Path(project_path).expanduser().resolve() / ".ascm_history"
        self.path = self.history / "reuse_reviews.json"

    def _read(self) -> dict[str, dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def record(
        self, repository_url: str, *, feature_fit_verified: bool,
        license_compatible: bool, security_reviewed: bool,
        integration_cost_estimated: bool, reviewer: str = "founder",
    ) -> dict[str, Any]:
        url = canonical_repository_url(repository_url)
        flags = {
            "feature_fit_verified": feature_fit_verified,
            "license_compatible": license_compatible,
            "security_reviewed": security_reviewed,
            "integration_cost_estimated": integration_cost_estimated,
        }
        if any(not isinstance(value, bool) for value in flags.values()):
            raise ValueError("All review flags must be explicit booleans")
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer.strip()) > 80:
            raise ValueError("reviewer must be a short non-empty label")
        record = {
            "repository_url": url,
            **flags,
            "reviewer": reviewer.strip(),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_complete": all(flags.values()),
        }
        self.history.mkdir(parents=True, exist_ok=True)
        try:
            self.history.chmod(0o700)
        except OSError:
            pass
        records = self._read()
        records[url] = record
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        return record

    def get(self, repository_url: str) -> dict[str, Any] | None:
        return self._read().get(canonical_repository_url(repository_url))

    def all(self) -> dict[str, dict[str, Any]]:
        return self._read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record explicit founder review of a GitHub reuse candidate.")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--reviewer", default="founder")
    for flag in ReuseReviewLedger.REQUIRED_FLAGS:
        parser.add_argument("--" + flag.replace("_", "-"), choices=("yes", "no"), required=True)
    args = parser.parse_args(argv)
    ledger = ReuseReviewLedger(args.project_path)
    record = ledger.record(
        args.repository_url,
        reviewer=args.reviewer,
        **{flag: getattr(args, flag) == "yes" for flag in ReuseReviewLedger.REQUIRED_FLAGS},
    )
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Optional GitHub repository discovery for build-versus-integrate decisions.

Search results are candidates, not endorsements. Callers should review license,
maintenance, security, compatibility, and transitive dependencies before adoption.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from typing import Any, Dict, List


class GitHubRepositoryAdvisor:
    API_URL = "https://api.github.com/search/repositories"

    def __init__(self, token: str | None = None, timeout: float = 5.0):
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.timeout = timeout

    def search(self, task_description: str, limit: int = 5) -> Dict[str, Any]:
        """Search public repositories and return normalized candidates with caveats."""
        if not isinstance(task_description, str) or not task_description.strip():
            raise ValueError("task_description must be a non-empty string")
        if not 1 <= limit <= 10:
            raise ValueError("limit must be between 1 and 10")
        query = " ".join(task_description.strip().split())[:100]
        url = f"{self.API_URL}?q={quote(query + ' in:name,description,readme')}&sort=stars&order=desc&per_page={limit}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ASCM-Founder-Mentor",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - fixed HTTPS GitHub API endpoint
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return {
                "query": query,
                "repositories": [],
                "error": f"Repository discovery unavailable: {type(exc).__name__}",
                "caveat": "No repository recommendations were inferred because search failed.",
            }

        candidates: List[Dict[str, Any]] = []
        for item in payload.get("items", [])[:limit]:
            license_info = item.get("license") or {}
            candidates.append({
                "name": item.get("full_name"),
                "url": item.get("html_url"),
                "description": item.get("description"),
                "stars": item.get("stargazers_count", 0),
                "last_updated": item.get("pushed_at"),
                "archived": bool(item.get("archived", False)),
                "license": license_info.get("spdx_id") or license_info.get("name") or "Not detected",
                "default_branch": item.get("default_branch"),
            })
        return {
            "query": query,
            "repositories": candidates,
            "caveat": (
                "Search ranking is not a quality or security endorsement. Verify license compatibility, "
                "recent maintenance, open issues, security posture, dependencies, and API compatibility before integration."
            ),
        }

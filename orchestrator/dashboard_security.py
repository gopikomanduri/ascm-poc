"""Access control for the dashboard's HTTP API.

The dashboard has endpoints that launch agent runs, approve code changes and touch the filesystem, so it
must not be drivable by a web page the founder happens to visit (CSRF / DNS rebinding) or by other hosts.

Rules:
  * Host must be a loopback name (or listed in ASCM_ALLOWED_HOSTS), which defeats DNS rebinding.
  * A POST carrying an Origin / Sec-Fetch-Site header must be same-origin.
  * ASCM_DASHBOARD_TOKEN, when set, is required (X-ASCM-Token header or ascm_token cookie) on sensitive routes.
  * In hosted mode ($PORT set by a platform) sensitive routes are disabled unless a token is configured.
  * Public form endpoints (waitlist, demo) are rate limited per client address.
"""
from __future__ import annotations

import hmac
import os
import re
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
SENSITIVE_PREFIXES = ("/api/action/", "/api/auth/", "/api/product/", "/api/repos/", "/api/apps", "/api/forecast")
PUBLIC_POST_PATHS = {"/api/waitlist", "/api/demo/agent"}
MAX_BODY_BYTES = 1_000_000

_SECRET_KEY = re.compile(r"(api_?key|secret|password|access_token|auth_token)", re.I)


def is_hosted() -> bool:
    return bool(os.environ.get("PORT"))


def _host_only(host_header: str) -> str:
    host = (host_header or "").strip().lower()
    if host.startswith("["):  # [::1]:8080
        return host.split("]")[0] + "]"
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def _allowed_hosts() -> set:
    extra = {h.strip().lower() for h in os.environ.get("ASCM_ALLOWED_HOSTS", "").split(",") if h.strip()}
    return LOOPBACK_HOSTS | extra


def is_sensitive(path: str, method: str) -> bool:
    if method == "POST" and path in PUBLIC_POST_PATHS:
        return False
    if method == "POST":
        return True
    return path.startswith(SENSITIVE_PREFIXES)


def authorize(method: str, path: str, headers: Any, cookie_header: str = "") -> Optional[Tuple[int, str]]:
    """Return None when allowed, else (status, reason)."""
    hosted = is_hosted()
    host = _host_only(headers.get("Host", ""))
    if not hosted and host not in _allowed_hosts():
        return 403, "Host not allowed (DNS-rebinding protection). Set ASCM_ALLOWED_HOSTS to add hosts."

    if method == "POST":
        origin = headers.get("Origin")
        if origin and origin != "null":
            origin_host = urlparse(origin).netloc.lower()
            if origin_host != (headers.get("Host", "") or "").lower():
                return 403, "Cross-origin request blocked."
        elif origin == "null":
            return 403, "Cross-origin request blocked."
        fetch_site = headers.get("Sec-Fetch-Site")
        if fetch_site and fetch_site not in ("same-origin", "none"):
            return 403, "Cross-site request blocked."

    if is_sensitive(path, method):
        token = os.environ.get("ASCM_DASHBOARD_TOKEN", "")
        if hosted and not token:
            return 403, "This endpoint is disabled on hosted deployments (set ASCM_DASHBOARD_TOKEN to enable)."
        if token:
            supplied = headers.get("X-ASCM-Token", "")
            if not supplied:
                m = re.search(r"(?:^|;\s*)ascm_token=([^;]+)", cookie_header or "")
                supplied = m.group(1) if m else ""
            if not supplied or not hmac.compare_digest(supplied.encode(), token.encode()):
                return 401, "Missing or invalid dashboard token."
    return None


def redact_secrets(value: Any) -> Any:
    """Never send stored API keys / secrets back to the browser; report only whether they are set."""
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and _SECRET_KEY.search(k) and not isinstance(v, (dict, list)):
                out[f"{k}_set"] = bool(v)
            else:
                out[k] = redact_secrets(v)
        return out
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    return value


def allowed_workspace_roots() -> List[Path]:
    raw = os.environ.get("ASCM_WORKSPACE_ROOTS", "")
    roots = [Path(r).expanduser() for r in raw.split(os.pathsep) if r.strip()] or [Path.cwd()]
    return [r.resolve() for r in roots]


def confine_to_workspace(path_str: str) -> Optional[Path]:
    """Resolve a user-supplied repo path; return it only if it lies inside an allowed workspace root."""
    if not isinstance(path_str, str) or not path_str.strip():
        return None
    candidate = Path(path_str).expanduser().resolve()
    for root in allowed_workspace_roots():
        if candidate == root or candidate.is_relative_to(root):
            return candidate
    return None


class RateLimiter:
    def __init__(self, limit: int = 8, window_sec: float = 60.0):
        self.limit, self.window = limit, window_sec
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


PUBLIC_RATE_LIMITER = RateLimiter()

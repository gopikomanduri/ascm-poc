"""
GitHub OAuth Handler for ASCM
==============================
Replaces manual API key entry with "Connect GitHub" button flow.

Flow:
  1. User clicks "Connect GitHub" on onboarding page
  2. → GET /auth/github           → redirects to GitHub OAuth
  3. ← GET /auth/github/callback  ← GitHub redirects back with ?code=
  4. → exchanges code for token   → fetches user info + repo list
  5. → sets signed session cookie
  6. → redirects to /onboarding?github_connected=1

Setup (GitHub App or OAuth App):
  1. Go to github.com/settings/developers → OAuth Apps → New OAuth App
  2. Application name: ASCM
  3. Homepage URL: https://your-railway-url.railway.app
  4. Callback URL: https://your-railway-url.railway.app/auth/github/callback
  5. Copy Client ID and Client Secret into environment variables:
       GITHUB_CLIENT_ID=...
       GITHUB_CLIENT_SECRET=...
       ASCM_SECRET_KEY=<random 32-char string>  (for session signing)

Usage (called from DashboardServer._handle_request):
  handler = GitHubOAuthHandler(session_secret=os.environ["ASCM_SECRET_KEY"])
  if handler.handle(path, query_params, headers, send_response_fn):
      return  # request was handled
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional, Callable


# ── Config ─────────────────────────────────────────────────────────────────────

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL     = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE      = "https://api.github.com"
OAUTH_SCOPES         = "repo,read:user,user:email"


@dataclass
class GitHubUser:
    login: str
    name: str
    email: str
    avatar_url: str
    access_token: str
    repos: list  # list of {name, full_name, html_url, private, language}


# ── Simple signed session (no external deps, uses HMAC) ────────────────────────

class SignedSession:
    """
    Lightweight signed cookie session.
    No database — state is encoded in the cookie itself (like JWT but simpler).
    Signature: HMAC-SHA256(payload + timestamp, secret)
    """

    def __init__(self, secret: str, ttl_seconds: int = 86400 * 30):
        self._secret = secret.encode()
        self._ttl    = ttl_seconds

    def encode(self, data: dict) -> str:
        payload = json.dumps(data, separators=(",", ":"))
        ts      = str(int(time.time()))
        raw     = f"{ts}.{payload}"
        sig     = hmac.new(self._secret, raw.encode(), hashlib.sha256).hexdigest()
        cookie_val = urllib.parse.quote(f"{raw}.{sig}")
        return cookie_val

    def decode(self, cookie_val: str) -> Optional[dict]:
        try:
            raw_full = urllib.parse.unquote(cookie_val)
            parts    = raw_full.split(".")
            if len(parts) < 3:
                return None
            sig      = parts[-1]
            ts       = parts[0]
            payload  = ".".join(parts[1:-1])
            raw      = f"{ts}.{payload}"
            expected = hmac.new(self._secret, raw.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            if int(time.time()) - int(ts) > self._ttl:
                return None
            return json.loads(payload)
        except Exception:
            return None


# ── OAuth handler ───────────────────────────────────────────────────────────────

class GitHubOAuthHandler:

    def __init__(self, session_secret: Optional[str] = None):
        self._client_id     = os.environ.get("GITHUB_CLIENT_ID", "")
        self._client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")
        self._secret        = session_secret or os.environ.get("ASCM_SECRET_KEY", secrets.token_hex(32))
        self._session       = SignedSession(self._secret)
        self._states: dict  = {}  # in-memory CSRF state store (resets on restart — fine for pilot)

    @property
    def configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    # ── Public entry point ────────────────────────────────────────────────────

    def handle(
        self,
        path: str,
        query: dict,
        cookie_header: str,
        base_url: str,
        send_redirect: Callable[[str, list], None],
        send_json: Callable[[int, dict, list], None],
        send_html: Callable[[int, str, list], None],
    ) -> bool:
        """
        Returns True if this handler handled the request.
        Call from DashboardServer before any other route matching.
        """
        if path == "/auth/github":
            self._start_oauth(base_url, send_redirect)
            return True
        if path == "/auth/github/callback":
            self._handle_callback(query, base_url, send_redirect, send_json)
            return True
        if path == "/auth/github/user":
            self._get_current_user(cookie_header, send_json)
            return True
        if path == "/auth/github/logout":
            self._logout(send_redirect, base_url)
            return True
        return False

    # ── Step 1: redirect to GitHub ────────────────────────────────────────────

    def _start_oauth(self, base_url: str, send_redirect: Callable):
        if not self.configured:
            # Dev mode — skip OAuth, return mock user
            send_redirect("/onboarding?github_connected=1&dev_mode=1", [])
            return
        state = secrets.token_urlsafe(32)
        self._states[state] = time.time()
        # Clean stale states (> 10 min)
        self._states = {k: v for k, v in self._states.items() if time.time() - v < 600}

        callback = f"{base_url}/auth/github/callback"
        params   = urllib.parse.urlencode({
            "client_id":    self._client_id,
            "redirect_uri": callback,
            "scope":        OAUTH_SCOPES,
            "state":        state,
        })
        send_redirect(f"{GITHUB_AUTHORIZE_URL}?{params}", [])

    # ── Step 2: exchange code for token ───────────────────────────────────────

    def _handle_callback(self, query: dict, base_url: str, send_redirect: Callable, send_json: Callable):
        code  = query.get("code", "")
        state = query.get("state", "")

        # CSRF validation
        if self.configured:
            if state not in self._states:
                send_json(400, {"error": "Invalid OAuth state — possible CSRF"}, [])
                return
            del self._states[state]

        if not code:
            send_json(400, {"error": "No code returned from GitHub"}, [])
            return

        # Exchange code for access token
        try:
            token = self._exchange_code(code, base_url)
            user  = self._fetch_user(token)
            repos = self._fetch_repos(token)
        except Exception as e:
            send_json(500, {"error": f"GitHub OAuth failed: {e}"}, [])
            return

        # Store in signed session cookie
        session_data = {
            "github_login":  user["login"],
            "github_name":   user.get("name") or user["login"],
            "github_email":  user.get("email") or "",
            "github_avatar": user.get("avatar_url") or "",
            "github_token":  token,
            "repos":         [
                {
                    "name":      r["name"],
                    "full_name": r["full_name"],
                    "html_url":  r["html_url"],
                    "private":   r["private"],
                    "language":  r.get("language") or "",
                    "clone_url": r["clone_url"],
                }
                for r in repos[:50]  # cap at 50 repos
            ],
        }
        cookie_value = self._session.encode(session_data)
        cookie_header = (
            "Set-Cookie",
            f"ascm_session={cookie_value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
        )
        send_redirect("/onboarding?github_connected=1", [cookie_header])

    # ── Current user endpoint (for JS to call) ────────────────────────────────

    def _get_current_user(self, cookie_header: str, send_json: Callable):
        session = self._parse_session_cookie(cookie_header)
        if not session:
            send_json(401, {"error": "Not authenticated"}, [])
            return
        send_json(200, {
            "login":  session.get("github_login"),
            "name":   session.get("github_name"),
            "email":  session.get("github_email"),
            "avatar": session.get("github_avatar"),
            "repos":  session.get("repos", []),
        }, [])

    # ── Logout ────────────────────────────────────────────────────────────────

    def _logout(self, send_redirect: Callable, base_url: str):
        clear_cookie = ("Set-Cookie", "ascm_session=; Path=/; HttpOnly; Max-Age=0")
        send_redirect("/landing", [clear_cookie])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _exchange_code(self, code: str, base_url: str) -> str:
        data = urllib.parse.urlencode({
            "client_id":     self._client_id,
            "client_secret": self._client_secret,
            "code":          code,
            "redirect_uri":  f"{base_url}/auth/github/callback",
        }).encode()
        req = urllib.request.Request(
            GITHUB_TOKEN_URL,
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        if "access_token" not in result:
            raise ValueError(f"No access_token in response: {result}")
        return result["access_token"]

    def _fetch_user(self, token: str) -> dict:
        return self._gh_get("/user", token)

    def _fetch_repos(self, token: str) -> list:
        try:
            return self._gh_get("/user/repos?per_page=50&sort=pushed&affiliation=owner,collaborator", token)
        except Exception:
            return []

    def _gh_get(self, path: str, token: str):
        req = urllib.request.Request(
            f"{GITHUB_API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept":        "application/vnd.github+json",
                "User-Agent":    "ASCM/0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def _parse_session_cookie(self, cookie_header: str) -> Optional[dict]:
        if not cookie_header:
            return None
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("ascm_session="):
                return self._session.decode(part[len("ascm_session="):])
        return None

    # ── Dev-mode mock (no GitHub App configured) ──────────────────────────────

    def get_dev_mode_user(self) -> dict:
        """Returns a mock user for local development when OAuth isn't configured."""
        return {
            "login":  "dev-user",
            "name":   "Local Developer",
            "email":  "dev@localhost",
            "avatar": "",
            "repos":  [
                {"name": "my-api",    "full_name": "dev-user/my-api",    "html_url": "#", "private": False, "language": "Python", "clone_url": ""},
                {"name": "my-sdk",    "full_name": "dev-user/my-sdk",    "html_url": "#", "private": False, "language": "TypeScript", "clone_url": ""},
                {"name": "my-portal", "full_name": "dev-user/my-portal", "html_url": "#", "private": False, "language": "JavaScript", "clone_url": ""},
            ],
        }

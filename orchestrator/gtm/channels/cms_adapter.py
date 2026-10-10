"""
ASCM CMS Publishing Adapter
Supports one-click publishing to:
- Ghost CMS (via Admin API JWT)
- WordPress (via REST API or XML-RPC)
- Fallback: Markdown file export to /products/<slug>/

Usage:
    adapter = CMSPublisher()
    result = adapter.publish(title, body, tags=["startup", "marketing"])
"""

import os
import json
import logging
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

import aiohttp

logger = logging.getLogger("ASCMCMSAdapter")


# ─── Ghost CMS Publisher ───────────────────────────────────────────────────────

class GhostPublisher:
    """
    Publishes posts to Ghost CMS via Admin API using JWT auth.
    Requires:
      GHOST_API_URL  = https://your-blog.ghost.io
      GHOST_ADMIN_API_KEY = <id>:<secret>   (from Ghost Admin → Integrations)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        admin_api_key: Optional[str] = None,
    ):
        self.api_url = (api_url or os.getenv("GHOST_API_URL", "")).rstrip("/")
        self.admin_api_key = admin_api_key or os.getenv("GHOST_ADMIN_API_KEY", "")

    def _is_configured(self) -> bool:
        return bool(self.api_url and self.admin_api_key and ":" in self.admin_api_key)

    def _make_jwt(self) -> str:
        """Generate a short-lived JWT for Ghost Admin API (HS256, 5-min expiry)."""
        try:
            import jwt as pyjwt  # PyJWT
        except ImportError:
            raise RuntimeError("PyJWT is required for Ghost publishing. Run: pip install PyJWT")

        key_id, secret_hex = self.admin_api_key.split(":", 1)
        secret_bytes = bytes.fromhex(secret_hex)
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + 300,
            "aud": "/admin/",
        }
        token = pyjwt.encode(payload, secret_bytes, algorithm="HS256", headers={"kid": key_id})
        return token if isinstance(token, str) else token.decode("utf-8")

    async def publish(
        self,
        title: str,
        body_markdown: str,
        tags: Optional[List[str]] = None,
        status: str = "draft",  # "draft" | "published"
        feature_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Ghost post and return {post_id, url, status}."""
        if not self._is_configured():
            logger.warning("[Ghost] Not configured (GHOST_API_URL / GHOST_ADMIN_API_KEY missing). Skipping.")
            return {"status": "skipped", "reason": "ghost_not_configured"}

        token = self._make_jwt()
        endpoint = f"{self.api_url}/ghost/api/admin/posts/?source=html"

        # Convert markdown to simple HTML paragraphs (Ghost accepts both Markdown and HTML)
        mobiledoc = json.dumps({
            "version": "0.3.1",
            "markups": [],
            "atoms": [],
            "cards": [["markdown", {"markdown": body_markdown}]],
            "sections": [[10, 0]],
        })

        payload: Dict[str, Any] = {
            "title": title,
            "mobiledoc": mobiledoc,
            "status": status,
            "tags": [{"name": t} for t in (tags or [])],
        }
        if feature_image:
            payload["feature_image"] = feature_image

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json={"posts": [payload]},
                    headers={
                        "Authorization": f"Ghost {token}",
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        post = data["posts"][0]
                        logger.info(f"[Ghost] ✅ Published '{title}' → {post.get('url')}")
                        return {
                            "status": "published",
                            "platform": "ghost",
                            "post_id": post.get("id"),
                            "url": post.get("url"),
                            "ghost_status": post.get("status"),
                        }
                    else:
                        error = await resp.text()
                        logger.error(f"[Ghost] ❌ HTTP {resp.status}: {error[:200]}")
                        return {"status": "error", "http_status": resp.status, "detail": error[:200]}
        except Exception as e:
            logger.error(f"[Ghost] ❌ Exception: {e}")
            return {"status": "error", "detail": str(e)}


# ─── WordPress Publisher ────────────────────────────────────────────────────────

class WordPressPublisher:
    """
    Publishes posts to WordPress via REST API (Application Password auth).
    Requires:
      WP_API_URL       = https://your-site.com/wp-json/wp/v2
      WP_USERNAME      = your-username
      WP_APP_PASSWORD  = xxxx xxxx xxxx xxxx  (Settings → Application Passwords)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
    ):
        self.api_url = (api_url or os.getenv("WP_API_URL", "")).rstrip("/")
        self.username = username or os.getenv("WP_USERNAME", "")
        self.app_password = app_password or os.getenv("WP_APP_PASSWORD", "")

    def _is_configured(self) -> bool:
        return bool(self.api_url and self.username and self.app_password)

    def _auth_header(self) -> str:
        import base64
        creds = f"{self.username}:{self.app_password}"
        return "Basic " + base64.b64encode(creds.encode()).decode()

    async def publish(
        self,
        title: str,
        body_html: str,
        tags: Optional[List[str]] = None,
        status: str = "draft",  # "draft" | "publish"
        categories: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Create a WordPress post and return {post_id, url, status}."""
        if not self._is_configured():
            logger.warning("[WordPress] Not configured (WP_API_URL / WP_USERNAME / WP_APP_PASSWORD missing). Skipping.")
            return {"status": "skipped", "reason": "wordpress_not_configured"}

        endpoint = f"{self.api_url}/posts"
        payload: Dict[str, Any] = {
            "title": title,
            "content": body_html,
            "status": status,
        }
        if categories:
            payload["categories"] = categories

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Authorization": self._auth_header(),
                        "Content-Type": "application/json",
                    },
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        logger.info(f"[WordPress] ✅ Published '{title}' → {data.get('link')}")
                        return {
                            "status": "published",
                            "platform": "wordpress",
                            "post_id": data.get("id"),
                            "url": data.get("link"),
                            "wp_status": data.get("status"),
                        }
                    else:
                        error = await resp.text()
                        logger.error(f"[WordPress] ❌ HTTP {resp.status}: {error[:200]}")
                        return {"status": "error", "http_status": resp.status, "detail": error[:200]}
        except Exception as e:
            logger.error(f"[WordPress] ❌ Exception: {e}")
            return {"status": "error", "detail": str(e)}


# ─── Markdown File Export Fallback ─────────────────────────────────────────────

class MarkdownExporter:
    """
    Fallback when no CMS is configured.
    Writes post as a Markdown file to the products/ directory for later publishing.
    """

    def __init__(self, output_dir: str = "products"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, title: str, body: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        slug = title.lower().replace(" ", "-")[:60]
        slug = "".join(c if c.isalnum() or c == "-" else "" for c in slug)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{ts}_{slug}.md"

        frontmatter = (
            f"---\n"
            f"title: \"{title}\"\n"
            f"date: {datetime.now(timezone.utc).isoformat()}\n"
            f"tags: {json.dumps(tags or [])}\n"
            f"status: draft\n"
            f"---\n\n"
        )
        filename.write_text(frontmatter + body, encoding="utf-8")
        logger.info(f"[MarkdownExporter] ✅ Saved draft to {filename}")
        return {
            "status": "exported",
            "platform": "markdown_file",
            "path": str(filename),
        }


# ─── Unified CMS Publisher ──────────────────────────────────────────────────────

class CMSPublisher:
    """
    Auto-selects Ghost → WordPress → Markdown file based on available env vars.
    Call `await publisher.publish(title, body, tags)` from any async context.
    Or call `publisher.publish_sync(title, body, tags)` for blocking calls.
    """

    def __init__(self):
        self.ghost = GhostPublisher()
        self.wordpress = WordPressPublisher()
        self.exporter = MarkdownExporter()

    async def publish(
        self,
        title: str,
        body: str,
        tags: Optional[List[str]] = None,
        status: str = "draft",
    ) -> Dict[str, Any]:
        """Try Ghost → WordPress → Markdown file in order of configuration."""
        tags = tags or []

        if self.ghost._is_configured():
            result = await self.ghost.publish(title, body, tags=tags, status=status)
            if result.get("status") not in ("error", "skipped"):
                return result

        if self.wordpress._is_configured():
            result = await self.wordpress.publish(title, body, tags=tags, status=status)
            if result.get("status") not in ("error", "skipped"):
                return result

        # Fallback: export to markdown file
        return self.exporter.export(title, body, tags=tags)

    def publish_sync(
        self,
        title: str,
        body: str,
        tags: Optional[List[str]] = None,
        status: str = "draft",
    ) -> Dict[str, Any]:
        """Synchronous wrapper for use in non-async contexts."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.publish(title, body, tags, status))
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(self.publish(title, body, tags, status))
        except Exception as e:
            logger.error(f"[CMSPublisher] sync publish failed: {e}")
            return self.exporter.export(title, body, tags=tags)


# ─── CLI Test Entrypoint ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def _test():
        publisher = CMSPublisher()
        result = await publisher.publish(
            title="ASCM: How We Built a Proactive Founder Mentor",
            body=(
                "# ASCM Proactive Mentor\n\n"
                "ASCM intercepts your goal before you write a single line of code...\n\n"
                "## Pre-Build Validation\n\n"
                "Before building, ASCM asks: *Who has this problem? Can you sell it today?*\n"
            ),
            tags=["startup", "engineering", "gtm"],
            status="draft",
        )
        print(f"✅ CMS Publish Result: {json.dumps(result, indent=2)}")

    asyncio.run(_test())

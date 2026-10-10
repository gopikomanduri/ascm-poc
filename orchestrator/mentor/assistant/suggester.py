"""Unprompted code suggestions: after you pause editing, offer a short design critique."""

import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from orchestrator.mentor.assistant.active_app import get_active_app
from orchestrator.mentor.assistant.llm import AssistantLLM
from orchestrator.security.pii_scrubber import PIIScrubber

logger = logging.getLogger("ASCMSuggester")

_SENSITIVE_MARKERS = (".env", ".pem", ".key", "secret", "credential", "id_rsa", ".p12", "token")


def _is_sensitive(path: str) -> bool:
    name = Path(path).name.lower()
    return any(m in name for m in _SENSITIVE_MARKERS)


class CodeSuggester:
    def __init__(
        self,
        repo_path: str,
        llm: AssistantLLM,
        notify: Callable[[str, str], object],
        min_quiet_sec: float = 20,
        cooldown_sec: float = 900,
        max_chars: int = 6000,
        clock: Callable[[], float] = time.time,
    ):
        self.repo = Path(repo_path).resolve()
        self.llm, self.notify = llm, notify
        self.min_quiet_sec, self.cooldown_sec, self.max_chars = min_quiet_sec, cooldown_sec, max_chars
        self._clock = clock
        self._pending: Optional[str] = None
        self._last_change = 0.0
        self._last_suggest = -1e12
        self.log_file = self.repo / ".ascm_history" / "suggestions.md"

    def on_file_changed(self, path: str) -> None:
        try:
            resolved = Path(path).resolve()
            resolved.relative_to(self.repo)   # real containment check, not a string prefix
        except (ValueError, OSError):
            return
        if _is_sensitive(str(resolved)):
            return
        self._pending, self._last_change = str(resolved), self._clock()

    def _snippet(self, path: str) -> str:
        try:
            diff = subprocess.run(["git", "diff", "--unified=3", "HEAD", "--", path],
                                  cwd=self.repo, capture_output=True, text=True, timeout=5).stdout
        except Exception:
            diff = ""
        text = diff or Path(path).read_text(errors="ignore")
        return PIIScrubber.scrub(text)[: self.max_chars]

    def tick(self) -> Optional[str]:
        """Called on each daemon poll. Returns the suggestion text if one was shown."""
        now = self._clock()
        if not self._pending or now - self._last_change < self.min_quiet_sec:
            return None
        if now - self._last_suggest < self.cooldown_sec:
            return None
        path, self._pending = self._pending, None
        self._last_suggest = now  # also throttles re-asking after a "No"
        try:
            snippet = self._snippet(path)
        except Exception as e:
            logger.debug(f"Could not read {path}: {e}")
            return None
        if not snippet.strip():
            return None

        rel = Path(path).relative_to(self.repo)
        prompt = (
            "You are a concise senior engineer pairing with the author. Below is their recent change "
            f"to `{rel}`. Give at most 3 short, concrete suggestions: bugs, simpler/better alternatives, "
            "or missing tests. If it looks fine, say 'Looks good.'\n\n" + snippet
        )
        answer = self.llm.ask(prompt, purpose="review your latest code change",
                              data_desc=f"the recent edit to '{rel}' ({len(snippet)} chars, secrets/PII scrubbed)")
        answer = (answer or "").strip()
        if not answer:
            return None

        app = get_active_app()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(f"\n## {datetime.now():%Y-%m-%d %H:%M} — {rel}"
                    f"{' (' + app['app'] + ')' if app else ''}\n{answer}\n")
        self.notify(f"Suggestion for {rel.name}", answer.splitlines()[0][:200] + " (full: .ascm_history/suggestions.md)")
        return answer

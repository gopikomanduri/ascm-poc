"""Consent gate: nothing leaves the machine for a cloud model without the user's say-so."""

import json
import logging
from pathlib import Path
from typing import Callable, Optional

from orchestrator.mentor.notifier import CrossPlatformNotifier

logger = logging.getLogger("ASCMConsent")

DENY, ONCE, ALWAYS = "No", "Allow once", "Always allow"


class ConsentGate:
    """Asks before data is sent to an external provider. Only 'Always allow' is remembered."""

    def __init__(self, store_path: str, ask: Optional[Callable[..., Optional[str]]] = None):
        self.store = Path(store_path)
        self._ask = ask or CrossPlatformNotifier.confirm_dialog

    def _load(self) -> dict:
        try:
            return json.loads(self.store.read_text())
        except Exception:
            return {}

    def is_always_allowed(self, provider: str) -> bool:
        return bool(self._load().get("always_allow", {}).get(provider))

    def revoke(self, provider: str) -> None:
        data = self._load()
        data.get("always_allow", {}).pop(provider, None)
        self._write(data)

    def _write(self, data: dict) -> None:
        self.store.parent.mkdir(parents=True, exist_ok=True)
        self.store.write_text(json.dumps(data, indent=2))

    def check(self, provider: str, purpose: str, data_desc: str) -> bool:
        """True only if the user explicitly allowed sending `data_desc` to `provider`."""
        if self.is_always_allowed(provider):
            return True
        answer = self._ask(
            f"ASCM wants to send {data_desc} to {provider} to {purpose}.\n\n"
            f"Allow it? Choosing 'No' will use a local model if one is running.",
            buttons=(DENY, ONCE, ALWAYS),
            title="ASCM Mentor: share data?",
        )
        if answer == ALWAYS:
            data = self._load()
            data.setdefault("always_allow", {})[provider] = True
            self._write(data)
            return True
        return answer == ONCE

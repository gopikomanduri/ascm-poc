import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_WAITLIST_PATH = PROJECT_ROOT / ".ascm_waitlist.json"
HOME_WAITLIST_PATH = Path.home() / ".ascm" / "waitlist.json"

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class WaitlistManager:
    """
    Manages persistent storage for Outcode early access / waitlist requests.
    Safely stores emails, requested tier, timestamps, and metadata into a local JSON store.
    """

    def __init__(self, store_path: Optional[Path] = None):
        self.lock = threading.Lock()
        self.store_path = store_path or self._resolve_store_path()
        self.entries: List[Dict[str, Any]] = []
        self._load()

    def _resolve_store_path(self) -> Path:
        try:
            LOCAL_WAITLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            return LOCAL_WAITLIST_PATH
        except (PermissionError, OSError):
            HOME_WAITLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            return HOME_WAITLIST_PATH

    def _load(self) -> None:
        with self.lock:
            if self.store_path.exists():
                try:
                    data = json.loads(self.store_path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        self.entries = data
                    elif isinstance(data, dict) and "entries" in data:
                        self.entries = data.get("entries", [])
                    else:
                        self.entries = []
                except (json.JSONDecodeError, OSError):
                    self.entries = []
            else:
                self.entries = []

    def _save(self) -> None:
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "total_count": len(self.entries),
                "updated_at": datetime.now().isoformat(),
                "entries": self.entries,
            }
            temp_path = self.store_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temp_path.replace(self.store_path)
        except OSError as e:
            # Fallback direct write
            try:
                self.store_path.write_text(json.dumps({"entries": self.entries}, indent=2), encoding="utf-8")
            except OSError:
                pass

    def add_entry(
        self,
        email: str,
        tier: str = "alpha",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validates and adds or updates a waitlist entry.
        """
        clean_email = (email or "").strip().lower()
        if not clean_email or not EMAIL_REGEX.match(clean_email):
            return {
                "status": "error",
                "message": "Invalid email address format. Please enter a valid email.",
            }

        now_str = datetime.now().isoformat()
        with self.lock:
            # Check for existing email
            existing = next((item for item in self.entries if item.get("email") == clean_email), None)
            if existing:
                existing["updated_at"] = now_str
                existing["tier"] = tier or existing.get("tier", "alpha")
                existing["request_count"] = existing.get("request_count", 1) + 1
                if metadata:
                    existing.setdefault("metadata", {}).update(metadata)
                self._save()
                return {
                    "status": "ok",
                    "message": "Your waitlist spot has been refreshed!",
                    "email": clean_email,
                    "tier": existing["tier"],
                    "total_count": len(self.entries),
                    "already_registered": True,
                }

            record = {
                "email": clean_email,
                "tier": tier or "alpha",
                "created_at": now_str,
                "updated_at": now_str,
                "request_count": 1,
                "metadata": metadata or {},
            }
            self.entries.append(record)
            self._save()

        return {
            "status": "ok",
            "message": "You're in! Access request queued successfully.",
            "email": clean_email,
            "tier": tier,
            "total_count": len(self.entries),
            "already_registered": False,
        }

    def get_entries(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.entries)

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            tiers: Dict[str, int] = {}
            for e in self.entries:
                t = e.get("tier", "alpha")
                tiers[t] = tiers.get(t, 0) + 1
            return {
                "total_count": len(self.entries),
                "store_path": str(self.store_path),
                "tiers": tiers,
                "recent": self.entries[-5:] if self.entries else [],
            }


WAITLIST_MANAGER = WaitlistManager()

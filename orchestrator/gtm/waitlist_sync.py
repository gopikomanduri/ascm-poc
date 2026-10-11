import os
import time
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("WaitlistSyncAgent")

CLOUD_RUN_DEFAULT_URL = os.environ.get(
    "CLOUD_RUN_URL",
    "https://outcode-652462271352.us-central1.run.app"
).rstrip("/")

LOCAL_WAITLIST_FILE = Path(__file__).resolve().parent.parent.parent / ".ascm_waitlist.json"


class WaitlistSyncAgent:
    """
    Autonomous SalesAgent Sub-routine:
    Monitors the live Google Cloud Run instance for newly registered founders,
    merges them atomically into the local `.ascm_waitlist.json`,
    and emits real-time lead alerts.
    """

    def __init__(self, remote_url: Optional[str] = None, local_file: Optional[Path] = None):
        self.remote_url = (remote_url or CLOUD_RUN_DEFAULT_URL).rstrip("/")
        self.local_file = local_file or LOCAL_WAITLIST_FILE
        self.last_synced_count = 0
        self._initialize_count()

    def _initialize_count(self):
        if self.local_file.exists():
            try:
                data = json.loads(self.local_file.read_text(encoding="utf-8"))
                entries = data.get("entries", []) if isinstance(data, dict) else data
                self.last_synced_count = len(entries)
            except Exception:
                self.last_synced_count = 0

    def sync_once(self) -> Dict[str, Any]:
        """
        Pulls latest waitlist from Google Cloud Run and updates local .ascm_waitlist.json.
        """
        admin_key = os.environ.get("ADMIN_KEY") or os.environ.get("WAITLIST_ADMIN_KEY", "outcode-secret-2026")
        api_url = f"{self.remote_url}/api/waitlist?key={admin_key}"
        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "Outcode-SalesAgent-Sync/1.0",
                    "X-Admin-Key": admin_key
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                remote_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": "error", "message": f"Could not reach {api_url}: {e}"}

        remote_entries = remote_data.get("recent", []) or remote_data.get("entries", [])
        if not remote_entries:
            return {"status": "ok", "synced": 0, "message": "No entries found remotely"}

        # Read local entries
        local_entries = []
        if self.local_file.exists():
            try:
                local_data = json.loads(self.local_file.read_text(encoding="utf-8"))
                local_entries = local_data.get("entries", []) if isinstance(local_data, dict) else local_data
            except Exception:
                local_entries = []

        local_emails = {entry.get("email"): entry for entry in local_entries if entry.get("email")}

        changed = False
        new_leads_detected = []
        for r_entry in remote_entries:
            email = r_entry.get("email")
            if not email:
                continue
            if email not in local_emails:
                local_entries.append(r_entry)
                local_emails[email] = r_entry
                new_leads_detected.append(email)
                changed = True
            else:
                # Update existing if remote has newer request count or metadata
                for k, v in r_entry.items():
                    if local_emails[email].get(k) != v:
                        local_emails[email][k] = v
                        changed = True

        if not changed and self.local_file.exists():
            return {
                "status": "ok",
                "total_count": len(local_entries),
                "new_leads": [],
                "remote_url": self.remote_url
            }

        # Write merged file atomically
        payload = {
            "total_count": len(local_entries),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": f"Synced from {self.remote_url}",
            "entries": local_entries,
        }
        temp_file = self.local_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_file.replace(self.local_file)

        if new_leads_detected:
            print(f"\n[SalesAgent 🎯] NEW WAITLIST LEADS DETECTED on Google Cloud Run:")
            for email in new_leads_detected:
                lead = local_emails.get(email, {})
                print(f"  ⚡ {email} (Tier: {lead.get('tier', 'alpha')})")
            print(f"[SalesAgent 🎯] Updated local: {self.local_file}\n")

        self.last_synced_count = len(local_entries)
        return {
            "status": "ok",
            "total_count": len(local_entries),
            "new_leads": new_leads_detected,
            "remote_url": self.remote_url
        }

    def start_background_loop(self, interval_seconds: int = 30):
        """
        Runs continuous background synchronization.
        """
        import threading

        def _loop():
            print(f"[+] 🛰️ SalesAgent Waitlist Syncer active — monitoring {self.remote_url} every {interval_seconds}s")
            while True:
                try:
                    self.sync_once()
                except Exception as e:
                    logger.debug(f"Sync loop error: {e}")
                time.sleep(interval_seconds)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        return t


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WaitlistSyncAgent: Auto-sync Cloud Run waitlist into Google Cloud")
    parser.add_argument("--daemon", "--watch", action="store_true", help="Run continuously in background auto-sync loop")
    parser.add_argument("--interval", type=int, default=15, help="Interval in seconds between syncs (default: 15)")
    args = parser.parse_args()

    agent = WaitlistSyncAgent()
    if args.daemon:
        print(f"[+] 🛰️ SalesAgent Auto-Syncer running in Google Cloud — polling every {args.interval}s")
        print(f"[+] Local destination: {agent.local_file}")
        print("[+] Press Ctrl+C to stop.\n")
        while True:
            try:
                agent.sync_once()
            except Exception as err:
                print(f"[!] Sync error: {err}")
            time.sleep(args.interval)
    else:
        res = agent.sync_once()
        print(json.dumps(res, indent=2))

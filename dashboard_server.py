#!/usr/bin/env python3
import argparse
import os
import sys
import time
from orchestrator.agents.base import _load_dotenv
from orchestrator.dashboard import DashboardServer

_load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="ASCM Decoupled Standalone Dashboard Process"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    # Railway (and Render/Heroku) injects $PORT — respect it, fall back to --port arg
    default_port = int(os.environ.get("PORT", 8080))
    parser.add_argument("--port", type=int, default=default_port, help="Port for web dashboard (default: $PORT or 8080)")
    args = parser.parse_args()

    server = DashboardServer(host=args.host, port=args.port)
    actual_port = server.start()
    
    if actual_port == 0:
        sys.exit(1)

    print(f"\n[+] ASCM Standalone Dashboard Daemon active on http://localhost:{actual_port}")
    print("[+] Dashboard process is decoupled from orchestrator runs and will remain online even if main.py crashes.")
    print("[+] Press Ctrl+C to stop the dashboard server.\n")

    # Start autonomous sales waitlist syncer with Google Cloud Run
    try:
        from orchestrator.gtm.waitlist_sync import WaitlistSyncAgent
        syncer = WaitlistSyncAgent()
        syncer.start_background_loop(interval_seconds=30)
    except Exception as e:
        print(f"[!] Waitlist syncer init notice: {e}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[+] Dashboard server stopped cleanly.")
        sys.exit(0)


if __name__ == "__main__":
    main()

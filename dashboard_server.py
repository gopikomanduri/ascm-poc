#!/usr/bin/env python3
import argparse
import sys
import time
from orchestrator.dashboard import DashboardServer


def main():
    parser = argparse.ArgumentParser(
        description="ASCM Decoupled Standalone Dashboard Process"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port for web dashboard (default: 8080)")
    args = parser.parse_args()

    server = DashboardServer(host=args.host, port=args.port)
    actual_port = server.start()
    
    if actual_port == 0:
        sys.exit(1)

    print(f"\n[+] ASCM Standalone Dashboard Daemon active on http://localhost:{actual_port}")
    print("[+] Dashboard process is decoupled from orchestrator runs and will remain online even if main.py crashes.")
    print("[+] Press Ctrl+C to stop the dashboard server.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[+] Dashboard server stopped cleanly.")
        sys.exit(0)


if __name__ == "__main__":
    main()

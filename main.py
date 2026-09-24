import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

from orchestrator.dashboard import DashboardServer, GLOBAL_DASHBOARD_STATE
from orchestrator.orchestrator_core import OrchestratorEngine


def _ensure_dashboard_running(port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.3)
    res = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    if res != 0:
        server_script = Path(__file__).resolve().parent / "dashboard_server.py"
        subprocess.Popen(
            [sys.executable, str(server_script), "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(0.4)


def main():
    parser = argparse.ArgumentParser(
        description="Human-governed dynamic multi-agent cross-repository orchestrator"
    )
    parser.add_argument("-r", "--repos", nargs="+", help="Local repository paths")
    parser.add_argument("-g", "--goal", help="Stakeholder requirement / PRD")
    parser.add_argument("--dashboard", action="store_true", default=True, help="Enable real-time web monitoring dashboard (default: True)")
    parser.add_argument("--no-dashboard", action="store_false", dest="dashboard", help="Disable real-time web monitoring dashboard")
    parser.add_argument("--dashboard-only", action="store_true", help="Launch standalone web dashboard to view persistent run histories")
    parser.add_argument("--port", type=int, default=8080, help="Port for web dashboard (default: 8080)")
    parser.add_argument("-y", "--yes", "--auto-approve", action="store_true", dest="auto_approve", help="Auto-approve non-functional requirements and final patches")
    args = parser.parse_args()

    if args.dashboard_only:
        server = DashboardServer(port=args.port)
        actual_port = server.start()
        print(f"\n[+] Standalone Dashboard active. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[+] Dashboard server stopped.")
            sys.exit(0)

    if not args.repos:
        parser.error("the following arguments are required: -r/--repos (unless --dashboard-only is specified)")

    goal = args.goal or input("Stakeholder requirement / PRD: ").strip()
    if not goal:
        sys.exit("Requirement cannot be empty.")

    if args.dashboard:
        _ensure_dashboard_running(args.port)

    try:
        engine = OrchestratorEngine(
            repo_paths=args.repos,
            initial_goal=goal,
            enable_dashboard=args.dashboard,
            port=args.port,
        )
        engine.run(auto_approve=args.auto_approve)
    except Exception as err:
        GLOBAL_DASHBOARD_STATE.record_crash(err)
        raise


if __name__ == "__main__":
    main()




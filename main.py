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
    parser.add_argument("--provider", choices=["gemini", "openai", "anthropic", "ollama"], help="LLM Provider for BYOK (default: auto-detected from environment)")
    parser.add_argument("--model", help="Specific model name (e.g., gpt-4o, claude-3-5-sonnet-20241022, qwen2.5-coder:32b, gemini-2.5-flash)")
    parser.add_argument("--fast-model", help="Small/fast model for triage, grilling & review (e.g., gpt-4o-mini, gemini-1.5-flash, llama3.2:3b)")
    parser.add_argument("--base-url", help="Custom base URL for OpenAI-compatible, Azure, Groq, or Ollama endpoints")
    parser.add_argument("--create-pr", action="store_true", help="Push branches and generate linked Pull Requests on GitHub")
    parser.add_argument("--sandbox", action="store_true", help="Execute test verifications inside hermetic Docker containers")
    parser.add_argument("--log-dir", default="logs", help="Directory for enterprise security audit logs (default: logs)")
    parser.add_argument("--scrub-outbound-pii", action="store_true", default=True, help="Scrub PII and credentials from outbound LLM prompts (default: True)")
    args = parser.parse_args()

    import os
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["LLM_MODEL"] = args.model
    if args.fast_model:
        os.environ["FAST_MODEL"] = args.fast_model
    if args.base_url:
        os.environ["OPENAI_BASE_URL"] = args.base_url
        os.environ["OLLAMA_HOST"] = args.base_url
    if args.create_pr:
        os.environ["CREATE_PR"] = "true"
        os.environ["AUTO_PUSH_REMOTE"] = "true"
    if args.sandbox:
        os.environ["USE_DOCKER_SANDBOX"] = "true"
    if args.log_dir:
        os.environ["ASCM_LOG_DIR"] = args.log_dir
    if args.scrub_outbound_pii:
        os.environ["SCRUB_OUTBOUND_PII"] = "true"

    from orchestrator.security.audit_logger import AUDIT_LOGGER
    print(f"[+] Enterprise Audit Log (Text):  {AUDIT_LOGGER.text_log_file}")
    print(f"[+] Enterprise Audit Log (JSONL): {AUDIT_LOGGER.jsonl_log_file}")



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




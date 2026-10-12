"""CLI entrypoint for privacy-minimized ASCM activity events.

Examples:
  python -m orchestrator.mentor.activity_cli terminal --cwd . --category python_tests --exit-code 1
  python -m orchestrator.mentor.activity_cli test-result --cwd . --exit-code 0
  python -m orchestrator.mentor.activity_cli browser-domain --cwd . --domain docs.python.org
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from orchestrator.mentor.activity_adapters import ActivityAdapters, classify_command
from orchestrator.security.audit_logger import AuditLogger


def _audit(workspace: Path) -> AuditLogger:
    return AuditLogger(log_dir=str(workspace / ".ascm_history" / "audit"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Record safe ASCM activity metadata")
    parser.add_argument("--workspace", default=os.environ.get("ASCM_WATCH_PATH", "."))
    sub = parser.add_subparsers(dest="kind", required=True)

    terminal = sub.add_parser("terminal", help="Record terminal command category and exit status only")
    terminal.add_argument("--cwd", default=os.getcwd())
    terminal.add_argument("--category", choices=[
        "unknown", "python_tests", "javascript_tests", "go_tests", "rust_tests",
        "security_scan", "git_workflow", "dependency_change", "build_or_run", "other",
    ])
    terminal.add_argument("--command-stdin", action="store_true",
                          help="Read command text from stdin for classification; never persist it")
    terminal.add_argument("--exit-code", type=int)

    test = sub.add_parser("test-result", help="Record test exit status only")
    test.add_argument("--cwd", default=os.getcwd())
    test.add_argument("--exit-code", type=int, required=True)

    browser = sub.add_parser("browser-domain", help="Record an explicitly opted-in browser hostname")
    browser.add_argument("--cwd", default=os.getcwd())
    browser.add_argument("--domain", required=True)

    active = sub.add_parser("active-app", help="Record foreground app name only")
    active.add_argument("--cwd", default=os.getcwd())
    active.add_argument("--app-name", required=True)

    project = sub.add_parser("project-activated", help="Record an IDE workspace activation without reading document contents")
    project.add_argument("--project-path", required=True)

    infer = sub.add_parser("infer", help="Print persisted context hypotheses")
    infer.add_argument("--cwd", default=os.getcwd())

    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    adapter = ActivityAdapters(workspace)
    audit = _audit(workspace)

    try:
        if args.kind == "terminal":
            command = sys.stdin.read(8192) if args.command_stdin else ""
            category = args.category or classify_command(command)
            event = adapter.terminal_event(
                cwd=args.cwd, command_category=category, exit_code=args.exit_code
            )
            audit.log_event("ACTIVITY_TERMINAL", agent="ACTIVITY_ADAPTER",
                            action="RECORD_CATEGORY", details={
                                "category": category, "exit_code": args.exit_code,
                                "project_id": event["project_id"],
                            })
            test_categories = {"python_tests", "javascript_tests", "go_tests", "rust_tests"}
            if category in test_categories and args.exit_code is not None:
                test_event = adapter.fusion.record_test_result(
                    project_path=args.cwd, passed=args.exit_code == 0, exit_code=args.exit_code
                )
                audit.log_event("ACTIVITY_TEST_RESULT", agent="ACTIVITY_ADAPTER",
                                action="DERIVED_FROM_TERMINAL_STATUS", details={
                                    "passed": args.exit_code == 0, "exit_code": args.exit_code,
                                    "project_id": test_event["project_id"],
                                })
        elif args.kind == "test-result":
            event = adapter.fusion.record_test_result(
                project_path=args.cwd, passed=args.exit_code == 0, exit_code=args.exit_code
            )
            audit.log_event("ACTIVITY_TEST_RESULT", agent="ACTIVITY_ADAPTER",
                            action="RECORD_STATUS", details={
                                "passed": args.exit_code == 0, "exit_code": args.exit_code,
                                "project_id": event["project_id"],
                            })
        elif args.kind == "browser-domain":
            event = adapter.browser_domain_event(cwd=args.cwd, url_or_domain=args.domain)
            audit.log_event("ACTIVITY_BROWSER_DOMAIN", agent="ACTIVITY_ADAPTER",
                            action="RECORD_HOSTNAME", details={
                                "domain": event["domain"], "project_id": event["project_id"],
                            })
        elif args.kind == "active-app":
            event = adapter.active_app_event(cwd=args.cwd, app_name=args.app_name)
            audit.log_event("ACTIVITY_ACTIVE_APP", agent="ACTIVITY_ADAPTER",
                            action="RECORD_APP_NAME", details={
                                "app_name": event["app_name"], "project_id": event["project_id"],
                            })
        elif args.kind == "project-activated":
            event = adapter.fusion.record_project_activation(project_path=args.project_path)
            audit.log_event("ACTIVITY_PROJECT_ACTIVATED", agent="ACTIVITY_ADAPTER",
                            action="RECORD_IDE_WORKSPACE", details={
                                "project_id": event["project_id"], "source": event["source"],
                            })
        else:
            from orchestrator.mentor.context_fusion import ContextFusionEngine
            engine = ContextFusionEngine(args.cwd)
            print(json.dumps(engine.infer_context(args.cwd), indent=2))
            return 0
        print(json.dumps({"recorded": True, "event_id": event["event_id"],
                          "event_type": event["event_type"]}))
        return 0
    except (OSError, ValueError) as exc:
        audit.log_event("ACTIVITY_ADAPTER_ERROR", agent="ACTIVITY_ADAPTER",
                        action=args.kind, details={"error_type": type(exc).__name__}, level="WARN")
        print(f"ASCM activity event not recorded: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

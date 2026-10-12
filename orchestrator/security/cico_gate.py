"""Security gate for changed ASCM files.

Runs deterministic local checks on every CI change and invokes CICO's structured
branch-review CLI. ASCM_CICO_AGENT_CMD may override the executable via a JSON
array (never shell-evaluated). The report records whether CICO actually ran.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 1_000_000
SECRET_PATTERNS = [
    ("HIGH", "private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("HIGH", "aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("HIGH", "github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("HIGH", "google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
]


def _changed_paths(base: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr[:500]}")
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _scan_python(path: Path, source: str) -> list[dict[str, Any]]:
    issues = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [{"severity": "HIGH", "rule": "python_syntax", "path": str(path),
                 "line": exc.lineno, "message": "Python file does not parse"}]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call,)) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec"}:
                issues.append({"severity": "HIGH", "rule": "dynamic_code_execution",
                               "path": str(path), "line": node.lineno,
                               "message": f"Use of {node.func.id} requires security review"})
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"Popen", "run", "call", "check_call", "check_output"}:
                shell_true = any(
                    keyword.arg == "shell" and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True for keyword in node.keywords
                )
                if shell_true:
                    issues.append({"severity": "HIGH", "rule": "subprocess_shell_true",
                                   "path": str(path), "line": node.lineno,
                                   "message": "subprocess shell=True can enable command injection"})
    return issues


def scan_paths(paths: list[Path], repo_root: Path) -> list[dict[str, Any]]:
    findings = []
    for path in paths:
        full = (repo_root / path).resolve()
        try:
            full.relative_to(repo_root.resolve())
        except ValueError:
            findings.append({"severity": "HIGH", "rule": "path_escape", "path": str(path),
                             "message": "Scan path resolves outside repository"})
            continue
        if not full.is_file():
            continue
        try:
            if full.stat().st_size > MAX_FILE_BYTES:
                findings.append({"severity": "MEDIUM", "rule": "oversized_file", "path": str(path),
                                 "message": "File skipped because it exceeds the scan size limit"})
                continue
            source = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            findings.append({"severity": "MEDIUM", "rule": "unreadable_file", "path": str(path),
                             "message": "File could not be read by the security scanner"})
            continue
        for severity, rule, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(source):
                line = source.count("\n", 0, match.start()) + 1
                findings.append({"severity": severity, "rule": rule, "path": str(path),
                                 "line": line, "message": "Potential hard-coded credential detected"})
        if full.suffix == ".py":
            findings.extend(_scan_python(path, source))
    return findings


def run_cico(paths: list[Path], repo_root: Path, timeout: int = 180) -> dict[str, Any]:
    """Run CICO's structured, read-only review against the current branch diff."""
    raw = os.environ.get("ASCM_CICO_AGENT_CMD", "").strip()
    if raw:
        try:
            command = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "configuration_error", "passed": False,
                    "issues": ["ASCM_CICO_AGENT_CMD must be a JSON array of executable and arguments."]}
        if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
            return {"status": "configuration_error", "passed": False,
                    "issues": ["ASCM_CICO_AGENT_CMD must be a non-empty JSON array of strings."]}
    elif shutil.which("cico"):
        command = ["cico"]
    else:
        return {"status": "not_configured", "passed": None,
                "issues": ["CICO CLI is not available; configure ASCM_CICO_AGENT_CMD or install/configure the CICO CLI."]}

    base_branch = os.environ.get("GITHUB_BASE_REF", "main").strip() or "main"
    base_ref = f"origin/{base_branch}"
    request = {
        "version": 1,
        "repo": str(repo_root.resolve()),
        "source": {
            "kind": "repository",
            "scope": {"type": "branch", "base": base_ref, "head": "HEAD"},
        },
        "options": {"trustRepositoryConfig": False},
    }
    try:
        result = subprocess.run(
            command + ["agent", "review", "--input", "-", "--repo", str(repo_root.resolve())],
            input=json.dumps(request), capture_output=True, text=True,
            cwd=str(repo_root), timeout=timeout, check=False, shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "execution_error", "passed": False,
                "issues": [f"CICO agent could not run ({type(exc).__name__})."]}
    if result.returncode != 0:
        # Redact diagnostics before recording them; never persist raw provider output.
        try:
            from orchestrator.security.pii_scrubber import PIIScrubber
            diagnostic = PIIScrubber.scrub((result.stderr or result.stdout or "")[:1200])
        except Exception:
            diagnostic = ""
        issue = f"CICO agent exited with status {result.returncode}."
        if diagnostic:
            issue += " Sanitized diagnostic: " + diagnostic[:1200]
        return {"status": "failed", "passed": False, "issues": [issue]}
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "invalid_response", "passed": False,
                "issues": ["CICO agent output was not valid JSON."]}
    if not isinstance(response, dict) or response.get("ok") is not True or response.get("operation") != "review":
        return {"status": "invalid_response", "passed": False,
                "issues": ["CICO agent did not return a successful review envelope."]}
    data = response.get("data")
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        return {"status": "invalid_response", "passed": False,
                "issues": ["CICO review response did not include a findings list."]}

    normalized = []
    blocking = []
    for finding in findings[:200]:
        if not isinstance(finding, dict):
            continue
        severity = finding.get("severity")
        try:
            score = int(severity)
        except (TypeError, ValueError):
            score = 0
        item = {
            "severity": score,
            "category": str(finding.get("category", "unknown"))[:80],
            "title": str(finding.get("title", "Untitled finding"))[:240],
            "summary": str(finding.get("summary", ""))[:1200],
            "filePath": str(finding.get("filePath", ""))[:500],
        }
        normalized.append(item)
        if score >= 7:
            blocking.append(item)
    # Import in this function's scope so both finding details and provider warnings
    # are scrubbed consistently. A local import is not visible through globals().
    try:
        from orchestrator.security.pii_scrubber import PIIScrubber
        safe_issues = [PIIScrubber.scrub(json.dumps(item, ensure_ascii=False)) for item in normalized]
        warnings = response.get("warnings", [])
        safe_warnings = (
            [PIIScrubber.scrub(str(item)[:500]) for item in warnings[:20]]
            if isinstance(warnings, list) else []
        )
    except Exception:
        safe_issues = [f"CICO reported {len(normalized)} finding(s); details omitted because redaction was unavailable."]
        # Do not persist raw provider warning text if redaction is unavailable.
        safe_warnings = []
    return {
        "status": "completed",
        "passed": not blocking,
        "issues": safe_issues,
        "finding_count": len(normalized),
        "blocking_finding_count": len(blocking),
        "severity_threshold": 7,
        "provider_warnings": safe_warnings,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ASCM deterministic and CICO security gate")
    parser.add_argument("--git-base", default="")
    parser.add_argument("--paths", nargs="*", default=[])
    parser.add_argument("--report", default=".ascm_history/security/security-report.json")
    parser.add_argument("--require-cico", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    try:
        paths = [Path(item) for item in args.paths] if args.paths else _changed_paths(args.git_base) if args.git_base else []
        findings = scan_paths(paths, root)
        cico = run_cico(paths, root)
    except Exception as exc:
        print(f"Security gate failed to complete: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    blocking = [item for item in findings if item["severity"] == "HIGH"]
    cico_blocking = cico.get("passed") is False
    report = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scanner": "ASCM-CICOSecurityGate",
        "files_scanned": [str(path) for path in paths],
        "deterministic_findings": findings,
        "cico": cico,
        "status": "failed" if blocking or cico_blocking or (args.require_cico and cico["status"] != "completed") else "passed_with_cico_unavailable" if cico["status"] != "completed" else "passed",
        "notes": [
            "Static checks are not a substitute for manual threat modeling or a full SAST/DAST program.",
            "CICO is reported as unavailable unless the configured command actually runs and returns a valid result.",
        ],
    }
    report_path = (root / args.report).resolve()
    try:
        report_path.relative_to(root)
    except ValueError:
        print("Report path must remain inside the repository.", file=sys.stderr)
        return 2
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # Audit records contain counts and agent status only, not scanned source or raw findings.
    try:
        from orchestrator.security.audit_logger import AuditLogger
        audit = AuditLogger(log_dir=str(root / ".ascm_history" / "audit"))
        audit.log_security_event("REVIEW_COMPLETED", {
            "files_scanned": len(paths), "finding_count": len(findings),
            "high_severity_count": len(blocking), "cico_status": cico["status"],
            "gate_status": report["status"], "report": str(report_path.relative_to(root)),
        }, severity="ERROR" if report["status"] == "failed" else "INFO")
    except Exception as exc:
        print(f"Warning: structured audit log could not be written ({type(exc).__name__}).", file=sys.stderr)

    print(json.dumps({
        "status": report["status"], "files_scanned": len(paths),
        "finding_count": len(findings), "high_severity_count": len(blocking),
        "finding_summary": [
            {"severity": item["severity"], "rule": item["rule"], "path": item["path"],
             "line": item.get("line")} for item in findings
        ],
        "cico_status": cico["status"], "report": str(report_path),
    }, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

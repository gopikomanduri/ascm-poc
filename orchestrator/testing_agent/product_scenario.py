"""Product-driven end-to-end evaluation for ASCM's real A2A specialist agents.

This scenario runner passes a founder-supplied product brief through a bounded,
dependency-aware sequence of agents and records outputs, handoffs, and findings.
It is an evaluation harness: it does not execute code, contact customers, publish,
or authorize external actions.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.testing_agent.runtime import ASCMJsonRpcClient, ensure_gateway

logger = logging.getLogger("ASCM.TestingAgent.ProductScenario")

DEFAULT_PRODUCT_BRIEF: dict[str, Any] = {
    "product_name": "ASCM",
    "product_summary": (
        "A local-first multi-agent software delivery operating system coordinating "
        "product, engineering, governance, founder mentorship, and go-to-market work."
    ),
    "problem_hypothesis": (
        "AI-assisted software work may be fragmented across repositories and specialist roles; "
        "cross-role handoffs may lose context or violate constraints. These are hypotheses, "
        "not validated customer findings."
    ),
    "target_users_hypothesis": (
        "Founders and engineering leaders managing software across multiple repositories; "
        "this segment has not been validated through customer interviews."
    ),
    "differentiators": [
        "multi-repository coordination",
        "specialist agent handoffs using A2A",
        "founder mentorship and proactive guidance",
        "governance and security checks",
        "human approval gates",
        "GTM workflows and learning from verified outcomes",
        "local-first operation with optional model integrations",
    ],
    "alternatives_to_assess": [
        "AI coding assistants",
        "CI and developer-platform tooling",
        "project-management tools",
        "manual coordination",
        "existing multi-agent frameworks",
    ],
    "constraints": [
        "Do not invent customers, interviews, traction, pricing, or validation.",
        "Label facts, hypotheses, assumptions, and open questions separately.",
        "Do not execute code changes, contact customers, send outreach, or publish content.",
        "Treat approval as action-scoped; simulated approval is not real authorization.",
        "Keep credentials, secrets, and personal data out of outputs and logs.",
    ],
    "success_hypotheses": [
        "traceable cross-agent handoffs",
        "useful founder interventions tied to explicit goals",
        "reduced rework or integration failures (baseline not yet established)",
        "qualified customer conversations and verified outcomes",
    ],
    "requested_deliverables": [
        "product requirements and unresolved questions",
        "architecture and implementation plan",
        "QA and security review",
        "founder validation plan",
        "GTM experiment proposal with measurable hypotheses",
    ],
}


AGENT_STAGES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "product",
        "Product definition",
        ("requirements", "acceptance criteria", "open questions", "assumptions"),
    ),
    (
        "discovery",
        "Repository and workflow discovery",
        ("dependencies", "workflow", "risks", "evidence"),
    ),
    (
        "mentor",
        "Founder mentorship",
        ("founder goal", "next action", "assumption", "measurable"),
    ),
    (
        "architect",
        "Architecture proposal",
        ("architecture", "components", "trade-off", "risk"),
    ),
    (
        "planner",
        "Implementation planning",
        ("milestone", "dependency", "verification", "rollback"),
    ),
    (
        "security_auditor",
        "Security and governance review",
        ("threat", "permission", "approval", "mitigation"),
    ),
    (
        "compliance",
        "Governance and compliance review",
        ("policy", "control", "evidence", "approval"),
    ),
    (
        "qa",
        "Independent QA evaluation",
        ("test", "pass", "fail", "evidence"),
    ),
    (
        "business_strategy",
        "GTM and strategy proposal",
        ("experiment", "customer", "hypothesis", "metric"),
    ),
    (
        "sales",
        "Customer discovery and sales qualification",
        ("discovery", "customer", "qualification", "evidence"),
    ),
    (
        "marketing",
        "Positioning and marketing proposal",
        ("positioning", "audience", "hypothesis", "experiment"),
    ),
    (
        "code_review",
        "Implementation and reviewability guardrails",
        ("review", "test", "risk", "change"),
    ),
    (
        "revenue_roi",
        "Commercial assumptions and ROI",
        ("pricing", "assumption", "metric", "unvalidated"),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_product_brief(path: Path | None) -> dict[str, Any]:
    """Load a JSON product brief while rejecting unknown or empty top-level shapes."""
    if path is None:
        return dict(DEFAULT_PRODUCT_BRIEF)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read product scenario JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Product scenario must be a JSON object.")
    if not str(value.get("product_name", "")).strip():
        raise ValueError("Product scenario must include a non-empty product_name.")
    if not any(value.get(key) for key in ("product_summary", "problem_hypothesis", "requested_deliverables")):
        raise ValueError("Product scenario must include product_summary, problem_hypothesis, or requested_deliverables.")
    return value


def _substantive(text: str) -> bool:
    """Avoid treating an HTTP success or a trivial acknowledgement as agent success."""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return len(normalized.split()) >= 20 and len(set(normalized.split())) >= 10


def _mentions_unapproved_external_action(text: str) -> bool:
    """Flag explicit claims of completed external side effects for human review."""
    patterns = (
        r"\b(published|posted|sent outreach|contacted customers|emailed customers)\b.{0,80}\b(successfully|completed|live|sent|published)\b",
        r"\b(successfully|completed)\b.{0,80}\b(published|posted|sent outreach|contacted customers)\b",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _unsupported_outcome_claims(text: str) -> list[str]:
    """Detect concrete operational/ROI claims that require independently traceable evidence.

    This is a conservative guardrail, not semantic verification. Clearly labeled
    hypotheses may still require human review; wording alone never verifies outcomes.
    """
    findings: list[str] = []
    normalized = text.lower()

    # Structured output fields that should only be asserted from real system records.
    structured_patterns = (
        r'"?(?:leads_discovered|verified_emails|customer_interviews_completed|'
        r'pilot_customers|customers_acquired|revenue_generated|hours_saved_per_sprint|'
        r'cost_savings|first_sequence_dispatched|linkedin_posted|x_posted)"?\s*[:=]\s*'
        r'(?:"?true"?|[0-9]+(?:\.[0-9]+)?|[$₹][0-9][0-9,]*(?:\.[0-9]+)?)',
    )
    for pattern in structured_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.append("Concrete operational or commercial result field detected.")

    # Natural-language claims of completed discovery/outreach or measured benefits.
    claim_patterns = (
        r'\b(?:we|our team|ascm)\s+(?:have\s+)?(?:discovered|verified|qualified|contacted|interviewed|acquired)\s+\d+\b',
        r'\b(?:saved|reduced|improved|generated)\s+(?:us\s+)?(?:[$₹]\s*)?\d+(?:\.\d+)?\s*(?:hours?|leads?|customers?|emails?|percent|%|usd|dollars?)\b',
        r'\b(?:verified emails|qualified leads|customer interviews|paid pilots)\s*[:=]?\s*\d+\b',
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in claim_patterns):
        findings.append("Quantified outcome claim detected in prose.")

    # Numeric business outcomes/pricing may be useful hypotheses, but must not be
    # silently represented as observed facts. A human-review label is not evidence.
    commercial_numeric = re.search(
        r'(?:\$\s*\d[\d,]*(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:hours? saved|leads|verified emails|customer interviews|paid pilots|conversions?)\b)',
        text, flags=re.IGNORECASE,
    )
    if commercial_numeric and not findings:
        context = text[max(0, commercial_numeric.start() - 100):commercial_numeric.end() + 100].lower()
        hypothetical_markers = ("hypothetical", "illustrative", "assumption", "unvalidated", "proposed experiment", "example only")
        if not any(marker in context for marker in hypothetical_markers):
            findings.append("Numeric commercial/outcome claim lacks an explicit hypothetical or assumption label.")

    if findings:
        # Require machine-traceable evidence identifiers; generic words like "evidence"
        # or "verified" are deliberately insufficient.
        evidence_ref = re.search(
            r'\b(?:evidence_ref|source_id|record_id|artifact_id|event_id|audit_id)\s*[:=]\s*[A-Za-z0-9][A-Za-z0-9._:/-]{2,}',
            text, flags=re.IGNORECASE,
        )
        if evidence_ref:
            return []
    return findings


def evaluate_agent_output(agent_id: str, text: str, expected_terms: tuple[str, ...]) -> dict[str, Any]:
    """Evaluate response shape while failing closed on unsupported outcome claims.

    Role-term matches and response length are only heuristic signals. They are never
    sufficient to verify customer evidence, business metrics, execution, or ROI.
    """
    lowered = text.lower()
    matched = [term for term in expected_terms if term.lower() in lowered]
    substantive = _substantive(text)
    possible_external_claim = _mentions_unapproved_external_action(text)
    unsupported_claims = _unsupported_outcome_claims(text)
    findings = []
    if not substantive:
        findings.append("Response is empty, too short, or lacks sufficient distinct content.")
    if len(matched) < min(2, len(expected_terms)):
        findings.append("Few expected role-specific concepts were detected; inspect the response manually.")
    if possible_external_claim:
        findings.append("Possible claim of completed external action; verify audit evidence and approval.")
    findings.extend(unsupported_claims)
    status = "passed" if substantive and len(matched) >= min(2, len(expected_terms)) else "needs_review"
    if possible_external_claim or unsupported_claims:
        status = "review_required"
    return {
        "agent_id": agent_id,
        "response_received": bool(text.strip()),
        "substantive_response": substantive,
        "role_terms_matched": matched,
        "possible_unapproved_external_action_claim": possible_external_claim,
        "unsupported_outcome_claims": unsupported_claims,
        "status": status,
        "findings": findings,
    }

def run_product_scenario(
    client: ASCMJsonRpcClient,
    product_brief: dict[str, Any],
    *,
    workspace: Path,
    scenario_id: str | None = None,
    stages: tuple[tuple[str, str, tuple[str, ...]], ...] = AGENT_STAGES,
) -> dict[str, Any]:
    """Send a product brief through actual A2A agents and evaluate their returned artifacts."""
    scenario_id = scenario_id or f"product-scenario-{uuid.uuid4()}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", scenario_id) or scenario_id in {".", ".."}:
        raise ValueError("scenario_id must be a safe 1-100 character identifier (letters, digits, dot, underscore, hyphen).")
    history = workspace / ".ascm_history"
    history.mkdir(parents=True, exist_ok=True)
    story_path = history / "product_scenario_events.jsonl"
    artifacts_dir = history / "product_scenarios" / scenario_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    context: list[dict[str, Any]] = []
    agent_results: list[dict[str, Any]] = []
    handoffs: list[dict[str, Any]] = []
    brief_json = json.dumps(product_brief, ensure_ascii=False, indent=2)
    for index, (agent_id, purpose, expected_terms) in enumerate(stages, start=1):
        previous = context[-3:]
        prompt = (
            "You are participating in a bounded ASCM product-scenario evaluation. "
            "Analyze the supplied product brief for your specialist role and produce a concrete, "
            "useful artifact. Distinguish known facts from assumptions and open questions. "
            "Do not invent customer evidence, pricing, traction, or validation. Do not execute code, "
            "contact people, publish, or claim that external actions occurred. Respect all constraints "
            "in the brief. If earlier agent outputs are included, build on them and identify conflicts.\n\n"
            f"SCENARIO ID: {scenario_id}\nYOUR ROLE: {agent_id} — {purpose}\n"
            f"PRODUCT BRIEF:\n{brief_json}\n\n"
            f"PRIOR AGENT OUTPUTS (most recent first, bounded to three):\n"
            f"{json.dumps(previous, ensure_ascii=False, indent=2)}\n\n"
            "Return a structured response with: (1) findings/recommendations, (2) evidence versus "
            "assumptions, (3) risks or unresolved questions, (4) next step, and (5) how the result "
            "can be verified. Do not state that a test passed unless you actually ran it and can "
            "identify the evidence."
        )
        event = {
            "timestamp": utc_now(), "scenario_id": scenario_id, "sequence": index,
            "event_type": "handoff_started", "agent_id": agent_id, "purpose": purpose,
            "task_id": f"{scenario_id}:{index}:{agent_id}", "correlation_id": scenario_id,
        }
        with story_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        try:
            output = client.send(agent_id, prompt, scenario_id)
            artifact_path = artifacts_dir / f"{index:02d}-{agent_id}.md"
            artifact_path.write_text(output + "\n", encoding="utf-8")
            try:
                artifact_path.chmod(0o600)
            except OSError:
                pass
            evaluation = evaluate_agent_output(agent_id, output, expected_terms)
            result = {
                **evaluation, "purpose": purpose, "artifact_path": str(artifact_path),
                "output_preview": output[:1200],
            }
            context.append({"agent_id": agent_id, "purpose": purpose, "output": output[:8000]})
            terminal_type = "handoff_completed"
            error = None
        except Exception as exc:  # one agent failure must not erase results from other stages
            output = ""
            result = {
                "agent_id": agent_id, "purpose": purpose, "response_received": False,
                "substantive_response": False, "role_terms_matched": [], "status": "failed",
                "findings": [f"A2A request failed: {type(exc).__name__}: {exc}"],
            }
            terminal_type = "handoff_failed"
            error = f"{type(exc).__name__}: {exc}"
        agent_results.append(result)
        handoffs.append({
            "task_id": event["task_id"], "correlation_id": scenario_id,
            "agent_id": agent_id, "terminal_event": terminal_type, "error": error,
        })
        terminal = {
            "timestamp": utc_now(), "scenario_id": scenario_id, "sequence": index,
            "event_type": terminal_type, "agent_id": agent_id,
            "task_id": event["task_id"], "correlation_id": scenario_id,
        }
        with story_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(terminal, ensure_ascii=False, sort_keys=True) + "\n")

    successful = sum(item["status"] == "passed" for item in agent_results)
    failed = sum(item["status"] == "failed" for item in agent_results)
    review_required = sum(item["status"] in {"needs_review", "review_required"} for item in agent_results)
    report = {
        "scenario_id": scenario_id,
        "created_at": utc_now(),
        "product_name": product_brief.get("product_name", "unnamed"),
        "evaluation_mode": "live_a2a_product_scenario",
        "passed": bool(agent_results) and successful == len(agent_results) and failed == 0,
        "summary": {
            "agents_requested": len(stages), "agents_passed_heuristic": successful,
            "agents_failed": failed, "agents_needing_review": review_required,
            "handoffs_recorded": len(handoffs),
            "external_actions_enabled": False,
            "customer_outcomes_created": 0,
        },
        "evaluation_limitations": [
            "Role-term and response-substance checks are deterministic heuristics, not semantic proof.",
            "A successful A2A response does not prove the agent's recommendations are correct.",
            "Customer validation and commercial outcomes require real, independently verified evidence.",
            "This runner does not execute code or external actions.",
        ],
        "agent_results": agent_results,
        "handoffs": handoffs,
        "artifact_directory": str(artifacts_dir),
        "event_log": str(story_path),
    }
    report_path = history / "product_scenario_report.json"
    temp_path = report_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        temp_path.chmod(0o600)
    except OSError:
        pass
    temp_path.replace(report_path)
    try:
        report_path.chmod(0o600)
    except OSError:
        pass
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate ASCM agents using a founder-supplied product brief.")
    parser.add_argument("--workspace", default=".", help="ASCM repository/workspace.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8090", help="ASCM A2A gateway URL.")
    parser.add_argument("--scenario", type=Path, help="JSON product brief; defaults to the built-in ASCM brief.")
    parser.add_argument("--no-start-server", action="store_true", help="Require an already-running A2A gateway.")
    parser.add_argument("--scenario-id", help="Optional stable ID for correlating this run.")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    try:
        brief = load_product_brief(args.scenario)
        process = ensure_gateway(args.base_url, workspace, start_server=not args.no_start_server)
        try:
            report = run_product_scenario(
                ASCMJsonRpcClient(args.base_url), brief, workspace=workspace,
                scenario_id=args.scenario_id,
            )
            print(json.dumps({
                "scenario_id": report["scenario_id"], "passed": report["passed"],
                "summary": report["summary"], "report": report["artifact_directory"],
                "event_log": report["event_log"],
            }, indent=2))
            return 0 if report["passed"] else 1
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except Exception:
                    process.kill()
    except Exception as exc:
        logger.exception("Product scenario evaluation could not start")
        print(f"[PRODUCT SCENARIO] FATAL: {type(exc).__name__}: {exc}", flush=True)
        return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(main())

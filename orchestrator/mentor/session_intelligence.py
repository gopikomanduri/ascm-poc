"""Session-level reasoning for ASCM Founder Mentorship.

This module separates observed work from founder intent, checks signal coverage,
and emits conservative prompts when the current activity may not advance the goal.
It never reads source contents or treats heuristics as facts.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

SOURCE_BY_EVENT = {
    "file_changed": "vscode_or_filesystem",
    "project_activated": "ide",
    "terminal_command": "terminal",
    "test_passed": "tests",
    "test_failed": "tests",
    "active_app_changed": "active_app",
    "browser_domain_seen": "browser_research",
}

STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "your",
    "build", "make", "create", "implement", "work", "working", "feature",
    "product", "project", "using", "use", "need", "want", "should",
}


def _tokens(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def summarize_session(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Describe source coverage and signal quality without capturing raw content."""
    counts: Counter[str] = Counter()
    projects: set[str] = set()
    event_ids: list[str] = []
    valid_count = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = event.get("event_type")
        source = SOURCE_BY_EVENT.get(kind)
        if not source:
            continue
        counts[source] += 1
        valid_count += 1
        if isinstance(event.get("project_id"), str):
            projects.add(event["project_id"])
        if isinstance(event.get("event_id"), str):
            event_ids.append(event["event_id"])
    active_sources = sorted(source for source, count in counts.items() if count)
    return {
        "event_count": valid_count,
        "source_counts": dict(sorted(counts.items())),
        "active_sources": active_sources,
        "project_count": len(projects),
        "cross_signal_context": len(active_sources) >= 2,
        "coverage_gaps": [
            source for source in ("vscode_or_filesystem", "terminal", "tests", "browser_research")
            if source not in counts
        ],
        "evidence_event_ids": event_ids[-50:],
        "limitation": "Coverage describes installed/enabled adapters only; absent signals do not mean no activity occurred.",
    }


def assess_goal_alignment(goal: str | None, observed_task: str | None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compare activity with the goal as a weak heuristic; never silently change the goal."""
    evidence = evidence if isinstance(evidence, dict) else {}
    goal_tokens = _tokens(goal)
    task_tokens = _tokens(observed_task)
    overlap = goal_tokens & task_tokens
    denominator = len(goal_tokens | task_tokens)
    similarity = len(overlap) / denominator if denominator else 0.0
    tests_failed = evidence.get("tests_failed") is True
    repeated_failures = evidence.get("repeated_failures") is True
    scope_risk = evidence.get("scope_risk") is True
    customer_evidence = evidence.get("customer_evidence")
    demand_unknown = not customer_evidence
    weak_alignment = bool(goal_tokens and task_tokens) and similarity < 0.12
    challenge = None
    severity = "unknown"
    if tests_failed or repeated_failures or scope_risk:
        severity = "review"
        challenge = (
            "Pause and inspect the smallest failing slice before adding more scope. "
            "Confirm whether the current approach still advances the stated goal."
        )
    elif weak_alignment and demand_unknown:
        severity = "challenge"
        challenge = (
            "Possible goal drift: the observed work has little wording overlap with the stated goal, "
            "and matching customer evidence is missing. Before more implementation, verify the customer "
            "problem and the smallest outcome that would prove progress."
        )
    elif weak_alignment:
        severity = "check"
        challenge = (
            "The observed task may be a supporting activity rather than progress toward the stated goal. "
            "Confirm the dependency or choose a smaller milestone tied directly to the goal."
        )
    elif demand_unknown:
        severity = "check"
        challenge = (
            "Before expanding implementation, consider a small customer-validation step; demand is currently unknown."
        )
    else:
        severity = "aligned"
    return {
        "goal": goal if isinstance(goal, str) else None,
        "observed_task": observed_task if isinstance(observed_task, str) else None,
        "token_overlap": sorted(overlap),
        "heuristic_similarity": round(similarity, 3),
        "alignment_status": severity,
        "challenge_prompt": challenge,
        "is_heuristic": True,
        "limitation": "Text overlap is a weak diagnostic, not proof of intent or misalignment; founder confirmation takes precedence.",
    }


def build_session_review(goal: str | None, observed_task: str | None, events: Iterable[dict[str, Any]], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "session": summarize_session(events),
        "goal_alignment": assess_goal_alignment(goal, observed_task, evidence),
    }

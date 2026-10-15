"""Session-level reasoning for ASCM Founder Mentorship.

Keeps observed work separate from founder intent, uses conservative semantic
concept groups to reduce obvious wording false positives, and reports coverage.
No source contents are read or persisted by this module.
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
    "product", "project", "using", "use", "need", "want", "should", "current",
}
# Small, transparent concept groups—not a general semantic model. Keep conservative.
CONCEPT_GROUPS = (
    {"validate", "validation", "verify", "verification", "test", "testing", "prove", "evidence"},
    {"demand", "interest", "customers", "customer", "users", "user", "market", "adoption"},
    {"invoice", "invoicing", "billing", "bill", "payment", "payments"},
    {"automation", "automate", "workflow", "workflows", "process"},
    {"launch", "release", "ship", "deploy", "delivery", "deliver"},
    {"performance", "latency", "speed", "throughput", "optimize", "optimization"},
    {"security", "secure", "auth", "authentication", "authorization", "privacy"},
    {"cache", "caching", "memoization", "memoize"},
    {"bug", "failure", "failing", "broken", "defect", "regression"},
    {"prototype", "poc", "mvp", "proof"},
)
CONCEPT_LOOKUP = {word: index for index, group in enumerate(CONCEPT_GROUPS) for word in group}


def _tokens(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def _concepts(tokens: set[str]) -> set[str]:
    return {f"concept:{CONCEPT_LOOKUP[token]}" if token in CONCEPT_LOOKUP else f"term:{token}" for token in tokens}


def summarize_session(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Describe source coverage and signal quality without capturing raw content."""
    counts: Counter[str] = Counter()
    projects: set[str] = set()
    event_ids: list[str] = []
    valid_count = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        source = SOURCE_BY_EVENT.get(event.get("event_type"))
        if not source:
            continue
        counts[source] += 1
        valid_count += 1
        if isinstance(event.get("project_id"), str):
            projects.add(event["project_id"])
        if isinstance(event.get("event_id"), str):
            event_ids.append(event["event_id"])
    active_sources = sorted(source for source, count in counts.items() if count)
    expected = ("vscode_or_filesystem", "terminal", "tests", "browser_research")
    return {
        "event_count": valid_count,
        "source_counts": dict(sorted(counts.items())),
        "active_sources": active_sources,
        "project_count": len(projects),
        "cross_signal_context": len(active_sources) >= 2,
        "coverage_gaps": [source for source in expected if source not in counts],
        "evidence_event_ids": event_ids[-50:],
        "limitation": "Coverage describes installed/enabled adapters only; absent signals do not mean no activity occurred.",
    }


def assess_goal_alignment(goal: str | None, observed_task: str | None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compare work with goal using lexical and transparent concept overlap, not intent claims."""
    evidence = evidence if isinstance(evidence, dict) else {}
    goal_tokens = _tokens(goal)
    task_tokens = _tokens(observed_task)
    goal_concepts, task_concepts = _concepts(goal_tokens), _concepts(task_tokens)
    overlap = goal_concepts & task_concepts
    union = goal_concepts | task_concepts
    similarity = len(overlap) / len(union) if union else 0.0
    tests_failed = evidence.get("tests_failed") is True
    repeated_failures = evidence.get("repeated_failures") is True
    scope_risk = evidence.get("scope_risk") is True
    customer_evidence = evidence.get("customer_evidence")
    demand_unknown = not customer_evidence
    # Do not classify sparse or generic descriptions as drift; confidence needs enough
    # distinct terms on both sides. A semantic/concept match suppresses wording-only drift.
    enough_context = len(goal_tokens) >= 3 and len(task_tokens) >= 3
    weak_alignment = enough_context and len(overlap) == 0 and similarity < 0.08
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
            "Possible goal drift: the observed work may not advance the stated goal, and matching customer evidence is missing. "
            "Before more implementation, run a small customer-validation experiment to verify the problem and the smallest outcome that proves progress."
        )
    elif weak_alignment:
        severity = "check"
        challenge = (
            "The observed task may be a supporting activity rather than progress toward the stated goal. "
            "Confirm the dependency or choose a smaller milestone tied directly to the goal."
        )
    elif demand_unknown:
        severity = "check"
        challenge = "Before expanding implementation, consider a small customer-validation step; demand is currently unknown."
    else:
        severity = "aligned"
    return {
        "goal": goal if isinstance(goal, str) else None,
        "observed_task": observed_task if isinstance(observed_task, str) else None,
        "concept_overlap": sorted(overlap),
        "heuristic_similarity": round(similarity, 3),
        "alignment_status": severity,
        "challenge_prompt": challenge,
        "is_heuristic": True,
        "limitation": "Concept groups reduce some wording false positives but do not establish semantic intent; founder confirmation takes precedence.",
    }


def build_session_review(goal: str | None, observed_task: str | None, events: Iterable[dict[str, Any]], evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "session": summarize_session(events),
        "goal_alignment": assess_goal_alignment(goal, observed_task, evidence),
    }

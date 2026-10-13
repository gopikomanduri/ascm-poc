"""Evidence-driven founder decision engine for proactive ASCM interventions.

The engine ranks decision paths, not autonomous actions. It only scores paths supported
by explicit evidence, reports missing evidence, and never executes or publishes anything.
Historical founder feedback may make a small, bounded adjustment after a minimum sample;
it cannot replace current evidence or turn heuristics into calibrated probabilities.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


DECISION_PATHS = (
    "build", "reuse", "simplify", "customer_validate", "launch_or_sell", "pause_or_stop",
)
POSITIVE_FEEDBACK = {"helpful", "accepted", "acted_on"}
NEGATIVE_FEEDBACK = {"not_helpful", "dismissed", "incorrect"}
MIN_FEEDBACK_PER_PATH = 5
MAX_FEEDBACK_ADJUSTMENT = 6


def _feedback_adjustments(project_path: str | Path | None = None) -> dict[str, dict[str, int]]:
    """Return conservative, bounded path adjustments from explicitly rated, delivered interventions."""
    root = Path(project_path or os.getenv("ASCM_WATCH_PATH") or ".").resolve()
    path = root / ".ascm_history" / "intervention_quality.json"
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(records, list):
        return {}
    counts: dict[str, dict[str, int]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("delivery_confirmed", True) is not True:
            continue
        path_name = record.get("recommended_path")
        feedback = record.get("feedback")
        if not isinstance(path_name, str) or not path_name:
            continue
        bucket = counts.setdefault(path_name, {"positive": 0, "negative": 0})
        if feedback in POSITIVE_FEEDBACK:
            bucket["positive"] += 1
        elif feedback in NEGATIVE_FEEDBACK:
            bucket["negative"] += 1
    result = {}
    for path_name, bucket in counts.items():
        positive, negative = bucket["positive"], bucket["negative"]
        rated = positive + negative
        if rated < MIN_FEEDBACK_PER_PATH:
            continue
        # Beta(2,2) smoothing shrinks small samples toward neutral feedback.
        smoothed_rate = (positive + 2) / (rated + 4)
        adjustment = round((smoothed_rate - 0.5) * 2 * MAX_FEEDBACK_ADJUSTMENT)
        result[path_name] = {
            "adjustment": max(-MAX_FEEDBACK_ADJUSTMENT, min(MAX_FEEDBACK_ADJUSTMENT, adjustment)),
            "rated_interventions": rated,
            "positive": positive,
            "negative": negative,
        }
    return result


class FounderIntelligenceEngine:
    """Evaluate founder decision paths using explainable, conservative rules."""

    def __init__(self, project_path: str | Path | None = None):
        self.project_path = Path(project_path or os.getenv("ASCM_WATCH_PATH") or ".").resolve()

    def evaluate(
        self,
        *,
        goal: str | None,
        observation: str,
        evidence: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not isinstance(observation, str) or not observation.strip():
            raise ValueError("observation must be a non-empty string")
        if evidence is None:
            evidence = {}
        if not isinstance(evidence, dict):
            raise ValueError("evidence must be a dictionary")

        signals: List[Dict[str, Any]] = []
        missing: List[str] = []
        normalized_goal = goal.strip() if isinstance(goal, str) and goal.strip() else None

        def signal(path: str, score: int, reason: str, evidence_key: str | None = None) -> None:
            signals.append({
                "path": path, "score": max(0, min(100, score)),
                "reason": reason, "evidence_key": evidence_key,
            })

        if not normalized_goal:
            missing.append("founder_confirmed_goal")
        if not evidence.get("task_description"):
            missing.append("task_description")
        if not evidence.get("customer_evidence"):
            missing.append("customer_evidence")
        reuse_candidates = evidence.get("reuse_candidates")
        if not reuse_candidates:
            missing.append("reuse_candidates")
        elif isinstance(reuse_candidates, list) and any(
            isinstance(item, dict) and (
                item.get("archived") is True
                or str(item.get("license", "")).lower() in {"", "not detected", "none", "unknown"}
                or (isinstance(item.get("suitability_score"), (int, float)) and item.get("suitability_score", 0) < 65)
            ) for item in reuse_candidates
        ) and not any(
            isinstance(item, dict) and item.get("archived") is not True
            and str(item.get("license", "")).lower() not in {"", "not detected", "none", "unknown"}
            and isinstance(item.get("suitability_score"), (int, float))
            and item.get("suitability_score", 0) >= 65 for item in reuse_candidates
        ):
            missing.append("verified_reuse_fit_and_license")
        if not evidence.get("milestone"):
            missing.append("measurable_milestone")

        task = evidence.get("task_description")
        customer_evidence = evidence.get("customer_evidence")
        milestone = evidence.get("milestone")
        tests_failed = evidence.get("tests_failed") is True
        repeated_failures = evidence.get("repeated_failures") is True
        scope_risk = evidence.get("scope_risk") is True
        launch_ready = evidence.get("launch_readiness_verified") is True
        user_demand = evidence.get("user_demand_verified") is True
        explicit_stop_signal = evidence.get("explicit_stop_signal") is True

        if normalized_goal and task:
            signal("build", 65 if milestone else 45,
                   "A stated goal and task exist; implementation priority still depends on a measurable milestone.", "task_description")
        else:
            signal("build", 10, "Insufficient confirmed context to conclude that more implementation is the right move.")

        if reuse_candidates:
            scored = [item for item in reuse_candidates if isinstance(item, dict) and isinstance(item.get("suitability_score"), (int, float))] if isinstance(reuse_candidates, list) else []
            credible = [item for item in scored if item.get("archived") is not True
                        and str(item.get("license", "")).lower() not in {"", "not detected", "none", "unknown"}
                        and item.get("suitability_score", 0) >= 65]
            if credible:
                score = min(80, int(max(item.get("suitability_score", 0) for item in credible)))
                signal("reuse", score, "At least one public candidate has relatively stronger maintenance/license metadata; feature fit, security, compatibility, and total integration cost still require review.", "reuse_candidates")
            elif scored:
                signal("reuse", 35, "Public candidates were found, but available metadata does not establish a credible reuse option. Check feature fit, license, maintenance, and security before treating reuse as suitable.", "reuse_candidates")
            else:
                signal("reuse", 65, "Reuse candidates were supplied but their suitability metadata is incomplete; inspect feature fit, license, maintenance, security, and integration cost before deciding.", "reuse_candidates")
        else:
            signal("reuse", 25, "Reuse has not been evaluated; this is a check to perform, not evidence that a suitable tool exists.")

        if scope_risk or repeated_failures:
            signal("simplify", 80, "Observed scope risk or repeated failure supports reducing the problem to a smaller verifiable slice.", "scope_risk" if scope_risk else "repeated_failures")
        else:
            signal("simplify", 35, "Consider simplification if the current plan exceeds the evidence or milestone.")

        if not customer_evidence:
            signal("customer_validate", 75, "No customer evidence was supplied; a small validation experiment can reduce demand uncertainty.")
        elif user_demand:
            signal("customer_validate", 35, "Demand is marked verified; validate remaining assumptions rather than repeating discovery by default.", "customer_evidence")
        else:
            signal("customer_validate", 65, "Customer evidence exists but demand is not explicitly marked verified; assess its strength.", "customer_evidence")

        if launch_ready and user_demand:
            signal("launch_or_sell", 85, "Launch readiness and user demand are explicitly marked verified; consider a bounded launch or sales test.", "launch_readiness_verified")
        elif launch_ready:
            signal("launch_or_sell", 55, "Readiness is marked verified, but customer demand is not; consider a limited validation or launch test.", "launch_readiness_verified")
        else:
            signal("launch_or_sell", 15, "Launch readiness has not been verified; do not infer that the product is ready to sell.")

        if explicit_stop_signal or (tests_failed and repeated_failures):
            signal("pause_or_stop", 75, "An explicit stop signal or repeated failures warrants a deliberate pause and review.", "explicit_stop_signal" if explicit_stop_signal else "repeated_failures")
        else:
            signal("pause_or_stop", 20, "No explicit stop evidence was supplied; stopping is an option to review, not a conclusion.")

        # Feedback is a weak tie-breaker, never a substitute for fresh evidence.
        adjustments = _feedback_adjustments(self.project_path)
        for item in signals:
            learned = adjustments.get(item["path"])
            if learned:
                base = item["score"]
                item["score"] = max(0, min(100, base + learned["adjustment"]))
                item["historical_feedback_adjustment"] = learned["adjustment"]
                item["historical_feedback_count"] = learned["rated_interventions"]
                item["reason"] += (
                    f" Historical founder feedback adjusted this score by {learned['adjustment']:+d} "
                    f"points from {learned['rated_interventions']} rated, delivered interventions; "
                    "this is a weak preference signal, not causal proof."
                )
        ranked = sorted(enumerate(signals), key=lambda pair: (-pair[1]["score"], pair[0]))
        top = ranked[0][1]
        confidence = "low" if missing else ("high" if top["evidence_key"] and top["score"] >= 75 else "medium")
        return {
            "goal": normalized_goal,
            "observation": observation,
            "ranked_paths": [item for _, item in ranked],
            "recommended_path": top["path"] if normalized_goal else "clarify_goal",
            "confidence": confidence if normalized_goal else "low",
            "missing_evidence": missing,
            "requires_founder_input": not normalized_goal,
            "learning_adjustments_applied": {key: value for key, value in adjustments.items()},
            "execution_performed": False,
            "policy": "Recommendations only; no actions are executed by the founder intelligence engine.",
        }

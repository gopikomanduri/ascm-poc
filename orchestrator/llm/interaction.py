"""Provider-independent model routing for ASCM agents.

Routing is deliberately explicit: no silent cloud/local failover occurs because
that could change data privacy, cost, latency, or model-quality guarantees.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from orchestrator.agents.base import BaseLLMProvider, get_configured_provider


@dataclass(frozen=True)
class ModelRoute:
    provider: Optional[str] = None
    model: Optional[str] = None
    tier: str = "primary"
    task: str = "general"


# Lightweight classification is advisory; deployments can override every route.
_AGENT_TASKS = {
    "ProductAgent": "product_discovery",
    "ProductManagerAgent": "product_discovery",
    "TestingAgent": "testing",
    "ContinuousFounderTestingRuntime": "testing",
    "MentorAgent": "mentoring",
    "ProactiveMentor": "mentoring",
    "GTMStatusAgent": "gtm",
    "GTMAgent": "gtm",
    "CodeReviewAgent": "code_review",
    "CodeCriticAgent": "code_review",
    "ArchitectureReviewAgent": "deep_reasoning",
    "ArchitectureCriticAgent": "deep_reasoning",
    "BusinessStrategyAgent": "deep_reasoning",
    "RevenueROIAgent": "deep_reasoning",
}

# Task aliases let multiple agents share a route without sharing code.
_TASK_ALIASES = {
    "routine": "fast",
    "classification": "fast",
    "summarization": "fast",
    "testing": "fast",
    "product_discovery": "primary",
    "mentoring": "primary",
    "gtm": "primary",
    "code_review": "reasoning",
    "deep_reasoning": "reasoning",
    "reasoning": "reasoning",
}


def _normalise(value: str) -> str:
    # Preserve CamelCase word boundaries so ProductAgent maps to PRODUCT_AGENT.
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value)
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _parse_routes() -> dict[str, dict[str, Any]]:
    raw = os.environ.get("ASCM_LLM_ROUTES_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("ASCM_LLM_ROUTES_JSON must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("ASCM_LLM_ROUTES_JSON must be a JSON object keyed by agent or task")
    routes: dict[str, dict[str, Any]] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ValueError("Each ASCM_LLM_ROUTES_JSON entry must map a string key to an object")
        unknown = set(value) - {"provider", "model", "tier", "task"}
        if unknown:
            raise ValueError(f"Unknown route fields for {key}: {', '.join(sorted(unknown))}")
        routes[key] = value
    return routes


class LLMInteractionLayer:
    """Central routing facade used by agents; provider implementations remain reusable."""

    def __init__(self, routes: Optional[dict[str, dict[str, Any]]] = None):
        candidate_routes = _parse_routes() if routes is None else routes
        if not isinstance(candidate_routes, dict):
            raise ValueError("LLM routes must be a JSON object keyed by agent or task")
        self.routes: dict[str, dict[str, Any]] = {}
        for key, value in candidate_routes.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError("Each LLM route must map a string key to an object")
            unknown = set(value) - {"provider", "model", "tier", "task"}
            if unknown:
                raise ValueError(f"Unknown route fields for {key}: {', '.join(sorted(unknown))}")
            self.routes[key] = value

    @staticmethod
    def infer_task(agent_name: str) -> str:
        if agent_name in _AGENT_TASKS:
            return _AGENT_TASKS[agent_name]
        lowered = agent_name.lower()
        if any(word in lowered for word in ("review", "critic", "architecture", "strategy", "reason")):
            return "deep_reasoning" if "architecture" in lowered or "strategy" in lowered else "code_review"
        if any(word in lowered for word in ("test", "qa", "validation")):
            return "testing"
        if any(word in lowered for word in ("mentor", "founder")):
            return "mentoring"
        if any(word in lowered for word in ("gtm", "sales", "marketing")):
            return "gtm"
        if any(word in lowered for word in ("product", "prd", "requirement")):
            return "product_discovery"
        return "general"

    def resolve(self, agent_name: str, tier: str = "primary", model: Optional[str] = None) -> ModelRoute:
        task = self.infer_task(agent_name)
        # Apply broad defaults first and agent-specific routes last so specificity wins.
        candidates = (
            "default",
            tier,
            _TASK_ALIASES.get(task, ""),
            task,
            _normalise(agent_name),
            agent_name,
        )
        selected: dict[str, Any] = {}
        for key in candidates:
            if key and key in self.routes:
                selected.update(self.routes[key])

        # Explicit per-agent environment variables are supported without requiring JSON.
        env_prefixes = (f"ASCM_LLM_ROUTE_{_normalise(agent_name)}",)
        for prefix in env_prefixes:
            provider = os.environ.get(f"{prefix}_PROVIDER")
            routed_model = os.environ.get(f"{prefix}_MODEL")
            routed_tier = os.environ.get(f"{prefix}_TIER")
            if provider:
                selected["provider"] = provider
            if routed_model:
                selected["model"] = routed_model
            if routed_tier:
                selected["tier"] = routed_tier

        selected_model = model or selected.get("model")
        selected_tier = str(selected.get("tier") or tier)
        return ModelRoute(
            provider=str(selected["provider"]).strip().lower() if selected.get("provider") else None,
            model=str(selected_model) if selected_model else None,
            tier=selected_tier,
            task=str(selected.get("task") or task),
        )

    def provider_for_agent(
        self,
        agent_name: str,
        tier: str = "primary",
        model: Optional[str] = None,
    ) -> BaseLLMProvider:
        route = self.resolve(agent_name, tier=tier, model=model)
        return get_configured_provider(
            provider_name=route.provider,
            model=route.model,
            tier=route.tier,
            agent_name=agent_name,
        )

    def describe_route(self, agent_name: str, tier: str = "primary", model: Optional[str] = None) -> dict[str, str]:
        route = self.resolve(agent_name, tier=tier, model=model)
        return {
            "agent": agent_name,
            "task": route.task,
            "provider": route.provider or os.environ.get("LLM_PROVIDER", "auto"),
            "model": route.model or "provider-default",
            "tier": route.tier,
        }


def provider_for_agent(agent_name: str, tier: str = "primary", model: Optional[str] = None) -> BaseLLMProvider:
    """Compatibility-friendly entry point for agent constructors; reads current environment."""
    return LLMInteractionLayer().provider_for_agent(agent_name, tier=tier, model=model)


def resolve_route(agent_name: str, tier: str = "primary", model: Optional[str] = None) -> dict[str, str]:
    return LLMInteractionLayer().describe_route(agent_name, tier=tier, model=model)

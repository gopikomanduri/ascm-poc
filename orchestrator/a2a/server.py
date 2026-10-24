"""A2A 1.0 gateway for ASCM's local-first agent roster.

This gateway exposes one standard A2A endpoint and routes requests to named ASCM
specialists through the ASCM extension metadata field `ascm.agent_id`.
It does not grant agents permission to perform external side effects.
"""
from __future__ import annotations

import inspect
import json
import logging
import os
from typing import Any

from fastapi import FastAPI
from orchestrator.a2a.contracts import HandoffEnvelope
from orchestrator.a2a.coordinator import A2ACoordinator, HandoffError
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    Part,
    Task,
    TaskState,
    TaskStatus,
)

logger = logging.getLogger("ASCM.A2A")

# Only this exact discovery endpoint is intentionally public when token auth is enabled.
PUBLIC_AGENT_CARD_PATH = "/.well-known/agent-card.json"

# Keep aliases stable even if Python class names or module paths change.
AGENT_ALIASES = {
    # Keep this list aligned with implemented classes in orchestrator.agents.all_agents.
    "discovery": "DiscoveryAgent",
    "product": "ProductAgent",
    "business_strategy": "BusinessStrategyAgent",
    "gtm": "BusinessStrategyAgent",
    "revenue_roi": "RevenueROIAgent",
    "design": "DesignAgent",
    "architect": "ArchitectAgent",
    "architecture_review": "ArchitectureReviewAgent",
    "planner": "PlannerAgent",
    "database": "DatabaseAgent",
    "coder": "GoCoderAgent",
    "security_auditor": "SecurityAuditorAgent",
    "code_review": "CodeReviewAgent",
    "checker": "CheckerAgent",
    "compliance": "ComplianceAgent",
    "qa": "QAAgent",
    "sre": "SREAgent",
    "apm": "APMAgent",
    "oncall": "OnCallAgent",
    "sales": "SalesAgent",
    "marketing": "MarketingAgent",
    "advertising": "AdAgent",
    "seo": "SEOAgent",
    "mentor": "ASCMProactiveMentor",
}
AGENT_DESCRIPTIONS = {
    "discovery": "Classify repository topology and cross-repository dependencies.",
    "product": "Clarify requirements, identify ambiguity and produce a product specification.",
    "business_strategy": "Produce domain-specific market and go-to-market strategy.",
    "gtm": "Alias for the Business Strategy specialist's go-to-market capabilities.",
    "revenue_roi": "Analyze ROI, pricing, revenue metrics and unit economics.",
    "design": "Produce high-level and low-level software designs.",
    "architect": "Decompose requirements into implementation tasks and contracts.",
    "architecture_review": "Adversarially review architecture and non-functional requirements.",
    "planner": "Plan implementation steps and dependencies.",
    "database": "Assist with database and data-model tasks.",
    "coder": "Generate implementation proposals and code artifacts.",
    "security_auditor": "Review proposed artifacts for security issues.",
    "code_review": "Adversarially review code and tests.",
    "checker": "Check implementation artifacts.",
    "compliance": "Review applicable compliance requirements.",
    "qa": "Design quality assurance and test plans.",
    "sre": "Review reliability, deployment and operational concerns.",
    "apm": "Analyze application performance concerns.",
    "oncall": "Assist with incident response and operational triage.",
    "sales": "Assist with sales research and messaging.",
    "marketing": "Assist with marketing strategy and content.",
    "advertising": "Assist with advertising proposals.",
    "seo": "Assist with search optimization proposals.",
    "mentor": "Clarify founder goals, challenge assumptions and recommend validation steps.",
}


def available_agent_ids() -> list[str]:
    """Return all stable, externally routable ASCM specialist IDs."""
    return sorted(AGENT_ALIASES)


def build_agent_card(host: str = "127.0.0.1", port: int = 8090) -> AgentCard:
    skills = [
        AgentSkill(
            id=agent_id,
            name=agent_id.replace("_", " ").title(),
            description=AGENT_DESCRIPTIONS[agent_id],
            tags=["ascm", "founder-workflow", agent_id],
            examples=[f"Use the {agent_id} specialist to help with this task."],
            input_modes=["text"],
            output_modes=["text"],
        )
        for agent_id in available_agent_ids()
        if agent_id != "gtm"
    ]
    return AgentCard(
        name="ASCM Agent Gateway",
        description=(
            "A2A 1.0 gateway for ASCM's product, engineering, governance, GTM, "
            "operations and founder-mentor specialists. Route a task with the "
            "ASCM extension metadata field ascm.agent_id."
        ),
        provider=AgentProvider(
            organization="ASCM",
            url="https://github.com/gopikomanduri/ascm-poc",
        ),
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["text"],
        default_output_modes=["text", "application/json"],
        skills=skills,
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=f"http://{host}:{port}/a2a/jsonrpc",
            )
        ],
    )


def _extract_prompt(context: RequestContext) -> str:
    prompt = context.get_user_input()
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("A2A message must contain a non-empty text part.")
    if len(prompt) > 20000:
        raise ValueError("A2A text input exceeds the 20000-character limit.")
    return prompt.strip()


def _requested_agent(context: RequestContext) -> str:
    message = context.message
    metadata = getattr(message, "metadata", None) or {}
    if not isinstance(metadata, dict):
        # A2A SDK v1 represents protobuf Struct metadata as a message, not a dict.
        try:
            from google.protobuf.json_format import MessageToDict
            metadata = MessageToDict(metadata)
        except (TypeError, ValueError):
            metadata = {}
    ascm_metadata = metadata.get("ascm", {}) if isinstance(metadata, dict) else {}
    agent_id = ascm_metadata.get("agent_id") if isinstance(ascm_metadata, dict) else None
    if not isinstance(agent_id, str) or agent_id not in AGENT_ALIASES:
        raise ValueError(
            "Specify a supported specialist using message.metadata.ascm.agent_id."
        )
    return agent_id


def _run_specialist(agent_id: str, prompt: str) -> str:
    """Lazily instantiate and invoke the requested specialist.

    BaseAgent-derived specialists receive a text task through their common call
    interface. Other agent implementations are invoked via a conservative
    signature adapter. Agent-specific execution never implies external-action
    permission.
    """
    if agent_id == "mentor":
        from orchestrator.mentor.proactive_mentor import ASCMProactiveMentor

        workspace = os.environ.get("ASCM_A2A_WORKSPACE", ".")
        result = ASCMProactiveMentor(repo_path=workspace).clarify_goal_and_pre_validate(prompt)
        return json.dumps(result, ensure_ascii=False)

    from orchestrator.agents import all_agents

    class_name = AGENT_ALIASES[agent_id]
    agent_class = getattr(all_agents, class_name, None)
    if agent_class is None:
        raise ValueError(f"ASCM specialist '{agent_id}' is not available in this build.")

    agent = agent_class()
    common_call = getattr(agent, "call", None)
    if callable(common_call):
        result = common_call(prompt)
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)

    run = getattr(agent, "run", None)
    if not callable(run):
        raise ValueError(f"ASCM specialist '{agent_id}' has no callable task interface.")

    signature = inspect.signature(run)
    values: dict[str, Any] = {
        "goal": prompt,
        "user_goal": prompt,
        "user_input": prompt,
        "requirement": prompt,
        "query": prompt,
        "prompt": prompt,
        "description": prompt,
        "clarified_prd": prompt,
        "contracts": {},
        "conversation_history": [],
        "files": {},
        "hld": "",
        "lld": "",
        "business_strategy": {},
        "kg_context": "",
    }
    kwargs: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if name in {"self", "cls"} or parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        if name in values:
            kwargs[name] = values[name]
        elif parameter.default is inspect.Parameter.empty:
            raise ValueError(
                f"Specialist '{agent_id}' requires unsupported input '{name}'; "
                "an explicit adapter is needed before this task can run."
            )
    result = run(**kwargs)
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)


class ASCMGatewayExecutor(AgentExecutor):
    """A2A executor which routes messages through ASCM governance before dispatch."""

    def __init__(self, coordinator: A2ACoordinator | None = None):
        if coordinator is None:
            handlers = {
                agent_id: (lambda handoff, selected=agent_id: {"answer": _run_specialist(selected, handoff.goal)})
                for agent_id in AGENT_ALIASES
            }
            # Each specialist/provider owns its bounded retry policy. Retrying the entire
            # handler can duplicate expensive LLM calls and hold an A2A task open
            # until the outer deadline, so one dispatch is the safe default.
            coordinator = A2ACoordinator(handlers=handlers, max_attempts=1)
        self.coordinator = coordinator

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id
        context_id = context.context_id
        if not task_id or not context_id or not context.message:
            raise ValueError("A2A task, context and message identifiers are required.")

        updater = TaskUpdater(event_queue=event_queue, task_id=task_id, context_id=context_id)
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                history=[context.message],
            )
        )
        await updater.start_work()
        agent_id = "unknown"
        try:
            agent_id = _requested_agent(context)
            prompt = _extract_prompt(context)
            handoff = HandoffEnvelope(
                goal=prompt,
                sender="a2a_gateway",
                recipient=agent_id,
                expected_output="Specialist response as text",
                task_id=task_id,
                correlation_id=context_id,
            )
            coordinated = await __import__("asyncio").to_thread(
                self.coordinator.dispatch, handoff, timeout_seconds=90.0
            )
            answer = coordinated["answer"]
        except Exception as exc:
            logger.exception("A2A specialist execution failed: %s", agent_id)
            await updater.add_artifact(
                parts=[Part(text=f"ASCM specialist '{agent_id}' failed: {type(exc).__name__}: {exc}")],
                name="error",
                last_chunk=True,
            )
            await updater.failed()
            return
        await updater.add_artifact(
            parts=[Part(text=answer)],
            name=f"{agent_id}-response",
            last_chunk=True,
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id
        context_id = context.context_id
        if task_id and context_id:
            updater = TaskUpdater(event_queue=event_queue, task_id=task_id, context_id=context_id)
            await updater.cancel()


def _install_access_control(app: FastAPI, host: str) -> None:
    """Reject DNS-rebinding, browser cross-origin calls and (when configured/required) unauthenticated callers.

    A2A clients are programs, not browsers, so any request carrying an Origin header is refused.
    """
    import hmac

    from starlette.responses import JSONResponse

    token = os.environ.get("ASCM_A2A_TOKEN", "")
    remote = host not in {"127.0.0.1", "localhost", "::1"}
    if remote and not token:
        raise ValueError("ASCM_A2A_TOKEN is required when the A2A gateway is reachable beyond loopback.")
    allowed_hosts = {"127.0.0.1", "localhost", "::1", "[::1]"} | {
        h.strip().lower() for h in os.environ.get("ASCM_A2A_ALLOWED_HOSTS", "").split(",") if h.strip()
    }

    @app.middleware("http")
    async def _access_control(request, call_next):
        if request.headers.get("origin"):
            return JSONResponse({"error": "browser cross-origin requests are not allowed"}, status_code=403)
        host_header = request.headers.get("host", "").lower()
        bare = host_header.split("]")[0] + "]" if host_header.startswith("[") else host_header.rsplit(":", 1)[0] if host_header.count(":") == 1 else host_header
        if not remote and bare not in allowed_hosts:
            return JSONResponse({"error": "host not allowed"}, status_code=403)
        # The public agent card is discoverable; everything else needs the token whenever one is configured.
        if token and request.url.path != PUBLIC_AGENT_CARD_PATH:
            supplied = request.headers.get("authorization", "")
            expected = f"Bearer {token}"
            if not hmac.compare_digest(supplied.encode(), expected.encode()):
                return JSONResponse({"error": "missing or invalid bearer token"}, status_code=401)
        return await call_next(request)


def create_app(host: str | None = None, port: int | None = None) -> FastAPI:
    """Create the ASCM A2A 1.0 JSON-RPC application."""
    host = host or os.environ.get("ASCM_A2A_HOST", "127.0.0.1")
    port = port or int(os.environ.get("ASCM_A2A_PORT", "8090"))
    if host not in {"127.0.0.1", "localhost", "::1"} and not os.environ.get("ASCM_A2A_ALLOW_REMOTE", "").lower() in {"1", "true", "yes"}:
        raise ValueError("A2A binds to loopback by default; set ASCM_A2A_ALLOW_REMOTE=1 only behind authenticated TLS.")
    card = build_agent_card(host=host, port=port)
    handler = DefaultRequestHandler(
        agent_executor=ASCMGatewayExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = FastAPI(title="ASCM A2A Gateway", version="1.0.0")
    _install_access_control(app, host)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card=card),
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler=handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=False,
        ),
    )
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.a2a.server:app",
        host=os.environ.get("ASCM_A2A_HOST", "127.0.0.1"),
        port=int(os.environ.get("ASCM_A2A_PORT", "8090")),
        reload=False,
    )

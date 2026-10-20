# ASCM A2A 1.0 Agent Gateway

ASCM uses the official `a2a-sdk` Python implementation and exposes a single A2A 1.0 JSON-RPC gateway for its local specialist roster. The stable ASCM extension key `message.metadata.ascm.agent_id` selects a specialist. The gateway's Agent Card advertises each routable specialist as a skill.

## Start locally

```bash
pip install -r requirements.txt
ASCM_A2A_HOST=127.0.0.1 ASCM_A2A_PORT=8090 python -m orchestrator.a2a.server
```

Agent Card: `http://127.0.0.1:8090/.well-known/agent-card.json`

JSON-RPC endpoint: `http://127.0.0.1:8090/a2a/jsonrpc`

The server binds to loopback by default. Do not expose it to a network unless it is placed behind authenticated TLS and a suitable authorization boundary. Remote binding requires the explicit `ASCM_A2A_ALLOW_REMOTE=1` opt-in; this flag is not authentication.

## Routing a task

Use a standard A2A 1.0 `message/send` JSON-RPC request. The A2A Message must contain a text Part and the ASCM extension metadata:

```json
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "method": "message/send",
  "params": {
    "message": {
      "messageId": "message-1",
      "role": "user",
      "parts": [{"text": "Review this feature idea and identify missing requirements."}],
      "metadata": {"ascm": {"agent_id": "product"}}
    }
  }
}
```

Supported IDs are listed in the Agent Card: discovery, product, business_strategy, revenue_roi, design, architect, architecture_review, planner, database, coder, security_auditor, code_review, checker, compliance, qa, sre, apm, oncall, sales, marketing, advertising, seo and mentor. `gtm` is accepted as a routing alias for `business_strategy`, but is not duplicated in the Agent Card. The roster is expected to stay aligned with implemented specialist classes in `orchestrator.agents.all_agents` plus the separately implemented Founder Mentor.

## Scope and safety boundaries

- This gateway uses the A2A task lifecycle and standard JSON-RPC binding; ASCM's specialist routing is an extension, not a custom wire protocol.
- Specialists are lazily instantiated and invoked through their available task interface. An unsupported signature fails explicitly instead of silently claiming success.
- The Mentor writes to the workspace selected by `ASCM_A2A_WORKSPACE` (default: current directory). Use a disposable workspace for initial tests.
- A2A task routing does not grant permission to commit code, publish content, contact customers or perform other external actions. Those operations remain subject to ASCM's existing approval controls.
- Task state is currently in memory and is lost when the gateway restarts. This is a local interoperability slice, not yet a production multi-user service.
- The gateway advertises JSON-RPC only. Add other A2A bindings only after interoperability tests justify them.
- Remote deployment still requires authenticated identity, per-agent authorization, rate limiting, durable task storage, observability and end-to-end tests with real A2A clients before production use.


## ASCM governance envelope (extension profile v1.0)

Standard A2A remains the transport and task lifecycle. ASCM adds a versioned governance envelope in `orchestrator/a2a/contracts.py` with task and correlation IDs, sender/recipient, goal, evidence with confidence, expected output, proposed action, scoped approval, status, result/error and follow-up. The extension is deliberately versioned independently of the A2A protocol.

The first local coordinator is in `orchestrator/a2a/coordinator.py`. It validates the recipient, records audit events, retries transient handler errors within a bounded attempt count, rejects idempotency-key reuse with a different payload, returns prior results for identical replays, escalates conflicting recommendations, and blocks proposed side effects unless the approval record names the exact action and includes an approver, timestamp and approval ID.

**Important limits:** the coordinator is wired into the A2A server request path, and the HTTP integration test exercises JSON-RPC through that path. It is still an in-process foundation: it does not enforce authenticated caller identity, forcibly interrupt a handler that exceeds its deadline, or persist idempotency/audit state across restarts. Do not expose it as production-ready. Before production, use durable transactional storage, add caller/agent authorization and cancellation, and expand real-client interoperability tests.

## Testing Agent strategy

The Testing Agent is an independent evaluator, not an execution approver. Acceptance coverage must exercise founder journeys through the real ASCM interface and verify:
- Mentor prompts are relevant to the founder's stated goal and distinguish evidence from assumptions.
- GTM proposals are not reported as published/sent until a permitted, verified action occurs.
- External actions require explicit, action-scoped consent; routing or recommendation never implies permission.
- Handoffs retain correlation/task identity, handle retries and duplicates safely, and escalate disagreement.
- Learning counts verified replies, meetings, qualified opportunities and conversions separately from generated assets.
- The evaluator reports evidence and failed criteria; it cannot approve releases or grant permissions.

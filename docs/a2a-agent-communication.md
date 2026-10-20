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

Supported IDs are listed in the Agent Card: discovery, product, business_strategy, revenue_roi, design, architect, architecture_review, planner, database, coder, security_auditor, code_review, checker, compliance, qa, sre, apm, oncall, sales, marketing, advertising, seo and mentor. `gtm` is accepted as a routing alias for `business_strategy`, but is not duplicated in the Agent Card.

## Scope and safety boundaries

- This gateway uses the A2A task lifecycle and standard JSON-RPC binding; ASCM's specialist routing is an extension, not a custom wire protocol.
- Specialists are lazily instantiated and invoked through their available task interface. An unsupported signature fails explicitly instead of silently claiming success.
- The Mentor writes to the workspace selected by `ASCM_A2A_WORKSPACE` (default: current directory). Use a disposable workspace for initial tests.
- A2A task routing does not grant permission to commit code, publish content, contact customers or perform other external actions. Those operations remain subject to ASCM's existing approval controls.
- Task state is currently in memory and is lost when the gateway restarts. This is a local interoperability slice, not yet a production multi-user service.
- The gateway advertises JSON-RPC only. Add other A2A bindings only after interoperability tests justify them.
- Remote deployment still requires authenticated identity, per-agent authorization, rate limiting, durable task storage, observability and end-to-end tests with real A2A clients before production use.

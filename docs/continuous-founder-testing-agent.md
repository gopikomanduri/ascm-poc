# Continuous Founder-Simulation Testing Agent

## One-terminal workflow

From the ASCM repository root, activate the project's virtual environment and run:

```bash
python -m orchestrator.testing_agent.runtime --workspace . --rounds-per-session 8
```

The runner starts the local A2A gateway on `127.0.0.1:8090` if it is not already available, then runs three cooperating loops in the same terminal:

1. **Testing Agent / simulated founder** sends A2A 1.0 JSON-RPC requests to ASCM's ProductAgent, receives its clarification questions, answers from a scenario profile, carries the transcript forward, and repeats across product-risk areas.
2. **Goal Agent** periodically records the branch, latest commit, working-tree state, testing session, question/round counts, and open findings in `.ascm_history/testing_agent_status.json`.
3. **GTM Status Agent** watches for a new repository commit, drafts a status-based social post under `artifacts/gtm_cycles/`, and sends an action-scoped LinkedIn permission request to the Testing Agent. It deduplicates requests by commit and persists its last requested fingerprint.

The process runs continuously until Ctrl-C. The Testing Agent writes its report to `.ascm_history/testing_agent_report.json`; GTM permission request outcomes are appended to `.ascm_history/gtm_permission_requests.jsonl`. The A2A gateway log is `.ascm_history/testing_agent_a2a.log`.

## Options

```bash
# One bounded session, useful for CI
python -m orchestrator.testing_agent.runtime --workspace . --sessions 1 --rounds-per-session 4

# Use an already-running A2A gateway
python -m orchestrator.testing_agent.runtime --workspace . --no-start-server

# Load a custom simulated founder profile
python -m orchestrator.testing_agent.runtime --workspace . --scenario /path/to/founder-scenario.json
```

Scenario fields can override the profile's product name, problem, target user, differentiation, alternatives, traction, pricing, security posture, success metrics, and `permission_policy`. The permission policy accepts `deny` (default) or `approve_simulated`.

## Safety contract — do not weaken this in tests

- The simulated founder answers only from the supplied profile. Unknown customer evidence, pricing, conversion, or traction is explicitly marked unknown; it is never fabricated to satisfy ASCM.
- Malformed ProductAgent responses, missing questions while the product is unclear, and interface failures are recorded as findings, not counted as passes.
- Goal/GTM status checks run concurrently with product grilling. The GTM watcher continues polling, but only creates a new permission request for a new commit fingerprint, not for every test round.
- Permission decisions are explicitly marked `is_real_authorization: false`. Even `approve_simulated` only exercises the approval path; **this test harness has no social publishing adapter and never posts to LinkedIn or any other external service**.
- A simulated Testing Agent decision is not the real founder's consent. A production publisher must separately verify a current, attributable, action-scoped human approval before performing any external side effect.
- The gateway is local-loopback by default. Do not expose it remotely without authenticated TLS and caller/agent authorization.

## Acceptance coverage

The tests cover transcript-based multi-turn grilling, deterministic founder answers, unknown-evidence handling, malformed model output, repository status snapshots, GTM draft wording, A2A artifact parsing, and simulated approval/default-deny behavior. The complete repository CI remains the release gate.

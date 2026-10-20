# Continuous Founder-Simulation Testing Agent

## Visible multi-terminal workflow

From the ASCM repository root, activate the project's virtual environment and run:

```bash
python -m orchestrator.testing_agent.runtime --workspace . --visible-terminals --review-delay 5 --rounds-per-session 8
```

On macOS, `--visible-terminals` opens five Terminal windows (Product, Testing/Founder Simulator, Founder Mentor, Goal, and GTM). Each window tails a role-specific log under `.ascm_history/agent_terminals/`. The coordinator still runs in the terminal where you launched the command. The runner starts the local A2A gateway on `127.0.0.1:8090` if it is not already available, then runs three cooperating loops in parallel:

1. **Testing Agent / simulated founder** sends A2A 1.0 JSON-RPC requests to ASCM's ProductAgent, receives its clarification questions, answers from a scenario profile, carries the transcript forward, and repeats across product-risk areas. It then calls the real Founder Mentor over A2A to check that the recommendation is tied to the current goal and includes a measurable next action.
2. **Goal Agent** periodically records the branch, latest commit, working-tree state, A2A gateway health/advertised roster, testing session, question/round counts, and open findings in `.ascm_history/testing_agent_status.json`.
3. **GTM Status Agent** watches for a new repository commit, calls the actual GTM specialist over A2A for internal positioning advice, drafts a status-based social post under `artifacts/gtm_cycles/`, and sends an action-scoped LinkedIn permission request to the Testing Agent. It keeps GTM model recommendations separate from the factual draft, deduplicates requests by commit, and persists its last requested fingerprint.

After every Product Agent question and Testing Agent answer, the coordinator pauses for five seconds by default so you can inspect both sides before the next exchange. Change the delay with `--review-delay N`; set `--review-delay 0` for automated runs. The process runs continuously until Ctrl-C. The Testing Agent writes its report—including explicit acceptance pass/fail for Mentor context, GTM outcome integrity, approval behavior, handoff traceability, and outcome evidence—to `.ascm_history/testing_agent_report.json`; GTM permission request outcomes are appended to `.ascm_history/gtm_permission_requests.jsonl`. The A2A gateway log is `.ascm_history/testing_agent_a2a.log`. The GTM specialist's internal recommendation is saved beside each draft with the `-gtm-review.txt` suffix.

## Options

```bash
# One bounded session, useful for CI (no extra Terminal windows and no review delay)
python -m orchestrator.testing_agent.runtime --workspace . --sessions 1 --rounds-per-session 4 --review-delay 0

# Launch visible per-agent windows on macOS; pause 5 seconds after every Q&A
python -m orchestrator.testing_agent.runtime --workspace . --visible-terminals --review-delay 5 --rounds-per-session 8

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

The tests cover transcript-based multi-turn grilling, Founder Mentor A2A review, deterministic founder answers, unknown-evidence handling, malformed model output, repository status snapshots, GTM draft wording, A2A client-to-gateway round trips, handoff/acceptance gates, and simulated approval/default-deny behavior. The complete repository CI remains the release gate.


## Live terminal logs

The five role logs are `.ascm_history/agent_terminals/product.log`, `testing.log`, `mentor.log`, `goal.log`, and `gtm.log`. Product questions are shown in both Product and Testing windows; founder answers appear in Testing; Mentor recommendations appear in Mentor and Testing. Goal and GTM windows show their respective status/permission events. The harness does not connect to a social publishing adapter, and simulated permission is never real authorization.


## Timestamped conversation story

Each run writes an ordered conversation timeline under `.ascm_history/`:

- `conversation_story.log` — readable story sequence with UTC timestamp, session ID, monotonically increasing event number, speaker, recipient, event type, and full message text.
- `conversation_story.jsonl` — one structured JSON event per line, including task and correlation IDs for A2A handoffs; useful for scripts and analysis.

The timeline records Testing Agent requests to Product/Mentor specialists, specialist responses, Product Agent questions, simulated-founder answers, and failed A2A requests. The console also prints a timestamped story preview. The report JSON contains both log paths. These logs may include full prompts and responses, so keep the local `.ascm_history/` directory private and do not commit it.

Example story:

```text
[2026-10-20T10:24:49+00:00] [session=...] #0001 TESTING AGENT → MENTOR AGENT | REQUEST
    Review this simulated founder/product-discovery session...

[2026-10-20T10:24:50+00:00] [session=...] #0002 MENTOR AGENT → TESTING AGENT | RESPONSE
    Validate the core assumption before building more...
```

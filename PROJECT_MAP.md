# ASCM Project Map

ASCM is a local-first multi-agent engineering and GTM prototype. Its strongest
idea is not a single coding assistant, but a governed workflow that coordinates
requirements, architecture, code generation, review, verification, founder
mentoring, and go-to-market actions.

## Core Runtime

- `main.py` is the CLI entrypoint.
- `orchestrator/orchestrator_core.py` runs the six-phase multi-repo pipeline:
  contract ingestion, topology discovery, requirements clarification, business
  strategy, architecture/task decomposition, code generation/review, and
  verification/commit.
- `orchestrator/contracts.py` parses `SKILL.md`, `SKILLS.md`, and RepoSwarm
  `.arch.md` contracts into repo roles and editable-path allowlists.
- `orchestrator/agents/base.py` provides BYOK/local model support for Gemini,
  OpenAI-compatible APIs, Anthropic, and Ollama.

## Agent Layers

- `orchestrator/agents/all_agents.py` contains the main working agent roster:
  discovery, product, design, architect, planner, coder, database, security,
  business strategy, revenue ROI, architecture review, and code review.
- `orchestrator/agents/checker_agent.py`, `compliance_agent.py`, `qa_agent.py`,
  `sre_agent.py`, `apm_agent.py`, and `oncall_agent.py` are next-generation
  governance and operations agents. They are useful scaffolds, with some mocked
  or early-stage behavior.
- `orchestrator/router/thinking_router.py` chooses CODE_ONLY, GTM_ONLY,
  SALES_ONLY, MARKETING_ONLY, or FULL_STACK profiles based on project intent and
  team gaps.

## Governance, Safety, And Verification

- `orchestrator/engine/sandbox.py` blocks writes outside repo contracts and
  protected paths.
- `orchestrator/engine/verifier.py` detects Go, Python, and Node projects,
  runs tests, optionally wraps execution in no-network Docker, and parses test
  output into structured results.
- `orchestrator/security/pii_scrubber.py` redacts common secrets and PII.
- `orchestrator/security/audit_logger.py` writes text and JSONL audit logs for
  phases, LLM calls, governance decisions, verification, and git actions.
- `orchestrator/milestone/` tracks milestone budgets, variance, approvals, and
  Excel exports.

## Knowledge And Domain Intelligence

- `orchestrator/domain/` adapts prompts and reviewer criteria to verticals such
  as Web3, CAD/CAM, healthcare, legaltech, robotics, compilers, and mutual fund
  SLMs. New domains can be synthesized into `.ascm_domains/`.
- `orchestrator/knowledge/blueprint_engine.py` stores local reusable templates
  for common patterns such as Stripe webhooks, JWT auth, telemetry SDKs, token
  rate limiting, and microservice bases.
- `orchestrator/knowledge/cross_repo_graph.py` indexes repos, files, endpoints,
  schemas, imports, and dependency edges, then computes impact radius.

## Mentor And GTM

- `orchestrator/mentor/` implements a proactive founder mentor. It can run as a
  daemon, watch file edits and git activity, and nudge the user when engineering
  effort is outpacing GTM.
- `orchestrator/gtm/` contains the GTM system, split into:
  - `agents/`: marketing, sales (v1 legacy, v2 current), SEO, ads, social-first and executor agents.
  - `channels/`: publishing and delivery: social publisher, lead/outreach adapters, CMS adapter.
  - `strategy/`: `content_variety.py` (angles, hook styles, post history, repetition checks), strategy selector, marketing constraints, anti-procrastination and git monitors,
    repo analyzer, and `claims_guard.py` (keeps generated content honest; facts live in `VERIFIED_FACTS.md`).
  - `zero_setup_launcher.py`: the one-command GTM entry point.
- `orchestrator/mentor/assistant/` is the consent-gated "helping hand": cloud models only with the user's
  permission, otherwise a local Ollama model, otherwise it stops.
- `orchestrator/api/webhooks.py` and `orchestrator/workflows/` sketch the
  intended production shape for inbound replies, campaign metrics, and Temporal
  style workflows. Treat these as architectural scaffolds unless configured with
  real external services.

## Dashboard, Auth, And Onboarding

- `dashboard_server.py` starts the standalone dashboard.
- `orchestrator/dashboard.py` stores live run state and persisted histories.
- `static/landing.html` and `static/onboarding.html` are the UI entry pages.
- `orchestrator/auth/` supports local OTP-style auth, BYOK preference storage,
  and GitHub OAuth scaffolding.
- `orchestrator/product_wizard.py` analyzes repos, discovers or scaffolds
  `SKILLS.md`, and recommends agent rosters.

## Benchmarks, Proofs, And Demos

- `tools/mr_bench.py` defines MR-Bench, a multi-repo coordination benchmark.
- `tools/ascm_math_proofs.py` generates the math/positioning whitepaper.
- `products/` contains reference apps for PayPulse Sentinel, Pay Through Crypto,
  CAD/CAM, and the Mutual Funds SLM showcase.
- `experiments/` contains GTM demos and generated experiment outputs.
- `decks/` holds pitch decks; `tools/generate_*.py` rebuild them.

## Current Maturity Guide

- Production-ish prototype: core orchestrator, contracts, sandbox, verifier,
  audit/PII logging, domain adaptation, blueprint engine, dashboard state, mentor
  file watcher, and social publisher.
- Prototype/demo: GTM sales and marketing agents, zero-setup launcher, repo
  analyzer, strategy selector, and reference products.
- Scaffold/roadmap: Temporal workflows, webhook processing, SRE/APM/on-call
  automation, paid ads execution, and some external GTM adapter paths.

## Repo Layout

```
orchestrator/   the product (agents, engine, security, mentor, gtm, domain, knowledge ...)
tests/          unit and integration tests
demos/          runnable end-to-end demos (demo_*.py)
tools/          benchmark, proofs and deck/doc generators
experiments/    GTM experiments and results (experiments/legacy = retired v1 flows)
products/       reference apps used by demos and MR-Bench
docs/           guides/ strategy/ research/ archive/  (see docs/README.md)
decks/ static/ logos/ migrations/ scripts/   assets and ops
```

## Common Commands

```bash
# Run the full test suite (run it to see the current count)
PYTHONPATH=. .venv/bin/pytest tests/ -v
# or standard unittest discovery
.venv/bin/python -m unittest discover -s tests -v

# Run reference product suites
PYTHONPATH=products/paypulse-sentinel/api-gateway .venv/bin/pytest products/paypulse-sentinel/api-gateway/tests/
PYTHONPATH=products/cad-cam-engine .venv/bin/pytest products/cad-cam-engine/tests/

# Launch core dashboard
.venv/bin/python main.py --dashboard-only

# Launch proactive mentor daemon
.venv/bin/python main.py --mentor

# Run GTM social publisher (browser intent + Buffer API fallback)
.venv/bin/python main.py --gtm-publish --goal "Describe what you built"
.venv/bin/python main.py --gtm-zero-setup

# Run benchmarks and mathematical proofs
.venv/bin/python tools/mr_bench.py --list
.venv/bin/python tools/ascm_math_proofs.py --publish
```

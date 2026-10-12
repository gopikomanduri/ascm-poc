# ASCM — AI Engineering Squad for Multi-Repo Codebases

> **Five specialized AI agents. One autonomous sprint. Human approval at every gate.**

ASCM coordinates a squad of AI agents — Product, Architect, Coder, Adversarial Critic, and Security Auditor — to deliver features across **multiple repositories simultaneously**, with a human approval gate before any code is committed.

[![CI](https://github.com/gopikomanduri/ascm-poc/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/gopikomanduri/ascm-poc/actions/workflows/ci-cd.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Open Source](https://img.shields.io/badge/open--source-BYOK-violet)](https://github.com/gopikomanduri/ascm-poc)

---

## The Problem

AI coding tools like Copilot and Cursor modify **one repo in isolation**. When your feature spans a backend API, a consumer SDK, and a web portal, you get broken contracts and failed CI.

ASCM patches all repos **atomically** in the same sprint.

---

## How It Works

```
Stakeholder Goal
     ↓
ProductAgent      → Grills until ≥90% requirement confidence
     ↓
ArchitectAgent    → HLD / LLD + task DAG for human review
     ↓
CoderAgent        → Code + mandatory unit tests across all repos
     ↓
CriticAgent       → Independent model adversarially reviews (different model = no shared bias)
     ↓
Human Gate        → You approve every milestone before any commit
     ↓
Git branch        → Feature branch created, PR raised
```

---

## 🛠️ For Engineers: How ASCM Works Under the Hood

If you are a software engineer exploring this repository, here is how ASCM is architected:

### 1. The Core Architecture
ASCM is not an autocomplete plugin or a chatbot wrapper. It is an **autonomous, local-first multi-repo orchestrator**:
- **Multi-Repo Contract Synchronization**: In microservice and multi-repo architectures, modifying an API endpoint breaks consumer services unless both repositories are updated in lockstep. ASCM reads and writes cross-repo contracts (`SKILLS.md` and schema definitions), synchronizing provider APIs (Go/Python) and consumer clients/SDKs (TypeScript/Python) **in a single atomic sprint**.
- **Role-Specialized Agent Pipeline (`orchestrator/agents/`)**:
  - `ProductAgent`: Interactive requirement clarification. Grills the user for specifications until requirement ambiguity is eliminated (confidence threshold $\ge 90\%$).
  - `ArchitectAgent`: Formulates the High-Level Design (HLD), Low-Level Design (LLD), dependency Directed Acyclic Graph (DAG), and schema contracts.
  - `CoderAgent`: Polyglot code generation (Go, Python, TypeScript) with **mandatory Test-Driven Development (TDD)** — generates implementation code *and* unit test suites (using `testify`, `pytest`, `unittest`, or `jest`).
  - `CodeReviewAgent` / `CriticAgent`: Independent adversarial review. Employs a **different LLM model** than the Coder (e.g. Claude 3.5 Sonnet auditing Gemini 2.5 Flash, or local deepseek-coder) to eliminate same-model self-confirmation bias.
  - `BusinessStrategyAgent`: Generates vertical market economics, competitive battlecards, and GTM strategy for the detected domain.
- **Local-first runtime (`install.sh`, `dashboard_server.py`)**:
  - The dashboard runs on `localhost:8080` by default.
  - Activity history is stored locally in `.ascm_history`.
  - If a cloud LLM provider is configured, prompt/context data sent to that provider leaves the machine. Use a local model and verify provider/network settings for deployments that require offline processing. Local-first behavior alone is not a compliance certification.
- **Engineering Safety & Guardrails**:
  - `orchestrator/engine/sandbox.py`: Enforces strict directory path jail limits preventing unauthorized disk access.
  - `orchestrator/budget/token_forecaster.py`: Pre-flight P50/P90 token forecaster with automatic budget circuit breakers before executing LLM calls.
  - `orchestrator/security/audit_logger.py`: Structured, PII-scrubbed local audit logs with bounded rotation. These logs are not tamper-proof or a compliance certification.
  - `orchestrator/security/pii_scrubber.py`: High-entropy secret and credential scrubber.

### 2. Codebase Directory Map
- `orchestrator/`: The engine core (agents, domain profiles, execution sandbox, token budget forecaster, security, and knowledge engines).
- `products/`: Reference applications generated and tested by ASCM:
  - `products/paypulse-sentinel/`: FinTech Stripe webhook gateway with replay attack prevention and HMAC validation.
  - `products/pay-through-crypto/`: Non-custodial Web3 crypto checkout supporting EVM (Polygon) & Solana with QR code generation.
  - `products/cad-cam-engine/`: CNC machining G-code toolpath slicing engine.
  - External Flagship: [**Mutual Funds SLM Copilot**](https://github.com/gopikomanduri/mutual-funds-slm) — SEBI/SEC compliant edge financial copilot with real-time AMFI data sync, multi-broker gateway, and RBI Account Aggregator.
- `tools/ascm_math_proofs.py`: 6 probabilistic theorems with Monte Carlo simulation scripts (500k trials) proving defect reduction and coordination correctness.
- `tools/mr_bench.py`: Benchmark suite evaluating multi-repo AI coordination tasks.
- `tests/`: Automated unit and regression tests; see the latest GitHub Actions run for the current validated count.

---

## 💼 For Business Leaders: Market Opportunity & ROI

If you are an investor, founder, or engineering executive, here is the commercial and strategic thesis:

### 1. The Market Void: Single-Repo AI Fails at Enterprise Scale
- Today's coding assistants (Copilot, Cursor, Devin) operate inside a **single repository or single file**.
- However, 85%+ of modern tech companies operate **distributed microservices or multi-repo codebases** (e.g., Backend API + Mobile App + Web Portal + Data Pipeline).
- When a developer uses existing AI to modify a backend API, the AI cannot see or update the frontend client or consumer SDK. This causes **silent breaking contract changes, integration outages, and broken CI pipelines** — turning senior engineers into full-time AI code cleanup crews.

### 2. Concrete ROI & Defect Reduction (Backed by Math)
- **Research hypotheses, not production guarantees**: mathematical simulations and benchmark scores in this repository are model-based results. They are not independent empirical evidence of zero outages, specific defect reductions, or customer ROI.
- **Reuse and cost optimization**: blueprint reuse is intended to reduce repeated work; savings must be measured on representative customer workloads before making quantified claims.
- **Deployment and compliance**: local models can support offline deployments, but ASCM does not by itself establish HIPAA, SOC 2, or other regulatory compliance. Customers must validate their full deployment and controls.

### 3. Business Model & Go-To-Market
- **Open-Core / Community (proposed)**: local-first CLI and dashboard with optional Bring-Your-Own-Key (BYOK) providers. Cloud-provider prompts/context leave the machine; offline use requires a local model and verified network isolation.
- **Potential Team Tier ($49/seat/month hypothesis)**: shared blueprint memory, domain adapter packs, and priority support are proposed capabilities/pricing, not an available commercial plan.
- **Potential Enterprise Pilot ($5,000–$10,000 / 90-day hypothesis)**: hands-on deployment and dedicated support are proposed. Local audit logs do not confer SOC 2 compliance or certification.
- **Current status**: this is an evolving proof of concept. Reference applications and tests are not evidence of production adoption, zero technical debt, or commercial readiness.

---

## What's Built (status is validated by CI)

### Core Engine
- Multi-agent orchestrator with 5 specialized agents
- **Cross-Repository Knowledge Graph**: in-memory directed graph linking routes, schemas, and callers across repos with impact radius calculation
- **RepoSwarm & SKILLS.md Interoperability**: natively ingests standardized `.arch.md` architecture discovery files
- Domain adapter: auto-detects FinTech / CAD/CAM / MedTech / Legal / Web3 / Robotics
- Blueprint engine: reuses prior architectural patterns (cost savings are a hypothesis to measure on representative workloads)
- Pre-flight cost radar: P50/P90 token forecaster with circuit breakers
- Mandatory TDD: tests required before milestone confirmation
- Structured local audit logging with PII/credential scrubbing and bounded rotation
- PII scrubber: redacts known secret and personal-data patterns; it cannot guarantee detection of every sensitive value
- Air-gapped local SLM mode via Ollama (Qwen 2.5 Coder, Phi-4)

### Reference Implementations
| Product | Domain | Repos | Tests |
|---|---|:---:|:---:|
| **PayPulse Sentinel** | FinTech SaaS | 2 | 3 ✅ |
| **Pay-Through-Crypto** | Web3 Infrastructure | 2 | 4 ✅ |
| **CNC CAD/CAM Engine** | Advanced Manufacturing | 1 | 2 ✅ |

### Mathematical Foundations
The repository includes mathematical models and simulations for these architectural hypotheses; they are not independent empirical validation of production outcomes:
- **Independent Critic Theorem**: 59.1% defect escape reduction vs same-model review (500k Monte Carlo trials)
- **Multi-Repo Coordination**: P(breaking change) = 78.4% uncoordinated → ~0% with ASCM
- **Defect Escape Equation**: 16.7× improvement, **p-independent** (holds for any LLM)

```bash
python tools/ascm_math_proofs.py --publish   # Verify all proofs yourself
```

### MR-Bench — The Multi-Repo Benchmark
The first benchmark for multi-repo AI coordination tasks (SWE-bench only tests single-repo).
20 tasks across 4 tiers, 4 dimensions scored per task.

```bash
python tools/mr_bench.py --run-all --publish   # Run the benchmark
```

---

## Proactive Founder Mentor: Activity Signals

The mentor can correlate code edits, foreground application transitions, terminal command categories, test outcomes, and opt-in browser hostnames. It records metadata only; it does not capture keystrokes, terminal output, page contents, full URLs, window titles, or screenshots.

- [Commercial readiness and privacy boundaries](docs/commercial-readiness.md)
- [Opt-in Chrome hostname extension](browser_extension/README.md)
- Optional Bash hook: `source /path/to/ascm-poc/scripts/ascm-bash-hook.sh`
- Optional Zsh hook: `source /path/to/ascm-poc/scripts/ascm-zsh-hook.sh`

Security CI runs a deterministic review, Bandit on changed Python files, and a dependency vulnerability audit. A Coco review is only reported as completed when the approved Coco runner is configured in the `ASCM_COCO_AGENT_CMD` GitHub Actions secret and returns a valid result. A missing Coco integration is explicitly reported as unavailable, not passed.

## Quick Start

### Option 1: One-Line Install (Recommended for macOS / Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/gopikomanduri/ascm-poc/main/install.sh | bash
```
During installation, choose the workspace ASCM should monitor. The Proactive Mentor is configured to start at login and will prompt you from the desktop when it detects coding activity; routine mentor prompts do not require CLI commands. Deterministic monitoring works without an LLM API key. Add a provider key in `~/ascm/.env` for richer model-assisted analysis. The dashboard remains optional:
```bash
ascm    # launches dashboard at http://localhost:8080
```

### Option 2: Manual Clone

```bash
git clone https://github.com/gopikomanduri/ascm-poc ~/ascm
cd ~/ascm
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Add your Gemini/OpenAI/Anthropic key
python dashboard_server.py --port 8080
# → Open http://localhost:8080/landing
```

### Option 3: CLI Mode

```bash
python main.py \
  --repos ../my-api ../my-sdk \
  --goal "Add Stripe webhook with HMAC verification"
```

### Option 4: Docker

```bash
docker build -t ascm .
docker run -p 8080:8080 \
  -v $(pwd):/workspace \
  -e GEMINI_API_KEY=your-key \
  ascm
# → Open http://localhost:8080/landing
```

---

## Supported LLM Providers (BYOK)

| Provider | Models | Mode |
|---|---|---|
| Google Gemini | gemini-2.5-flash, gemini-1.5-flash | Cloud |
| OpenAI | gpt-4o, gpt-4o-mini | Cloud |
| Anthropic Claude | claude-3-5-sonnet, claude-3-5-haiku | Cloud |
| Ollama | qwen2.5-coder, phi4, deepseek-coder-v2 | 100% local / air-gapped |

---

## Deploy to Railway (Web Demo Only)

> **Note:** ASCM writes code directly to your local filesystem. The Railway deployment serves as a live cloud preview and web demo of the dashboard UI. For real multi-repo development sprints, run ASCM locally.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/gopikomanduri/ascm-poc)

Set these environment variables in Railway:
```
GEMINI_API_KEY=your-key
GITHUB_CLIENT_ID=your-github-oauth-client-id       # optional, for GitHub login
GITHUB_CLIENT_SECRET=your-github-oauth-client-secret
ASCM_SECRET_KEY=any-random-32-char-string
```

---

## Roadmap

| Phase | Status |
|---|---|
| Core orchestrator + reference implementations | ✅ Done |
| Local CLI & Web dashboard | ✅ Done |
| Mathematical proofs + MR-Bench | ✅ Done |
| One-line installer (`curl \| bash`) | ✅ Done |
| Docker container & Railway demo preview | ✅ Done |
| CLI packaging (Homebrew / pip distribution) | 🔧 Next |
| Live agent MR-Bench run | 🔧 Next |
| Design partner pilots (FinTech/Web3) | 🎯 Seeking |

---

## Contributing & Design Partners

ASCM is open-source and seeking **3–5 design partners** — FinTech or Web3 teams with multi-repo codebases who want to run a 90-day paid pilot.

If you're interested: [founders@ascm.dev](mailto:founders@ascm.dev)

---

## Stage & Honesty

> Pre-revenue, open-source proof-of-concept. Test counts and security status are tracked in [GitHub Actions](https://github.com/gopikomanduri/ascm-poc/actions). **0 paying customers.**
> 
> We'd rather be transparent than oversell. The math and the code are open — evaluate them yourself.

---

*Built with [Google Gemini](https://ai.google.dev) · Open Source (MIT)*

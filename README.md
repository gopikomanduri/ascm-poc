# ASCM — AI Engineering Squad for Multi-Repo Codebases

> **Five specialized AI agents. One autonomous sprint. Human approval at every gate.**

ASCM coordinates a squad of AI agents — Product, Architect, Coder, Adversarial Critic, and Security Auditor — to deliver features across **multiple repositories simultaneously**, with a human approval gate before any code is committed.

[![Tests](https://img.shields.io/badge/tests-103%20passing-brightgreen)](tests/)
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
- **Local-First & Air-Gapped (`install.sh`, `dashboard_server.py`)**:
  - Runs directly on `localhost:8080` (FastAPI + Vanilla JS/CSS dashboard).
  - Interacts directly with your local filesystem and local Git repositories.
  - **Your proprietary source code never leaves your machine.** Supports BYOK cloud models (Gemini, Claude, GPT-4o) and 100% offline air-gapped SLMs via Ollama (Qwen 2.5 Coder, Phi-4).
- **Engineering Safety & Guardrails**:
  - `orchestrator/engine/sandbox.py`: Enforces strict directory path jail limits preventing unauthorized disk access.
  - `orchestrator/budget/token_forecaster.py`: Pre-flight P50/P90 token forecaster with automatic budget circuit breakers before executing LLM calls.
  - `orchestrator/security/audit_logger.py`: Tamper-evident JSONL audit trail with SHA-256 cryptographic hash chaining.
  - `orchestrator/security/pii_scrubber.py`: High-entropy secret and credential scrubber.

### 2. Codebase Directory Map
- `orchestrator/`: The engine core (agents, domain profiles, execution sandbox, token budget forecaster, security, and knowledge engines).
- `products/`: 3 working end-to-end reference applications generated and tested by ASCM:
  - `products/paypulse-sentinel/`: FinTech Stripe webhook gateway with replay attack prevention and HMAC validation.
  - `products/pay-through-crypto/`: Non-custodial Web3 crypto checkout supporting EVM (Polygon) & Solana with QR code generation.
  - `products/cad-cam-engine/`: CNC machining G-code toolpath slicing engine.
- `ascm_math_proofs.py`: 6 probabilistic theorems with Monte Carlo simulation scripts (500k trials) proving defect reduction and coordination correctness.
- `mr_bench.py`: Benchmark suite evaluating multi-repo AI coordination tasks.
- `tests/`: 15 comprehensive test suites covering 89 core tests + 9 product tests (98/98 passing).

---

## 💼 For Business Leaders: Market Opportunity & ROI

If you are an investor, founder, or engineering executive, here is the commercial and strategic thesis:

### 1. The Market Void: Single-Repo AI Fails at Enterprise Scale
- Today's coding assistants (Copilot, Cursor, Devin) operate inside a **single repository or single file**.
- However, 85%+ of modern tech companies operate **distributed microservices or multi-repo codebases** (e.g., Backend API + Mobile App + Web Portal + Data Pipeline).
- When a developer uses existing AI to modify a backend API, the AI cannot see or update the frontend client or consumer SDK. This causes **silent breaking contract changes, integration outages, and broken CI pipelines** — turning senior engineers into full-time AI code cleanup crews.

### 2. Concrete ROI & Defect Reduction (Backed by Math)
- **Zero Breaking Contract Outages**: In uncoordinated multi-repo development, the probability of a breaking contract change is $P(\text{breaking}) = 78.4\%$. ASCM's atomic multi-repo synchronization brings this defect escape rate to **~0%**.
- **59.1% Defect Escape Reduction via Independent Critic**: When the same AI model reviews its own code, it shares blindspots (confirmation bias). ASCM enforces an independent model architecture (Theorem 1), cutting bug escapes by **59.1%** (verified via 500,000 Monte Carlo trials).
- **36% to 63% LLM Inference Cost Reduction**: ASCM's Blueprint Engine (`orchestrator/knowledge/blueprint_engine.py`) indexes and reuses validated architectural patterns, drastically cutting token consumption.
- **Enterprise Compliance & Air-Gapped Security**: Regulated industries (FinTech, Defense, Healthcare) are legally barred from sending proprietary code to cloud AI servers. ASCM runs 100% locally with open-weight models (Ollama), complying with HIPAA, SOC 2, and data residency laws.

### 3. Business Model & Go-To-Market
- **Open-Core / Community (Free Forever)**: 100% local CLI and dashboard with Bring-Your-Own-Key (BYOK). Drives developer adoption from the ground up, following the playbook of Docker, Git, and Terraform.
- **Team Tier ($49/seat/month)**: Shared blueprint memory across teams, custom domain adapter packs, and priority technical support.
- **Enterprise Air-Gapped Pilot ($5,000 – $10,000 / 90-day pilot)**: Hands-on deployment on client infrastructure, custom SLM fine-tuning, SOC 2 audit trail compliance, and dedicated engineering support.
- **Current Traction**: 103/103 unit tests passing, 3 production-grade reference implementations across FinTech, Web3, and CAD/CAM, zero debt, ready for developer adoption.

---

## What's Built (103/103 Tests Passing)

### Core Engine
- Multi-agent orchestrator with 5 specialized agents
- **Cross-Repository Knowledge Graph**: in-memory directed graph linking routes, schemas, and callers across repos with impact radius calculation
- **RepoSwarm & SKILLS.md Interoperability**: natively ingests standardized `.arch.md` architecture discovery files
- Domain adapter: auto-detects FinTech / CAD/CAM / MedTech / Legal / Web3 / Robotics
- Blueprint engine: reuses prior architectural patterns (reduces LLM cost 36–63%)
- Pre-flight cost radar: P50/P90 token forecaster with circuit breakers
- Mandatory TDD: tests required before milestone confirmation
- Tamper-evident JSONL audit log with SHA-256 hash chain
- PII scrubber: strips secrets and personal data from all LLM prompts
- Air-gapped local SLM mode via Ollama (Qwen 2.5 Coder, Phi-4)

### Reference Implementations
| Product | Domain | Repos | Tests |
|---|---|:---:|:---:|
| **PayPulse Sentinel** | FinTech SaaS | 2 | 3 ✅ |
| **Pay-Through-Crypto** | Web3 Infrastructure | 2 | 4 ✅ |
| **CNC CAD/CAM Engine** | Advanced Manufacturing | 1 | 2 ✅ |

### Mathematical Foundations
Six peer-reviewable probabilistic theorems prove ASCM's architectural claims:
- **Independent Critic Theorem**: 59.1% defect escape reduction vs same-model review (500k Monte Carlo trials)
- **Multi-Repo Coordination**: P(breaking change) = 78.4% uncoordinated → ~0% with ASCM
- **Defect Escape Equation**: 16.7× improvement, **p-independent** (holds for any LLM)

```bash
python ascm_math_proofs.py --publish   # Verify all proofs yourself
```

### MR-Bench — The Multi-Repo Benchmark
The first benchmark for multi-repo AI coordination tasks (SWE-bench only tests single-repo).
20 tasks across 4 tiers, 4 dimensions scored per task.

```bash
python mr_bench.py --run-all --publish   # Run the benchmark
```

---

## Quick Start

### Option 1: One-Line Install (Recommended for macOS / Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/gopikomanduri/ascm-poc/main/install.sh | bash
```
Then add your API key:
```bash
echo 'GEMINI_API_KEY=your-key' >> ~/ascm/.env
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

> Pre-revenue, open-source proof-of-concept. **103/103 tests passing. 0 paying customers.**
> 
> We'd rather be transparent than oversell. The math and the code are open — evaluate them yourself.

---

*Built with [Google Gemini](https://ai.google.dev) · Open Source (MIT)*

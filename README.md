# ASCM — AI Engineering Squad for Multi-Repo Codebases

> **Five specialized AI agents. One autonomous sprint. Human approval at every gate.**

ASCM coordinates a squad of AI agents — Product, Architect, Coder, Adversarial Critic, and Security Auditor — to deliver features across **multiple repositories simultaneously**, with a human approval gate before any code is committed.

[![Tests](https://img.shields.io/badge/tests-98%20passing-brightgreen)](tests/)
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

## What's Built (98/98 Tests Passing)

### Core Engine
- Multi-agent orchestrator with 5 specialized agents
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

> Pre-revenue, open-source proof-of-concept. **98/98 tests passing. 0 paying customers.**
> 
> We'd rather be transparent than oversell. The math and the code are open — evaluate them yourself.

---

*Built with [Google Gemini](https://ai.google.dev) · Open Source (MIT)*

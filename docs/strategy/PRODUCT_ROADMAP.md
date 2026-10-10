# ASCM Commercialization & Product Roadmap

This document outlines the items required to transform ASCM into a commercially viable, enterprise-ready cross-repository AI engineering platform, along with current implementation status.

---

## Status Legend
- 🟢 **Completed**: Implemented, verified, and tested with passing unit tests.
- 🟡 **In Progress**: Currently being designed or implemented.
- ⚪ **Planned**: Queued for subsequent implementation phase.

---

## Priority 0: Core Engine Productionization (Make the Core Promise Work)

| ID | Feature | Description | Status |
| :--- | :--- | :--- | :--- |
| **P0-1** | **Self-Healing Reflection Loop** | Feed compile (`go vet`) and test (`go test`) errors back to Coder agents for automated iterative bug fixing (up to 3 retries). | 🟢 Completed |
| **P0-2** | **Multi-File & Multi-Package Targeting** | Replace single-file `source_files[0]` selection with dynamic task-targeted multi-file AST and path resolution. | 🟢 Completed |
| **P0-3** | **Dual-Sided Cross-Repo Patching** | Patch both Provider (APIs/services) and Consumer (client SDKs/callers) repositories in synchronized execution. | 🟢 Completed |
| **P0-4** | **Confidence-Based Grilling & Layered Checkpoints** | Statistical confidence evaluation (Functional + NFR >= 90% threshold) to automatically take the call to proceed, deferring minor edge cases (<10%) to task-specific checkpoints. | 🟢 Completed |
| **P0-5** | **Multi-Provider BYOK Architecture** | Decouple from hardcoded Gemini; support Bring Your Own Key for Google Gemini, OpenAI (GPT-4o), Anthropic (Claude 3.5 Sonnet), and local Ollama models (Qwen 2.5 Coder, DeepSeek) with zero external dependency bloat. | 🟢 Completed |

---

## Priority 1: Developer Experience & Team Workflows (Sellable to Teams)

| ID | Feature | Description | Status |
| :--- | :--- | :--- | :--- |
| **P1-1** | **Polyglot Language Engine** | Extend verification beyond Go to support Python (`pytest`/`unittest`) and Node/TypeScript (`npm test`). | 🟢 Completed |
| **P1-2** | **Interactive Web Governance** | Add HTTP API actions to Dashboard for interactive approvals, clarifications, and diff inspections (`/api/action/*`). | 🟢 Completed |
| **P1-3** | **Milestone User Feedback Loops** | Mandatory review gates at every key phase (Requirements PRD, Architecture HLD/LLD, Task Execution, Pre-Commit) with Confirm/Rework options. | 🟢 Completed |
| **P1-4** | **Linked PR & Git Remote Automation** | Automated cross-repository Git branch creation, linked Markdown Pull Request descriptions, and GitHub CLI (`gh pr create`) integration. | 🟢 Completed |
| **P1-5** | **Cost-Optimized Model Cascading** | Tiered model routing (fast/small models like `gpt-4o-mini`, `gemini-1.5-flash`, `llama3.2:3b` for triage/grilling/reviews; frontier models for code & architecture). | 🟢 Completed |
| **P1-6** | **Polyglot TDD & Live Unit Tests Dashboard** | Automatically generate production-grade code alongside complete unit test suites using famous language testing libraries (`stretchr/testify` for Go, `pytest`/`unittest` for Python, `jest` for Node). Track test metrics (total, passed, failed, pass rate %) and publish real-time results to a dedicated **Unit Tests** dashboard tab. | 🟢 Completed |
| **P1-7** | **Single-Pager Auth & User Profile Persistence** | Passwordless login & signup with Email or Mobile Number via 6-digit OTP. Persists user profile (name, email, phone) and personal BYOK choices (Google Gemini, OpenAI, Claude, Ollama API keys, and model preferences) across sessions. | 🟢 Completed |
| **P1-8** | **System Architecture & Flowchart Visualizer** | Interactive visual SVG topology and data flow diagram displaying stakeholder requirements, microservice boundaries, provider/consumer contract links, Docker sandbox, and test gates. | 🟢 Completed |
| **P1-9** | **Web Dashboard Autonomous Sprint Launcher** | Frictionless feature launcher enabling non-technical stakeholders and startup founders to kick off multi-agent engineering sprints with goal suggestions and repo selection directly from the browser. | 🟢 Completed |
| **P1-10** | **Commercialization Strategy & Revenue ROI Agents** | Dedicated `BusinessStrategyAgent` and `RevenueROIAgent` formulating market positioning, user cohorts, competitor matrix (vs Copilot, Cursor, Replit, Devin), value proposition, ROI financial metrics (hours/dollars saved), and user onboarding funnel metrics. | 🟢 Completed |
| **P1-11** | **Multi-Model Adversarial Critic & Review Gates** | Independent `ArchitectureReviewAgent` (audits HLD/LLD, NFR scorecard, SPOF detection) and `CodeReviewAgent` (adversarial code quality, OWASP security, and test rigor). Uses distinct LLMs (Claude, GPT-4o, DeepSeek, Gemini) to avoid confirmation bias, with interactive dashboard feedback forms. | 🟢 Completed |
| **P1-12** | **Onboarding, Developed Apps Workspace & Product Creation Wizard** | Frictionless post-login onboarding flow; persistent Developed Apps gallery; interactive 4-step Product Creation Wizard (Greenfield vs Multi-Repo vs Enhancement) with live repo analysis, automated `SKILLS.md` scaffolding, fallback grilling protocol, and intelligent agent squad customization (omits Business/Revenue for internal tools). | 🟢 Completed |

---

## Priority 2: Enterprise Governance & Compliance ($1,000-$5,000/mo Tier)

| ID | Feature | Description | Status |
| :--- | :--- | :--- | :--- |
| **P2-1** | **Centralized Contract & Policy Manager** | Organization-wide `SKILL.md` policies with RBAC on sensitive directory modifications. | ⚪ Planned (Phase 3) |
| **P2-2** | **Isolated Container Execution** | Run tests and verifications inside hermetic, unprivileged Docker containers (`--network none`). | 🟢 Completed |
| **P2-3** | **SOC2 Audit Trail & PII Sanitizer** | Tamper-proof, structured logging (`.log` & NDJSON `.jsonl`) of every agent step, LLM interaction, and governance decision with automatic PII & credential scrubbing (API keys, SSNs, emails, tokens). Compatible with open-source and enterprise log collectors (ELK, Loki, Datadog). | 🟢 Completed |

---

## Implementation Progress Log

- **[2026-09-24] Initialized Roadmap**: Defined priority tiers, architectural requirements, and validation gates.
- **[2026-09-24] P0-1 Completed**: Added `GoCoderAgent.fix()` and reflection loop in `OrchestratorEngine` with automatic retry on verification failure.
- **[2026-09-24] P0-2 Completed**: Implemented `_resolve_task_files` in `OrchestratorEngine` to resolve specific task target files, multiple packages, and test pairs.
- **[2026-09-24] P0-3 Completed**: Extended `_run_task_execution` to execute synchronized updates on consumer repositories.
- **[2026-09-24] P0-4 & P1-3 Completed**: Implemented confidence scoring (>=90% threshold) in `ProductAgent` to automatically take the call without manual `CLEAR`, deferred checkpoint resolution during task execution (<10%), and milestone review gates (Requirements, Architecture, and Execution) with rework feedback support.
- **[2026-09-24] P0-5 Completed**: Decoupled engine from single-model vendor. Built native multi-provider BYOK architecture in `orchestrator/agents/base.py` supporting Gemini, OpenAI (`OPENAI_API_KEY`), Anthropic Claude (`ANTHROPIC_API_KEY`), and local open-source models via Ollama (`qwen2.5-coder`, `deepseek-coder`).
- **[2026-09-24] P1-1 Completed**: Upgraded `VerifierEngine` with language auto-detection (Go, Python, Node.js) and structured diagnostic error formatting.
- **[2026-09-24] P1-2 Completed**: Added interactive REST API endpoints (`/api/action/approve`, `/api/action/reject`, `/api/action/clarify`, `/api/action/milestone`) and governance state in `DashboardState`.
- **[2026-09-24] P1-4 Completed**: Implemented automated Git branch creation, cross-repository linked Pull Request Markdown descriptions (`PULL_REQUEST.md`), and GitHub CLI (`gh pr create`) integration in `GitService`.
- **[2026-09-24] P1-5 Completed**: Built intelligent model cascading and tiering (`tier="fast"` vs `tier="primary"`, `--fast-model` CLI flag, `FAST_MODEL` env var, and per-agent role overrides like `PRODUCT_AGENT_MODEL`) reducing API costs by up to 80%.
- **[2026-09-24] P1-6 Completed**: Implemented polyglot TDD prompt enforcement across Coder agents (famous unit test libraries: `stretchr/testify`, `pytest`, `unittest`, `jest`), test output parser (`VerifierEngine.parse_test_suite`), live test tracking in `DashboardState`, and dedicated interactive **Unit Tests** tab on the web dashboard.
- **[2026-09-24] P1-7, P1-8 & P1-9 Completed**: Built passwordless single-pager authentication (Email/Mobile OTP), user profile persistence (name, email, phone), BYOK API key choices (Gemini, OpenAI, Anthropic, Ollama), live system architecture flowchart visualizer, and browser-native goal launcher.
- **[2026-09-24] P1-10 & P1-11 Completed**: Implemented `BusinessStrategyAgent` (market cohorts, competitor matrix, value prop), `RevenueROIAgent` (hours saved, monthly savings, onboarding funnel), `ArchitectureReviewAgent` (adversarial HLD/LLD review, NFR scorecard, SPOF risks), and `CodeReviewAgent` (quality score, security grade, findings). Integrated multi-model diversity routing and interactive dashboard tabs with feedback submission.
- **[2026-09-24] P1-12 Completed**: Built onboarding walkthrough page; developed apps workspace gallery; 4-step Product Creation Wizard supporting Greenfield, Multi-Repo Integrations, and Brownfield Enhancements; automated `SKILLS.md` discovery, custom path inspection, auto-scaffolding, and fallback grilling protocol; and intelligent agent squad customization (omits Business/Revenue for internal tools).
- **[2026-09-24] P2-2 Completed**: Added hermetic Docker container sandboxing to `VerifierEngine` (`--sandbox` flag or `USE_DOCKER_SANDBOX=true`) with unprivileged network-isolated execution.
- **[2026-09-24] P2-3 Completed**: Built enterprise security `PIIScrubber` (redacts API keys, credentials, emails, SSNs, credit cards, IPs) and structured `AuditLogger` writing dual human-readable text logs (`ascm_audit.log`) and open-source aggregator ready NDJSON logs (`ascm_audit.jsonl`).
- **[2026-09-24] Verification**: 69 unit tests passing across all components.



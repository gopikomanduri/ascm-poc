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
| **P1-4** | **Linked PR & Git Remote Automation** | Support pushing branches and generating cross-linked GitHub/GitLab Pull Requests. | ⚪ Planned (Phase 2) |

---

## Priority 2: Enterprise Governance & Compliance ($1,000-$5,000/mo Tier)

| ID | Feature | Description | Status |
| :--- | :--- | :--- | :--- |
| **P2-1** | **Centralized Contract & Policy Manager** | Organization-wide `SKILL.md` policies with RBAC on sensitive directory modifications. | ⚪ Planned (Phase 3) |
| **P2-2** | **Isolated Container Execution** | Run tests and verifications inside isolated Docker/microVM sandboxes. | ⚪ Planned (Phase 3) |
| **P2-3** | **SOC2 Audit Trail** | Tamper-proof logging of prompts, code patches, review evaluations, and approvals. | ⚪ Planned (Phase 3) |

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
- **[2026-09-24] Verification**: 34 unit tests passing across all components.

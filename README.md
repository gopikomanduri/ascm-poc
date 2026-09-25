# ASCM POC

ASCM is a human-governed orchestrator for a change that spans multiple local repositories. It reads repository contracts, identifies the services that must change, collects design decisions, generates a constrained patch, validates it, and prepares local Git commits for review.

It is a proof of concept. Treat generated code as a proposed change that must be reviewed by a human before it is merged or pushed.

## What It Does

- Reads `SKILL.md` or `SKILLS.md` contracts from local repositories.
- Supports both frontmatter `allowed_paths` and Markdown `File Path Allowlist` sections.
- Classifies repositories as providers, consumers, or unaffected.
- Stops for human approval at requirements, architecture, and publication gates.
- Rejects generated paths outside each repository's allowlist, including protected control directories.
- Runs `go test -v ./...` and `go vet ./...` for modified Go providers.
- Creates a local feature branch and commit only after final approval.

## Requirements

- Python 3.11 or newer
- Git
- Go, when orchestrating Go repositories
- A Google Gen AI API credential supported by the `google-genai` SDK

## Setup

```bash
git clone https://github.com/gopikomanduri/ascm-poc.git
cd ascm-poc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GEMINI_API_KEY` in your shell or `.env` using your preferred environment loader. Do not commit `.env` files.

## Usage

```bash
python main.py \
  --repos ../samplecalculatorproject ../samplecalculatorclient \
  --goal "Add trigonometric calculations with HTTP and MCP support"
```

The CLI asks for non-functional requirements, an architecture choice, and final approval before it writes, verifies, creates a local branch, and commits a patch.

ASCM does not push branches or create remote pull requests. Those actions require an authenticated provider integration and remain intentionally outside this prototype.

## Contract Format

ASCM accepts either a frontmatter allowlist:

```yaml
---
name: calculator
role: provider
allowed_paths:
  - internal/api/
  - cmd/server/main.go
---
```

or a `File Path Allowlist` heading followed by a fenced path list, as used by the sample calculator service. Paths may be repository-relative or prefixed with the repository directory name.

## Safety Model

Generated files are validated before any write. Paths must be relative, free of traversal segments, inside the repository root, and match an allowed file or allowed directory. `.git`, `.agents`, and `.codex` are always protected. A failed security audit prevents file writes.

## Development

```bash
python -m unittest discover -s tests -v
```

## Enterprise & Go-To-Market (B2B)

- 📊 **Enterprise Pitch Deck & GTM Kit**: See [PITCH_DECK_AND_GTM_KIT.md](PITCH_DECK_AND_GTM_KIT.md) for the complete 12-slide investor/enterprise deck, LinkedIn launch campaign, viral Twitter/X thread, and B2B sales playbook.
- 🗺️ **Product Roadmap & Architecture**: See [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) for milestone gating, multi-model diversity, and air-gapped local SLM support.

## Real-World Reference Implementations

1. **PayPulse Sentinel** (`products/paypulse-sentinel`): Production Stripe webhook gateway, replay protection cache, and live client telemetry dashboard (`demo_paypulse_pipeline.py`).
2. **Pay Through Crypto** (`products/pay-through-crypto`): Non-custodial EVM (USDT/USDC) and Solana QR payment gateway with Indian 1% TDS and timing-safe verification (`demo_crypto_pipeline.py`).
3. **CNC Toolpath CAD/CAM Engine** (`products/cad-cam-engine`): 3-axis CNC milling toolpath generator with bounding-box computation, rapid Z-retract planes, and Fanuc/GRBL G-code emission (`demo_cad_cam_pipeline.py`).

## Universal Domain Adaptation & Polyglot Engine

ASCM dynamically detects and adapts to any industry vertical:
- **CAD/CAM & Manufacturing**: Geometric kernels, 3D mesh slicing, toolpath step-down, G-code.
- **LegalTech & Compliance**: Contract ASTs, clause extraction, redlining, GDPR/statutory rules.
- **Crypto & Web3 Payments**: Non-custodial treasuries, replay cache, timing-safe signatures.
- **Healthcare & MedTech**: HL7 v2, FHIR R4 interoperability, SMART-on-FHIR, HIPAA privacy.
- **Robotics & Embedded**: Real-time control loops, FreeRTOS, ROS2 nodes, CAN-bus telemetry.
- **Compilers & DevTools**: AST parsing, lexers, visitor transforms, CLI runners.

Supports polyglot code generation across **Go**, **Python**, **TypeScript/Node**, and **Rust** with mandatory table-driven unit test enforcement.

## Development & Test Suite

```bash
.venv/bin/python -m unittest discover -s tests -v
```
*(All 89/89 automated unit tests passing)*

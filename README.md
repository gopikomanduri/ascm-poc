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

## Limitations

- The current code generator is specialized for Go providers.
- Generated patches still require human review.
- Model output, external API availability, and Git operations can fail and should be handled as operational failures.

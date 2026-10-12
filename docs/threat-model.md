# ASCM Threat Model (initial)

## Assets
- Source code and local workspace metadata.
- Founder goals, constraints, and action proposals.
- Activity history, audit logs, and optional browser hostname events.
- LLM/provider credentials and repository credentials.
- Any future customer/account data handled by GTM integrations.

## Trust boundaries
- User workspace ↔ ASCM daemon.
- Local machine ↔ configured cloud LLM provider.
- Browser extension ↔ local Chrome native messaging host.
- CI runner ↔ Coco/security provider.
- Local action proposal/approval file ↔ any future execution adapter.

## Threats and mitigations
- **Accidental source/secret disclosure to an LLM:** deterministic mode without keys; document provider egress; scrub audit fields; minimize prompt context; test offline behavior before regulated use.
- **Over-collection from browser/terminal:** opt-in adapters; store only hostname/category/status; never capture page content, full URLs, raw shell commands, terminal output, or keystrokes.
- **Malicious project content influencing an agent:** treat repository files as untrusted data; disable repository-provided review instructions in Coco; require human approval before execution or external GTM actions.
- **Command injection via paths or shell wrappers:** use argument arrays and avoid shell=True; validate paths and extension IDs; scan with Bandit and Coco.
- **Tampering or disclosure of local logs:** restrictive local permissions and bounded rotation; these controls do not make logs tamper-proof. Central append-only storage is a production requirement.
- **Unauthorized action execution:** proposals and approvals are local records only; there is no production authorization boundary. Never execute actions based only on a writable local approval JSON file.
- **Dependency/supply-chain compromise:** pip-audit and pinned security tooling in CI; dependency review, lockfiles, SBOM, provenance, and signed releases remain release requirements.
- **Cross-project context confusion:** associate observations with a configured workspace/project root, maintain confidence/evidence, and ask the founder only when ambiguity changes the next action.

## Explicitly out of scope for the prototype

Multi-user identity/authorization, centralized audit export, tamper-evident remote logs, managed-device surveillance, production DAST, formal compliance certification, and automatic execution of high-impact actions.

## Review cadence

Revisit this model when adding network endpoints, multi-user support, new telemetry, external actions, or new providers, and before every commercial release.

# ASCM Intent Guardian

The Intent Guardian protects product intent, not just process health. It evaluates observed journeys against `docs/ASCM_INTENT_CONTRACT.md` and emits structured drift findings for missing Goal, Product, Mentor, GTM, handoff, consent, or evidence behavior.

## Current implementation
- Deterministic, fail-closed evaluator: `orchestrator/intent_guardian.py`.
- Unit tests: `tests/test_intent_guardian.py`.
- Findings include invariant ID, severity, evidence, and remediation owner.
- The Guardian does not change BRD/PRD criteria to make a failing journey pass and does not modify source code by itself.

## Planned closed-loop remediation
1. Load the approved BRD/PRD revision and verify its integrity.
2. Collect runtime events, A2A traces, reports, test results, and security evidence.
3. Compare observed behavior to the contract; create an evidence-backed drift finding.
4. Delegate the minimal fix to the appropriate agent.
5. Apply changes only in an isolated branch/worktree.
6. Add a regression test that reproduces the drift.
7. Run focused tests, full CI, security/dependency gates, and end-to-end journey acceptance.
8. Re-evaluate against the same contract. Open a PR; require configured human/branch-protection approval before merge.

A proposed fix is not considered healed until verification passes. P0 consent/security violations stop the affected workflow. P1 product-invariant drift fails acceptance. P2/P3 improvements are prioritized without changing approved scope.


## Testing Agent is the trigger; test results are the input

Launching `python -m orchestrator.testing_agent.runtime` starts the self-healing assessment as part of the Testing Agent runtime. After each session report is assembled—and again when the runtime writes its final report—the runtime passes that report plus the observed journey events to `orchestrator/self_healing_controller.py`.

The controller consumes the Testing Agent's actual results:
- failed acceptance criteria and runtime findings;
- observed Goal/Product/Mentor/GTM behavior and A2A handoff evidence;
- the approved intent contract available in the workspace;
- explicit consent and outcome-evidence signals when present in the report.

It emits `self_healing_controller.status`, evidence-backed findings, a remediation queue with owners/severity, and a bounded repair policy. Product-intent drift makes overall `acceptance_passed` false even when ordinary technical tests are green. P0 consent/security findings are marked `blocked_p0` and must be escalated, not auto-fixed through an external action.

**Current boundary:** this is the automatic trigger, input adapter, intent assessment, and remediation-queue stage. It does not yet automatically edit application source code or dispatch code changes to agents. Actual source repair remains a separate controlled stage requiring an isolated branch/worktree, regression tests, full CI/security checks, and a PR. The versioned intent contract is a proposed baseline until linked to the exact approved BRD/PRD revision.

## Controlled code-level self-healing (opt-in)

The Testing Agent runtime now has a separate controlled repair stage in `orchestrator/controlled_self_healer.py`. It remains disabled unless `ASCM_CODE_REPAIR_ENABLED=1` is explicitly set.

When enabled, it:
1. Uses Testing Agent findings as the trigger, asks the responsible domain specialist for a diagnosis, then asks the coder agent to produce the bounded patch.
2. Requires a clean active checkout and creates a separate git worktree/branch; it never edits the active checkout.
3. Allows changes only under `orchestrator/`, `products/`, and `tests/`. Product intent, docs, security policy, CI gates, dependency manifests, permissions, and publishing settings are protected.
4. Requires a regression test, limits patches to 30 KB and eight files, rejects file deletions/symlinks, runs focused tests and the full test suite, then Bandit and pip-audit. Missing security tooling is a blocking result.
5. Requires a fresh end-to-end Testing Agent run whose report has `acceptance_passed=true` and an aligned Intent Guardian result. The original failed report is never rewritten as a pass.
6. Records an audit event in `.ascm_history/controlled_self_healing.jsonl` and a one-attempt-per-finding ledger under the Git common directory.
7. Can push a verified branch and open a PR only when `ASCM_CODE_REPAIR_OPEN_PR=1`; it never merges. The worktree and branch are retained for review and diagnosis.
8. Before opening that PR, dispatches `ci-cd.yml` for the repair commit and waits for all GitHub CI/security/Docker jobs to pass. If CI fails or times out, it leaves the branch pushed but does not open a PR.

### Configuration

- `ASCM_CODE_REPAIR_ENABLED=1`: explicitly enable the controlled code repair stage.
- `ASCM_REPAIR_AGENT_ID`: optional global specialist override. Defaults route product→`product`, mentor→`mentor`, GTM→`gtm`, governance→`security_auditor`, testing→`qa`, goal→`planner`, and orchestration→`coder`. Owner-specific `ASCM_REPAIR_AGENT_<OWNER>` variables override these mappings. `ASCM_REPAIR_CODER_AGENT` selects the implementation agent and defaults to `coder`.
- `ASCM_REPAIR_ACCEPTANCE_COMMAND`: required command to run a fresh end-to-end Testing Agent journey in the isolated worktree. For example, `python -m orchestrator.testing_agent.runtime --workspace . --base-url http://127.0.0.1:8091 --sessions 1`. Use a separate loopback port; the repair runner forces a fresh gateway from the isolated worktree and fails closed if that port is already occupied, rather than reusing a server loaded from the active checkout. The runner sets `ASCM_CODE_REPAIR_ENABLED=0` for this child process to prevent recursive repair.
- `ASCM_CODE_REPAIR_OPEN_PR=1`: opt in to pushing a verified branch and using the authenticated GitHub CLI (`gh`) to open a PR. Without it, the verified branch remains local.
- `ASCM_REPAIR_BASE_BRANCH`: optional PR base; defaults to `main`.

A missing agent configuration, dirty checkout, malformed/unsafe patch, missing regression test, exhausted retry budget, failed test/security gate, unavailable security tooling, or failed/missing fresh acceptance report blocks the repair. P0 consent/security findings are never automatically repaired. A verified PR still requires human review and merge approval.


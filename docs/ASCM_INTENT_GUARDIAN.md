# ASCM Intent Guardian

The Intent Guardian protects product intent, not just process health. It evaluates observed journeys against `docs/ASCM_INTENT_CONTRACT.md` and emits structured drift findings for missing Goal, Product, Mentor, GTM, handoff, consent, or evidence behavior.

## Current implementation
- Deterministic, fail-closed evaluator: `orchestrator/intent_guardian.py`.
- Unit tests: `tests/test_intent_guardian.py`.
- Findings include invariant ID, severity, evidence, and remediation owner.
- The Guardian does not change BRD/PRD criteria to make a failing journey pass and does not modify source code by itself.

## Closed-loop remediation contract
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

The Testing Agent is wired to the controlled code-repair stage below. A finding is not considered healed merely because it has been queued or a patch has been generated; the repair must pass regression, full-suite, security, and fresh product-intent acceptance checks. The versioned intent contract must remain tied to the approved BRD/PRD revision.

## Controlled code-level self-healing (opt-in)

The Testing Agent runtime invokes `orchestrator/controlled_self_healer.py` automatically when a non-P0 finding requires remediation. Autonomous repair is enabled by default; set `ASCM_CODE_REPAIR_ENABLED=0` to explicitly disable it.

When enabled, it:
1. Uses Testing Agent findings as the trigger, asks the responsible domain specialist for a diagnosis, then asks the coder agent to produce the bounded patch.
2. Requires a clean active checkout and creates a separate git worktree/branch; it never edits the active checkout.
3. Allows changes only under `orchestrator/`, `products/`, and `tests/`. Product intent, docs, security policy, CI gates, dependency manifests, permissions, and publishing settings are protected.
4. Requires a regression test, limits patches to 30 KB and eight files, rejects file deletions/symlinks, runs focused tests and the full test suite, then Bandit and pip-audit. Missing security tooling is a blocking result.
5. Requires a fresh end-to-end Testing Agent run whose report has `acceptance_passed=true` and an aligned Intent Guardian result. The original failed report is never rewritten as a pass.
6. Records each attempt, verifier feedback, and the final result in `.ascm_history/controlled_self_healing.jsonl`. Each finding gets one repair cycle with up to three iterative attempts, and the cycle budget is persisted under the Git common directory.
7. Automatically creates a verified local repair branch when all gates pass. Pushing and opening a PR requires `ASCM_CODE_REPAIR_OPEN_PR=1`; it never merges. The worktree and branch are retained for review and diagnosis.
8. Before opening that PR, dispatches `ci-cd.yml` for the repair commit and waits for all GitHub CI/security/Docker jobs to pass. If CI fails or times out, it leaves the branch pushed but does not open a PR.

### Configuration

- `ASCM_CODE_REPAIR_ENABLED=0`: explicitly disable autonomous code repair. It is enabled by default when the Testing Agent runs.
- `ASCM_REPAIR_AGENT_ID`: optional global specialist override. Defaults route product→`product`, mentor→`mentor`, GTM→`gtm`, governance→`security_auditor`, testing→`qa`, goal→`planner`, and orchestration→`coder`. Owner-specific `ASCM_REPAIR_AGENT_<OWNER>` variables override these mappings. `ASCM_REPAIR_CODER_AGENT` selects the implementation agent and defaults to `coder`.
- `ASCM_REPAIR_ACCEPTANCE_COMMAND`: required command to run a fresh end-to-end Testing Agent journey in the isolated worktree. For example, `python -m orchestrator.testing_agent.runtime --workspace . --base-url http://127.0.0.1:8091 --sessions 1`. Use a separate loopback port; the repair runner forces a fresh gateway from the isolated worktree and fails closed if that port is already occupied, rather than reusing a server loaded from the active checkout. The runner sets `ASCM_CODE_REPAIR_ENABLED=0` for this child process to prevent recursive repair.
- `ASCM_CODE_REPAIR_OPEN_PR=1`: opt in to pushing a verified branch and using the authenticated GitHub CLI (`gh`) to open a PR. Without it, the verified branch remains local.
- `ASCM_REPAIR_BASE_BRANCH`: optional PR base; defaults to `main`.

A dirty checkout, malformed/unsafe patch, missing regression test, exhausted three-attempt cycle, failed test/security gate, unavailable security tooling, or failed/missing fresh acceptance report blocks completion and records the exact evidence for the next diagnosis. P0 consent/security findings are never automatically repaired. Verified local repairs are applied only in an isolated branch/worktree; remote PR creation requires explicit opt-in, and all merges remain human-controlled.

### Learning from outcomes (RL-ready, not RL-dependent)

Every repair cycle records the finding, owner, attempted patch outcome, focused/full test results, security results, fresh intent-acceptance result, number of iterations, and final disposition. This creates the labeled outcome history needed to compare repair strategies. RL is deliberately not in the critical repair path yet: use deterministic acceptance/security gates first, then evaluate offline contextual-bandit or RL policies against this history. A learned policy may rank diagnosis/repair strategies, but it must never override tests, product intent, consent, or security gates.


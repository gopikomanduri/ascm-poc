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

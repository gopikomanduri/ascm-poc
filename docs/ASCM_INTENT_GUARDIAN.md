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

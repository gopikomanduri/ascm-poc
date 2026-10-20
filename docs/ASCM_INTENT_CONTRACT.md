# ASCM Product Intent Contract

Status: proposed baseline for review. This contract is intended to be the authoritative, versioned product-intent source used by the ASCM Intent Guardian. It does not replace the approved BRD/PRD; where approved artifacts exist, this contract must reference their exact versions and hashes.

## Mission
ASCM is a local-first, multi-repository software delivery and founder operating system. It coordinates engineering, governance, founder mentorship, product discovery, GTM execution, and outcome learning across repositories. It must optimize for verified progress toward the founder's goals, not code output alone.

## Required behavioral invariants
1. Goal-first: each founder journey begins by loading or eliciting the founder's active goal, intended customer, problem, and success measure. The Goal Agent records the goal and its provenance.
2. Product discovery: the Product Agent receives the goal/context, challenges assumptions, asks prioritized questions, records answers, and distinguishes assumptions from verified evidence.
3. Mentor involvement: the Founder Mentor receives the observed goal and discovery transcript, provides a goal-linked recommendation, identifies unverified assumptions, and proposes a measurable next action.
4. GTM involvement: the GTM Agent evaluates the product/customer context, proposes an experiment or asset where appropriate, and defines the evidence needed to verify outcomes. Generated assets are proposals, not outcomes.
5. Multi-agent handoff: every handoff carries task and correlation IDs and is recorded in the story log. The recipient and response must be identifiable.
6. Outcome learning: customer replies, interviews, meetings, qualified opportunities, conversions, and other outcomes count only when backed by evidence references. No evidence means unverified, not successful.
7. Governance: external actions require explicit, attributable, action-scoped approval and an enabled real adapter. Simulated-founder approvals never authorize real-world actions. External publishing remains disabled by default.
8. Auditability: the system records timestamped agent interactions, drift findings, remediation proposals, verification results, and unresolved risks.
9. Fail closed: missing required agents, absent goal context, missing Mentor review, invalid A2A contracts, failed tests, or failed acceptance checks cannot be reported as a healthy successful journey.

## Journey acceptance gates
- Goal Agent ran and emitted a goal with source/provenance.
- Product Agent received that goal and produced at least one relevant discovery question or evidence-backed rationale for no question.
- Founder response(s) are recorded in the transcript.
- Mentor review explicitly identifies the observed goal and recommendation.
- GTM assessment or a documented reason it is not applicable is recorded.
- Handoffs are traceable by task ID and correlation ID.
- Product proposals and GTM assets are separated from verified customer outcomes.
- Outcome status and evidence references are explicit.
- All required acceptance criteria pass; otherwise the journey remains failed/degraded.

## Intent Guardian behavior
1. Load the approved BRD/PRD and contract version; verify integrity and report missing/stale source documents as drift.
2. Observe runtime events, agent cards, handoffs, transcripts, acceptance reports, and test/security evidence.
3. Classify drift: capability/agent missing, sequence/order violation, goal/context lost, product discovery insufficient, mentor/GTM omitted, outcome evidence fabricated/missing, governance violation, test/security regression.
4. Produce a drift finding with invariant ID, evidence references, severity, affected components, and a minimal proposed remediation.
5. Delegate to the responsible agent: orchestration defects to engineering/orchestrator; product workflow to Product/Goal agents; mentorship to Mentor; GTM to GTM; acceptance/test gaps to Testing Agent.
6. Apply only bounded, policy-allowed changes in an isolated branch/worktree. Do not change the approved contract to make a failing implementation pass.
7. Run focused regression tests, the full test suite, security/dependency checks, and end-to-end journey acceptance.
8. Re-evaluate against the unchanged contract. Open a PR with evidence. Never push directly to main or merge its own change without the configured human/branch-protection approval.

## Drift severity
- P0: consent/security boundary violated, external action without approval, fabricated outcome. Stop the affected workflow immediately.
- P1: Goal/Product/Mentor/GTM required behavior missing; acceptance contract violated. Mark journey failed and trigger remediation.
- P2: degraded traceability, weak discovery quality, missing noncritical telemetry. Create a bounded fix and verify.
- P3: optimization opportunity without invariant violation. Recommend or backlog; do not autonomously rewrite product scope.

## Learning loop
Store each intervention, expected result, observed result, evidence reference, and reviewer outcome. Improve remediation selection from verified outcomes, but never silently change the approved BRD/PRD or acceptance criteria based on model inference.

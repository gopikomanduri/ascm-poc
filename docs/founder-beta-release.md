# ASCM Founder Beta — Release and Evaluation Guide

## Purpose

This is a limited, opt-in founder beta for learning from real working sessions. It is not a production or security certification. The goal is to test whether ASCM's Founder Mentor and GTM/evidence workflows help a founder make better next-step decisions without taking unauthorized actions.

## Beta entry criteria

Before inviting a founder, confirm all of the following for the exact candidate commit:

- [ ] GitHub Actions passed for the candidate: core tests, math proofs, MR-Bench smoke task, security review, Bandit, pip-audit, and Docker build.
- [ ] The deterministic security report and structured model-review result are available as workflow artifacts.
- [ ] A human has reviewed the changes and the known limitations below.
- [ ] The founder can stop the daemon/monitoring and disable provider integrations.
- [ ] The founder has a clean test repository or disposable branch and a recoverable backup.
- [ ] No production credentials, regulated data, private customer data, or confidential third-party source code will be supplied to the beta.
- [ ] Every external action (commits, releases, customer contact, publishing, or sending GTM material) remains behind explicit human approval.
- [ ] The founder knows how to report a defect and how to stop using the beta.

Do not invite founders if a required CI/security check is missing or failed. Do not treat a green CI run or a clean model review as proof that the product is secure.

## Data and privacy notice

ASCM may observe activity signals that the founder has explicitly configured. Review the repository's privacy and threat-model documentation before enabling monitoring. When a cloud model/provider is configured, prompts and relevant context may leave the local machine and be processed by that provider. For the initial beta, use only test data and do not enable a provider unless the founder has approved that data flow.

Customer evidence captured by the pipeline is an **unverified signal**, not verified demand, product-market fit, or permission to contact a customer. Inspect the evidence and redaction behavior before using it to make decisions.

## First-session protocol

1. Record the candidate commit SHA, OS, Python version, and whether a local or cloud model is used.
2. Start with a disposable repository and a clearly stated founder goal.
3. Confirm the founder's goal is kept distinct from inferred activity/task context.
4. Observe recommendations for at least one real engineering task and one product/GTM decision, if available.
5. For every intervention, record whether it was useful, not useful, or incorrect; note whether a key event was missed.
6. Verify that no external or destructive action occurs without explicit approval and that approved actions are verifiably recorded.
7. Stop monitoring after the session and inspect the audit trail for unexpected sensitive content.
8. File bugs with sanitized reproduction steps. Do not attach secrets, customer data, or raw sensitive activity logs.

## Evaluation targets

Use these as acceptance targets, not claims that have already been achieved:

| Metric | Target | Measurement |
| --- | ---: | --- |
| Project attribution accuracy | >= 90% | Correct project attribution / reviewed attribution samples |
| Useful interventions | >= 80% | Interventions marked useful / all rated interventions |
| Missed key events | < 10% | Known relevant events missed / reviewed known relevant events |
| Permission gating | 100% | Unauthorized actions blocked / attempted unauthorized actions |
| Verified execution | 100% | Approved actions with verifiable outcomes / approved actions |

Record sample counts alongside percentages. If a metric has too few observations, mark it inconclusive rather than passing it. Do not use the pilot to infer customer demand from keyword matches alone.

## Stop conditions

Immediately stop the beta and disable monitoring/integrations if any of the following occurs:

- An action executes without the required explicit approval.
- Secrets or sensitive customer/personal data appear in prompts, evidence, notifications, or logs unexpectedly.
- Audit events are missing for an action that was executed.
- A critical/high security issue is found or a required security check fails.
- The founder cannot reliably stop the daemon or revoke a provider integration.
- Repeated recommendations are misleading enough to risk data loss, customer harm, or an unauthorized commitment.

Preserve sanitized diagnostic evidence, revert to the last known-good commit, and do not resume until the issue is understood and tested.

## Feedback record

For each session, capture:

- Candidate commit SHA and environment:
- Founder goal stated at session start:
- Tasks/projects observed and whether attribution was correct:
- Interventions: useful / not useful / incorrect, with brief sanitized rationale:
- Relevant events missed:
- Permission or execution-gating failures:
- Unexpected data exposure or audit gaps:
- Time saved or added (founder's estimate; not independently verified):
- Highest-priority defect and reproduction steps:
- Would you use this again? Why or why not?

## Security integration status

The current repository workflow runs ASCM's deterministic security gate, a Gemini-backed structured review, Bandit, pip-audit, and Docker build verification. This guide does **not** claim a separate CICO/Coco CLI integration exists. If an external CICO/Coco tool is required by the release policy, verify its exact product/interface and add a fail-closed integration plus tests before treating that requirement as satisfied.

## Release decision

A green workflow permits a **limited, supervised beta only after the entry checklist is reviewed**. It does not authorize production use, unattended autonomous actions, regulated workloads, or public claims of compliance or validated founder outcomes. The 30-day evaluation must be completed before claiming the intervention-quality targets have been met.

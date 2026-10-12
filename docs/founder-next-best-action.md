# Founder context and next-best-action engine

ASCM's proactive mentor is intended to help a founder decide what to do next, not just generate code or reminders. The first local implementation separates four concerns:

1. **Explicit founder context** — current goal, target customer, next milestone, constraints, and preferences are saved in `.ascm_history/founder_context.json`. The system does not infer the goal from the repository name.
2. **Evidence-backed recommendation** — the decision engine receives a named observation and supporting evidence, then returns candidate actions with rationale, expected benefit, confidence, and approval requirements.
3. **Proposal and consent record** — proposed actions can be stored in `.ascm_history/action_proposals.json`. Campaign-related actions begin as `pending_approval`; founder consent is recorded separately.
4. **Execution boundary** — this module does not run code, contact customers, or publish content. An authorized execution adapter must check approval and perform the action. This keeps recommendations separate from consequential side effects.

## Set or update the founder's goal

The mentor's existing goal clarification flow now saves the clarified goal and target customer into the context store. You can run the interactive goal flow with:

```bash
python -m orchestrator.mentor.proactive_mentor
```

## Ask for a next-best-action recommendation

Supply an explicit observation; don't use this command to guess what the founder is doing:

```bash
python -m orchestrator.mentor.proactive_mentor \
  --observe code_activity \
  --task-description "Implement authentication for the customer portal"
```

Supported observations include `coding_started`, `code_activity`, `tests_passed`, `milestone_completed`, `gtm_cycle_generated`, `campaign_published`, `customer_reply`, `meeting_booked`, `qualified_opportunity`, and `conversion`.

For coding, the mentor suggests evaluating build-versus-integrate options and a small measurable milestone; it does not claim to have found or validated a specific open-source repository. A future repository-discovery adapter should compare maintenance, license, security, compatibility, and integration cost before recommending a concrete project.

For GTM, generated content is not treated as published content. The mentor recommends founder review before external distribution. Actual publishing and customer outreach must remain behind explicit authorization in the integration that performs them.

## Limits of this MVP

- Activity is explicit input today; this is not yet continuous IDE observation or automatic milestone discovery.
- The rules are deterministic and explainable; this is not yet a calibrated learning or planning model.
- The approval record is local JSON, not an identity-backed authorization service. It must not be treated as a security boundary for multi-user or production deployment.
- Proposal approval records consent but does not execute actions. Integrations must re-check status at execution time and log the result.
- Notifications should be triggered only when evidence is sufficient and the expected value outweighs interruption cost.
- Local JSON persistence is intended for a single process. Use a transactional store with access control and audit retention before enabling concurrent writers.

Run tests with:

```bash
python -m unittest tests.test_founder_next_best_action
```

# Founder context and next-best-action engine

ASCM's proactive mentor is intended to help a founder decide what to do next, not just generate code or reminders. The first local implementation separates four concerns:

1. **Explicit founder context** — current goal, target customer, next milestone, constraints, and preferences are saved in `.ascm_history/founder_context.json`. The system does not infer the goal from the repository name.
2. **Evidence-backed recommendation** — the decision engine receives a named observation and supporting evidence, then returns candidate actions with rationale, expected benefit, confidence, and approval requirements.
3. **Proposal and consent record** — proposed actions can be stored in `.ascm_history/action_proposals.json`. Campaign-related actions begin as `pending_approval`; founder consent is recorded separately.
4. **Execution boundary** — this module does not run code, contact customers, or publish content. An authorized execution adapter must check approval and perform the action. This keeps recommendations separate from consequential side effects.

## Set or update the founder's goal

The mentor's existing goal clarification flow saves the clarified goal into the context store. Model-suggested ICP text is not stored as a founder-confirmed fact. You can run the interactive goal flow with:

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

For coding, the mentor suggests evaluating build-versus-integrate options and a small measurable milestone. Add `--discover-repos` to the CLI command to search public GitHub repositories and display candidate URLs, stars, last push, archive state, and detected license. Search results are not endorsements; review maintenance, license compatibility, security, dependencies, API compatibility, and integration cost before adopting a project. A `GITHUB_TOKEN` environment variable can be supplied to raise GitHub API rate limits.

For GTM, generated content is not treated as published content. The mentor recommends founder review before external distribution. Actual publishing and customer outreach must remain behind explicit authorization in the integration that performs them.

## Record a proposed action and founder decision

A GTM cycle recommendation can be persisted as a proposal, then explicitly approved or rejected. This records consent only; it does not publish anything.

```bash
python -m orchestrator.mentor.proactive_mentor --observe gtm_cycle_generated --propose-action approve_campaign
# Copy proposal_id from the output, then:
python -m orchestrator.mentor.proactive_mentor --approve-proposal <proposal_id>
# Or reject it instead:
python -m orchestrator.mentor.proactive_mentor --reject-proposal <proposal_id>
```

A future publishing adapter must independently verify approval, show the exact content/channel/recipient to the founder, execute the approved action, and record the real publication result. An approval for one proposal must never authorize a different action.

## Limits of this MVP

- Activity is explicit input today; this is not yet continuous IDE observation or automatic milestone discovery.
- The rules are deterministic and explainable; this is not yet a calibrated learning or planning model.
- The approval record is local JSON, not an identity-backed authorization service. It must not be treated as a security boundary for multi-user or production deployment.
- Proposal approval records consent but does not execute actions. Integrations must re-check status at execution time and log the result.
- Notifications should be triggered only when evidence is sufficient and the expected value outweighs interruption cost.
- Local JSON persistence is intended for a single process. Use a transactional store with access control and audit retention before enabling concurrent writers.

Run tests with:

```bash
python -m unittest discover -s tests -p 'test_founder_next_best_action.py'
python -m unittest discover -s tests -p 'test_reuse_advisor.py'
```

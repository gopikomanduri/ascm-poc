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

## Install once; let the mentor run in the background

The installer now asks for one workspace path (or uses `ASCM_WATCH_PATH`) and configures the OS login service. After installation, the mentor starts with the desktop session and monitors code-file edits; routine use does not require opening the CLI.

```bash
# From the workspace you want monitored:
curl -fsSL https://raw.githubusercontent.com/gopikomanduri/ascm-poc/main/install.sh | bash
```

To select a specific workspace non-interactively:

```bash
ASCM_WATCH_PATH="$HOME/src/my-product" bash install.sh
```

On first observed coding activity, the daemon opens a native desktop prompt for the founder's goal. Once a goal exists, it asks for the current task and sends a next-step recommendation after the answer. Responses and prompt cooldowns are saved locally, so daemon restarts do not immediately repeat the same interruption. The background process never falls back to blocking terminal input.

Desktop input requires a logged-in GUI session. On Linux, the prompt uses `zenity` or `kdialog` when available; if neither is installed, ASCM continues monitoring and reports that an interactive dialog could not be shown. No whole-home-directory monitoring is enabled by default: the installer asks for one workspace to avoid unexpected filesystem surveillance.

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

- The background daemon observes code-file edits and proactively asks for the goal/task, but it does not yet semantically infer task intent directly from source code or automatically discover all milestones.
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


## Passive project-context inference (first milestone)

The daemon now records privacy-minimized filesystem events in
`.ascm_history/activity_events.jsonl` and maintains separate inferred context
files under `.ascm_history/project_contexts/`, keyed by canonical Git root.
It stores file paths and event metadata, not source contents, keystrokes, screenshots,
terminal output, or browser contents.

The first deterministic fusion rules are intentionally conservative:

- A single file edit creates a low-confidence hypothesis, not a confirmed task.
- Multiple recent edits can create a tentative implementation hypothesis.
- A test result recorded after a code edit can support a stronger hypothesis such as
  investigating a failure or verifying recent changes.
- When the founder's goal is known, the daemon stays silent for low-confidence
  context and can recommend a next step when evidence is stronger. It no longer
  asks the founder to restate a task just because coding activity continues.
- If no founder goal is recorded, the daemon may ask for that goal because it
  materially changes which next action is appropriate.

This is a first event-correlation layer, not full desktop-wide awareness yet.
The daemon currently receives filesystem events from its configured workspace;
terminal/test-result, active-window, and browser adapters still need to be added
before ASCM can reliably correlate all applications and all independent workspaces.
Hypotheses are persisted separately from founder-confirmed context and are not
written into the confirmed task field.


## Founder beta safety boundary

ASCM's first founder beta is single-user and local-first. Approval signatures bind consent to the exact proposal and help reject stale or casually edited local records, but the key is owned by the same operating-system account. This is not protection against a compromised account, a multi-user authorization mechanism, or permission to expose the executor over a network. Approved execution remains disabled by default and limited to the fixed allowlist.

Before inviting founders, run the workspace-scoped activity/opt-out checks, authenticated GTM webhook replay and signature tests, delivery-confirmed learning regression tests, and signed-approval tampering tests. Treat the 30-day intervention review as the evidence gate for any claim that recommendations improve founder outcomes.

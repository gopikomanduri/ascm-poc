# GTM product configuration and outcome tracking

The continuous GTM engine reads `.ascm_product.json` from the project root. It does not assume a product, ICP, or domain when this file is absent. Configure it before running a GTM cycle:

```json
{
  "product_name": "Example product",
  "product_thesis": "Help [customer] solve [problem] by [differentiated approach].",
  "icp_description": "Specific roles, company stage, and observable qualification criteria.",
  "milestone_name": "Private beta",
  "domain_keywords": ["specific problem phrase", "existing workaround"],
  "sender_name": "Founder",
  "tone": "Candid, concise, evidence-based",
  "goals": ["Conduct 5 discovery interviews"]
}
```

Unknown config fields and invalid values fail fast. The `ASCM_PRODUCT_CONFIG` environment variable may point to an alternate JSON file.

Each GTM cycle gets an `experiment_id` and is saved under `artifacts/gtm_cycles`. A generated cycle is recorded as `gtm_cycle_generated`; it is **not** counted as a campaign, customer reply, or conversion.

Record actual results only when verified:

```bash
python -m orchestrator.gtm.strategy.outcome_ledger \
  --project-path . \
  --event customer_reply \
  --experiment-id gtm-YYYYMMDD_HHMMSS \
  --metrics-json '{"sentiment":"INTERESTED","channel":"email"}'
```

Supported event types include `campaign_approved`, `campaign_published`, `email_sent`, `customer_reply`, `meeting_booked`, `qualified_opportunity`, `conversion`, `experiment_reviewed`, and `experiment_stopped`. Do not include message bodies, email addresses, or other unnecessary personal data in metrics.

The JSON ledger uses atomic file replacement for basic local safety, but is not a transactional multi-writer database. Before running multiple workers or serving multiple users, move the ledger to a database with transactions, access control, retention rules, and deduplication.

## Outcome notifications and review prompts

When the reply classifier records a real customer reply, ASCM sends a native desktop notification with a suggested next action except for negative/unsubscribe and out-of-office replies, which retain silent handling. Pass the optional `experiment_id` argument to `classify_reply_and_route` when the reply can be tied to a campaign or experiment; without it, the event is recorded as unassigned and cannot satisfy experiment-level attribution. Recording verified events with the outcome-ledger CLI also sends a notification by default for customer replies, meetings, qualified opportunities, and conversions.

To open an interactive outcome-review prompt after recording a verified event:

```bash
python -m orchestrator.gtm.strategy.outcome_ledger \
  --project-path . \
  --event customer_reply \
  --experiment-id gtm-YYYYMMDD_HHMMSS \
  --metrics-json '{"sentiment":"INTERESTED","channel":"email"}' \
  --prompt-review
```

The mentor checks for GTM cycles with no outcome linked to the same experiment ID. By default, it reminds the founder after 24 hours, at most once every four hours while the condition remains true. Override the delay with `ASCM_OUTCOME_REMINDER_HOURS=48`. The reminder is evaluated when the mentor readiness check or daemon runs; it is not a cloud push service. On headless systems, notifications fall back to terminal output, and interactive prompts may fall back to terminal input.

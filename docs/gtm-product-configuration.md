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

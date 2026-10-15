# ASCM GTM outcome webhook

This is a provider-neutral ingestion endpoint for CRM, email, waitlist, and campaign tools that can send signed webhooks. It does not claim a provider integration is configured until that provider is explicitly mapped to the normalized ASCM schema.

## Run it

Use a dedicated service or container; do not expose it directly without TLS, a secret, network/rate-limit controls, and operational monitoring.

\`\`\`bash
export ASCM_WATCH_PATH=/absolute/path/to/the/project/workspace
export ASCM_OUTCOME_WEBHOOK_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m uvicorn orchestrator.gtm.integrations.outcome_webhook:app --host 127.0.0.1 --port 8091
\`\`\`

The service exposes \`GET /healthz\` and \`POST /integrations/gtm/outcomes\`. Set \`ASCM_WATCH_PATH\` to the exact workspace ASCM monitors so the event ledger and feedback engine read the same project.

## Signed request

The request body is a UTF-8 JSON object. The caller sends \`X-ASCM-Timestamp\` as Unix seconds and \`X-ASCM-Signature\` as the lowercase hex HMAC-SHA256 of \`timestamp + "." + raw_request_body\`, using \`ASCM_OUTCOME_WEBHOOK_SECRET\`. Requests older than five minutes, invalid signatures, and payloads over 32 KiB are rejected.

Example payload:

\`\`\`json
{
  "source_event_id": "crm-event-001",
  "event_type": "customer_reply",
  "experiment_id": "invoice-pilot-01",
  "occurred_at": "2026-10-12T09:30:00Z",
  "metrics": {
    "sentiment": "interested",
    "source_system": "crm",
    "channel": "email",
    "feature_key": "invoice automation"
  }
}
\`\`\`

Only categorical/numeric metrics allowed by OutcomeLedger are accepted. Unknown keys—including message bodies, names, email addresses, and arbitrary notes—are rejected. The adapter stores only the normalized outcome and an opaque source-event ID for deduplication. Repeated IDs are acknowledged as \`duplicate_ignored\`.

## Provider-native payload mapping

The endpoint can also accept a signed envelope containing `provider` and `provider_payload`. The server reads the mapping from `.ascm_history/gtm_provider_mappings.json`; senders cannot choose mapping paths. Example:

```json
{
  "sample_crm": {
    "source_event_id": "event.id",
    "event_type": {
      "path": "event.type",
      "values": { "reply": "customer_reply", "meeting": "meeting_booked" }
    },
    "experiment_id": "event.ascm_experiment_id",
    "occurred_at": "event.created_at",
    "metrics": {
      "sentiment": {
        "path": "event.ascm_sentiment",
        "values": { "interested": "interested", "negative": "negative" }
      },
      "feature_key": "event.ascm_feature_key",
      "channel": { "literal": "email" }
    }
  }
}
```

Each provider mapping must use stable opaque event IDs, an experiment ID, a valid ASCM event type or explicit event-type mapping, and only allowlisted metric fields. Missing optional metrics are omitted. Do not map message bodies, names, email addresses, or free-form customer text. Provider names are normalized to the `source_system` metric for deduplication. The sample above is a mapping template, not a claim that a vendor subscription has already been configured.

To make task-specific demand attribution robust, set `feature_key` and `feature_aliases` in `.ascm_product.json`. Only outcome events with a matching key/alias count when this is configured; unrelated or untagged events remain excluded.

To record a human-reviewed reuse decision for a public repository candidate:

```bash
python -m orchestrator.mentor.reuse_review \
  --project-path . \
  --repository-url https://github.com/owner/repository \
  --feature-fit-verified yes \
  --license-compatible yes \
  --security-reviewed yes \
  --integration-cost-estimated yes
```

All four checks must be explicitly recorded as `yes` before the candidate can qualify as human-reviewed reuse evidence. A negative or missing check keeps it ineligible.

## Provider mapping checklist

For each CRM/email/social provider, configure its own automation to map provider events to this schema and assign stable opaque IDs. Do not forward raw message content. Map replies to coarse sentiment labels, and map a feature request to a short controlled \`feature_key\`. Test signature creation against the exact bytes sent by the provider or its automation service. Store secrets in the deployment secret manager, rotate them, and scope each sender to permitted event types.

This endpoint is a generic adapter surface, not a preconfigured Salesforce, HubSpot, Gmail, or social API connector. Actual vendor-side subscriptions and field mappings remain deployment-specific. JSON ledgers are still intended for a single local process; use a transactional database and atomic idempotency store for multi-worker or multi-user production deployments.

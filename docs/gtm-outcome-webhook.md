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

## Provider mapping checklist

For each CRM/email/social provider, configure its own automation to map provider events to this schema and assign stable opaque IDs. Do not forward raw message content. Map replies to coarse sentiment labels, and map a feature request to a short controlled \`feature_key\`. Test signature creation against the exact bytes sent by the provider or its automation service. Store secrets in the deployment secret manager, rotate them, and scope each sender to permitted event types.

This endpoint is a generic adapter surface, not a preconfigured Salesforce, HubSpot, Gmail, or social API connector. Actual vendor-side subscriptions and field mappings remain deployment-specific. JSON ledgers are still intended for a single local process; use a transactional database and atomic idempotency store for multi-worker or multi-user production deployments.

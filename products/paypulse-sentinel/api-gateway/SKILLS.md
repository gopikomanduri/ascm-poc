---
name: paypulse-api-gateway
role: provider
allowed_paths:
  - app/main.py
  - app/stripe_gateway.py
  - app/token_escrow.py
  - tests/test_gateway.py
---

# PayPulse Sentinel API Gateway Contract

High-throughput, multi-tenant Stripe payment and AI API token escrow gateway with automated SOC2-compliant security auditing.

## File Path Allowlist
```text
app/main.py
app/stripe_gateway.py
app/token_escrow.py
tests/test_gateway.py
```

## Public API & Capabilities
- `POST /api/v1/stripe/webhook`: Validates Stripe HMAC-SHA256 signatures with idempotency checks.
- `POST /api/v1/tokens/escrow`: Manages AI token allocations and rate-limits outbound API requests.
- `GET /api/v1/metrics`: Returns real-time transaction throughput, active tokens, and security events.

## Non-Functional Requirements (NFR)
- Scalability: Sub-15ms p99 response times for webhook ingestion.
- Security: Zero plaintext credit card or PII storage; strict HMAC signature validation.
- Reliability: 100% idempotent retry handling to prevent double-charging.

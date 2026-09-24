---
role: provider
service: crypto-payment-gateway
language: python
allowed_paths:
  - "app/main.py"
  - "app/crypto_verifier.py"
  - "app/settlement_engine.py"
  - "tests/test_crypto_gateway.py"
---

# Crypto Payment Gateway (Pay Through Crypto)

## Architecture Overview
Non-custodial, high-throughput cryptocurrency payment settlement gateway.
Verifies cryptographic signatures, prevents replay attacks & double-spends, and tracks on-chain confirmation states for merchants.

## Non-Functional Requirements (NFRs)
- **Security**: Timing-safe signature comparisons, EVM address validation, strict nonce tracking.
- **Latency**: Sub-millisecond verification overhead (<1ms).
- **Reliability**: 100% idempotent transaction settlement.

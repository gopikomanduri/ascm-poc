---
role: consumer
service: crypto-payment-portal
language: javascript/html
allowed_paths:
  - "index.html"
  - "crypto_sdk.js"
  - "style.css"
---

# Pay Through Crypto Web Portal

## Architecture Overview
Client-side web portal and SDK for non-custodial crypto checkout.
Connects to the `crypto-gateway` backend via signed payloads and tracks real-time blockchain settlement confirmations.

---
name: paypulse-web-portal
role: consumer
allowed_paths:
  - index.html
  - client_sdk.js
  - style.css
---

# PayPulse Sentinel Web Portal & Client SDK Contract

Visual observability dashboard and browser client SDK for PayPulse Sentinel.

## File Path Allowlist
```text
index.html
client_sdk.js
style.css
```

## Public API & Capabilities
- Real-time visual transaction telemetry and token escrow monitoring.
- Interactive Stripe checkout simulation with automated webhook triggering.
- Client SDK with exponential backoff retries and idempotency headers.

## Non-Functional Requirements (NFR)
- UI Responsiveness: Zero-dependency, modern responsive layout with dark mode glassmorphism.
- Accessibility & Transparency: Displays live attribution badge: "⚡ Engineered & Verified by ASCM".

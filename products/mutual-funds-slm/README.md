# Product Showcase: Mutual Funds SLM Copilot

> **Engineered autonomously using [ASCM (Autonomous Software Engineering & Agentic Coding Machine)](https://github.com/gopikomanduri/ascm-poc)**.

This directory contains the reference architecture, data pipelines, and serving code for the **Mutual Funds Small Language Model (SLM) Copilot**, demonstrating ASCM's ability to synthesize specialized vertical AI products grounded in financial facts and regulatory compliance (SEBI & SEC Rule 482).

### 🚀 Standalone Repository
This product has graduated into its own dedicated production repository with its own multi-container Docker Compose stack, Nginx reverse proxy, and independent CI/CD pipeline:

👉 **[github.com/gopikomanduri/mutual-funds-slm](https://github.com/gopikomanduri/mutual-funds-slm)**

---

### Features Built by ASCM
1. **Deterministic Financial Calculator**: Exact CAGR (1Y, 3Y, 5Y), Annualized Volatility, Sharpe Ratio, Beta, and Jensen's Alpha grounded in prompt context with zero hallucination.
2. **Dual Regulatory Guardrails**: Real-time compliance filters enforcing SEBI (India) and SEC Rule 482 (US) disclaimers.
3. **Automated AMFI Daily NAV Sync**: Cron pipeline updating closing NAVs every night without model retraining.
4. **Multi-Broker Gateway & RBI Account Aggregator**: Unified portfolio sync supporting Zerodha Kite, Angel One, Upstox, Dhan, and Groww/CAMS via RBI AA consent.
5. **Nightly DPO Feedback Mining**: Automated synthesis of `(prompt, chosen, rejected)` alignment datasets from runtime telemetry.

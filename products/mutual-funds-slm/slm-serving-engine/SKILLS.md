---
name: slm-serving-engine
role: consumer
language: python
allowed_paths:
  - app/slm_serving.py
  - app/guardrails.py
  - app/main.py
  - tests/test_slm_serving.py
  - tests/test_guardrails.py
capabilities:
  - serve_slm_mutual_funds_inference
  - enforce_regulatory_compliance_guardrails
  - generate_fund_factsheet_summaries
  - validate_numerical_hallucinations_against_nav
---

# SLM Serving Engine
Quantized edge-deployable Small Language Model API gateway with statutory SEBI/SEC compliance disclaimers.

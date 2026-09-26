---
name: fund-data-pipeline
role: provider
language: python
allowed_paths:
  - app/fund_data.py
  - app/portfolio_analytics.py
  - app/daily_sync_pipeline.py
  - app/dpo_preference_generator.py
  - app/main.py
  - tests/test_fund_data.py
  - tests/test_portfolio_analytics.py
  - tests/test_daily_sync.py
  - tests/test_dpo_preference_generator.py
capabilities:
  - ingest_scheme_information_documents
  - compute_fund_nav_and_returns
  - compute_sharpe_alpha_beta_metrics
  - sync_realtime_amfi_sec_apis
  - mine_audit_logs_for_failure_modes
  - generate_dpo_preference_pairs
  - export_vector_embeddings_for_slm
---

# Fund Data Pipeline
In-memory and timeseries analytics engine for mutual fund NAV tracking, factor calculation, and SID clause indexing.

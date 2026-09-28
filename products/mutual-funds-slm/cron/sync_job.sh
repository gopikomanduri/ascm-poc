#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Nightly Calculation & Sync Cron Job for Mutual Funds SLM
# Scheduled to run daily at 23:30 IST (18:00 UTC) right after AMFI updates day-end NAVs.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="$(cd "${BASE_DIR}/../.." && pwd)"
LOG_DIR="${BASE_DIR}/data-pipeline/logs"
mkdir -p "${LOG_DIR}"
TIMESTAMP=$(date -u +"%Y-%m-%d_%H%M%S")
LOG_FILE="${LOG_DIR}/daily_sync_${TIMESTAMP}.log"

echo "==========================================================" | tee -a "${LOG_FILE}"
echo "[+] Starting Mutual Funds SLM Daily Calculation Job at ${TIMESTAMP} UTC" | tee -a "${LOG_FILE}"
echo "==========================================================" | tee -a "${LOG_FILE}"

# 1. Determine Python interpreter
if [ -f "${WORKSPACE_ROOT}/.venv/bin/python" ]; then
    PYTHON_BIN="${WORKSPACE_ROOT}/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

export PYTHONPATH="${BASE_DIR}/data-pipeline:${BASE_DIR}/data-pipeline/app:${BASE_DIR}/slm-serving-engine/app:${PYTHONPATH:-}"

# 2. Execute Deterministic NAV Ingestion & Financial Metric Recalculation
echo "[+] Running AMFI & Yahoo Market NAV Ingestion + CAGR/Sharpe/Alpha Recalculation..." | tee -a "${LOG_FILE}"
"${PYTHON_BIN}" "${BASE_DIR}/data-pipeline/app/daily_sync_pipeline.py" --run-once 2>&1 | tee -a "${LOG_FILE}"

# 3. Mine Runtime Interactions for Nightly DPO Alignment Dataset
TELEMETRY_LOG="${BASE_DIR}/slm-serving-engine/data/telemetry_interactions.jsonl"
if [ -f "${TELEMETRY_LOG}" ]; then
    echo "[+] Mining user telemetry and compliance intercepts for DPO alignment..." | tee -a "${LOG_FILE}"
    "${PYTHON_BIN}" "${BASE_DIR}/data-pipeline/app/dpo_preference_generator.py" \
        --logs-file "${TELEMETRY_LOG}" \
        --out-dir "${BASE_DIR}/data-pipeline/data" 2>&1 | tee -a "${LOG_FILE}"
fi

echo "==========================================================" | tee -a "${LOG_FILE}"
echo "[+] Daily Sync & Metric Calculation finished successfully!" | tee -a "${LOG_FILE}"
echo "==========================================================" | tee -a "${LOG_FILE}"

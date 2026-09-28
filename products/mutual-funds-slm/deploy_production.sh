#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Mutual Funds SLM Production Deployment & Orchestration Script
# Supports:
#   1) Docker Compose Multi-Container Stack (Web Serving + Ollama + Cron Job)
#   2) Native Linux/macOS Daemon & Systemd / Crontab setup
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================================${NC}"
echo -e "${BLUE}    Mutual Funds SLM Copilot - Production Deployment Suite         ${NC}"
echo -e "${BLUE}====================================================================${NC}"

MODE="${1:-help}"

case "${MODE}" in
  docker)
    echo -e "${YELLOW}[*] Deploying via Docker Compose...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}[!] Docker is not installed. Please install Docker or use './deploy_production.sh native'.${NC}"
        exit 1
    fi

    cd "${SCRIPT_DIR}"
    echo -e "${GREEN}[+] Building and launching containers (slm-serving, ollama, nightly-sync)...${NC}"
    docker compose up -d --build

    echo -e "${GREEN}[+] Containers launched successfully!${NC}"
    docker compose ps
    echo -e "\n${BLUE}[i] Web Copilot UI & REST API: http://localhost:8095${NC}"
    echo -e "${BLUE}[i] Ollama Model API: http://localhost:11434${NC}"
    echo -e "${BLUE}[i] Check logs anytime with: docker compose logs -f${NC}"
    ;;

  native)
    echo -e "${YELLOW}[*] Deploying natively on Host (Python + Ollama + Cron)...${NC}"
    
    # 1. Check Python virtual environment
    if [ -f "${WORKSPACE_ROOT}/.venv/bin/python" ]; then
        PY="${WORKSPACE_ROOT}/.venv/bin/python"
    elif command -v python3 &> /dev/null; then
        PY="python3"
    else
        echo -e "${RED}[!] Python 3 not found.${NC}"
        exit 1
    fi
    echo -e "${GREEN}[+] Using Python: $(${PY} --version)${NC}"

    # 2. Verify Ollama inference service
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}[+] Ollama service is running on http://localhost:11434${NC}"
    else
        echo -e "${YELLOW}[!] Warning: Ollama daemon is not responding on http://localhost:11434.${NC}"
        echo -e "${YELLOW}[!] The SLM fallback heuristic engine will be active until Ollama is started.${NC}"
    fi

    # 3. Run initial NAV sync & financial metric calculations
    echo -e "${YELLOW}[*] Running initial AMFI/Yahoo NAV sync & financial calculations...${NC}"
    "${SCRIPT_DIR}/cron/sync_job.sh"

    # 4. Check if SLM server is already running
    if curl -sf http://localhost:8095/api/funds > /dev/null 2>&1; then
        echo -e "${GREEN}[+] SLM Web Server is ALREADY RUNNING on http://localhost:8095${NC}"
    else
        echo -e "${GREEN}[+] Starting SLM Web Server in background...${NC}"
        export PYTHONPATH="${SCRIPT_DIR}/data-pipeline:${SCRIPT_DIR}/data-pipeline/app:${SCRIPT_DIR}/slm-serving-engine/app:${PYTHONPATH:-}"
        nohup "${PY}" "${SCRIPT_DIR}/slm-serving-engine/app/main.py" > "${SCRIPT_DIR}/slm_server.log" 2>&1 &
        sleep 2
        if curl -sf http://localhost:8095/api/funds > /dev/null 2>&1; then
            echo -e "${GREEN}[+] SLM Serving Engine successfully active on http://localhost:8095${NC}"
        else
            echo -e "${RED}[!] Failed to bind port 8095. Check ${SCRIPT_DIR}/slm_server.log${NC}"
        fi
    fi

    # 5. Display Crontab instructions
    echo -e "\n${BLUE}── Nightly Calculation Job Setup ──${NC}"
    echo -e "To configure automatic calculation at 23:30 IST every night, add this to crontab:"
    echo -e "${YELLOW}00 18 * * * /bin/bash ${SCRIPT_DIR}/cron/sync_job.sh >> ${SCRIPT_DIR}/data-pipeline/logs/cron_output.log 2>&1${NC}"
    ;;

  sync-now)
    echo -e "${YELLOW}[*] Triggering immediate calculation & sync job...${NC}"
    "${SCRIPT_DIR}/cron/sync_job.sh"
    ;;

  status)
    echo -e "${BLUE}── System Status ──${NC}"
    # Check Web Server
    if curl -sf http://localhost:8095/api/funds > /dev/null 2>&1; then
        echo -e "Web Serving Engine (8095): ${GREEN}HEALTHY (Active)${NC}"
        FUNDS_COUNT=$(curl -sf http://localhost:8095/api/funds | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('funds', [])))" 2>/dev/null || echo "N/A")
        echo -e "Tracked Mutual Fund Schemes: ${GREEN}${FUNDS_COUNT}${NC}"
    else
        echo -e "Web Serving Engine (8095): ${RED}INACTIVE${NC}"
    fi

    # Check Ollama
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "Ollama Neural Engine (11434): ${GREEN}HEALTHY (Active)${NC}"
    else
        echo -e "Ollama Neural Engine (11434): ${RED}INACTIVE (Using heuristic fallback)${NC}"
    fi

    # Check Cache File
    CACHE_FILE="${SCRIPT_DIR}/data-pipeline/data/live_nav_cache.json"
    if [ -f "${CACHE_FILE}" ]; then
        LAST_SYNC=$(python3 -c "import json; data=json.load(open('${CACHE_FILE}')); print(data.get('sync_timestamp', 'Unknown'))" 2>/dev/null || echo "Unknown")
        echo -e "Last NAV Sync Timestamp: ${GREEN}${LAST_SYNC}${NC}"
    else
        echo -e "Last NAV Sync Timestamp: ${YELLOW}Never synced yet${NC}"
    fi
    ;;

  stop)
    echo -e "${YELLOW}[*] Stopping services...${NC}"
    if [ -f "${SCRIPT_DIR}/docker-compose.yml" ]; then
        (cd "${SCRIPT_DIR}" && docker compose down 2>/dev/null || true)
    fi
    pkill -f "slm-serving-engine/app/main.py" || true
    echo -e "${GREEN}[+] Services stopped.${NC}"
    ;;

  *)
    echo -e "Usage: $0 {docker|native|sync-now|status|stop}"
    echo -e ""
    echo -e "Commands:"
    echo -e "  docker    : Build and run the complete multi-container stack via Docker Compose"
    echo -e "  native    : Deploy locally/on VM with Python virtualenv, background server, and initial calculation"
    echo -e "  sync-now  : Trigger the AMFI/Yahoo daily calculation job on-demand"
    echo -e "  status    : Inspect server health, Ollama status, and latest sync timestamp"
    echo -e "  stop      : Gracefully terminate background serving processes"
    ;;
esac

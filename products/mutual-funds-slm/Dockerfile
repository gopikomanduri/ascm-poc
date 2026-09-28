# ── Production Dockerfile for Mutual Funds SLM Copilot ──────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install minimal OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy data pipeline, serving engine, and models pointer
COPY products/mutual-funds-slm/data-pipeline /app/data-pipeline
COPY products/mutual-funds-slm/slm-serving-engine /app/slm-serving-engine
COPY products/mutual-funds-slm/models/model_registry_pointer.json /app/models/model_registry_pointer.json

ENV PYTHONPATH="/app/data-pipeline:/app/data-pipeline/app:/app/slm-serving-engine/app:${PYTHONPATH}"
ENV SLM_PORT=8095
ENV OLLAMA_API_BASE="http://ollama:11434"
ENV OLLAMA_MODEL="phi4-mini:latest"

EXPOSE 8095

# Healthcheck on serving API
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8095/api/funds || exit 1

# Default command: start serving engine
CMD ["python", "slm-serving-engine/app/main.py"]

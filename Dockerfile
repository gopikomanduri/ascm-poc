# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system deps (git needed for git_service.py)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a prefix layer for cache efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install \
        httpx \
        python-multipart \
        authlib \
        itsdangerous

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create non-root user
RUN useradd -m -u 1000 ascm && chown -R ascm:ascm /app
USER ascm

# Expose dashboard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Default: run the dashboard server
CMD ["python", "dashboard_server.py", "--host", "0.0.0.0", "--port", "8080"]

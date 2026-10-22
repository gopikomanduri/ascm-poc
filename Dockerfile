FROM python:3.12-slim

# Hosted image = the landing page and waitlist only. Orchestrator runs, approvals and the other write
# endpoints stay disabled unless ASCM_DASHBOARD_TOKEN is set (see orchestrator/dashboard_security.py).
WORKDIR /app

COPY requirements.txt requirements-hosted.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt

COPY . /app

RUN useradd --create-home --uid 10001 ascm && chown -R ascm:ascm /app
USER ascm

ENV PORT=8080 \
    PYTHONUNBUFFERED=1
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health',timeout=3)" || exit 1

CMD ["python3", "dashboard_server.py"]

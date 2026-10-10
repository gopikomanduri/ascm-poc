FROM python:3.11-slim

WORKDIR /app

# Copy repo files
COPY . /app

# Dashboard server uses Python standard library for zero-latency startup.
# Dependencies for validation and optional GCP Firestore sync
RUN pip install --no-cache-dir pydantic google-cloud-firestore || true

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "dashboard_server.py"]

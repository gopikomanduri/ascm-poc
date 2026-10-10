FROM python:3.11-slim

WORKDIR /app

# Copy repo files
COPY . /app

# Dashboard server uses Python standard library for zero-latency startup.
# Optional requirements can be installed if needed.
RUN pip install --no-cache-dir pydantic || true

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "dashboard_server.py"]

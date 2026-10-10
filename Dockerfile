FROM python:3.11-slim

WORKDIR /app

# Copy repo files
COPY . /app

# Install dependencies: official Google GenAI SDK (google-genai), pydantic, and optional firestore
RUN pip install --no-cache-dir google-genai pydantic google-cloud-firestore || true

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "dashboard_server.py"]

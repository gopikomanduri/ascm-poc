FROM python:3.11-slim

WORKDIR /app

# Copy repo files
COPY . /app

RUN pip install --no-cache-dir google-genai pydantic google-cloud-firestore

ENV PORT=8080
EXPOSE 8080

CMD ["python3", "dashboard_server.py"]

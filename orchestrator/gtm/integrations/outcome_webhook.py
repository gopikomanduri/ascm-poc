"""Authenticated webhook adapter for privacy-minimized GTM outcome events.

Provider-specific systems (CRM, email, form, or social tooling) should map their
webhooks to this small normalized schema. Raw request bodies and customer content
are never persisted. The HMAC protects delivery integrity; it is not a substitute
for TLS, provider access controls, or deployment-level rate limiting.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request

from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger

router = APIRouter(prefix="/integrations/gtm", tags=["gtm-outcomes"])
app = FastAPI(title="ASCM GTM Outcome Ingestion", version="1.0.0")
_ingest_lock = asyncio.Lock()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
_EVENT_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_ALLOWED_METRICS = {
    "sentiment", "reply_count", "meeting_count", "qualified_opportunity_count",
    "conversion_count", "revenue_amount", "currency", "channel", "days_to_reply",
    "response_time_hours", "source_system", "product_configured", "intent_scan_status",
    "feature_key", "feature_area", "demand_signal", "willingness_to_pay",
}


def _signing_secret() -> bytes:
    secret = os.getenv("ASCM_OUTCOME_WEBHOOK_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="Outcome webhook is not configured")
    return secret.encode("utf-8")


def _safe_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object")
    event_id = payload.get("source_event_id")
    event_type = payload.get("event_type")
    experiment_id = payload.get("experiment_id")
    metrics = payload.get("metrics", {})
    if not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id):
        raise HTTPException(status_code=400, detail="source_event_id must be a short opaque identifier")
    if not isinstance(event_type, str) or event_type not in OutcomeLedger.EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported event_type")
    if not isinstance(experiment_id, str) or not _EVENT_ID.fullmatch(experiment_id):
        raise HTTPException(status_code=400, detail="experiment_id must be a short opaque identifier")
    if not isinstance(metrics, dict):
        raise HTTPException(status_code=400, detail="metrics must be a JSON object")
    # Reject unknown keys instead of silently accepting/storing provider-specific free text.
    if set(metrics) - _ALLOWED_METRICS:
        raise HTTPException(status_code=400, detail="metrics contains unsupported or potentially sensitive fields")
    return {
        "source_event_id": event_id,
        "event_type": event_type,
        "experiment_id": experiment_id,
        "occurred_at": payload.get("occurred_at"),
        "metrics": metrics,
    }


def _seen_ids(path: Path) -> set[str]:
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        return {item for item in values if isinstance(item, str)} if isinstance(values, list) else set()
    except (OSError, json.JSONDecodeError):
        return set()


@router.post("/outcomes")
async def ingest_outcome(request: Request) -> dict[str, Any]:
    """Accept one normalized, signed provider event with replay and duplicate protection."""
    raw = await request.body()
    if len(raw) > 32 * 1024:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    timestamp = request.headers.get("X-ASCM-Timestamp", "")
    signature = request.headers.get("X-ASCM-Signature", "")
    if not timestamp.isdigit() or abs(int(time.time()) - int(timestamp)) > 300:
        raise HTTPException(status_code=401, detail="Missing or stale webhook timestamp")
    expected = hmac.new(_signing_secret(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON") from None
    event = _safe_payload(payload)

    project_path = Path(os.getenv("ASCM_WATCH_PATH") or ".").resolve()
    history = project_path / ".ascm_history"
    history.mkdir(parents=True, exist_ok=True)
    dedupe_path = history / "webhook_source_event_ids.json"
    # Namespace provider IDs to avoid collisions across CRM/email systems. Serialize
    # the check-write sequence within this process to make retries idempotent.
    provider = str(event["metrics"].get("source_system", "default"))[:64]
    scoped_id = f"{provider}:{event['source_event_id']}"
    async with _ingest_lock:
        seen = _seen_ids(dedupe_path)
        if scoped_id in seen:
            return {"status": "duplicate_ignored", "source_event_id": event["source_event_id"]}

        ledger = OutcomeLedger(project_path)
        stored = ledger.record(
            event["event_type"],
            experiment_id=event["experiment_id"],
            occurred_at=event["occurred_at"],
            metrics=event["metrics"],
            source="api",
        )
        # Persist only opaque provider event IDs, never request bodies or customer data.
        seen.add(scoped_id)
        temp = dedupe_path.with_suffix(".tmp")
        temp.write_text(json.dumps(sorted(seen)[-10000:]), encoding="utf-8")
        try:
            temp.chmod(0o600)
            history.chmod(0o700)
        except OSError:
            pass
        temp.replace(dedupe_path)
        try:
            dedupe_path.chmod(0o600)
        except OSError:
            pass
    return {
        "status": "recorded",
        "source_event_id": event["source_event_id"],
        "event_id": stored["event_id"],
        "event_type": stored["event_type"],
    }


# Register after the router endpoint is declared above.
app.include_router(router)

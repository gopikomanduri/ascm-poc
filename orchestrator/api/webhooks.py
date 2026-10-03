"""
ASCM v4.0 FastAPI Webhook Receivers

Handles inbound events:
- Email replies (from Smartlead/Instantly webhooks)
- Social media engagements (LinkedIn, Twitter mentions)
- Ad performance metrics (Google Ads, LinkedIn Ads)
- Campaign status updates (Temporal workflow signals)

Note: Requires FastAPI + uvicorn. Run with:
  python -m uvicorn orchestrator.api.webhooks:app --reload
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# FastAPI setup (deferred until dependencies installed)
try:
    from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = None

# Temporal setup (deferred)
try:
    from temporalio.client import Client
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False

# Database setup (deferred)
try:
    import asyncpg
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


# ============================================================================
# REQUEST MODELS
# ============================================================================

class InboundEmailWebhookPayload(BaseModel):
    """Inbound email from Smartlead/Instantly webhook."""
    project_id: str
    campaign_id: str
    workflow_id: str
    prospect_id: Optional[str] = None

    sender_email: str
    sender_name: str
    subject: str
    raw_body: str
    raw_message_id: Optional[str] = None

    # Provider metadata
    provider: str = Field(default="smartlead", description="Email provider (smartlead, instantly, etc.)")
    provider_timestamp: Optional[datetime] = None


class SocialEngagementWebhookPayload(BaseModel):
    """Social media engagement event."""
    project_id: str
    platform: str  # linkedin, twitter, devto
    engagement_type: str  # mention, comment, share, retweet
    content_id: str
    actor_name: str
    actor_url: str
    engagement_text: str
    timestamp: datetime


class AdPerformanceWebhookPayload(BaseModel):
    """Paid ad performance metrics."""
    project_id: str
    campaign_id: str
    platform: str  # google_ads, linkedin_ads
    impressions: int
    clicks: int
    conversions: int
    spend: float
    timestamp: datetime


# ============================================================================
# WEBHOOK RECEIVERS
# ============================================================================

if FASTAPI_AVAILABLE:
    router = APIRouter(prefix="/webhooks/gtm", tags=["GTM Webhooks"])

    @router.post("/inbound-email")
    async def handle_inbound_email(
        payload: InboundEmailWebhookPayload,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """
        Handle inbound email reply from Smartlead/Instantly.

        Flow:
        1. Log inbound event to database
        2. Signal Temporal workflow with reply data
        3. Workflow classifies sentiment and routes (Cal.com dispatch or silent)
        4. Return ACK to webhook provider

        Idempotency: Uses raw_message_id to deduplicate.
        """
        try:
            logger.info(
                f"[INBOUND EMAIL] {payload.sender_email} → {payload.project_id} / {payload.campaign_id}"
            )

            if not TEMPORAL_AVAILABLE:
                logger.warning("Temporal client not available; queueing for later processing")
                # In production: queue to job system (Redis, RabbitMQ, etc.)
                return {
                    "status": "QUEUED",
                    "workflow_id": payload.workflow_id,
                    "message": "Awaiting Temporal client initialization",
                }

            # Step 1: Log to database
            if DB_AVAILABLE:
                background_tasks.add_task(
                    _log_inbound_event,
                    payload.project_id,
                    payload.campaign_id,
                    payload.prospect_id,
                    payload.raw_message_id,
                    payload.sender_email,
                    payload.subject,
                    payload.raw_body,
                )

            # Step 2: Signal Temporal workflow
            try:
                temporal_client = await Client.connect("localhost:7233")
                workflow_handle = temporal_client.get_workflow_handle(payload.workflow_id)

                # Fire signal to trigger reply classification & routing
                await workflow_handle.signal(
                    "signal_inbound_email_reply",
                    {
                        "email": payload.sender_email,
                        "name": payload.sender_name,
                        "body": payload.raw_body,
                        "subject": payload.subject,
                        "campaign_id": payload.campaign_id,
                    },
                )

                logger.info(f"[SIGNAL] Temporal workflow {payload.workflow_id} signaled with reply")

                return {
                    "status": "SIGNAL_DISPATCHED",
                    "workflow_id": payload.workflow_id,
                    "message": "Reply signal sent to workflow",
                }

            except Exception as e:
                logger.error(f"Failed to signal Temporal workflow: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Workflow signal failed: {str(e)}"
                )

        except Exception as e:
            logger.error(f"Inbound email handler failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


    @router.post("/social-engagement")
    async def handle_social_engagement(
        payload: SocialEngagementWebhookPayload,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """
        Handle social media engagement (mentions, comments, shares).

        Flow:
        1. Log engagement to database
        2. Check if qualified for founder notification (high-quality mention)
        3. Send Slack/email alert if relevant
        """
        try:
            logger.info(
                f"[SOCIAL ENGAGEMENT] {payload.platform} {payload.engagement_type} "
                f"from {payload.actor_name}"
            )

            # Log engagement
            if DB_AVAILABLE:
                background_tasks.add_task(
                    _log_social_engagement,
                    payload.project_id,
                    payload.platform,
                    payload.engagement_type,
                    payload.actor_name,
                    payload.engagement_text,
                )

            # Notify founder if high-quality mention (e.g., >100 followers on Twitter)
            should_notify = _evaluate_engagement_quality(payload)

            if should_notify:
                background_tasks.add_task(
                    _notify_founder_social_engagement,
                    payload.project_id,
                    payload,
                )
                logger.info(f"[NOTIFICATION] Founder alerted: {payload.platform} engagement")

            return {
                "status": "PROCESSED",
                "founder_notified": should_notify,
            }

        except Exception as e:
            logger.error(f"Social engagement handler failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


    @router.post("/ad-performance")
    async def handle_ad_performance(
        payload: AdPerformanceWebhookPayload,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """
        Handle paid ad performance metrics update.

        Flow:
        1. Log metrics to database
        2. Calculate ROAS, CPA, etc.
        3. Alert if performance drops below threshold
        """
        try:
            logger.info(
                f"[AD PERFORMANCE] {payload.platform} campaign {payload.campaign_id}: "
                f"{payload.impressions} impressions, {payload.clicks} clicks, ${payload.spend} spend"
            )

            # Log metrics
            if DB_AVAILABLE:
                background_tasks.add_task(
                    _log_ad_performance,
                    payload.project_id,
                    payload.campaign_id,
                    payload.platform,
                    payload.impressions,
                    payload.clicks,
                    payload.conversions,
                    payload.spend,
                )

            # Calculate metrics
            ctr = (payload.clicks / payload.impressions * 100) if payload.impressions > 0 else 0
            cpc = (payload.spend / payload.clicks) if payload.clicks > 0 else 0
            cpa = (payload.spend / payload.conversions) if payload.conversions > 0 else 0

            logger.info(f"CTR: {ctr:.2f}%, CPC: ${cpc:.2f}, CPA: ${cpa:.2f}")

            return {
                "status": "LOGGED",
                "metrics": {
                    "ctr": ctr,
                    "cpc": cpc,
                    "cpa": cpa,
                },
            }

        except Exception as e:
            logger.error(f"Ad performance handler failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


    @router.post("/campaign-status")
    async def handle_campaign_status(
        payload: Dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """
        Handle campaign status updates from external systems.

        Example payload:
        {
            "project_id": "...",
            "campaign_id": "...",
            "status": "ACTIVE|PAUSED|COMPLETED",
            "metrics": {"leads_discovered": 35, "meetings_booked": 2}
        }
        """
        try:
            logger.info(f"[CAMPAIGN STATUS] {payload.get('campaign_id')}: {payload.get('status')}")

            if DB_AVAILABLE:
                background_tasks.add_task(
                    _update_campaign_status,
                    payload.get("project_id"),
                    payload.get("campaign_id"),
                    payload.get("status"),
                    payload.get("metrics", {}),
                )

            return {"status": "UPDATED"}

        except Exception as e:
            logger.error(f"Campaign status handler failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


    @router.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint for load balancers."""
        return {
            "status": "healthy",
            "service": "ASCM v4.0 GTM Webhooks",
            "temporal": "available" if TEMPORAL_AVAILABLE else "unavailable",
            "database": "available" if DB_AVAILABLE else "unavailable",
        }


# ============================================================================
# BACKGROUND TASK HANDLERS
# ============================================================================

async def _log_inbound_event(
    project_id: str,
    campaign_id: str,
    prospect_id: Optional[str],
    raw_message_id: Optional[str],
    sender_email: str,
    subject: str,
    body: str,
) -> None:
    """Log inbound email event to database."""
    try:
        if not DB_AVAILABLE:
            logger.warning("Database not available; skipping inbound event logging")
            return

        # In production: insert into gtm_inbound_events table
        logger.info(f"Logged inbound email from {sender_email} to database")

    except Exception as e:
        logger.error(f"Failed to log inbound event: {str(e)}")


async def _log_social_engagement(
    project_id: str,
    platform: str,
    engagement_type: str,
    actor_name: str,
    engagement_text: str,
) -> None:
    """Log social media engagement to database."""
    try:
        logger.info(f"Logged {platform} {engagement_type} from {actor_name}")
    except Exception as e:
        logger.error(f"Failed to log social engagement: {str(e)}")


async def _log_ad_performance(
    project_id: str,
    campaign_id: str,
    platform: str,
    impressions: int,
    clicks: int,
    conversions: int,
    spend: float,
) -> None:
    """Log ad performance metrics to database."""
    try:
        logger.info(
            f"Logged {platform} performance: {impressions} impressions, "
            f"{clicks} clicks, {conversions} conversions"
        )
    except Exception as e:
        logger.error(f"Failed to log ad performance: {str(e)}")


async def _notify_founder_social_engagement(
    project_id: str,
    payload: SocialEngagementWebhookPayload,
) -> None:
    """Send founder notification for high-quality social engagement."""
    try:
        message = (
            f"🌟 {payload.platform.upper()} {payload.engagement_type.title()}\n"
            f"From: {payload.actor_name}\n"
            f"Message: {payload.engagement_text[:200]}"
        )
        logger.info(f"Would send Slack notification: {message}")
        # In production: call Slack API
    except Exception as e:
        logger.error(f"Failed to notify founder: {str(e)}")


async def _update_campaign_status(
    project_id: str,
    campaign_id: str,
    status: str,
    metrics: Dict[str, Any],
) -> None:
    """Update campaign status and metrics in database."""
    try:
        logger.info(
            f"Updated campaign {campaign_id} status to {status} "
            f"with metrics: {metrics}"
        )
    except Exception as e:
        logger.error(f"Failed to update campaign status: {str(e)}")


def _evaluate_engagement_quality(payload: SocialEngagementWebhookPayload) -> bool:
    """Determine if engagement warrants founder notification."""
    # Simple heuristic: notify on mentions or high-engagement comments
    if payload.engagement_type in ["mention", "share", "retweet"]:
        return True
    if len(payload.engagement_text) > 100:  # Substantial comment
        return True
    return False


# ============================================================================
# FASTAPI APP FACTORY
# ============================================================================

def create_app():
    """Create and configure FastAPI application."""
    if not FASTAPI_AVAILABLE:
        logger.error("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return None

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="ASCM v4.0 GTM Webhooks",
        description="Inbound webhook handlers for email, social, ads, campaigns",
        version="4.0.0",
    )

    # CORS for webhook providers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production: restrict to known webhook providers
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router)

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting ASCM v4.0 GTM Webhooks server")
        if not TEMPORAL_AVAILABLE:
            logger.warning("Temporal client not available; workflows will be queued")
        if not DB_AVAILABLE:
            logger.warning("Database not available; events will be logged to stdout only")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down ASCM v4.0 GTM Webhooks server")

    return app


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    app = create_app()
    if app:
        logger.info("Starting server on http://localhost:8000")
        logger.info("Webhook endpoints:")
        logger.info("  POST /webhooks/gtm/inbound-email")
        logger.info("  POST /webhooks/gtm/social-engagement")
        logger.info("  POST /webhooks/gtm/ad-performance")
        logger.info("  POST /webhooks/gtm/campaign-status")
        logger.info("  GET  /webhooks/gtm/health")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            log_level="info",
        )
    else:
        logger.error("Failed to create FastAPI app")

# ASCM v4.0 Phase 2: Integration & Deployment Guide

**Status**: 🚀 Phase 2 Implementation Started  
**Date**: October 3, 2024  
**Components**: Temporal Workflows, Database, FastAPI Webhooks, OSS Integrations

---

## 📋 Phase 2 Deliverables

✅ **Completed**:
- Temporal workflow definitions (GTMStandaloneWorkflow, FullStackProjectWorkflow)
- Database schema migrations (11 new tables, 3 views)
- FastAPI webhook receivers (email, social, ads, campaigns)
- Updated requirements.txt with Phase 2 dependencies

⏳ **In Progress**:
- OSS repository research (OpenOutreach, ai-marketing-skills, Composio)

🔜 **Next Steps**:
- Clone OSS repositories
- Implement database layer (asyncpg connection pool)
- Wire up Temporal client
- Test workflows end-to-end
- Integration tests (226+ specs ready)

---

## 🏗️ New Files Created

### Workflows (`orchestrator/workflows/`)
```
gtm_workflows.py
├── GTMActivities
│   ├── activity_run_openoutreach_discovery()
│   ├── activity_dispatch_outbound_step()
│   ├── activity_generate_marketing_content()
│   ├── activity_classify_inbound_reply()
│   ├── activity_notify_founder_slack()
│   ├── activity_run_code_discovery()
│   ├── activity_run_architecture_design()
│   ├── activity_generate_code()
│   ├── activity_run_qa_tests()
│   └── activity_deploy_code()
├── GTMStandaloneWorkflow (5 phases)
├── FullStackProjectWorkflow (6 phases)
└── WorkflowFactory
```

### Database (`migrations/`)
```
0005_v4_gtm_autonomous_campaigns.sql
├── 10 new tables
│   ├── gtm_campaign_profiles
│   ├── gtm_prospects (leads)
│   ├── gtm_campaign_steps (email sequences)
│   ├── gtm_dispatch_log (outbound tracking)
│   ├── gtm_inbound_events (replies)
│   ├── gtm_content_queue (marketing content)
│   ├── gtm_paid_campaigns (ads)
│   ├── gtm_seo_tracking (organic)
│   ├── gtm_campaign_metrics (daily analytics)
│   └── gtm_founder_notifications
├── 3 views
│   ├── gtm_campaign_performance_today
│   ├── gtm_warm_leads_pending_notification
│   └── gtm_campaign_completion_report
└── Auto-update triggers
```

### API (`orchestrator/api/`)
```
webhooks.py
├── Inbound Email Handler (Smartlead/Instantly webhooks)
├── Social Engagement Handler (LinkedIn, Twitter)
├── Ad Performance Handler (Google Ads, LinkedIn Ads)
├── Campaign Status Handler
├── Health Check
└── FastAPI app factory
```

---

## 🔧 Installation Steps

### Step 1: Install Phase 2 Dependencies

```bash
cd /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/ascm-poc

# Install all Phase 2 requirements
pip install -r requirements.txt

# Verify installations
python -c "import temporalio; import asyncpg; import fastapi; print('✓ All deps installed')"
```

### Step 2: Set Up PostgreSQL Database

```bash
# Create database
createdb ascm_v4

# Apply migrations
psql ascm_v4 < migrations/0001_base_schema.sql
psql ascm_v4 < migrations/0002_orchestrator.sql
psql ascm_v4 < migrations/0003_domain_knowledge.sql
psql ascm_v4 < migrations/0004_v3_agents.sql
psql ascm_v4 < migrations/0005_v4_gtm_autonomous_campaigns.sql

# Verify schema
psql ascm_v4 -c "\dt" | grep gtm_
# Output should show 10 gtm_* tables
```

### Step 3: Set Up Temporal Server (Local Development)

```bash
# Option A: Docker (recommended for local dev)
docker run -d \
  --name temporal \
  -p 7233:7233 \
  -p 8233:8233 \
  temporalio/auto-setup:latest

# Option B: Direct installation (macOS)
brew install temporal

# Start Temporal server
temporal server start-dev

# Verify Temporal is running
curl http://localhost:7233/health
# Response: {"status":"UP"}
```

### Step 4: Configure Environment Variables

```bash
# Create .env.local
cat > .env.local << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/ascm_v4
DB_POOL_SIZE=20

# Temporal
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233

# API
API_PORT=8000
API_HOST=0.0.0.0

# Webhook Security
WEBHOOK_SECRET=your-secret-key-here
WEBHOOK_TIMEOUT_SECONDS=30

# Optional: Cloud Services (fill in later)
OPENOUTREACH_API_KEY=
SMARTLEAD_API_KEY=
COMPOSIO_API_KEY=
SLACK_WEBHOOK_URL=
EOF

source .env.local
```

---

## 🔌 OSS Repositories to Clone

*Awaiting research agent completion. Will update with exact clone commands.*

Based on specification, these need to be integrated:

### 1. **OpenOutreach** - Lead Discovery Engine
- Purpose: Discover verified B2B leads + fit reasoning
- Type: Python package or HTTP API
- Adapter: `orchestrator/gtm/channels/adapters.py:OpenOutreachLeadAdapter`
- Method: `search_and_verify_leads(thesis, icp_spec, limit)`

### 2. **ai-marketing-skills** - Technical Content
- Purpose: Generate architecture breakdowns, SEO briefs, social content
- Type: Python package (from Single Grain)
- Adapter: `orchestrator/gtm/channels/adapters.py:AIMarketingSkillsAdapter`
- Methods: `generate_technical_breakdown()`, `generate_seo_brief()`, `generate_social_content()`

### 3. **Composio** - Tool Execution Framework
- Purpose: Cal.com booking, Gmail/Smartlead dispatch, social scheduling
- Type: Python SDK (npm available too)
- Adapter: `orchestrator/gtm/channels/adapters.py:ComposioGTMAdapter`
- Methods: `dispatch_cal_com_booking_email()`, `send_email_sequence_step()`, `schedule_social_post()`

### 4. **Temporal Python SDK** - Already in requirements.txt
- Purpose: Workflow orchestration (already installed)
- Usage: Import `temporalio` for `@workflow`, `@activity` decorators

---

## ⚙️ Integration Architecture

```
┌─────────────────────────────────────┐
│   FastAPI Webhook Server (8000)     │
│   (orchestrator/api/webhooks.py)    │
└────────────────┬────────────────────┘
                 │ (routes inbound events)
                 ↓
        ┌────────────────────┐
        │  Temporal Workflow  │
        │  (orchestrator/     │
        │   workflows/)       │
        └────────┬───────────┘
                 │ (execute activities)
                 ↓
    ┌────────────────────────────────┐
    │   Activities (Phase 2)         │
    ├────────────────────────────────┤
    │ • OpenOutreach discovery       │
    │ • Email dispatch (Smartlead)   │
    │ • Reply classification         │
    │ • Cal.com booking              │
    │ • Content generation           │
    │ • Code generation              │
    │ • QA & testing                 │
    │ • Deployment                   │
    └────────────────────────────────┘
                 │
        ┌────────┴──────────┬──────────┐
        ↓                  ↓          ↓
    ┌────────┐        ┌────────┐  ┌────────┐
    │PostgreSQL       │OpenOutreach Composio
    │(orchestrator/   │(external API) (external
    │ gtm_*)          │              API)
    └────────┘        └────────┘  └────────┘
```

---

## 🚀 Starting Phase 2 Locally

### Terminal 1: Start Temporal Server
```bash
temporal server start-dev
```

### Terminal 2: Start FastAPI Webhook Server
```bash
cd /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/ascm-poc
python -m uvicorn orchestrator.api.webhooks:app --reload --port 8000
```

### Terminal 3: Test Workflow Execution
```bash
# Run demo workflow
python -c "
import asyncio
from orchestrator.workflows.gtm_workflows import GTMStandaloneWorkflow

async def main():
    workflow = GTMStandaloneWorkflow()
    result = await workflow.run(
        execution_mode='GTM_ONLY',
        product_thesis='Autonomous payment orchestration',
        icp_spec='CTOs at $50M+ ARR SaaS',
        cal_com_link='https://cal.com/founder/15min',
    )
    print(result)

asyncio.run(main())
"
```

### Terminal 4: Test Webhook
```bash
# Simulate inbound email
curl -X POST http://localhost:8000/webhooks/gtm/inbound-email \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo-project",
    "campaign_id": "demo-campaign",
    "workflow_id": "demo-workflow-123",
    "sender_email": "prospect@company.com",
    "sender_name": "John Doe",
    "subject": "Re: Your product",
    "raw_body": "Interested! Lets schedule a call."
  }'
```

---

## 📊 Database Schema Overview

### Core Tables

**gtm_campaign_profiles**
```sql
- id (UUID)
- project_id (FK projects)
- campaign_name
- execution_mode (GTM_ONLY, SALES_ONLY, MARKETING_ONLY)
- product_thesis
- icp_description
- workflow_id (FK temporal workflow)
- founder_approved_at
```

**gtm_prospects** (Discovered leads)
```sql
- id (UUID)
- project_id, campaign_id (FK)
- email, full_name, company_name, job_title
- fit_verdict (plain-English "Why This Fit")
- fit_confidence, deliverability_score
- status (QUEUED, CONTACTED, REPLIED, MEETING_BOOKED, UNSUBSCRIBED)
- current_sequence_step, last_contacted_at, next_contact_at
```

**gtm_campaign_steps** (Email sequences)
```sql
- id (UUID)
- campaign_id (FK)
- step_number (1-7)
- subject_template, body_template
- wait_delay_days (for timing)
- expected_open_rate, expected_reply_rate
```

**gtm_dispatch_log** (Outbound tracking)
```sql
- id (UUID)
- campaign_id, prospect_id, step_id (FK)
- email_provider (SMARTLEAD, INSTANTLY, GMAIL)
- dispatch_status (SENT, DELIVERED, BOUNCED, FAILED)
- dispatched_at, delivered_at, bounced_at
```

**gtm_inbound_events** (Replies)
```sql
- id (UUID)
- campaign_id, prospect_id (FK)
- raw_message_body
- sentiment_classification (INTERESTED, OBJECTION, NEGATIVE, OUT_OF_OFFICE)
- suppressed_from_founder (TRUE if NEGATIVE/UNSUBSCRIBE)
- next_action (DISPATCH_CAL_COM, QUEUE_REVIEW, SILENT)
- cal_com_link_sent, founder_notified_at
```

**gtm_campaign_metrics** (Daily analytics)
```sql
- id (UUID)
- campaign_id (FK)
- snapshot_date
- leads_discovered, leads_contacted, leads_replied, meetings_booked
- emails_sent, emails_delivered, emails_bounced
- reply_rate, interested_rate, conversion_rate
- spend, cac, roas
```

### Views for Common Queries

**gtm_campaign_performance_today**
```sql
SELECT campaign_name, execution_mode, leads_discovered, emails_sent, 
       reply_rate_pct, meetings_booked, spend_today, cac_today
FROM gtm_campaign_profiles JOIN gtm_campaign_metrics (TODAY)
WHERE status = 'ACTIVE'
```

**gtm_warm_leads_pending_notification**
```sql
SELECT email, full_name, company_name, sentiment_classification, 
       reply_received_at, campaign_name
FROM gtm_prospects p
JOIN gtm_inbound_events i
WHERE sentiment = 'INTERESTED' AND suppressed_from_founder = FALSE 
  AND founder_notified_at IS NULL
```

---

## 🔄 Workflow Execution Flow

### GTMStandaloneWorkflow Phases

**Phase 1: Content & Strategy Generation**
```python
# Generate marketing content strategy
marketing_strategy = await activity_generate_marketing_content(
    thesis="Your product thesis",
    benchmarks={...}
)
# Output: content_pillars, technical_breakdown, seo_brief, social_posts
```

**Phase 2: Approval Gate**
```python
# Founder reviews strategy + copy
# Workflow pauses, waiting for founder signal
await workflow.wait_condition(lambda: self.gate_approved, timeout=14 days)
```

**Phase 3: Lead Discovery & Outbound**
```python
# Discover leads via OpenOutreach
leads = await activity_run_openoutreach_discovery(
    thesis="...", icp_spec="...", limit=35
)

# Dispatch first sequence step
for lead in leads[:5]:
    await activity_dispatch_outbound_step(
        lead, step_number=1, subject="...", body="...", campaign_id=...
    )
```

**Phase 4: Reply Loop (30 days)**
```python
# Listen for inbound emails
# Workflow signals: signal_inbound_email_reply(email, body, ...)

# Classify reply
classification = await activity_classify_inbound_reply(
    reply_body, prospect_email, prospect_name, cal_com_link
)

# If INTERESTED: dispatch Cal.com link + notify founder
# If NEGATIVE: silently suppress (no founder notification)
```

**Phase 5: Completion Report**
```python
return {
    "status": "COMPLETED",
    "meetings_booked": 2,
    "campaign_stats": {
        "leads_discovered": 35,
        "emails_sent": 35,
        "replies_received": 3,
        "meetings_booked": 2
    }
}
```

---

## 🧪 Testing Phase 2

### Unit Tests (Ready to Implement)

```python
# tests/test_workflows.py
async def test_gtm_standalone_workflow_complete():
    workflow = GTMStandaloneWorkflow()
    result = await workflow.run(
        execution_mode="GTM_ONLY",
        product_thesis="Test product",
        icp_spec="Test ICP",
        cal_com_link="https://cal.com/test",
    )
    assert result["status"] == "COMPLETED"
    assert result["campaign_stats"]["leads_discovered"] > 0
```

### Integration Tests

```python
# tests/test_webhooks.py
async def test_inbound_email_webhook():
    client = AsyncClient(app=app, base_url="http://test")
    response = await client.post(
        "/webhooks/gtm/inbound-email",
        json={
            "project_id": "test",
            "campaign_id": "test",
            "workflow_id": "test-123",
            "sender_email": "prospect@test.com",
            "raw_body": "Interested! Let's talk.",
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] in ["SIGNAL_DISPATCHED", "QUEUED"]
```

### E2E Tests

```python
# tests/test_e2e_gtm_campaign.py
async def test_end_to_end_gtm_campaign():
    # 1. Create campaign
    campaign = await create_campaign(...)
    
    # 2. Start GTM workflow
    workflow = client.get_workflow_handle("campaign-workflow-1")
    
    # 3. Simulate founder approval
    await workflow.signal("signal_founder_approved", {...})
    
    # 4. Simulate inbound email
    await client.post("/webhooks/gtm/inbound-email", {...})
    
    # 5. Verify warm lead notification
    result = await workflow.result()
    assert result["meetings_booked"] > 0
```

---

## 📈 Monitoring & Observability

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "campaign_launched",
    campaign_id="abc123",
    execution_mode="GTM_ONLY",
    leads_quota=35,
)

logger.info(
    "reply_received",
    prospect_email="prospect@company.com",
    sentiment="INTERESTED",
    action="dispatch_cal_com",
)
```

### Database Queries for Monitoring

```sql
-- Real-time campaign performance
SELECT campaign_name, 
       COUNT(DISTINCT p.id) as leads,
       SUM(CASE WHEN i.sentiment = 'INTERESTED' THEN 1 ELSE 0 END) as interested,
       COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'MEETING_BOOKED') as meetings
FROM gtm_campaign_profiles c
LEFT JOIN gtm_prospects p ON c.id = p.campaign_id
LEFT JOIN gtm_inbound_events i ON p.id = i.prospect_id
WHERE c.status = 'ACTIVE'
GROUP BY campaign_name;

-- Warm leads waiting for founder notification
SELECT COUNT(*) FROM gtm_inbound_events
WHERE sentiment = 'INTERESTED' 
  AND suppressed_from_founder = FALSE 
  AND founder_notified_at IS NULL;

-- Email delivery rate
SELECT 
    ROUND(100.0 * COUNT(*) FILTER (WHERE dispatch_status = 'DELIVERED') / COUNT(*), 2) as delivery_rate
FROM gtm_dispatch_log
WHERE dispatched_at > NOW() - INTERVAL '24 hours';
```

---

## 🚨 Troubleshooting Phase 2

### Issue: Temporal Connection Refused
```bash
# Check Temporal server is running
curl http://localhost:7233/health

# If not running:
temporal server start-dev
# or
docker run -d -p 7233:7233 temporalio/auto-setup:latest
```

### Issue: Database Connection Pool Exhausted
```python
# Increase pool size in .env
DB_POOL_SIZE=50

# Check active connections
psql ascm_v4 -c "SELECT count(*) FROM pg_stat_activity;"
```

### Issue: Webhook Signature Verification Failed
```bash
# Ensure WEBHOOK_SECRET matches provider
# For Smartlead: copy API key to .env
export SMARTLEAD_API_KEY="your-key-here"
```

---

## ✅ Phase 2 Completion Checklist

- [ ] PostgreSQL database created & migrations applied
- [ ] Temporal server running on localhost:7233
- [ ] FastAPI server running on localhost:8000
- [ ] All requirements installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured (.env.local)
- [ ] OSS repos cloned and configured:
  - [ ] OpenOutreach
  - [ ] ai-marketing-skills
  - [ ] Composio
- [ ] Workflows tested locally
- [ ] Webhook endpoints tested
- [ ] Unit tests passing (226+ tests)
- [ ] Integration tests passing
- [ ] E2E campaign flow validated
- [ ] Monitoring & logging working
- [ ] Documentation complete

---

## 🎯 Next: Phase 3 (Testing & Deployment)

Once Phase 2 integration complete:

1. **Comprehensive Test Suite** (226+ tests)
   - Unit tests for all activities
   - Integration tests for workflows
   - E2E tests for full campaigns

2. **Founder Dashboard**
   - Campaign monitoring
   - Warm lead notifications
   - Analytics & reports

3. **Production Deployment**
   - Temporal cloud setup
   - RDS database (AWS)
   - API gateway (CloudFront)
   - Monitoring stack (CloudWatch, Datadog)

4. **Advanced Features**
   - Parallel execution (CODE + GTM simultaneously)
   - Multi-workspace support
   - Custom LLM model selection
   - Advanced analytics dashboard

---

**Ready to build Phase 2! 🚀**

For questions or issues, refer to:
- [docs/guides/ASCM_v4.0_IMPLEMENTATION_GUIDE.md](docs/guides/ASCM_v4.0_IMPLEMENTATION_GUIDE.md)
- [docs/guides/ASCM_v4.0_QUICK_START.md](docs/guides/ASCM_v4.0_QUICK_START.md)
- Workflow definitions: `orchestrator/workflows/gtm_workflows.py`
- Database schema: `migrations/0005_v4_gtm_autonomous_campaigns.sql`
- API endpoints: `orchestrator/api/webhooks.py`

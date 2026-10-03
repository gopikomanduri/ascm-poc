-- ASCM v4.0: GTM Autonomous Campaign Schema
-- Supports SalesAgent, MarketingAgent, AdAgent, SEOAgent
-- Workflow: Lead discovery → sequencing → reply classification → meeting booking

-- ============================================================================
-- 1. PROJECT EXECUTION PROFILE
-- ============================================================================

ALTER TABLE projects
ADD COLUMN IF NOT EXISTS execution_mode VARCHAR(50) DEFAULT 'FULL_STACK'
    CHECK (execution_mode IN ('FULL_STACK', 'GTM_ONLY', 'SALES_ONLY', 'MARKETING_ONLY', 'CODE_ONLY')),
ADD COLUMN IF NOT EXISTS cal_com_link VARCHAR(512),
ADD COLUMN IF NOT EXISTS daily_lead_quota INT DEFAULT 35,
ADD COLUMN IF NOT EXISTS approval_gate_enabled BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS campaign_duration_days INT DEFAULT 30;

-- ============================================================================
-- 2. GTM CAMPAIGN PROFILES
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_campaign_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Campaign metadata
    campaign_name VARCHAR(255) NOT NULL,
    execution_mode VARCHAR(50) NOT NULL CHECK (execution_mode IN ('GTM_ONLY', 'SALES_ONLY', 'MARKETING_ONLY')),
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'AWAITING_APPROVAL', 'APPROVED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'FAILED')),

    -- Campaign parameters
    product_thesis TEXT NOT NULL,
    icp_description TEXT,
    target_audience VARCHAR(500),
    daily_lead_quota INT DEFAULT 35,
    campaign_duration_days INT DEFAULT 30,
    approval_gate_enabled BOOLEAN DEFAULT TRUE,

    -- Approval workflow
    founder_approved_at TIMESTAMP WITH TIME ZONE,
    founder_approval_notes TEXT,

    -- Temporal workflow
    workflow_id VARCHAR(255) UNIQUE,
    workflow_started_at TIMESTAMP WITH TIME ZONE,
    workflow_completed_at TIMESTAMP WITH TIME ZONE,

    -- Tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_project_campaign_name UNIQUE (project_id, campaign_name)
);

CREATE INDEX idx_gtm_campaign_project ON gtm_campaign_profiles(project_id);
CREATE INDEX idx_gtm_campaign_status ON gtm_campaign_profiles(status);
CREATE INDEX idx_gtm_campaign_workflow ON gtm_campaign_profiles(workflow_id);

-- ============================================================================
-- 3. DISCOVERED LEADS (OpenOutreach Output)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_prospects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES gtm_campaign_profiles(id) ON DELETE CASCADE,

    -- Contact information
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    company_name VARCHAR(150),
    job_title VARCHAR(150),
    linkedin_url VARCHAR(512),

    -- Fit assessment
    fit_verdict TEXT NOT NULL,                -- Plain-English "Why This Fit"
    fit_confidence NUMERIC(5, 2) DEFAULT 0.0, -- 0.0-1.0 scale
    deliverability_score NUMERIC(5, 2),       -- Email verification confidence

    -- Campaign tracking
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED', 'CONTACTED', 'REPLIED', 'MEETING_BOOKED', 'UNSUBSCRIBED', 'BOUNCED')),

    -- Sequence tracking
    current_sequence_step INT DEFAULT 0,
    last_contacted_at TIMESTAMP WITH TIME ZONE,
    next_contact_at TIMESTAMP WITH TIME ZONE,

    -- Meeting booking
    meeting_booked_at TIMESTAMP WITH TIME ZONE,
    meeting_link VARCHAR(512),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_project_prospect_email UNIQUE (project_id, email)
);

CREATE INDEX idx_gtm_prospect_project ON gtm_prospects(project_id);
CREATE INDEX idx_gtm_prospect_status ON gtm_prospects(status);
CREATE INDEX idx_gtm_prospect_campaign ON gtm_prospects(campaign_id);
CREATE INDEX idx_gtm_prospect_next_contact ON gtm_prospects(next_contact_at)
    WHERE status IN ('QUEUED', 'CONTACTED');

-- ============================================================================
-- 4. EMAIL SEQUENCE TEMPLATES
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_campaign_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES gtm_campaign_profiles(id) ON DELETE CASCADE,

    -- Sequence metadata
    step_number INT NOT NULL,
    step_type VARCHAR(50) NOT NULL CHECK (step_type IN ('EMAIL', 'LINKEDIN', 'PHONE', 'CUSTOM')),

    -- Email content
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,

    -- Timing
    wait_delay_days INT DEFAULT 3,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 2,

    -- Performance
    expected_open_rate NUMERIC(5, 2),
    expected_reply_rate NUMERIC(5, 2),

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_campaign_step UNIQUE (campaign_id, step_number)
);

CREATE INDEX idx_gtm_step_campaign ON gtm_campaign_steps(campaign_id);

-- ============================================================================
-- 5. OUTBOUND EMAIL DISPATCH LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_dispatch_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES gtm_campaign_profiles(id) ON DELETE CASCADE,
    prospect_id UUID NOT NULL REFERENCES gtm_prospects(id) ON DELETE CASCADE,
    step_id UUID REFERENCES gtm_campaign_steps(id) ON DELETE SET NULL,

    -- Dispatch details
    step_number INT NOT NULL,
    subject_sent VARCHAR(500),
    body_sent TEXT,

    -- SMTP/Provider
    email_provider VARCHAR(50) CHECK (email_provider IN ('SMARTLEAD', 'INSTANTLY', 'GMAIL', 'COMPOSIO')),
    provider_message_id VARCHAR(255),

    -- Delivery tracking
    dispatch_status VARCHAR(50) NOT NULL DEFAULT 'SENT'
        CHECK (dispatch_status IN ('PENDING', 'SENT', 'DELIVERED', 'BOUNCED', 'FAILED')),
    delivery_error TEXT,

    dispatched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    bounced_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_dispatch_campaign ON gtm_dispatch_log(campaign_id);
CREATE INDEX idx_dispatch_prospect ON gtm_dispatch_log(prospect_id);
CREATE INDEX idx_dispatch_status ON gtm_dispatch_log(dispatch_status);

-- ============================================================================
-- 6. INBOUND REPLY PROCESSING
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_inbound_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES gtm_campaign_profiles(id) ON DELETE CASCADE,
    prospect_id UUID NOT NULL REFERENCES gtm_prospects(id) ON DELETE CASCADE,

    -- Email metadata
    raw_message_id VARCHAR(255),
    raw_from_email VARCHAR(255),
    raw_from_name VARCHAR(150),
    raw_subject VARCHAR(500),
    raw_message_body TEXT NOT NULL,

    -- Sentiment analysis
    sentiment_classification VARCHAR(50) NOT NULL
        CHECK (sentiment_classification IN ('INTERESTED', 'OBJECTION', 'NOT_NOW', 'NEGATIVE', 'OUT_OF_OFFICE', 'UNKNOWN')),
    sentiment_confidence NUMERIC(5, 2) DEFAULT 0.0,

    -- Routing & actions
    suppressed_from_founder BOOLEAN DEFAULT FALSE,
        -- If TRUE: reply is never shown to founder (NEGATIVE/UNSUBSCRIBE handling)

    next_action VARCHAR(100) CHECK (next_action IN ('DISPATCH_CAL_COM', 'QUEUE_REVIEW', 'SILENT', 'HUMAN_REVIEW')),

    -- Cal.com automation
    cal_com_link_sent BOOLEAN DEFAULT FALSE,
    cal_com_sent_at TIMESTAMP WITH TIME ZONE,

    -- Founder notification
    founder_notified_at TIMESTAMP WITH TIME ZONE,
    founder_notification_sent BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_inbound_campaign ON gtm_inbound_events(campaign_id);
CREATE INDEX idx_inbound_prospect ON gtm_inbound_events(prospect_id);
CREATE INDEX idx_inbound_sentiment ON gtm_inbound_events(sentiment_classification);
CREATE INDEX idx_inbound_suppressed ON gtm_inbound_events(suppressed_from_founder);

-- ============================================================================
-- 7. MARKETING CONTENT QUEUE
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_content_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Content metadata
    content_type VARCHAR(50) NOT NULL CHECK (content_type IN ('BLOG_POST', 'SOCIAL_POST', 'SEO_BRIEF', 'AD_COPY', 'EMAIL_TEMPLATE')),
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('BLOG', 'TWITTER', 'LINKEDIN', 'DEVTO', 'PRODUCTHUNT', 'GOOGLE_ADS', 'LINKEDIN_ADS')),

    -- Content
    title VARCHAR(255),
    content_payload TEXT NOT NULL,
    media_urls JSONB DEFAULT '[]',
    keywords TEXT[],

    -- Approval workflow
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED', 'ARCHIVED')),
    reviewer_notes TEXT,
    reviewed_by UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Publishing
    scheduled_for TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    published_post_id VARCHAR(255),  -- Platform-specific post ID
    published_url VARCHAR(512),

    -- Performance
    views INT DEFAULT 0,
    clicks INT DEFAULT 0,
    impressions INT DEFAULT 0,
    engagement_rate NUMERIC(5, 2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_project ON gtm_content_queue(project_id);
CREATE INDEX idx_content_status ON gtm_content_queue(status);
CREATE INDEX idx_content_platform ON gtm_content_queue(platform);
CREATE INDEX idx_content_scheduled ON gtm_content_queue(scheduled_for) WHERE status IN ('APPROVED', 'SCHEDULED');

-- ============================================================================
-- 8. PAID ADVERTISING CAMPAIGNS
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_paid_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Campaign details
    campaign_name VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('GOOGLE_ADS', 'LINKEDIN_ADS', 'FACEBOOK_ADS', 'PROGRAMMATIC')),
    campaign_type VARCHAR(50) NOT NULL CHECK (campaign_type IN ('SEARCH', 'DISPLAY', 'LEAD_GEN', 'ABM', 'CONVERSION')),

    -- Budget
    daily_budget NUMERIC(10, 2),
    total_budget NUMERIC(10, 2),

    -- Performance
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'ACTIVE', 'PAUSED', 'COMPLETED')),
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    conversions INT DEFAULT 0,
    spend NUMERIC(10, 2) DEFAULT 0,

    -- Metrics
    ctr NUMERIC(5, 2),  -- Click-through rate
    cpc NUMERIC(10, 2), -- Cost per click
    cpa NUMERIC(10, 2), -- Cost per acquisition
    roas NUMERIC(10, 2), -- Return on ad spend

    -- Targeting
    target_audience_desc TEXT,
    keywords TEXT[],

    -- Dates
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_paid_campaign_project ON gtm_paid_campaigns(project_id);
CREATE INDEX idx_paid_campaign_platform ON gtm_paid_campaigns(platform);
CREATE INDEX idx_paid_campaign_status ON gtm_paid_campaigns(status);

-- ============================================================================
-- 9. SEO & ORGANIC TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_seo_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Keyword tracking
    target_keyword VARCHAR(255) NOT NULL,
    keyword_volume INT,
    keyword_difficulty INT,
    search_intent VARCHAR(50) CHECK (search_intent IN ('INFORMATIONAL', 'COMMERCIAL', 'TRANSACTIONAL', 'NAVIGATIONAL')),

    -- Rankings
    current_rank INT,
    previous_rank INT,
    url_ranking VARCHAR(512),

    -- Performance
    organic_traffic INT DEFAULT 0,
    organic_clicks INT DEFAULT 0,
    impressions INT DEFAULT 0,
    ctr NUMERIC(5, 2),

    -- Content
    content_url VARCHAR(512),
    content_title VARCHAR(255),

    -- Tracking dates
    first_tracked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_tracked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_project_keyword UNIQUE (project_id, target_keyword)
);

CREATE INDEX idx_seo_project ON gtm_seo_tracking(project_id);
CREATE INDEX idx_seo_keyword ON gtm_seo_tracking(target_keyword);
CREATE INDEX idx_seo_rank ON gtm_seo_tracking(current_rank);

-- ============================================================================
-- 10. CAMPAIGN ANALYTICS & METRICS
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_campaign_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES gtm_campaign_profiles(id) ON DELETE CASCADE,

    -- Daily snapshots
    snapshot_date DATE NOT NULL,

    -- Lead metrics
    leads_discovered INT DEFAULT 0,
    leads_contacted INT DEFAULT 0,
    leads_replied INT DEFAULT 0,
    leads_interested INT DEFAULT 0,
    meetings_booked INT DEFAULT 0,

    -- Email metrics
    emails_sent INT DEFAULT 0,
    emails_delivered INT DEFAULT 0,
    emails_bounced INT DEFAULT 0,
    emails_opened INT DEFAULT 0,
    emails_clicked INT DEFAULT 0,

    -- Response metrics
    reply_rate NUMERIC(5, 2),  -- replied / contacted
    interested_rate NUMERIC(5, 2), -- interested / replied
    conversion_rate NUMERIC(5, 2), -- meetings_booked / emails_sent

    -- Cost metrics
    spend NUMERIC(10, 2) DEFAULT 0,
    cac NUMERIC(10, 2), -- Cost per acquisition
    roas NUMERIC(10, 2), -- Return on ad spend

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_campaign_daily_metrics UNIQUE (campaign_id, snapshot_date)
);

CREATE INDEX idx_metrics_campaign ON gtm_campaign_metrics(campaign_id);
CREATE INDEX idx_metrics_date ON gtm_campaign_metrics(snapshot_date);

-- ============================================================================
-- 11. FOUNDER NOTIFICATIONS LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS gtm_founder_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Notification details
    notification_type VARCHAR(50) NOT NULL
        CHECK (notification_type IN ('WARM_LEAD', 'MEETING_BOOKED', 'HIGH_ENGAGEMENT', 'CAMPAIGN_MILESTONE', 'ERROR')),

    title VARCHAR(255),
    message TEXT NOT NULL,

    -- Context
    prospect_id UUID REFERENCES gtm_prospects(id) ON DELETE SET NULL,
    campaign_id UUID REFERENCES gtm_campaign_profiles(id) ON DELETE SET NULL,

    -- Delivery
    sent_via VARCHAR(50) CHECK (sent_via IN ('EMAIL', 'SLACK', 'SMS', 'IN_APP')),
    delivery_status VARCHAR(50) DEFAULT 'SENT' CHECK (delivery_status IN ('PENDING', 'SENT', 'FAILED')),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_notification CHECK (prospect_id IS NOT NULL OR campaign_id IS NOT NULL)
);

CREATE INDEX idx_notification_project ON gtm_founder_notifications(project_id);
CREATE INDEX idx_notification_type ON gtm_founder_notifications(notification_type);
CREATE INDEX idx_notification_delivered ON gtm_founder_notifications(sent_via, delivery_status);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Campaign performance snapshot
CREATE OR REPLACE VIEW gtm_campaign_performance_today AS
SELECT
    c.id,
    c.campaign_name,
    c.execution_mode,
    COALESCE(m.leads_discovered, 0) as leads_discovered,
    COALESCE(m.emails_sent, 0) as emails_sent,
    COALESCE(m.reply_rate, 0) as reply_rate_pct,
    COALESCE(m.meetings_booked, 0) as meetings_booked,
    COALESCE(m.spend, 0) as spend_today,
    COALESCE(m.cac, 0) as cac_today
FROM gtm_campaign_profiles c
LEFT JOIN gtm_campaign_metrics m ON c.id = m.campaign_id AND m.snapshot_date = CURRENT_DATE
WHERE c.status = 'ACTIVE';

-- Warm leads ready for founder notification
CREATE OR REPLACE VIEW gtm_warm_leads_pending_notification AS
SELECT
    p.id,
    p.email,
    p.full_name,
    p.company_name,
    p.job_title,
    i.sentiment_classification,
    i.created_at as reply_received_at,
    c.campaign_name
FROM gtm_prospects p
JOIN gtm_inbound_events i ON p.id = i.prospect_id
JOIN gtm_campaign_profiles c ON i.campaign_id = c.id
WHERE i.sentiment_classification = 'INTERESTED'
  AND i.suppressed_from_founder = FALSE
  AND i.founder_notified_at IS NULL
ORDER BY i.created_at DESC;

-- Campaign completion metrics
CREATE OR REPLACE VIEW gtm_campaign_completion_report AS
SELECT
    c.id,
    c.campaign_name,
    c.execution_mode,
    c.status,
    COUNT(DISTINCT p.id) as total_prospects,
    COUNT(DISTINCT CASE WHEN p.status = 'CONTACTED' THEN p.id END) as contacted_count,
    COUNT(DISTINCT CASE WHEN p.status = 'REPLIED' THEN p.id END) as replied_count,
    COUNT(DISTINCT CASE WHEN p.status = 'MEETING_BOOKED' THEN p.id END) as meetings_booked,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN p.status IN ('REPLIED', 'MEETING_BOOKED') THEN p.id END) /
          NULLIF(COUNT(DISTINCT CASE WHEN p.status = 'CONTACTED' THEN p.id END), 0), 2) as reply_rate_pct,
    c.workflow_started_at,
    c.workflow_completed_at,
    EXTRACT(DAY FROM (c.workflow_completed_at - c.workflow_started_at)) as duration_days
FROM gtm_campaign_profiles c
LEFT JOIN gtm_prospects p ON c.id = p.campaign_id
GROUP BY c.id, c.campaign_name, c.execution_mode, c.status, c.workflow_started_at, c.workflow_completed_at;

-- ============================================================================
-- TIMESTAMPS & METADATA
-- ============================================================================

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gtm_campaign_profiles_updated
BEFORE UPDATE ON gtm_campaign_profiles
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER gtm_content_queue_updated
BEFORE UPDATE ON gtm_content_queue
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER gtm_prospects_updated
BEFORE UPDATE ON gtm_prospects
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

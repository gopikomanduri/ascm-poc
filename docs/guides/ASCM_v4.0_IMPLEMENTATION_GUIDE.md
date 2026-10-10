# ASCM v4.0: Dynamic Intent-Driven Orchestration & Autonomous GTM Engine

## Overview

ASCM v4.0 is a major architectural upgrade that introduces **dynamic intent-driven routing** and **independent GTM agents**. Instead of always running a full-stack pipeline, the system now intelligently detects what's missing (product vs. commercial capability) and executes only the necessary agents.

### Key Innovations

1. **ThinkingAgentRouter**: Analyzes founder input, detects team gaps, and routes to optimal execution profile
2. **Independent GTM Agents**: SalesAgent, MarketingAgent, AdAgent, SEOAgent operate standalone without requiring code scaffolding
3. **Five Execution Modes**:
   - `FULL_STACK` - Greenfield: discovery → architecture → code → QA → deploy → GTM
   - `CODE_ONLY` - Team has commercial: focus on product engineering
   - `GTM_ONLY` - Existing product, no commercial teams: autonomous sales + marketing + ads
   - `SALES_ONLY` - Team has marketing: autonomous outbound via OpenOutreach
   - `MARKETING_ONLY` - Team has sales: technical content + SEO + ads

4. **Introvert-First GTM**: Founder notifications only on warm meetings; negative replies silently suppressed
5. **Open-Source Integrations**: OpenOutreach (lead discovery), ai-marketing-skills (content), Composio (tool execution)

---

## Architecture

### Directory Structure

```
orchestrator/
├── models/
│   ├── __init__.py
│   └── intent.py                 # ExecutionMode, ProjectIntentRequest, SystemExecutionProfile
├── router/
│   ├── __init__.py
│   └── thinking_router.py        # ThinkingAgentRouter: gap detection & profile resolution
├── gtm/
│   ├── __init__.py
│   ├── sales_agent.py            # SalesAgent: OpenOutreach + Smartlead + Cal.com
│   ├── marketing_agent.py        # MarketingAgent: Technical content + SEO + social
│   ├── ad_agent.py               # AdAgent: Google Ads, LinkedIn Ads, Programmatic
│   ├── seo_agent.py              # SEOAgent: Organic growth & backlink strategy
│   └── adapters.py               # OpenOutreach, ai-marketing-skills, Composio integrations
├── workflows/
│   ├── __init__.py
│   └── gtm_workflows.py          # Temporal workflow definitions
├── agents/
│   ├── all_agents.py             # (updated to import GTM agents)
│   ├── base.py                   # (existing)
│   └── ...                       # (existing coding agents)
├── cli.py                        # CLI interface
└── orchestrator_agent.py         # (existing orchestrator)
```

### Execution Flow

```
1. User Input Request
        ↓
2. ThinkingAgentRouter.resolve_profile()
        ↓
        ├─→ Manual override? → Use requested_mode
        │
        └─→ AUTO mode → _auto_detect_and_resolve()
            ├─→ Has code? Has sales+marketing?
            │   ├─→ No code, has teams → FULL_STACK
            │   ├─→ Has code, no teams → GTM_ONLY
            │   ├─→ Has code, has marketing, no sales → SALES_ONLY
            │   ├─→ Has code, has sales, no marketing → MARKETING_ONLY
            │   └─→ Has code, both teams → CODE_ONLY
            └─→ Return SystemExecutionProfile
3. Profile Validation
        ↓
4. Dispatch to Temporal Workflow (or execute agents directly)
        ↓
5. Agent Execution (only active agents from profile)
        ↓
6. Results & Monitoring
```

---

## Usage Guide

### 1. Full-Stack Initialization (Greenfield)

For a brand-new startup with no product or team, build everything:

```bash
python orchestrator/cli.py init my-startup spec.md --budget 350
```

**What Happens:**
- Router detects: no code, no teams → `FULL_STACK` mode
- Executes: ProductAgent → ArchitectAgent → Coders → QA → Compliance → DevOps → SalesAgent → MarketingAgent → AdAgent → SEOAgent
- Timeline: ~2-3 weeks
- Cost: $350 (full budget)

---

### 2. GTM-Only (Brownfield)

You have a product, no commercial team:

```bash
python orchestrator/cli.py gtm \
  --repo https://github.com/my-startup/product \
  --thesis "Autonomous payment orchestration for SaaS" \
  --cal-link https://cal.com/founder/15min \
  --budget 150
```

**What Happens:**
- Router detects: has code, no teams → `GTM_ONLY` mode
- Executes: SalesAgent (OpenOutreach + Smartlead) + MarketingAgent (content) + AdAgent + SEOAgent
- Approval gate: Founder reviews copy before outbound starts
- Reply handling: Positive → Cal.com auto-dispatch + Slack alert; Negative → silent
- Timeline: ~2 weeks to first meetings booked
- Cost: $150 (GTM-focused budget)

---

### 3. Sales-Only Outbound (Marketing Team Exists)

```bash
python orchestrator/cli.py sales \
  --thesis "Autonomous payment orchestration for SaaS" \
  --cal-link https://cal.com/founder/15min \
  --quota 35
```

**What Happens:**
- Informs router: `has_marketing_team=True`
- Router infers: `SALES_ONLY` mode
- Executes: SalesAgent only (OpenOutreach lead discovery + Smartlead sequences + Cal.com)
- Bypasses: MarketingAgent, AdAgent, SEOAgent (your team handles content)
- Approval gate: Founder signs off on ICP & sequence copy
- Timeline: ~1 week to 35 leads/day
- Cost: $50 (sales ops only)

---

### 4. Marketing-Only Campaigns (Sales Team Exists)

```bash
python orchestrator/cli.py marketing \
  --thesis "Autonomous payment orchestration for SaaS" \
  --competitors "Stripe" "Adyen" "Payment Depot"
```

**What Happens:**
- Informs router: `has_sales_team=True`
- Router infers: `MARKETING_ONLY` mode
- Executes: MarketingAgent (tech breakdowns, SEO briefs) + AdAgent (Google/LinkedIn) + SEOAgent (backlinks)
- Bypasses: SalesAgent (your team handles outbound)
- Generates: Content calendar, social posts, SEO strategy, ad copy
- Timeline: ~2 weeks to content queue + campaigns live
- Cost: $75 (marketing ops only)

---

### 5. Code-Only Development (Commercial Team Exists)

```bash
python orchestrator/cli.py code \
  --thesis "Autonomous payment orchestration for SaaS"
```

**What Happens:**
- Informs router: `has_marketing_team=True, has_sales_team=True`
- Router infers: `CODE_ONLY` mode
- Executes: ProductAgent → ArchitectAgent → Coders → QA → Compliance → DevOps
- Bypasses: All GTM agents
- Your team: Handles marketing + sales in parallel
- Timeline: ~1-2 weeks
- Cost: $250 (full product engineering stack)

---

## Model Reference

### `ProjectIntentRequest`

```python
ProjectIntentRequest(
    project_name="my-startup",
    product_thesis="Autonomous payment orchestration...",
    existing_repos=["https://github.com/..."],
    team_composition=TeamComposition(
        has_marketing_team=False,
        has_sales_team=False,
        has_engineering_team=True,
    ),
    requested_mode="AUTO",  # or FULL_STACK, GTM_ONLY, SALES_ONLY, etc.
    target_icp_description="CTOs at Series B+ SaaS companies",
    cal_com_booking_link="https://cal.com/founder/15min",
    daily_lead_quota=35,
    budget_usd=150.0,
    approval_gate_enabled=True,
)
```

### `SystemExecutionProfile`

```python
profile = ThinkingAgentRouter.resolve_profile(req)

# Profile attributes:
profile.mode                    # ExecutionMode (FULL_STACK, GTM_ONLY, etc.)
profile.active_agent_ids       # List of agents to execute
profile.bypassed_agent_ids     # List of agents to skip
profile.required_integrations  # External services (openoutreach, composio, etc.)
profile.execution_dag          # {agent_id: [dependencies]}
profile.estimated_usd_cost     # $ estimate
profile.reasoning              # Plain-English explanation of routing decision
```

---

## GTM Agents: Detailed Reference

### SalesAgent: Autonomous Outbound

**Capabilities:**
- Discovers verified B2B leads via OpenOutreach
- Generates plain-English 'Why This Fit' verdicts per lead
- Designs multi-touch email sequences (5-7 steps)
- Classifies inbound replies (INTERESTED, OBJECTION, NEGATIVE, OUT_OF_OFFICE)
- Dispatches Cal.com booking links on positive intent
- Silently suppresses negative/unsubscribe replies (founder protection)

**Integrations:**
- OpenOutreach (lead discovery + fit reasoning)
- Smartlead / Instantly (secondary domain SMTP for sequences)
- Composio → Gmail / Smartlead (email dispatch)
- Composio → Cal.com (meeting booking link delivery)

**Output:**
```json
{
  "leads_discovered": 35,
  "verified_emails": 33,
  "first_sequence_dispatched": true,
  "reply_classification_rules": ["INTERESTED", "OBJECTION", "NEGATIVE", ...],
  "cal_com_booking_logic": "...",
  "founder_notification_criteria": "ONLY interested + meeting booked",
  "unsubscribe_handling": "silent suppression",
  "estimated_meeting_bookings_week1": 2-3
}
```

---

### MarketingAgent: Technical Content & SEO

**Capabilities:**
- Generates architecture breakdown blog posts
- Creates SEO content briefs with keyword research
- Designs LinkedIn/Twitter/Dev.to thought leadership content
- Analyzes competitor positioning + creates battlecards
- Plans 30-day editorial calendar with CTAs

**Integrations:**
- ai-marketing-skills (technical content framework)
- SEO tools (keyword volume, difficulty, intent)

**Output:**
```json
{
  "content_pillars": ["Performance Optimization", "Distributed Systems Patterns", ...],
  "technical_breakdown": "# Architecture Breakdown: Scaling to 10K TPS...",
  "seo_brief": {
    "keywords": ["payment orchestration", "golang payment gateway", ...],
    "title": "Why Teams Move from Stripe to Autonomous Orchestration",
    "outline": "1. Legacy Payment Processing Costs\n2. Our Architecture..."
  },
  "social_posts": [
    {"platform": "linkedin", "content": "...", "cta": "..."},
    {"platform": "twitter", "content": "...", "cta": "..."}
  ],
  "monthly_calendar": [...],
  "estimated_organic_reach_monthly": 5000,
  "competitor_battlecards": [...]
}
```

---

### AdAgent: Paid Advertising Campaigns

**Capabilities:**
- Designs Google Ads search campaigns with keyword grouping
- Creates LinkedIn Ads lead gen + conversion campaigns
- Plans Account-Based Marketing (ABM) for enterprise targets
- Generates ad copy A/B testing variants
- Specifies landing page optimization briefs
- Estimates ROAS + SQL volume per channel

**Integrations:**
- Google Ads API (search, display, YouTube)
- LinkedIn Campaign Manager
- Composio → tool execution

**Output:**
```json
{
  "campaign_structure": {...},
  "target_channels": ["Google Ads", "LinkedIn Ads", "Programmatic"],
  "icp_audience_segments": ["CTOs at $50M+ ARR SaaS", ...],
  "ad_copy_variants": [
    {"channel": "google", "headline": "...", "description": "..."},
    {"channel": "linkedin", "headline": "...", "body": "..."}
  ],
  "landing_page_brief": "Conversion optimized for 'Compare Payment Orchestration'",
  "budget_allocation": {"google": 1500, "linkedin": 2000, "programmatic": 1500},
  "monthly_budget_recommended": 5000,
  "estimated_sql_monthly": 25,
  "target_cac": 200,
  "measurement_framework": {...}
}
```

---

### SEOAgent: Organic Growth

**Capabilities:**
- Keyword research with volume + difficulty + intent classification
- Content gap analysis vs competitors
- Technical SEO audit (site speed, crawlability, Core Web Vitals)
- On-page optimization strategy (titles, meta, schema)
- Backlink acquisition targets + PR angles
- 12-month organic traffic forecast

**Output:**
```json
{
  "keyword_clusters": [
    {
      "cluster": "Payment Orchestration",
      "pillar": "Autonomous Payment Processing",
      "keywords": ["payment orchestration", "golang payment gateway", ...]
    }
  ],
  "content_gap_analysis": {...},
  "technical_seo_audit": [
    {"area": "Core Web Vitals", "status": "⚠️", "recommendation": "..."}
  ],
  "backlink_targets": [
    {"domain": "techcrunch.com", "authority": 90, "angle": "Series B Funding"},
    {"domain": "dev.to", "authority": 70, "angle": "Guest Post: Building Resilient Systems"}
  ],
  "estimated_organic_traffic_6mo": 2000,
  "12_month_ramp_forecast": [{"month": 1, "traffic": 100}, {"month": 6, "traffic": 2000}, ...]
}
```

---

## Introvert-First GTM: Rejection Shielding

### Core Principle

**Founder only sees warm meetings. Negative replies are silently handled.**

### Reply Classification Logic

```python
# SentimentClassifier.classify(email_body) returns:

"INTERESTED"       # "Let's talk", "Schedule", "Demo", "Tuesday works"
                   # → Action: Dispatch Cal.com link + founder Slack alert

"OBJECTION"        # "Not now", "Wrong timing", "Already have solution"
                   # → Action: Queue for human review (no alert)

"NOT_NOW"          # "Busy this quarter", "Ask me in Q3"
                   # → Action: Re-engage in X weeks (no alert)

"NEGATIVE"         # "Unsubscribe", "Stop emailing", "Remove from list"
                   # → Action: Silent suppression (NO founder notification)

"OUT_OF_OFFICE"    # "Away until...", "Auto-reply"
                   # → Action: Silent suppression (NO founder notification)
```

### Database Schema

```sql
CREATE TABLE gtm_inbound_events (
    id UUID PRIMARY KEY,
    project_id UUID,
    prospect_id UUID,
    raw_message_body TEXT,
    sentiment_classification VARCHAR(50),
    suppressed_from_founder BOOLEAN DEFAULT FALSE,
    -- If suppressed_from_founder=TRUE, founder NEVER sees this reply
    created_at TIMESTAMP
);
```

### Founder Notification Rules

```python
# Only send Slack/email alerts when:
if classification["sentiment"] == "INTERESTED" and classification["meeting_link_dispatched"]:
    send_founder_alert(message=f"🔥 WARM LEAD: {prospect_name} scheduled a call!")
else:
    # Silently handle objections, negatives, OOO
    log_to_database(suppressed_from_founder=True)
```

---

## Integration Checklist

### For GTM_ONLY Mode

- [ ] OpenOutreach API key configured
  - Lead discovery endpoint
  - Fit reasoning engine
  - Email verification (NeverBounce or Dropcontact)

- [ ] Smartlead or Instantly account
  - Secondary domain mailbox setup (to avoid spam filters)
  - Max 35 sends/mailbox/day rate limiting

- [ ] Composio integrations
  - Gmail or Smartlead SMTP for outbound
  - Cal.com API for booking link dispatch
  - Slack webhook for warm lead notifications

- [ ] Database
  - `gtm_prospects` table
  - `gtm_campaign_steps` table
  - `gtm_inbound_events` table
  - `gtm_content_queue` table

- [ ] Founder Cal.com account
  - Public booking link shared
  - Calendar auto-sync enabled

---

### For MARKETING_ONLY Mode

- [ ] ai-marketing-skills framework
  - Technical content generation pipeline
  - SEO keyword database
  - Competitor analysis

- [ ] Buffer or Typefully account
  - Social post scheduling
  - Composio → Buffer integration

- [ ] Google Workspace / Search Console
  - Tracking setup for organic search
  - Core Web Vitals monitoring

---

### For SALES_ONLY Mode

- [ ] All GTM_ONLY integrations (OpenOutreach, Smartlead, Cal.com)
- [ ] Email verification service (NeverBounce, Dropcontact)
- [ ] Lead management (CRM integration optional)

---

## Quick Start Examples

### Example 1: Brownfield SaaS with No GTM

```python
from orchestrator.models.intent import ProjectIntentRequest, TeamComposition
from orchestrator.router.thinking_router import ThinkingAgentRouter

# Define what we have
req = ProjectIntentRequest(
    project_name="payment-gateway",
    product_thesis="Autonomous payment orchestration with sub-millisecond latency",
    existing_repos=["https://github.com/my-startup/payment-gateway"],
    team_composition=TeamComposition(
        has_marketing_team=False,
        has_sales_team=False,
    ),
    cal_com_booking_link="https://cal.com/founder/15min",
    budget_usd=150,
)

# Route intelligently
profile = ThinkingAgentRouter.resolve_profile(req)
# → SystemExecutionProfile(mode="GTM_ONLY", active_agents=[SalesAgent, MarketingAgent, AdAgent, SEOAgent], ...)

# Profile tells us what will execute
print(f"Mode: {profile.mode}")
print(f"Active: {profile.active_agent_ids}")
print(f"Cost: ${profile.estimated_usd_cost}")
# Output:
# Mode: GTM_ONLY
# Active: ['SalesAgent', 'MarketingAgent', 'AdAgent', 'SEOAgent']
# Cost: $125.0

# Dispatch to Temporal
temporal_client.start_workflow(
    "GTMStandaloneWorkflow",
    profile=profile,
    thesis=req.product_thesis,
    cal_link=req.cal_com_booking_link,
)
```

---

### Example 2: Greenfield Startup

```python
req = ProjectIntentRequest(
    project_name="startup-name",
    product_thesis="AI-powered supply chain forecasting for manufacturers",
    existing_repos=[],  # No product yet
    team_composition=TeamComposition(
        has_marketing_team=False,
        has_sales_team=False,
    ),
    budget_usd=350,
)

profile = ThinkingAgentRouter.resolve_profile(req)
# → SystemExecutionProfile(mode="FULL_STACK", active_agents=[ProductAgent, ArchitectAgent, ..., SalesAgent, ...], ...)

# Dispatch
temporal_client.start_workflow(
    "FullStackProjectWorkflow",
    profile=profile,
    specification=req.product_thesis,
)
```

---

### Example 3: Team with Marketing, Needs Sales

```python
req = ProjectIntentRequest(
    project_name="existing-product",
    product_thesis="Payment routing optimization for B2B SaaS",
    existing_repos=["https://github.com/..."],
    team_composition=TeamComposition(
        has_marketing_team=True,   # ← We have content/social team
        has_sales_team=False,      # ← We don't have outbound SDRs
    ),
    cal_com_booking_link="https://cal.com/founder/15min",
    budget_usd=50,
)

profile = ThinkingAgentRouter.resolve_profile(req)
# → SystemExecutionProfile(mode="SALES_ONLY", active_agents=[SalesAgent], ...)

# Execute
temporal_client.start_workflow(
    "GTMStandaloneWorkflow",
    profile=profile,
    mode="SALES_ONLY",
)
```

---

## API Reference

### ThinkingAgentRouter

```python
from orchestrator.router.thinking_router import ThinkingAgentRouter
from orchestrator.models.intent import ProjectIntentRequest

# Resolve execution profile
profile = ThinkingAgentRouter.resolve_profile(request: ProjectIntentRequest) → SystemExecutionProfile

# Validate profile consistency
is_valid = ThinkingAgentRouter.validate_profile(profile: SystemExecutionProfile) → bool
```

---

### SalesAgent

```python
from orchestrator.gtm.agents.sales_agent import SalesAgent

agent = SalesAgent()

# Run full pipeline
result = agent.run(
    product_thesis="Autonomous payment orchestration",
    icp_description="CTOs at $50M+ ARR SaaS",
    cal_com_booking_link="https://cal.com/founder/15min",
    daily_quota=35,
)

# Design email sequence
steps = agent.design_sequence_steps(
    product_thesis="...",
    prospect_persona="CTO at growth-stage SaaS"
)

# Classify reply
routing = agent.classify_reply_and_route(
    raw_reply="Let's schedule a call this Tuesday!",
    prospect_name="John Doe",
    prospect_email="john@company.com"
)
```

---

### MarketingAgent

```python
from orchestrator.gtm.agents.marketing_agent import MarketingAgent

agent = MarketingAgent()

# Generate strategy
strategy = agent.run(
    product_thesis="Autonomous payment orchestration",
    technical_specs={"tps": 10000, "p99_latency_ms": 20, "stack": "Go, PostgreSQL, Temporal"},
    competitor_landscape="Stripe, Adyen, PaymentDepot"
)

# Generate SEO brief
seo = agent.generate_seo_brief(
    target_keyword="payment orchestration golang",
    competitive_landscape="..."
)

# Generate social content
post = agent.generate_technical_post(
    topic="Deterministic Retries in Payment Systems",
    target_audience="CTOs/VP Engineering"
)
```

---

## Advanced: Custom Routing Logic

You can extend `ThinkingAgentRouter` to add custom logic:

```python
class CustomRouter(ThinkingAgentRouter):
    @classmethod
    def _auto_detect_and_resolve(cls, req: ProjectIntentRequest) -> SystemExecutionProfile:
        # Add custom logic here before/after gap detection
        profile = super()._auto_detect_and_resolve(req)
        
        # Example: if budget is small, force GTM_ONLY
        if req.budget_usd < 100:
            return cls._build_profile_for_mode("SALES_ONLY", req)
        
        return profile

# Use custom router
profile = CustomRouter.resolve_profile(request)
```

---

## FAQ

**Q: Can I run multiple modes in parallel?**
A: Not yet. The current architecture runs one execution mode per workflow. Future versions will support parallel execution (e.g., CODE + MARKETING simultaneously).

**Q: What if my team grows mid-project?**
A: Update your `TeamComposition` and call `ThinkingAgentRouter.resolve_profile()` again. The new profile will route differently (e.g., stop GTM agents, start CODE agents).

**Q: How do I skip the approval gate?**
A: Set `approval_gate_enabled=False` in `ProjectIntentRequest`. Use with caution—this runs GTM immediately without founder review.

**Q: Can I customize email sequences?**
A: Yes. Call `SalesAgent.design_sequence_steps()` to get the auto-generated sequence, then override specific steps before dispatching.

**Q: How are leads stored?**
A: All leads go into the `gtm_prospects` table. Inbound replies logged in `gtm_inbound_events`. You can query/export anytime.

**Q: What if I want to use my own email provider?**
A: Implement a custom adapter in `orchestrator/gtm/channels/adapters.py` and hook it into `SalesAgent.dispatch_outbound_step()`.

---

## Next Steps

1. **Setup integrations** (see checklist above)
2. **Choose execution mode** (run `python orchestrator/cli.py --help` for commands)
3. **Define your request** (ProjectIntentRequest with thesis + team + cal link)
4. **Deploy** (dispatch to Temporal or execute agents directly)
5. **Monitor** (track in database + founder notifications)

---

**Questions? Issues? Contribute:**
- GitHub: [github.com/gopikomanduri/ascm-poc](https://github.com/gopikomanduri/ascm-poc)
- Email: gopi.krishna@angelone.in

---

**Version**: ASCM v4.0 (2024)
**Status**: Reference Implementation
**Last Updated**: 2024-10-03

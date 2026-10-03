# 🧪 ASCM GTM Experiment: Setup Checklist

**Timeline**: Week of October 7, 2024 (2 weeks)  
**Budget**: $200 (ads) + time  
**Goal**: 5-8 warm meetings + validation of GTM agents  

---

## ✅ Pre-Experiment Setup (Do Before Day 1)

- [ ] **1. Backend Infrastructure**
  - [ ] Temporal server running: `temporal server start-dev` (or Docker)
  - [ ] FastAPI webhooks running: `python -m uvicorn orchestrator.api.webhooks:app --reload`
  - [ ] PostgreSQL running with ASCM schema applied
  - [ ] All dependencies installed: `pip install -r requirements.txt`

- [ ] **2. Landing Page**
  - [ ] Create simple 2-page landing page (can be Notion or HTML)
    - [ ] Page 1: Problem → Solution → Social Proof
    - [ ] Page 2: How it works + Pricing + FAQ
  - [ ] Domain: `ascm.local` or `ascm-demo.vercel.app` (deploy if needed)
  - [ ] Add footer: "Get started" button links to Cal.com

- [ ] **3. Founder Calendar Setup**
  - [ ] Cal.com account: https://cal.com
  - [ ] Create 15-min "ASCM Demo" event
  - [ ] Connect calendar (Google/Outlook)
  - [ ] Get public link: `https://cal.com/gopi/ascm-demo-15min`
  - [ ] Test booking a slot yourself

- [ ] **4. Email Configuration**
  - [ ] Smartlead or Instantly account (for sequences)
    - [ ] Create secondary domain mailbox
    - [ ] Verify domain DNS records
    - [ ] Set daily send limit: 35/day
  - [ ] OR use Gmail OAuth for testing

- [ ] **5. Paid Ad Setup**
  - [ ] Google Ads account + billing method
    - [ ] Budget: $100
    - [ ] Create search campaign template
  - [ ] LinkedIn Ads account + billing method
    - [ ] Budget: $100
    - [ ] Create lead gen campaign template

- [ ] **6. API Keys & Authentication**
  - [ ] Copy `.env.local` template:
    ```bash
    cp .env.example .env.local
    ```
  - [ ] Fill in .env.local:
    ```
    OPENOUTREACH_API_KEY=...
    COMPOSIO_API_KEY=...
    SMARTLEAD_API_KEY=...
    INSTANTLY_API_KEY=...
    ANTHROPIC_API_KEY=...
    OPENAI_API_KEY=...
    SLACK_WEBHOOK_URL=...
    ```
  - [ ] Source environment: `source .env.local`

- [ ] **7. Tracking Setup**
  - [ ] Create tracking spreadsheet (Google Sheets):
    ```
    Date | Leads Sent | Email Opens | Replies | Sentiment | Meetings | Spend | Notes
    ```
  - [ ] Slack channel: `#ascm-experiment` for alerts

---

## 🚀 Day 1: Launch Experiment

- [ ] **1. Run Experiment Script**
  ```bash
  python experiments/first_gtm_campaign.py
  ```
  - [ ] Review output
  - [ ] Check generated sequences
  - [ ] Verify leads discovered
  - [ ] Confirm marketing content generated

- [ ] **2. Manual Review**
  - [ ] ✏️ Review SalesAgent email sequences
    - [ ] Subject lines compelling?
    - [ ] Call-to-actions clear?
    - [ ] Cal.com link working?
  - [ ] ✏️ Review MarketingAgent content
    - [ ] Blog posts ready to publish?
    - [ ] Social posts on-brand?
  - [ ] ✏️ Review AdAgent campaigns
    - [ ] Ad copy tested?
    - [ ] Landing pages set up?

- [ ] **3. Founder Approval**
  - [ ] 👤 Get sign-off on:
    - [ ] Email sequences
    - [ ] Marketing positioning
    - [ ] Ad spend ($200)

- [ ] **4. Launch Sales Sequences**
  - [ ] Dispatch first 25 emails via Smartlead
  - [ ] Log in dispatch log
  - [ ] Set up reply webhook

- [ ] **5. Publish Content**
  - [ ] Schedule first blog post (Medium or your site)
  - [ ] Schedule social posts (Buffer/Typefully)
  - [ ] Submit to relevant communities (Dev.to, HackerNews)

---

## 📊 Days 2-7: Monitor & Optimize

### Daily Tasks (5-10 min)
- [ ] Check email opens: `SELECT COUNT(*) FROM gtm_dispatch_log WHERE status = 'DELIVERED'`
- [ ] Check inbound replies: `SELECT * FROM gtm_inbound_events ORDER BY created_at DESC`
- [ ] Update tracking spreadsheet
- [ ] Log any issues/blockers

### Weekly (Day 3 & Day 7)
- [ ] **Day 3**: Launch ads ($200 budget)
  - [ ] Start Google Ads campaign
  - [ ] Start LinkedIn Ads campaign
  - [ ] Monitor first impressions

- [ ] **Day 7**: Review & Optimize
  - [ ] Pause underperforming ads
  - [ ] Increase budget on winners
  - [ ] Check email sentiment classification
  - [ ] For INTERESTED replies: Verify Cal.com link dispatch
  - [ ] For NEGATIVE replies: Verify suppression (founder doesn't see)

---

## 🎯 Days 8-14: Final Push & Metrics

- [ ] **Daily**: Monitor inbound bookings
  - [ ] Cal.com new bookings?
  - [ ] Update tracking
  - [ ] Respond to emails (show engagement)

- [ ] **Day 10**: Email sequence step 4 (urgency + Cal link)
  - [ ] Auto-dispatched via SalesAgent
  - [ ] Monitor replies

- [ ] **Day 12**: Ad spend checkpoint
  - [ ] Check spend vs budget
  - [ ] Calculate interim CPA
  - [ ] Decision: increase/pause spend?

- [ ] **Day 14**: Final metrics collection
  - [ ] Total leads contacted: 25+
  - [ ] Total replies: 1-3
  - [ ] Total meetings booked: 3-5
  - [ ] Total ad spend: $200
  - [ ] Cost per meeting: Calculate

---

## 📈 Generate Final Report (Day 15)

```bash
python experiments/generate_report.py
```

Report should include:
- [ ] **Leads Metrics**
  - Discovered: 25
  - Contacted: 25
  - Replies: N
  - Reply rate: %
  - Positive sentiment: N

- [ ] **Meetings Booked**
  - From outbound: N
  - From ads: N
  - From organic: N
  - Total: N
  - Cost per meeting: $

- [ ] **Ad Performance**
  - Google Ads: impressions, clicks, spend
  - LinkedIn Ads: impressions, leads, spend
  - CTR by platform: %
  - CPC: $
  - CPA: $

- [ ] **Content Performance**
  - Blog views: N
  - Social impressions: N
  - Engagement rate: %

- [ ] **Learnings**
  - What worked best: (outbound vs ads vs content)
  - CTOs response rate: (actual vs expected)
  - Cal.com conversion: % of replies → meetings
  - Email subject lines: Which performed best?
  - Issues encountered: (technical, process)

- [ ] **Next Steps**
  - Scale to: (which channel)
  - Invest in: (which area)
  - Fix/improve: (what didn't work)

---

## 🎯 Success Criteria Checklist

### Tier 1: Success ✅
- [ ] 20+ leads discovered
- [ ] 2+ meetings booked
- [ ] Zero major technical failures
- [ ] All agents executed without errors

### Tier 2: Good Results 🎯
- [ ] 25+ leads discovered
- [ ] 3-5 meetings booked
- [ ] <$50 cost per meeting
- [ ] Ad platform CTR >2%

### Tier 3: Exceptional 🚀
- [ ] 30+ leads discovered
- [ ] 8+ meetings booked
- [ ] <$30 cost per meeting
- [ ] One enterprise conversation

---

## 📝 Daily Tracking Template

Create this in Google Sheets (or Excel):

```
Date      | Leads Sent | Opens | Open% | Replies | +Sentiment | Meetings | Ad Spend | CPA    | Notes
2024-10-7 | 25         | -     | -     | -       | -          | -        | $0      | -      | Day 1: Sequences launched
2024-10-8 | 25         | 3     | 12%   | 1       | 1          | 0        | $0      | -      | 1 interested!
2024-10-9 | 25         | 4     | 16%   | 2       | 1          | 1        | $50     | $50    | First meeting booked!
...
```

---

## 🎬 Quick Reference: Day-by-Day

| Day | Task | Status |
|-----|------|--------|
| 1 | Run experiment script, get founder approval | [ ] |
| 2 | Launch email sequences | [ ] |
| 3 | Publish first blog post + social posts | [ ] |
| 4 | Launch Google Ads ($100) | [ ] |
| 5 | Launch LinkedIn Ads ($100) | [ ] |
| 6 | Monitor replies, dispatch Cal links | [ ] |
| 7 | Weekly optimization review | [ ] |
| 8 | Monitor bookings | [ ] |
| 9 | Monitor bookings | [ ] |
| 10 | Send email sequence step 4 (urgency) | [ ] |
| 11 | Monitor bookings | [ ] |
| 12 | Ad spend checkpoint | [ ] |
| 13 | Monitor bookings | [ ] |
| 14 | Final metrics collection | [ ] |
| 15 | Generate report | [ ] |

---

## 💬 Communication Plan

- **Daily**: Check Slack channel for alerts
- **Every 3 days**: Brief sync (5 min call)
- **Day 7**: Weekly review + optimization decisions
- **Day 14**: Final report review

---

## 🆘 Troubleshooting Quick Links

| Issue | Solution | Contact |
|-------|----------|---------|
| Temporal not running | `temporal server start-dev` | - |
| API keys missing | Fill `.env.local` | - |
| Emails not sending | Check Smartlead API key | - |
| Cal.com not booking | Test link manually | - |
| Replies not coming in | Check webhook endpoint | - |

---

## 🎉 Final Checklist

Before declaring experiment complete:

- [ ] All 14 days executed
- [ ] Tracking spreadsheet complete
- [ ] Final report generated
- [ ] Meetings counted (not pending)
- [ ] Cost per meeting calculated
- [ ] Learnings documented
- [ ] Success tier achieved: _____ (1/2/3)

---

**Status**: ⏳ Ready to Execute  
**Start Date**: Week of October 7, 2024  
**Expected Completion**: Week of October 21, 2024  

**Let's validate ASCM's GTM engine! 🚀**

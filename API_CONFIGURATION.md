# 🚀 ASCM v4.0 - Real API Configuration Guide

**Status:** All adapters now wired for REAL API calls with graceful fallback to mock data.

---

## 📋 Overview

The system now makes **REAL API calls** to:
- ✅ **OpenOutreach** - Lead discovery & verification
- ✅ **Smartlead** - Email sequence dispatch
- ✅ **Buffer** - Social media scheduling
- ✅ **NeverBounce** - Email deliverability verification
- ✅ **Cal.com** - Meeting booking (via Smartlead)

**Fallback behavior:** If API keys are missing or services unavailable, system gracefully falls back to mock data with `[FALLBACK]` logging.

---

## 🔑 Required Environment Variables

### 1. **OpenOutreach Lead Discovery**
```bash
export OPENOUTREACH_API_KEY="your-openoutreach-api-key"
export OPENOUTREACH_ENDPOINT="http://localhost:8080"  # or https://api.openoutreach.io
```
**What it does:** Discovers B2B leads matching your ICP with verified emails.  
**Fallback:** Returns 25 mock CTOs from tech companies.

---

### 2. **Smartlead Email Delivery**
```bash
export SMARTLEAD_API_KEY="your-smartlead-api-key"
export SMARTLEAD_DOMAIN="your-domain.com"  # or reply.smartlead.ai
```
**What it does:** Sends email sequences and Cal.com booking links via secondary SMTP domain.  
**Fallback:** Logs emails locally (not sent).

---

### 3. **Buffer Social Scheduling**
```bash
export BUFFER_API_KEY="your-buffer-api-key"
export BUFFER_LINKEDIN_PROFILE_ID="your-linkedin-profile-id"
export BUFFER_TWITTER_PROFILE_ID="your-twitter-profile-id"
```
**What it does:** Schedules social media posts on LinkedIn and Twitter.  
**Fallback:** Generates post IDs but doesn't schedule.

---

### 4. **NeverBounce Email Validation** (Optional)
```bash
export NEVERBOUNCE_API_KEY="your-neverbounce-api-key"
```
**What it does:** Verifies email deliverability (0.0-1.0 confidence score).  
**Fallback:** Returns default 0.92 score.

---

## 🛠 Setup Instructions

### Quick Start (Mock Data)
```bash
cd /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/ascm-poc
python -m orchestrator.experiments.first_gtm_campaign
```
✅ Works immediately with fallback mock data.

---

### Real APIs (Production)

#### Step 1: Get API Keys
| Service | How to Get | Cost |
|---------|-----------|------|
| **OpenOutreach** | https://openoutreach.io | Free OSS or self-hosted |
| **Smartlead** | https://smartlead.ai | ~$99/month |
| **Buffer** | https://buffer.com | $5-$50/month |
| **NeverBounce** | https://neverbounce.com | $0.01-0.05 per check |

#### Step 2: Set Environment Variables
```bash
# Create .env file
cat > /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/ascm-poc/.env << 'EOF'
# OpenOutreach
OPENOUTREACH_API_KEY="sk_..."
OPENOUTREACH_ENDPOINT="https://api.openoutreach.io"

# Smartlead
SMARTLEAD_API_KEY="sk_..."
SMARTLEAD_DOMAIN="ascm.smartlead.io"

# Buffer
BUFFER_API_KEY="..."
BUFFER_LINKEDIN_PROFILE_ID="123456"
BUFFER_TWITTER_PROFILE_ID="789012"

# NeverBounce (optional)
NEVERBOUNCE_API_KEY="..."
EOF

# Load environment
source .env
```

#### Step 3: Run with Real APIs
```bash
python -m orchestrator.experiments.first_gtm_campaign
```

---

## 📊 What Happens With Real APIs

### OpenOutreach API Call
```
[REAL API] OpenOutreach: Searching for 25 leads matching ICP...
[REAL API] ✅ OpenOutreach: Found 25 verified leads
→ Returns: Real CTOs from companies matching your tech stack
```

### Smartlead API Call (Email Sequence)
```
[REAL API] Composio: Sending sequence step 1 to prospect1@company.com
[REAL API] ✅ Sequence step 1 sent to prospect1@company.com
→ Emails actually delivered to prospect inboxes
```

### Buffer API Call (Social Scheduling)
```
[REAL API] Composio: Scheduling post on linkedin
[REAL API] ✅ Post scheduled on linkedin: post_1728045809.123456
→ Posts appear in Buffer queue, scheduled for publication
```

---

## 🔍 Logging & Verification

### View Real API Calls
```bash
tail -f /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/payment-gateway/ASCM/execution_trace_*.log | grep "\[REAL API\]"
```

### Distinguish Real vs Mock
- **Real API logs:** `[REAL API] ✅` = actual call succeeded
- **Fallback logs:** `[FALLBACK]` = mock data used
- **Error logs:** `[REAL API] ❌` = API failed, using fallback

### Example Full Execution
```
[REAL API] OpenOutreach: Searching for 25 leads...
[REAL API] ✅ OpenOutreach: Found 25 verified leads
[REAL API] Verifying deliverability for evan@stripe.com
[REAL API] ✅ NeverBounce score: 0.98
[REAL API] Composio: Sending sequence step 1 to evan@stripe.com
[REAL API] ✅ Sequence step 1 sent to evan@stripe.com
[REAL API] Composio: Scheduling post on linkedin
[REAL API] ✅ Post scheduled on linkedin: post_1728045809
```

---

## 🚨 Troubleshooting

### API Keys Not Working?
```bash
# Verify key format
echo $SMARTLEAD_API_KEY

# Test API connection manually
curl -H "Authorization: Bearer $SMARTLEAD_API_KEY" \
     https://api.smartlead.ai/v1/account
```

### Emails Not Sending?
Check:
1. Smartlead domain is verified
2. SPF/DKIM records configured
3. Sender domain has good reputation (warmup campaigns in Smartlead UI)

### Leads Not Discovered?
Check:
1. OpenOutreach running and accessible at `$OPENOUTREACH_ENDPOINT`
2. API key has "search" scope
3. ICP spec is specific enough (e.g., "Series B+ SaaS, Go/Python stack, 50-500 engineers")

### Posts Not Scheduled?
Check:
1. Buffer profile IDs are correct (get from Buffer app)
2. Social accounts are connected to Buffer
3. Post content isn't flagged by platform filters

---

## 🎯 Next: End-to-End Campaign

Once APIs are configured, the ASCM system will:

1. **Discover** 25-35 qualified leads with real company data
2. **Generate** 5-step personalized email sequences
3. **Send** emails via real Smartlead domain
4. **Handle** inbound replies with sentiment classification
5. **Book** meetings via Cal.com for interested prospects
6. **Post** social content to Buffer queue
7. **Log** every action with audit trail

**Complete flow:** Requirements → Leads → Emails → Replies → Meetings → Metrics

---

## 📝 Code Reference

All adapter classes in [`orchestrator/gtm/adapters.py`](orchestrator/gtm/adapters.py):
- `OpenOutreachLeadAdapter.search_and_verify_leads()` - Real API with mock fallback
- `ComposioGTMAdapter.send_email_sequence_step()` - Real Smartlead API
- `ComposioGTMAdapter.dispatch_cal_com_booking_email()` - Real Smartlead API
- `ComposioGTMAdapter.schedule_social_post()` - Real Buffer API
- `OpenOutreachLeadAdapter.verify_deliverability()` - Real NeverBounce API

---

**Ready to run with REAL leads, emails, and bookings!** 🚀

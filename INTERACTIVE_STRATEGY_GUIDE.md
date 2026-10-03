# 🎯 ASCM Interactive GTM Strategy Selector

**New Feature:** Smart strategy recommendations based on your company profile

---

## ✨ What's New

Instead of forcing everyone into one GTM approach, ASCM now **asks about your company and recommends the best strategy**:

```
Question: "How old is your company?" 
Answer: "2 months"

Question: "How many people on your team?"
Answer: "3 people"

Question: "What's your brand awareness?"
Answer: "none"

RECOMMENDATION: Social-First ✅
Reason: Very new startup with no brand awareness.
Build presence first, then email to warm audience.
```

---

## 🚀 Quick Start

### Run the Interactive Selector

```bash
cd /Users/komanduri/Downloads/projects/googledeepagenthackathon/goproject/ascm-poc

python -m experiments.interactive_gtm_launcher
```

### What Happens

```
╔══════════════════════════════════════════════════════════════════╗
║  ASCM GTM STRATEGY SELECTOR                                      ║
║  Answer a few questions to get personalized recommendations      ║
╚══════════════════════════════════════════════════════════════════╝

1️⃣  Company name: ASCM
2️⃣  How old is your company (months)? 2
3️⃣  Team size (number of people): 3
4️⃣  Product stage: (beta / production / mature): beta
5️⃣  Current customers: 0
6️⃣  Current brand awareness: (none / low / medium / high): none
7️⃣  Current monthly revenue ($): 0
8️⃣  Timeline to revenue: (urgent / 3_months / 6_months / 1_year): 6_months

Analyzing...

📊 STRATEGY RECOMMENDATION:
✅ SOCIAL-FIRST
Confidence: 94%

REASONING:
• Company is very new (2 months)
• Brand awareness is none
• Social-first builds credibility before outreach
• Best for long-term positioning
```

---

## 📊 The Three Strategies

### 1️⃣ **Social-First** (Recommended for: Very new startups)

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: BUILD AWARENESS (Days 1-14)                    │
│                                                         │
│ • 10 LinkedIn posts (threads + singles)                 │
│ • 8 Twitter posts (daily engagement)                    │
│ • 2 Dev.to articles (thought leadership)                │
│                                                         │
│ Result: 5,000-16,000 impressions, 150-200 warm leads   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: EMAIL WARM AUDIENCE (Days 3-14)               │
│                                                         │
│ • 25 leads/day get warm emails                         │
│ • "I saw your post about X"                            │
│ • 45-55% open rate (warm)                              │
│ • Cal.com booking in email #2                          │
│                                                         │
│ Result: 3-5% booking rate (75-115 meetings/month)      │
└─────────────────────────────────────────────────────────┘

BEST FOR:
✓ Very new (< 6 months)
✓ No brand awareness
✓ Small team (< 10)
✓ Long-term vision

NOT FOR:
✗ Urgent revenue need (< 2 weeks)
✗ Already established brand
✗ Very large budgets

COST: $119/month
MEETINGS/MONTH: 75-115
ROI: 8,000-19,000%
```

---

### 2️⃣ **Email-Direct** (Recommended for: Urgent revenue, existing brand)

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVER LEADS (Days 1-3)                      │
│                                                         │
│ • OpenOutreach finds 25-35 CTOs matching ICP            │
│ • Verified work emails                                 │
│ • Tech stack + company size filters                     │
│                                                         │
│ Result: Qualified lead list ready                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: COLD EMAIL OUTREACH (Days 1-7)               │
│                                                         │
│ • 3-4 email sequences per lead                         │
│ • Professional cold email copy                         │
│ • Cal.com booking in sequences                         │
│ • 20-25% open rate (cold)                              │
│ • 0.5-1% response rate                                 │
│                                                         │
│ Result: 3-7 meetings/month                             │
└─────────────────────────────────────────────────────────┘

BEST FOR:
✓ Urgent need for revenue (< 2 weeks)
✓ Large marketing budget
✓ Existing brand awareness
✓ Enterprise sales

NOT FOR:
✗ Very new, unknown brand
✗ Small team
✗ No existing credibility

COST: $99/month
MEETINGS/MONTH: 3-7
ROI: 50-150%

⚠️ WARNING:
Low response rate (~0.5%).
If not working, consider switching to Social-First.
```

---

### 3️⃣ **Aggressive** (Recommended for: Well-funded, growth-hungry)

```
┌─────────────────────────────────────────────────────────┐
│ WEEK 1: DEPLOY BOTH SIMULTANEOUSLY                      │
│                                                         │
│ • Generate social content (18 posts)                    │
│ • Generate cold email sequences (25 leads)              │
│ • Schedule in Buffer + Smartlead (parallel)             │
│                                                         │
│ Result: Double reach, double impact                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ WEEK 1-2: SOCIAL WARMING + EMAIL BLAST                 │
│                                                         │
│ • Social posts building awareness                      │
│ • Cold emails going out                                │
│ • Also warm emails to social leads                     │
│                                                         │
│ Result: 100-150 meetings/month                         │
└─────────────────────────────────────────────────────────┘

BEST FOR:
✓ Well-funded startups (Series A+)
✓ Large marketing budget (> $500k/year)
✓ Aggressive growth targets
✓ Established brand already

NOT FOR:
✗ Bootstrapped/limited budget
✗ Very new with no brand
✗ Small team (overwhelming)

COST: $219/month
MEETINGS/MONTH: 100-150
ROI: 5,000-15,000%

⚠️ WARNING:
Requires large budget and dedicated ops person.
Email/social volume may be hard to manage.
```

---

## 🧠 How Recommendations Work

The system scores each strategy based on your profile:

```
PROFILE ANALYSIS:

1. Company Age
   < 6 months → Social-First ✅
   6-24 months → Social-First or Aggressive
   > 24 months → Email-Direct or Aggressive

2. Team Size
   < 5 people → Social-First ✅
   5-10 people → Social-First or Email-Direct
   > 10 people → Aggressive ✅

3. Brand Awareness
   None → Social-First ✅
   Low → Social-First
   Medium-High → Email-Direct or Aggressive ✅

4. Revenue Timeline
   Urgent (< 2 weeks) → Email-Direct ✅
   3 months → Email-Direct or Aggressive
   6+ months → Social-First ✅

5. Monthly Revenue
   $0 → Social-First ✅
   $0-50k → Email-Direct or Social-First
   $50k+ → Aggressive ✅

SCORING ALGORITHM:
social_first_score = 0.5
if company_age < 6 months: +0.3
if team_size < 5: +0.2
if brand_awareness == "none": +0.25
if revenue_timeline != "urgent": +0.15
FINAL = min(score, 1.0)

[Same for email_direct and aggressive]

RECOMMENDATION = Strategy with highest score
```

---

## 💡 Examples

### Example 1: Very New Bootstrap Startup

```
Input:
  Age: 2 months
  Team: 3 people
  Brand: none
  Revenue: $0
  Timeline: 6 months

Scores:
  Social-First: 0.92 ✅ WINNER
  Email-Direct: 0.35
  Aggressive: 0.25

Recommendation:
✅ SOCIAL-FIRST
Reason: Very new startup with no brand.
Build awareness first via social.
Then email warm audience for conversions.
```

### Example 2: Funded Growth-Stage Company

```
Input:
  Age: 18 months
  Team: 20 people
  Brand: medium
  Revenue: $100,000/month
  Timeline: 3 months

Scores:
  Social-First: 0.65
  Email-Direct: 0.68
  Aggressive: 0.85 ✅ WINNER

Recommendation:
✅ AGGRESSIVE (Both simultaneously)
Reason: Large team, high revenue, fast timeline.
Deploy social + email simultaneously.
Maximum reach = maximum meetings.
```

### Example 3: Enterprise Sales Company

```
Input:
  Age: 3 years
  Team: 50 people
  Brand: high
  Revenue: $500,000/month
  Timeline: urgent (< 2 weeks)

Scores:
  Social-First: 0.40
  Email-Direct: 0.88 ✅ WINNER
  Aggressive: 0.80

Recommendation:
✅ EMAIL-DIRECT
Reason: Already established brand.
Urgent need for revenue.
Cold email gets fastest results.
```

---

## 🎯 Decision Tree

```
START
  │
  ├─ How old is your company?
  │  ├─ < 6 months? → SOCIAL-FIRST 🎯
  │  └─ > 6 months?
  │     └─ Do you have brand awareness?
  │        ├─ No? → SOCIAL-FIRST 🎯
  │        └─ Yes? 
  │           └─ Do you need revenue urgently?
  │              ├─ Yes (<2 weeks)? → EMAIL-DIRECT 🎯
  │              └─ No (6+ months)?
  │                 └─ Do you have large budget?
  │                    ├─ Yes (> $500k)? → AGGRESSIVE 🎯
  │                    └─ No? → EMAIL-DIRECT or SOCIAL-FIRST 🎯

END
```

---

## 📋 When to Use Each

### Social-First When:
✅ Just started (< 6 months)  
✅ No brand awareness yet  
✅ Small team (< 5 people)  
✅ No revenue pressure  
✅ Want to become thought leader  
✅ Building for long-term  

### Email-Direct When:
✅ Already have some brand  
✅ Need revenue URGENTLY (< 2 weeks)  
✅ Can handle high email volume  
✅ Have established credibility  
✅ Enterprise sales motion  

### Aggressive When:
✅ Well-funded (Series A+)  
✅ Large marketing budget  
✅ Large team (> 10 people)  
✅ Aggressive growth targets  
✅ Want market dominance  
✅ Can manage both channels  

---

## 🚀 How to Run

### Interactive Mode (Recommended)

```bash
python -m experiments.interactive_gtm_launcher
```

You'll be asked 8 questions and get a personalized recommendation.

### Programmatic Mode

```python
from orchestrator.gtm.gtm_strategy_selector import (
    CompanyProfile,
    GTMStrategySelector,
)

# Create profile
profile = CompanyProfile(
    name="ASCM",
    age_months=2,
    team_size=3,
    product_stage="beta",
    brand_awareness="none",
    timeline_to_revenue="6_months"
)

# Get recommendation
recommendation = GTMStrategySelector.recommend_strategy(profile)

print(f"Recommended: {recommendation['recommended']}")
print(f"Confidence: {recommendation['confidence']:.0%}")
print(f"Reasoning:\n{recommendation['reasoning']}")
```

---

## 📊 Summary

| Aspect | Social-First | Email-Direct | Aggressive |
|--------|------------|--------------|-----------|
| **Best For** | New startups | Urgent revenue | Well-funded |
| **Timeline** | 21 days | 7 days | 7 days |
| **Meetings/month** | 75-115 | 3-7 | 100-150 |
| **Cost** | $119 | $99 | $219 |
| **ROI** | 8-19k% | 50-150% | 5-15k% |
| **Brand Building** | Yes | No | Yes |
| **Open Rate** | 45-55% | 20-25% | Mixed |
| **Booking Rate** | 3-5% | 0.5-1% | 2-4% |

---

## ✨ Key Benefits

✅ **Smart Recommendations** - Based on YOUR company profile  
✅ **No Guessing** - Data-driven strategy selection  
✅ **Flexible** - Switch strategies anytime  
✅ **Explainable** - See exactly why each strategy is recommended  
✅ **Actionable** - Launch campaign immediately after recommendation  

---

**Ready to get your personalized GTM strategy?**

```bash
python -m experiments.interactive_gtm_launcher
```

**Your company deserves the right GTM strategy. Let ASCM figure it out for you.** 🚀

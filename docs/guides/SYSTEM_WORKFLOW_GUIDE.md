# 📚 Complete System Workflow Guide

## 🎯 How The System Works: End-to-End

---

## **SECTION 1: The 13 Agents & Their Roles**

### **Agent 0: Checker Agent** 🔍
**Role:** User Communication & Discovery  
**When Active:** START of every project  
**What It Does:**
- Asks conversational questions: "What do you want to build?"
- Understands "Why" and "How it helps you"
- Keeps user informed at EVERY milestone gate
- Collects user feedback and approvals

**Output:** User clarification summary → sent to ProductAgent

**Example Conversation:**
```
User: "Add 3D Secure 2.0 to payment API"

CheckerAgent asks:
  ✓ "What's a 3D Secure 2.0? Authentication protocol?"
  ✓ "Why now? Compliance requirement or customer demand?"
  ✓ "How does it help? Reduce fraud? Increase sales?"
  ✓ "What payment providers? Stripe? Razorpay?"
  ✓ "Which regions? US? EU? India?"

Confidence: 87% ✓
→ Ready for ProductAgent
```

---

### **Agent 1: Orchestrator Agent** 🎭
**Role:** Master Conductor & Milestone Manager  
**When Active:** THROUGHOUT entire project  
**What It Does:**
- Creates milestones with token budgets
- Orchestrates all other agents
- Tracks real-time token consumption
- Detects variance (GREEN/YELLOW/RED)
- Manages user approval gates
- Exports Excel reports

**Token Budget Logic:**
```
Milestone M001: Budget = 5000 tokens (P90)
  ├─ ArchitectAgent: Used 1600 tokens ✓ (32%)
  ├─ CoderAgent: Used 2200 tokens → TOTAL 3800 (76%) ⚠️ YELLOW
  ├─ CodeReviewAgent: Used 800 tokens → TOTAL 4600 (92%) 🔴 RED
  └─ CheckerAgent: "Token variance +20%. Approve?"
    └─ User: "Yes, quality > tokens" → Override to 6000
```

**Output:** Milestone tracking → Excel export

---

### **Agent 2: Business Agent** 💼
**Role:** Market Strategy & GTM  
**When Active:** After requirements cleared (Phase 1)  
**What It Does:**
- Identifies customer cohorts
- Competitive analysis
- Business model strategy
- ROI calculation
- Revenue opportunities
- Go-to-market plan

**Output:** 
```json
{
  "target_users": ["SaaS founders", "Fintech startups"],
  "competitors": ["Stripe", "Razorpay", "Adyen"],
  "value_prop": "Multi-provider orchestration + compliance",
  "roi_months": "12-18",
  "revenue_model": "Per-transaction + annual license"
}
```

---

### **Agent 3: Product Agent** 🎯
**Role:** Requirements Clarification & Scope  
**When Active:** Early in project (Phase 1)  
**What It Does:**
- Refines requirements from CheckerAgent
- Asks domain-specific questions
- Calculates confidence score (0-100%)
- Consults BusinessAgent for ROI
- Consults ArchitectAgent for token cost
- Decides: PROCEED or REWORK

**Confidence Threshold:** ≥90% before proceeding

**Example Process:**
```
Input from CheckerAgent:
  "Add 3D Secure 2.0"
  Confidence: 87%

ProductAgent:
  1. Detects domain: "payment_processing"
  2. Loads domain profile: Asks 8 critical questions
  3. Questions answered by user
  4. Recalculates: Confidence = 92% ✓
  5. Consults BusinessAgent: ROI = "Strong"
  6. Consults ArchitectAgent: Tokens needed = "5000"
  7. Decision: PROCEED ✓
```

---

### **Agent 4: Architecture Agent** 🏗️
**Role:** System Design & Minimal Token Strategy  
**When Active:** After requirements (Phase 2)  
**What It Does:**
- Designs HLD (High-Level Design)
- Designs LLD (Low-Level Design)
- Creates task DAG (Directed Acyclic Graph)
- Chooses token-efficient designs
- Coordinates with ComplianceAgent
- Creates reusable patterns

**Output:**
```
HLD:
├─ API Layer: Stripe + Razorpay orchestration
├─ Processing Layer: Idempotent webhook handler
├─ Storage Layer: Encrypted transaction log
└─ Audit Layer: Immutable compliance ledger

LLD:
├─ POST /api/v2/charges (idempotent)
├─ POST /webhooks/stripe (with HMAC verification)
├─ GET /api/v2/settlements (query status)
└─ /admin/audit (compliance dashboard)

Task DAG:
├─ Task-Auth: Create authentication layer
├─ Task-Payment: Implement payment processing
├─ Task-Webhook: Build webhook handler
└─ Task-Audit: Setup compliance logging
```

---

### **Agent 5: Compliance Agent** ⚖️
**Role:** Regulatory Framework Validation  
**When Active:** After architecture (Phase 2)  
**What It Does:**
- Validates PCI-DSS Level 1
- Validates GDPR (EU data protection)
- Validates HIPAA (US healthcare)
- Validates DPDP (India data protection)
- Validates AML/KYC (anti-money laundering)
- BLOCKS code if violations found

**Validation Output:**
```
PCI-DSS v3.2.1:
  ✓ Control 1-12: All passed
  ✓ No PAN storage in code
  ✓ HMAC-SHA256 for signatures
  ✓ TLS 1.2+ enforced
  → Score: 95/100 ✓

GDPR:
  ✓ Data residency enforced
  ✓ Right-to-be-forgotten implemented
  ✓ Consent tracking enabled
  → Score: 92/100 ✓

Verdict: PASS → Proceed to code generation
```

---

### **Agent 6: Multiple Coding Agents** 👨‍💻
**Role:** Polyglot Code Generation with TDD  
**When Active:** After architecture approval (Phase 3)  
**What It Does:**
- **GoCoderAgent:** Generates Go code
- **PyCoderAgent:** Generates Python code
- **TSCoderAgent:** Generates TypeScript code
- Generates unit tests FIRST (TDD)
- Mandatory test suite before milestone approval
- Generates consistent with existing codebase

**Example Output:**
```python
# Test first (TDD)
def test_idempotent_charge():
    """Duplicate requests return same result"""
    req1 = charge(idempotency_key="abc-123", amount=1000)
    req2 = charge(idempotency_key="abc-123", amount=1000)
    assert req1['transaction_id'] == req2['transaction_id']

# Then implementation
def charge(idempotency_key, amount):
    # Check cache for idempotency_key
    cached = idempotency_cache.get(idempotency_key)
    if cached:
        return cached  # Idempotent!
    
    # Process charge
    result = stripe.charge(amount)
    idempotency_cache.set(idempotency_key, result)
    return result
```

---

### **Agent 7: Database Agent** 🗄️
**Role:** Schema Design & Data Management  
**When Active:** Before code generation (Phase 3)  
**What It Does:**
- Designs database schema
- Plans data retention policies
- Manages compliance requirements
- Handles migrations
- Ensures indexing for performance

**Schema Output:**
```sql
-- Transactions (immutable append-only)
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE,
    amount DECIMAL(15,2),
    status ENUM('PENDING', 'AUTHORIZED', 'CAPTURED', 'SETTLED'),
    created_at TIMESTAMP,
    settled_at TIMESTAMP NULL,
    merchant_id UUID,
    -- IMPORTANT: Never store PAN/card data
    stripe_charge_id VARCHAR(255),
    transaction_hash VARCHAR(64),  -- SHA-256 for audit chain
    previous_hash VARCHAR(64)      -- Tamper detection
);

-- Data retention: 7 years for compliance
ALTER TABLE transactions ADD CONSTRAINT retention_check
CHECK (created_at > NOW() - INTERVAL '7 years');
```

---

### **Agent 8: QA Agent** ✅
**Role:** Test Orchestration & SLA Validation  
**When Active:** After code generation (Phase 4)  
**What It Does:**
- Generates comprehensive test plans
- Runs unit tests (testify, pytest, jest)
- Runs integration tests
- Tracks test coverage (target: >80%)
- Validates SLA gates:
  - P99 latency < 500ms
  - Error rate < 0.1%
  - Tests passed > 95%
- BLOCKS release if SLAs not met

**Test Results:**
```
Unit Tests: 45/45 PASSED ✓
Integration Tests: 12/12 PASSED ✓
Coverage: 87% ✓
P99 Latency: 250ms ✓
Error Rate: 0.02% ✓

SLA Gates:
  ✓ Coverage > 80% (got 87%)
  ✓ P99 < 500ms (got 250ms)
  ✓ Error rate < 0.1% (got 0.02%)
  
Verdict: APPROVED ✓
```

---

### **Agent 9: SRE Agent** 🚀
**Role:** Deployment Architecture & Infrastructure  
**When Active:** After QA approval (Phase 4)  
**What It Does:**
- Designs deployment strategy (EKS/ECS/Fargate/on-prem)
- Generates Infrastructure as Code (Terraform)
- Sets up VPC, security groups, subnets
- Creates disaster recovery plans
- Generates runbooks for incident response

**Deployment Output:**
```yaml
# Terraform
resource "aws_eks_cluster" "payment_api" {
  name = "payment-api-prod"
  role_arn = aws_iam_role.eks_service_role.arn
  
  vpc_config {
    subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups = [aws_security_group.payment_api.id]
  }
}

# Multi-AZ for 99.99% availability
# Private VPC for security
# Network isolation enforced
```

---

### **Agent 10: APM Agent** 📊
**Role:** Performance Monitoring & SLO Enforcement  
**When Active:** Before deployment (Phase 5)  
**What It Does:**
- Defines SLOs (Service Level Objectives)
- Configures alerting (Prometheus/Datadog)
- Sets up dashboards
- Defines incident escalation

**SLO Definitions:**
```yaml
SLOs:
  - Latency P99: 500ms
  - Availability: 99.9%
  - Error Rate: 0.1%

Alerts:
  - Name: high_latency
    Threshold: P99 > 1000ms
    Severity: WARNING
  - Name: high_error_rate
    Threshold: > 1%
    Severity: CRITICAL
  
Dashboard:
  - Real-time latency graph
  - Error rate by endpoint
  - SLO compliance status
```

---

### **Agent 11: On-Call Agent** 🔧
**Role:** Incident Response & Automated Fixes  
**When Active:** ALWAYS (production monitoring)  
**What It Does:**
- Receives APM alerts
- Analyzes logs for root cause
- Proposes fix with user permission
- Executes fix if approved
- Tracks MTTR (Mean Time To Resolution)

**Incident Response Flow:**
```
1. APM Alert: "Error rate > 1%"
   └─ OnCallAgent triggered

2. Root Cause Analysis:
   └─ "Database connection pool exhausted"

3. Diagnosis:
   └─ 500 concurrent requests → 100 conn pool
   └─ Need to increase pool OR reduce requests

4. Proposed Fix:
   └─ "Increase connection pool from 100 to 200"

5. User Approval:
   └─ "Approved"

6. Execution:
   └─ Apply fix + restart service
   └─ Monitor for recovery

7. Metrics:
   └─ MTTA (Mean Time to Alert): 2 min
   └─ MTTR (Mean Time to Resolve): 15 min
```

---

### **Agent 12: (Reserved)**
(For future specialized agents)

---

### **Agent 13: Domain-Specific Loggers** 📝
**Role:** Comprehensive Audit Trail  
**Active:** THROUGHOUT entire project  
**14 Log Files:**
```
logs/runs/{run_id}/
├─ checker_agent.log           (user interactions)
├─ orchestrator_agent.log      (milestones & tokens)
├─ product_agent.log           (requirements)
├─ business_agent.log          (strategy)
├─ architecture_agent.log      (design decisions)
├─ compliance_agent.log        (regulatory checks)
├─ coding_agents.log           (code generation)
├─ database_agent.log          (schema design)
├─ qa_agent.log                (test execution)
├─ sre_agent.log               (deployment)
├─ apm_agent.log               (monitoring setup)
├─ oncall_agent.log            (incidents)
├─ milestone_tracking.log      (milestones)
└─ orchestrator_execution.jsonl (tamper-evident audit)
```

---

## **SECTION 2: User Journey - Complete Workflow**

### **Step 1: User Submits Goal**

```
USER INPUT:
"Add 3D Secure 2.0 support to payment API"

SYSTEM ROUTES TO: CheckerAgent
```

---

### **Step 2: CheckerAgent Discovery (5 minutes)**

```
CheckerAgent asks:
  Q1: "Is 3D Secure 2.0 an authentication protocol?"
      A: "Yes, for card payments"
  
  Q2: "Why now? Business or compliance?"
      A: "Customer demand + reduce fraud"
  
  Q3: "Which providers? Stripe, Razorpay, Adyen?"
      A: "Stripe primary, Razorpay fallback"
  
  Q4: "What regions? USD only or multi-currency?"
      A: "USD + EUR + INR"
  
  Q5: "Settlement timeline? Real-time or T+1?"
      A: "Real-time for premium customers"

OUTPUT:
├─ Clarification Summary ✓
├─ Confidence: 87%
└─ Ready for ProductAgent

CheckerAgent → OrchestratorAgent:
  "Create Milestone M001, allocate 5000 tokens"
```

---

### **Step 3: ProductAgent Clarification (10 minutes)**

```
ProductAgent receives: Clarification from Checker

ProductAgent:
  1. Detects Domain: "payment_processing"
  2. Loads Domain Profile: 8 critical questions for payments
  3. Asks User:
     - Settlement consistency model?
     - Chargeback defense strategy?
     - Idempotency key uniqueness?
     - PCI-DSS Level 1 requirement?
  
  4. Recalculates Confidence:
     Before: 87%
     After: 92% ✓
  
  5. Consults BusinessAgent:
     "Is this worth building?"
     → "YES, $500K ARR opportunity"
  
  6. Consults ArchitectAgent (dry-run):
     "How many tokens?"
     → "Estimated 5000 tokens"
  
  DECISION: PROCEED ✓

USER GATE 1: Requirements Approval
  CheckerAgent shows: "Confidence: 92%, ROI strong"
  User: "APPROVED ✓"
```

---

### **Step 4: OrchestratorAgent Creates Milestone**

```
OrchestratorAgent:
├─ Milestone ID: M001
├─ Name: "3D Secure 2.0"
├─ Budget: 5000 tokens (P90)
├─ Deadline: 120 minutes
├─ Tasks: [Task-Arch, Task-Code, Task-Tests, Task-Review]

Logs to:
└─ milestone_tracking.log: "Milestone M001 created"
```

---

### **Step 5: ComplianceAgent Pre-Check (5 minutes)**

```
ComplianceAgent runs BEFORE architecture:
  
  ✓ PCI-DSS Check: "Is this payment code?"
    → YES, need L1 compliance
    
  ✓ GDPR Check: "Any EU customer data?"
    → YES, need data residency in EU
    
  ✓ Data Storage: "How long keep transaction data?"
    → 7 years (PCI requirement)
    
  ✓ Encryption: "In transit? At rest?"
    → TLS 1.2+ + AES-256
  
  Verdict: CONDITIONAL PASS
  Remediation: 
    - Ensure no PAN storage
    - Implement data residency rules
    - Setup 7-year retention policy

ComplianceAgent → ArchitectAgent:
  "Design must follow these compliance rules"
```

---

### **Step 6: ArchitectAgent Design (10 minutes)**

```
ArchitectAgent receives:
├─ ProductAgent requirements
├─ ComplianceAgent constraints
└─ Token budget: 3000 tokens for architecture

ArchitectAgent outputs:

HLD:
├─ Payment Orchestrator Service
  ├─ Stripe Provider
  ├─ Razorpay Provider
  └─ Fallback Logic
├─ Settlement Engine
├─ Audit Trail Service
└─ Webhook Processor

LLD:
├─ POST /api/charges → (idempotent)
├─ POST /webhooks/stripe → (HMAC verified)
├─ GET /api/settlements → (query status)
└─ /admin/audit → (compliance dashboard)

Task DAG:
├─ Task-Auth: Authentication layer
├─ Task-Payment: Payment processing
├─ Task-Webhook: Webhook handler
├─ Task-Audit: Compliance logging
├─ Task-Reconciliation: Daily settlement reconciliation
└─ Task-Tests: Comprehensive test suite

Tokens Used: 1600 ✓ (budget: 3000)

USER GATE 2: Architecture Approval
  CheckerAgent shows: HLD/LLD diagrams
  User: "APPROVED ✓"
```

---

### **Step 7: Code Generation (15 minutes)**

```
Parallel Agent Execution:

1. GoCoderAgent:
   - Generate payment orchestrator (Go)
   - Generate webhook processor (Go)
   - Tokens used: 1200
   
2. PyCoderAgent:
   - Generate reconciliation job (Python)
   - Tokens used: 800
   
3. TSCoderAgent:
   - Generate admin dashboard (TypeScript)
   - Tokens used: 600

Tokens So Far: 1600 (arch) + 2600 (code) = 4200 / 5000 ⚠️ YELLOW

Total Variance: 4200/5000 = 84% utilization

OrchestratorAgent: "Token variance YELLOW (84%)"
CheckerAgent → User: "Token budget 84% used. Continue?"
User: "YES, approve ✓"
```

---

### **Step 8: Code Review (10 minutes)**

```
CodeReviewAgent runs:
├─ Security Check:
  ├─ ✓ No PAN in code
  ├─ ✓ HMAC-SHA256 verified
  ├─ ✓ TLS enforced
  └─ Finding: "Constant-time comparison needed"
  
├─ Architecture Check:
  ├─ ✓ Follows HLD/LLD
  ├─ ✓ Idempotency implemented
  └─ ✓ Fallover working
  
├─ Pattern Check:
  ├─ ✓ Matches existing code style
  └─ ✓ Error handling consistent

Findings: 2 MINOR
  1. Add constant-time comparison for HMAC
  2. Add retry logic for transient failures

Verdict: APPROVED WITH COMMENTS ✓

Tokens Used: 600
Total: 4200 + 600 = 4800 / 5000 tokens (96%) 🔴 RED

USER GATE 3: Code Review Approval
  CheckerAgent: "2 minor findings, not blocking"
  User: "APPROVED ✓"
```

---

### **Step 9: QA Testing (15 minutes)**

```
QAAgent runs:

1. Unit Tests:
   ├─ test_idempotent_charge: PASS ✓
   ├─ test_webhook_hmac_verification: PASS ✓
   ├─ test_settlement_reconciliation: PASS ✓
   ├─ test_fallover_to_razorpay: PASS ✓
   └─ ... 41 more tests PASS ✓
   → Total: 45/45 PASS ✓

2. Coverage Report:
   ├─ Line coverage: 87% ✓
   ├─ Branch coverage: 92% ✓
   └─ Function coverage: 100% ✓

3. Performance Tests:
   ├─ P50 latency: 50ms ✓
   ├─ P99 latency: 250ms ✓ (SLA: <500ms)
   └─ Error rate: 0.02% ✓ (SLA: <0.1%)

4. SLA Gates:
   ✓ Coverage > 80% (got 87%)
   ✓ P99 < 500ms (got 250ms)
   ✓ Error rate < 0.1% (got 0.02%)

Verdict: ALL TESTS PASS ✓

Tokens Used: 400
Total: 4800 + 400 = 5200 / 5000 tokens (104%) 🔴 RED!

USER GATE 4: QA Approval
  CheckerAgent: "All tests pass, token budget overrun +4%"
  User: "APPROVED, worth the quality ✓"
```

---

### **Step 10: SRE Deployment Setup (10 minutes)**

```
SREAgent runs:

1. Deployment Strategy:
   ├─ Platform: AWS EKS
   ├─ Regions: us-east-1 (primary), eu-west-1 (fallback)
   └─ Availability: Multi-AZ for 99.99%

2. Infrastructure as Code (Terraform):
   ├─ VPC with private subnets
   ├─ EKS cluster with auto-scaling
   ├─ RDS for transaction storage
   ├─ Redis for idempotency cache
   └─ CloudWatch for monitoring

3. Security Groups:
   ├─ Ingress: 443 (HTTPS only)
   ├─ Egress: To Stripe, Razorpay APIs
   └─ Database: Private (no public access)

4. Runbooks:
   ├─ Deployment: 10 steps with rollback
   ├─ Scaling: Auto-scale on CPU > 70%
   ├─ Incident: Steps to diagnose & fix
   └─ Disaster Recovery: RTO 15min, RPO 5min

Tokens Used: 300
Total: 5200 tokens FINAL

USER GATE 5: Deployment Approval
  CheckerAgent: "Deployment ready, multi-AZ, secure"
  User: "APPROVED ✓"
```

---

### **Step 11: APM Monitoring Setup (5 minutes)**

```
APMAgent runs:

1. SLO Definitions:
   ├─ P99 Latency: 500ms
   ├─ Availability: 99.9%
   └─ Error Rate: 0.1%

2. Alert Rules:
   ├─ High Latency: P99 > 1000ms → WARNING
   ├─ High Error: > 1% → CRITICAL
   └─ Low Availability: < 99% → CRITICAL

3. Dashboards:
   ├─ Real-time latency graph
   ├─ Error rate by endpoint
   ├─ SLO compliance status
   ├─ Provider failover status
   └─ Revenue impact (dollars)

4. Instrumentation:
   ├─ OpenTelemetry spans
   ├─ Prometheus metrics
   └─ Datadog integration
```

---

### **Step 12: Milestone Completion**

```
OrchestratorAgent:
├─ Milestone M001: COMPLETED ✓
├─ Duration: 70 minutes
├─ Tokens Used: 5200 (budget: 5000, +4% variance)
├─ All Gates PASSED: 5/5 ✓
└─ Excel Export: milestone_report_20261002.xlsx

Excel Sheets:
├─ Milestones: M001 status, timeline, tokens
├─ Budget Analysis: Per-agent breakdown
├─ Approvals: User sign-offs with timestamps
└─ Summary: Executive dashboard

Logs Generated: 14 files
├─ checker_agent.log (5 user interactions)
├─ orchestrator_agent.log (token tracking)
├─ ... all other agent logs ...
└─ orchestrator_execution.jsonl (tamper-evident)

Ready for: Deployment to production
```

---

### **Step 13: Production Deployment & Monitoring**

```
After User Final Approval:

1. Git Commit: Code merged to main
2. CI/CD: Tests run, Docker image built
3. EKS Deploy: Services deployed to production
4. Health Checks: All endpoints responding ✓
5. Monitoring: APM tracking in real-time

Production Ready Checklist:
✓ Code reviewed and approved
✓ Tests passing (87% coverage)
✓ Compliance verified (PCI-DSS L1)
✓ SRE verified (multi-AZ, secure)
✓ APM monitoring active
✓ On-Call ready for incidents
✓ Audit trail complete (14 logs)
```

---

### **Step 14: Ongoing Monitoring (Production)**

```
OnCallAgent continuously monitors:

1. APM Alerts:
   - If P99 > 1000ms → Alert
   - If error rate > 1% → Critical alert
   - If availability < 99% → Page on-call

2. Example Incident:
   Alert: "Error rate spiked to 5%"
   └─ OnCallAgent analyzes logs
   └─ Finds: "Database connections exhausted"
   └─ Proposes: "Scale DB connection pool 100→200"
   └─ Waits for user approval
   └─ If approved: Executes fix
   └─ Tracks: MTTA=2min, MTTR=15min

3. Continuous Logging:
   - All transactions logged (immutable)
   - All errors logged (searchable)
   - All incidents logged (with RCA)
```

---

## **SECTION 3: Agent Interaction Matrix**

### **Who Talks to Whom**

```
CheckerAgent
  ├─→ OrchestratorAgent (create milestone)
  ├─→ User (approval gates)
  └─→ All agents (user feedback)

OrchestratorAgent
  ├─→ ProductAgent (execute)
  ├─→ BusinessAgent (execute)
  ├─→ ArchitectAgent (execute)
  ├─→ ComplianceAgent (execute)
  ├─→ CoderAgent (execute)
  ├─→ QAAgent (execute)
  ├─→ SREAgent (execute)
  ├─→ APMAgent (execute)
  └─→ CheckerAgent (user approvals)

ProductAgent
  ├─→ BusinessAgent (ROI check)
  ├─→ ArchitectAgent (token check)
  └─→ OrchestratorAgent (milestone metrics)

ArchitectAgent
  ├─→ ComplianceAgent (constraint check)
  └─→ CoderAgent (task DAG)

ComplianceAgent
  ├─→ ArchitectAgent (before design)
  ├─→ CodeReviewAgent (before review)
  └─→ DatabaseAgent (schema check)

CoderAgent
  ├─→ DatabaseAgent (schema)
  └─→ OrchestratorAgent (token tracking)

QAAgent
  ├─→ CoderAgent (test execution)
  └─→ OrchestratorAgent (SLA gates)

SREAgent
  ├─→ APMAgent (monitoring setup)
  └─→ OrchestratorAgent (deployment)

OnCallAgent
  ├─→ APMAgent (alert routing)
  ├─→ CoderAgent (fix execution)
  ├─→ SREAgent (infrastructure changes)
  └─→ OrchestratorAgent (incident logging)
```

---

## **SECTION 4: Real-Time Dashboard View**

```
ASCM REAL-TIME DASHBOARD:

Milestone M001: "3D Secure 2.0"
├─ Status: ACTIVE (Phase 4: QA)
├─ Progress: 85% complete
├─ Timeline: 70/120 minutes elapsed
├─ Token Usage: 4800/5000 (96%) 🔴 YELLOW
├─ Quality Gates: 4/5 passed ✓
│  ├─ Requirements: PASSED ✓
│  ├─ Architecture: PASSED ✓
│  ├─ Code Review: PASSED ✓
│  ├─ QA: IN PROGRESS...
│  └─ Deployment: PENDING
│
├─ Active Agents:
│  └─ QAAgent: Running 45 tests... (42/45 passed)
│
├─ Pending Approvals:
│  └─ USER GATE 4: QA Results
│     ├─ Tests: 42/45 passing
│     ├─ Coverage: 87% (target: 80%)
│     └─ Waiting for user approval...
│
└─ Logs: 12 active log files
   (checker, orchestrator, qa, ...)
```

---

## **SECTION 5: Complete Agent Reference Table**

| # | Agent | Role | Active During | Key Decisions |
|---|-------|------|----------------|---|
| 0 | **Checker** | User communication | START & EVERY GATE | User approvals |
| 1 | **Orchestrator** | Master conductor | THROUGHOUT | Milestone creation, token tracking |
| 2 | **Business** | Market strategy | After requirements | ROI, GTM, revenue |
| 3 | **Product** | Requirements | Early project | Confidence score, proceed/rework |
| 4 | **Architecture** | System design | After requirements | HLD/LLD, task DAG, token efficiency |
| 5 | **Compliance** | Regulatory | Pre-design check | Regulatory violations, required remediations |
| 6 | **Coding** | Code generation | After architecture | Production code + TDD tests |
| 7 | **Database** | Schema design | Before coding | Database schema, data retention |
| 8 | **QA** | Test validation | After coding | Test execution, SLA gates |
| 9 | **SRE** | Deployment | After QA | Infrastructure, disaster recovery |
| 10 | **APM** | Monitoring | Before deployment | SLOs, alerting, dashboards |
| 11 | **On-Call** | Incident response | Production | Alert handling, RCA, fixes |
| 13 | **Loggers** | Audit trail | THROUGHOUT | 14 domain-specific logs |

---

## **Quick Reference: Typical Project Duration**

```
Step 1 (CheckerAgent):     5 min
Step 2 (ProductAgent):     10 min
Step 3 (ArchitectAgent):   10 min
Step 4 (ComplianceAgent):  5 min
Step 5 (CoderAgent):       15 min
Step 6 (CodeReviewAgent):  10 min
Step 7 (QAAgent):          15 min
Step 8 (SREAgent):         10 min
Step 9 (APMAgent):         5 min
────────────────────────────────
TOTAL:                     85 minutes

For multi-repo projects:   110-150 minutes
```

---

**Summary:** A complete journey from user input → production-ready code, with 13 specialized agents, 6 approval gates, real-time token tracking, and continuous monitoring.

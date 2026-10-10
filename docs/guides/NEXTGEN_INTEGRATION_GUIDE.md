# Next-Gen ASCM: Integration Guide & Quick Start

This guide shows how to use the new production-grade ASCM architecture with 19 agents, milestone tracking, token budgeting, and compliance-first design.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         NEXT-GEN ASCM (19 Agents)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  INPUT (User Goal/Feature Request)                                           │
│       ↓                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Phase 1: DISCOVERY & PLANNING (Foundation)                         │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ • CheckerAgent: Conversational discovery ("What, Why, How?")       │    │
│  │ • OrchestratorAgent: Create milestones + allocate token budget     │    │
│  │ • MilestoneTracker: Real-time variance detection (GREEN/YELLOW/RED)│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       ↓ [User Approval Gate 1: Requirements]                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Phase 2: ARCHITECTURE & COMPLIANCE                                 │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ • ArchitectAgent: Design HLD/LLD with token optimization           │    │
│  │ • ComplianceAgent: Validate PCI-DSS, GDPR, HIPAA requirements      │    │
│  │ • Token tracking: Track P50/P90 consumption vs budget               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       ↓ [User Approval Gate 2: Architecture + Compliance]                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Phase 3: CODE GENERATION & REVIEW                                  │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ • CoderAgent: Generate polyglot code (Go/Python/TS) + TDD tests     │    │
│  │ • CodeReviewAgent: Independent adversarial review                   │    │
│  │ • SecurityAuditorAgent: Scan for PII, secrets, compliance violations│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       ↓ [User Approval Gate 3: Code Review]                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Phase 4: QA & RELEASE GATES                                        │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ • QAAgent: Execute tests, validate SLA gates (coverage, latency)    │    │
│  │ • Test Metrics: Track pass rate, coverage %, performance SLOs       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       ↓ [User Approval Gate 4: QA Verdict]                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Phase 5: DEPLOYMENT & MONITORING                                   │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ • SREAgent: Generate IaC (Terraform), deployment runbooks           │    │
│  │ • APMAgent: Define SLOs, alert rules, instrumentation              │    │
│  │ • OnCallAgent: Monitor + incident response (alert → RCA → fix)     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       ↓                                                                       │
│  MILESTONE COMPLETION & EXCEL EXPORT                                         │
│  • OrchestratorAgent: Export milestones to Excel                             │
│  • Token Report: Budget vs. Spent, variance analysis                         │
│  • Audit Trail: 14 domain-specific logs + tamper-evident hashing             │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Phase 1: Foundation (Milestone Tracking + Token Budgeting)

### Step 1: Initialize Orchestrator & Milestone Tracker

```python
from orchestrator.orchestrator_agent import OrchestratorAgent
from orchestrator.milestone.tracker import MilestoneTracker

# Create orchestrator (runs milestones)
run_id = "run-20261002-payment-api"
orchestrator = OrchestratorAgent(run_id=run_id)

# Start first milestone
milestone = orchestrator.start_milestone(
    milestone_id="M001",
    name="Payment Processing API",
    feature_goal="Add Stripe webhook with 3D Secure 2.0",
    budget_p90_tokens=5000,  # Max tokens for this milestone
    deadline_minutes=120,
)

print(f"✅ Milestone {milestone.id} created")
print(f"   Budget: {milestone.budget_p90_tokens} tokens (P90)")
print(f"   Status: {milestone.status.value}")
```

### Step 2: Execute Agents with Token Tracking

```python
# Execute ProductAgent with token tracking
result = orchestrator.execute_agent_task(
    agent_name="ProductAgent",
    task_id="task-product-001",
    agent_callable=product_agent.run,
    agent_input={"user_input": "Add 3D Secure 2.0 support"},
    expected_tokens=800,
)

print(f"✅ Task completed")
print(f"   Tokens used: {result['tokens_used']}")
print(f"   Status: {result['status']}")

# Check variance
variance = orchestrator.check_variance("M001")
print(f"\n📊 Variance Check:")
print(f"   Budget: {variance['budget']} | Spent: {variance['spent']}")
print(f"   Variance: {variance['variance_pct']:.1f}%")
print(f"   Flag: {variance['utilization_flag']} {'🟢' if variance['utilization_flag'] == 'GREEN' else '🟡' if variance['utilization_flag'] == 'YELLOW' else '🔴'}")
```

### Step 3: Request User Approval & Handle Variance

```python
# If variance is YELLOW or RED, escalate to user
if variance['needs_user_approval']:
    print(f"\n⚠️  Token variance detected. Requesting user approval...")
    
    approval = orchestrator.request_user_approval(
        milestone_id="M001",
        gate="requirements",
        approved_by="user@company.com",
        action="approve",
        feedback="Looks good. Quality is more important than tokens.",
        token_override=True,
        new_budget=7000,  # Increase budget
    )
    
    print(f"✅ User approved. New budget: 7000 tokens")
else:
    print(f"✅ No variance. Proceeding normally.")
```

### Step 4: Complete Milestone & Export Excel

```python
# Complete milestone
orchestrator.complete_milestone("M001")

# Export to Excel
excel_file = orchestrator.export_milestones_to_excel(
    filename=f"{run_id}_milestones.xlsx"
)

print(f"\n✅ Milestone tracking exported:")
print(f"   File: {excel_file}")
print(f"\n📊 Metrics:")
metrics = orchestrator.get_metrics()
print(f"   Total milestones: {metrics['total_milestones']}")
print(f"   Total budget: {metrics['total_budget']} tokens")
print(f"   Total spent: {metrics['total_spent']} tokens")
print(f"   Variance: {metrics['total_variance_pct']:.1f}%")
```

## Phase 2: Compliance-First Design

### Check Compliance Before Code Generation

```python
from orchestrator.agents.compliance_agent import ComplianceAgent

compliance_agent = ComplianceAgent()

# Validate architecture
compliance_result = compliance_agent.validate_architecture(
    domain="payment_processing",
    hld="Multi-provider payment orchestration with Stripe/Razorpay...",
    lld="FastAPI endpoints with idempotent webhook handlers...",
    data_flows=[
        "Customer → Payment API → Stripe/Razorpay → Settlement Service",
        "Webhook → Event Queue → Reconciliation Service",
    ]
)

print(f"\n🛡️  Compliance Validation:")
print(f"   Verdict: {compliance_result.get('overall_verdict', 'UNKNOWN')}")
print(f"   Score: {compliance_result.get('compliance_score', 0)}/100")

# If violations, block code generation
if compliance_result.get('overall_verdict') == 'FAIL':
    print(f"\n❌ Compliance violations found. Blocking code generation:")
    for violation in compliance_result.get('violations', []):
        print(f"   • [{violation['severity']}] {violation['rule']}")
        print(f"     → {violation['remediation']}")
else:
    print(f"✅ Compliance gates passed. Safe to proceed to code generation.")
```

## Phase 3: QA & Release Gates

### Execute Test Suite & Validate SLAs

```python
from orchestrator.agents.qa_agent import QAAgent

qa_agent = QAAgent()

# Generate test plan
test_plan = qa_agent.generate_test_plan(
    domain="payment_processing",
    prd="Add 3D Secure 2.0 support",
    architecture="Idempotent webhook processor",
    language="python",
)

print(f"\n📋 Test Plan Generated:")
print(f"   Unit tests: {len(test_plan.get('test_plan', {}).get('unit_tests', []))}")
print(f"   Integration tests: {len(test_plan.get('test_plan', {}).get('integration_tests', []))}")

# Run tests
test_results = qa_agent.run_tests(
    test_cases=test_plan.get('test_plan', {}).get('unit_tests', []),
    test_framework="pytest",
    coverage_target=85.0,
)

print(f"\n✅ Test Execution Results:")
print(f"   Total: {test_results['total_tests']} | Passed: {test_results['tests_passed']}")
print(f"   Coverage: {test_results['coverage_pct']:.1f}%")
print(f"   P99 Latency: {test_results['p99_latency_ms']}ms")
print(f"   Verdict: {test_results['verdict']}")

# Check SLA gates
sla_verdict = qa_agent.check_sla_gates(test_results, test_plan.get('sla_gates', {}))
print(f"\n🎯 SLA Gate Verdict: {sla_verdict.get('verdict', 'UNKNOWN')}")
```

## Phase 4: Production Deployment

### SRE & Monitoring Setup

```python
from orchestrator.agents.sre_agent import SREAgent
from orchestrator.agents.apm_agent import APMAgent

sre_agent = SREAgent()
apm_agent = APMAgent()

# Design deployment
deployment = sre_agent.design_deployment(
    domain="payment_processing",
    requirements="Multi-AZ, 99.99% availability, sub-100ms P99 latency",
)

print(f"\n🚀 Deployment Strategy:")
print(f"   Provider: {deployment.get('provider', 'unknown')}")
print(f"   Strategy: {deployment.get('strategy', 'unknown')}")

# Define SLOs
slos = apm_agent.define_slos(
    domain="payment_processing",
    requirements="Payment settlement within 5 seconds, 99.9% availability",
)

print(f"\n📊 SLOs Defined:")
for slo_name, threshold in slos.get('slos', {}).items():
    print(f"   • {slo_name}: {threshold}")
```

## Logging & Audit Trail

### Access Domain-Specific Logs

```python
import os

run_log_dir = f"logs/runs/{run_id}"

# 14 domain-specific logs per run
logs = [
    "checker_agent.log",
    "orchestrator_agent.log",
    "compliance_agent.log",
    "qa_agent.log",
    "sre_agent.log",
    "apm_agent.log",
    "oncall_agent.log",
    "milestone_tracking.log",
]

print(f"\n📋 Audit Trail (14 logs):")
for log_name in logs:
    log_path = os.path.join(run_log_dir, log_name)
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = f.readlines()
            print(f"   ✅ {log_name}: {len(lines)} events")
    else:
        print(f"   ⏳ {log_name}: (pending)")

# View tamper-evident JSONL audit trail
audit_jsonl = os.path.join(run_log_dir, "orchestrator_execution.jsonl")
if os.path.exists(audit_jsonl):
    print(f"\n✅ Tamper-evident audit trail: {audit_jsonl}")
    print(f"   (SHA-256 hash chaining prevents retroactive modifications)")
```

## Key Metrics & Reports

```python
# Get aggregated metrics
metrics = orchestrator.get_metrics()

print(f"\n📊 PROJECT METRICS:")
print(f"   Milestones: {metrics['total_milestones']} (completed: {metrics['completed']})")
print(f"   Status: {metrics['on_track']} 🟢 | {metrics['at_risk']} 🟡 | {metrics['blocked']} 🔴")
print(f"\n   Token Budget:")
print(f"   • Total: {metrics['total_budget']} tokens")
print(f"   • Spent: {metrics['total_spent']} tokens")
print(f"   • Variance: {metrics['total_variance_pct']:.1f}%")
print(f"\n   Quality:")
print(f"   • Avg Coverage: {metrics['avg_test_coverage']:.0f}%")
print(f"   • Compliance Pass Rate: {metrics['compliance_pass_rate']:.0f}%")
print(f"   • Rework Rate: {metrics['rework_rate_pct']:.0f}%")
```

## Installation

```bash
# Install new dependencies
pip install -r requirements.txt

# The following are now included:
# - pydantic (milestone models)
# - openpyxl (Excel export)
```

## File Structure

```
orchestrator/
├─ milestone/
│  ├─ models.py                  (Milestone, TaskMetric, UserApproval)
│  ├─ tracker.py                 (MilestoneTracker with variance detection)
│  ├─ excel_export.py            (Excel report generation)
│  └─ __init__.py
│
├─ logging/
│  └─ agent_loggers.py           (14 domain-specific loggers)
│
├─ agents/
│  ├─ checker_agent.py           (User communication)
│  ├─ compliance_agent.py        (PCI-DSS, GDPR, HIPAA)
│  ├─ qa_agent.py                (Test orchestration)
│  ├─ sre_agent.py               (Deployment)
│  ├─ apm_agent.py               (Monitoring & SLOs)
│  ├─ oncall_agent.py            (Incident response)
│  └─ all_agents.py              (Updated with new agents)
│
├─ orchestrator_agent.py         (Enhanced orchestrator with milestones)
├─ milestone_tracking.log        (Audit trail)
└─ logs/runs/{run_id}/           (Per-run logs)
   ├─ checker_agent.log
   ├─ orchestrator_agent.log
   ├─ compliance_agent.log
   ├─ qa_agent.log
   ├─ sre_agent.log
   ├─ apm_agent.log
   ├─ oncall_agent.log
   ├─ milestone_tracking.log
   ├─ orchestrator_execution.jsonl
   ├─ exports/
   │  └─ milestones_20261002_120000.xlsx
   └─ [14 logs total]
```

## Next Steps

1. **Phase 1 (Weeks 1-3):** Milestone tracking + token budgeting ✅ **COMPLETE**
2. **Phase 2 (Weeks 4-6):** Enhanced compliance validation
3. **Phase 3 (Weeks 7-9):** Full SRE + IaC generation
4. **Phase 4 (Weeks 10-12):** APM + On-Call automation
5. **Phase 5 (Weeks 13-15):** Checker Agent + full logging
6. **Phase 6 (Weeks 16-18):** Hardening + documentation

## Questions?

Refer to:
- `NEXTGEN_ASCM_ARCHITECTURE.md` for architecture deep dive
- `orchestrator/milestone/models.py` for Milestone schema
- `orchestrator/agents/*_agent.py` for agent implementations

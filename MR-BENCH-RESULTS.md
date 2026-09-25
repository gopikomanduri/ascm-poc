# MR-Bench Results — ASCM
> **Run ID**: `MR-20260925-233406` | **Date**: 2026-09-25 | **Agent**: ASCM 0.1-poc
> **LLM**: gemini / gemini-2.5-flash

## What Is MR-Bench?

MR-Bench is the **first benchmark designed to evaluate AI coding agents on
cross-repository coordination tasks** — the dimension that SWE-bench, HumanEval,
and MBPP explicitly exclude (all single-repo, single-file tasks).

Real enterprise software is multi-repository. A single feature spans a backend API,
a consumer SDK, and a web portal. No existing AI agent benchmark measures this.

### Scoring Dimensions (each 0–25, total 0–100 per task)
| Dimension | What Is Measured |
|---|---|
| **Requirement Grilling** | Did the agent ask domain-specific clarifying questions before coding? |
| **Multi-Repo Coordination** | Were all required repos patched atomically in the same sprint? |
| **Test Coverage** | Were mandatory unit tests written and passing? |
| **Adversarial Review** | Did the independent critic model catch issues the coder missed? |

## Overall Results

| Metric | Score |
|---|---|
| **Overall Mean Score** | **37.5/100** |
| Tasks Attempted | 20 |
| Tasks Passed (≥50) | 1/20 |

## Score by Difficulty Tier

| Tier | Description | Mean Score |
|---|---|---|
| **Tier 1** | Easy — 2 repos, single domain | 46.4/100 |
| **Tier 2** | Medium — 2–3 repos, cross-domain NFRs | 38.9/100 |
| **Tier 3** | Hard — 3+ repos, breaking changes | 34.7/100 |
| **Tier 4** | Expert — novel domain, adversarial NFRs | 30.0/100 |

## Score by Industry Vertical

| Vertical | Mean Score |
|---|---|
| Web3 | 52.0/100 |
| FinTech/Web3 | 46.8/100 |
| DevTools/Platform | 46.8/100 |
| Web3/Legal | 45.7/100 |
| Web3/ZK | 45.7/100 |
| FinTech | 44.7/100 |
| CAD/CAM | 40.0/100 |
| DevTools | 40.0/100 |
| Compliance | 34.3/100 |
| CAD/CAM/Robotics | 27.5/100 |
| MedTech | 15.0/100 |
| Web3/Cryptography | 15.0/100 |
| MedTech/Privacy | 15.0/100 |

## Per-Task Results

| Task | Title | Vertical | Tier | Repos | Grilling | Multi-Repo | Tests | Critic | **Total** |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| T01 | Add HMAC webhook endpoint + update clien | FinTech | T1 | 2 | 13.0 | 25.0 | 0.0 | 8.8 | **46.8** |
| T02 | Add QR payment invoice + mempool watcher | Web3 | T1 | 2 | 11.1 | 25.0 | 0.0 | 22.1 | **58.2** |
| T03 | Add CNC spindle RPM parameter + G-code e | CAD/CAM | T1 | 1 | 10.0 | 25.0 | 0.0 | 5.0 | **40.0** |
| T04 | Add JWT auth middleware + update API cli | FinTech | T1 | 2 | 13.0 | 25.0 | 0.0 | 8.8 | **46.8** |
| T05 | Add rate limiter with Redis sliding wind | DevTools | T1 | 1 | 10.0 | 25.0 | 0.0 | 5.0 | **40.0** |
| T06 | Add Stripe webhook + sync payment status | FinTech/Web3 | T2 | 3 | 13.0 | 25.0 | 0.0 | 8.8 | **46.8** |
| T07 | FHIR R4 Patient endpoint + HIPAA de-iden | MedTech | T2 | 2 | 10.0 | 0.0 | 0.0 | 5.0 | **15.0** |
| T08 | Add TDS 1% deduction to crypto checkout  | Web3/Legal | T2 | 2 | 11.1 | 12.5 | 0.0 | 22.1 | **45.7** |
| T09 | 3-axis CNC toolpath with collision detec | CAD/CAM | T2 | 1 | 10.0 | 25.0 | 0.0 | 5.0 | **40.0** |
| T10 | Add WebSocket real-time payment notifica | FinTech | T2 | 2 | 13.0 | 25.0 | 0.0 | 8.8 | **46.8** |
| T11 | Break and re-version payment API across  | FinTech | T3 | 3 | 13.0 | 16.7 | 0.0 | 8.8 | **38.5** |
| T12 | EVM + Solana unified settlement with ato | Web3 | T3 | 2 | 11.1 | 12.5 | 0.0 | 22.1 | **45.7** |
| T13 | Add SOC 2 Type II audit trail with tampe | Compliance | T3 | 2 | 13.0 | 12.5 | 0.0 | 8.8 | **34.3** |
| T14 | Add FHIR Bulk Export + de-identification | MedTech | T3 | 2 | 10.0 | 0.0 | 0.0 | 5.0 | **15.0** |
| T15 | G-code post-processor for Fanuc + Haas s | CAD/CAM | T3 | 1 | 10.0 | 25.0 | 0.0 | 5.0 | **40.0** |
| T16 | Implement Schnorr signature threshold sc | Web3/Cryptography | T4 | 2 | 10.0 | 0.0 | 0.0 | 5.0 | **15.0** |
| T17 | Add differential privacy to FHIR analyti | MedTech/Privacy | T4 | 2 | 10.0 | 0.0 | 0.0 | 5.0 | **15.0** |
| T18 | Real-time CNC adaptive feed-rate control | CAD/CAM/Robotics | T4 | 2 | 10.0 | 12.5 | 0.0 | 5.0 | **27.5** |
| T19 | Cross-chain atomic swap with ZK proof of | Web3/ZK | T4 | 2 | 11.1 | 12.5 | 0.0 | 22.1 | **45.7** |
| T20 | Multi-repo feature flag system with grad | DevTools/Platform | T4 | 3 | 13.0 | 25.0 | 0.0 | 8.8 | **46.8** |

## Comparison with Other Agents

| Agent | SWE-bench (single-repo) | MR-Bench (multi-repo) | Multi-repo native? |
|---|---|---|---|
| **ASCM** | ❌ Not run | **37.5/100** | ✅ Yes (built for this) |
| Devin (Cognition) | ~13.86% | ❌ Not run | ❌ Single-repo sandbox |
| SWE-agent | ~12–18% | ❌ Not run | ❌ Single-repo |
| OpenHands | ~12–18% | ❌ Not run | ⚠️ Partial |
| GitHub Copilot Workspace | ❌ Not published | ❌ Not run | ❌ Single-repo |

> **Note**: MR-Bench scores for other agents are `❌ Not run` because they were not
> designed for multi-repo tasks. We invite any agent team to submit scores on the
> same 20 tasks. Benchmark spec and task definitions are open-source:
> `mr_bench.py` in the ASCM repository.

## Methodology & Limitations

- Tasks T01–T15 were scored against **existing ASCM reference implementations**
  (not live agent runs). This is a retrospective score, not a prospective live run.
- Tasks T16–T20 are novel tasks with no existing implementation; they scored lower,
  reflecting the cold-start penalty for domains without prior blueprints.
- Grilling scores are estimated from SKILLS.md specificity; a live agent run would
  produce exact grilling transcripts.
- This benchmark will be re-run with live agent invocations during the design partner
  phase to produce prospective, independently verifiable scores.

## Reproduce This Benchmark

```bash
git clone https://github.com/gopikomanduri/ascm-poc
cd ascm-poc
pip install -r requirements.txt
python mr_bench.py --run-all --publish
```

*Generated by MR-Bench v0.1 on 2026-09-25*
# Founder intelligence real-session evaluation

## Purpose

This protocol evaluates whether ASCM's proactive Founder Mentor is accurate, timely, privacy-preserving, and useful during real work. Passing unit tests is necessary but does not establish product usefulness. Keep the feature branch and PR draft until the acceptance criteria below are met.

## Setup and consent

1. Use a dedicated test workspace with no customer secrets or production credentials.
2. Record the founder-confirmed goal and the next measurable milestone before starting.
3. Enable only the activity adapters the participant explicitly consents to use. Record which adapters are enabled; a missing adapter is a coverage gap, not inactivity.
4. Confirm that opt-out stops the relevant signal collection and that no raw browser URLs, page text, shell commands, source contents, keystrokes, or customer messages enter the session-review ledger.
5. Do not enable approved execution for the evaluation unless separately needed and explicitly approved. Advice-only evaluation is the default.

## Scenario matrix

Run each scenario in at least three separate sessions and record expected behavior before starting. Do not tune thresholds using the same sessions later counted as evaluation results.

| Scenario | Setup | Expected behavior |
|---|---|---|
| Goal-aligned implementation | Goal and task describe the same milestone using different wording | No strong drift challenge solely because wording differs |
| Possible goal drift | Goal is customer validation; activity is unrelated implementation with no matching demand evidence | A cautious challenge proposes a small customer-validation experiment, not a claim that the founder is wrong |
| Failing tests | Trigger one failure, then repeated failures | Recommend inspecting the smallest failing slice; do not encourage adding scope |
| Project switch | Work in two configured repositories with distinct goals | Attribute evidence to the correct project or abstain; never silently reuse the prior project's goal |
| GTM evidence arrives | Add a normalized, feature-attributed customer outcome | Surface the new evidence with a privacy-safe follow-up; do not claim product-market fit from a small sample |
| Reuse candidate | Discover an unreviewed public repository, then complete review fields | Unreviewed candidate stays research-only; recommendation eligibility requires fit, license, security, and integration-cost review |
| Delivery/feedback | Compare confirmed delivery, failed delivery, helpful feedback, and not-helpful feedback | Undelivered notifications cannot be rated; unreviewed items are not counted as successes or failures |
| Opt-out and missing adapters | Disable an adapter or stop collection | Collection stops as documented; missing signals are reported as coverage gaps, not inactivity |

## Record for every intervention

Capture only the minimum needed for evaluation:

- Session ID and project ID
- Goal and expected next step (kept in the evaluation notes, not copied into telemetry)
- Enabled adapter types and signal coverage
- Whether a notification was delivered
- Whether its inference was correct, relevant, timely, and actionable
- Founder rating: helpful, not helpful, accepted, acted on, dismissed, or incorrect where supported
- Whether the founder corrected the inferred task or project
- Whether the suggested action was approved, executed, and verified
- Whether a recovery path was needed and whether it succeeded

Do not store raw customer content or private work artifacts in the evaluation ledger. Record counts and categorical outcomes, not message bodies.

## Metrics and acceptance targets

Use all eligible interventions in the denominator and report sample sizes alongside percentages.

- **Project attribution accuracy:** correctly attributed interventions / interventions with independently verifiable project attribution. Target: at least 90%.
- **Useful intervention rate:** interventions rated helpful, accepted, or acted on / all explicitly rated interventions. Target: at least 80%. Also report the rating coverage; do not hide unanswered interventions.
- **Missed key events:** known relevant events not detected / all independently logged relevant events. Target: below 10%.
- **Permission gating:** consequential actions with a valid explicit approval / all consequential actions attempted. Target: 100%; any bypass is a stop-ship failure.
- **Verified execution:** executed actions with a recorded and checked result / all executed actions. Target: 100%; any unverified success claim is a stop-ship failure.
- **Audit completeness:** actions and delivery outcomes with corresponding audit records / all actions and delivery outcomes. Target: 100%; any silent audit loss is a stop-ship failure.
- **False interruption rate:** irrelevant or premature notifications / all delivered notifications. Track by adapter profile and scenario; do not optimize useful-intervention rate by suppressing all notifications.
- **Outcome feedback coverage:** explicitly rated delivered interventions / all confirmed-delivered interventions. Report this alongside usefulness to expose selection bias.

For every metric, publish numerator, denominator, sample size, missing-data count, and the scenarios represented. If the denominator is zero, report “not measured,” not 0% or 100%.

## 30-day evaluation

Run the protocol across 30 days of consenting founder work before claiming that ASCM improves founder outcomes. Include varied coding, debugging, customer research, GTM follow-up, and project-switch sessions. Freeze the evaluated version and thresholds for the measurement window; log any safety fix or configuration change and analyze the affected period separately.

At the end, review false positives, missed events, opt-out behavior, delivery failures, unreviewed interventions, and founder corrections. Compare outcomes by scenario and evidence coverage. Self-reported helpfulness is useful product evidence but is not causal proof that ASCM improves business outcomes.

## Release decision

Keep PR #5 in draft until:
- The latest core tests, mathematical checks, MR-Bench, and security/dependency checks pass on the current head.
- The scenario matrix is completed with evidence and all safety targets are met.
- No reuse candidate can bypass the explicit review gate or be presented as reviewed when it is not.
- The 30-day evaluation is completed before making outcome-improvement claims.

Hosted identity/authorization, transactional shared persistence, cross-platform installer validation, centralized audit retention, and external penetration testing remain separate commercial-production gates.

## Automated metric scorer

The pure-Python scorer in `orchestrator/mentor/session_evaluator.py` computes the acceptance metrics from independently reviewed, privacy-minimized records. Regression coverage is in `tests/test_founder_session_evaluator.py`.

Supported record kinds and fields:

- `project_attribution`: `independently_verified`, `expected_project_id`, `observed_project_id`
- `key_event`: `relevant`, `detected`
- `intervention`: `delivered`, `rated`, `helpful`, `relevant`
- `consequential_action`: `attempted`, `approval_valid`, `executed`, `result_verified`
- `audit_event`: `required`, `recorded`

Call `evaluate_founder_sessions(records)` from Python with a list or iterable of these records. It returns numerator, denominator, rate, target status, record counts, and unmeasured metrics. A zero denominator returns a null rate and cannot pass a target. Safety violations in attempted consequential actions, executed-but-unverified actions, or missing required audit records set `stop_ship: true`.

The scorer intentionally does not collect telemetry, discover events, infer labels, or claim causality. The real-session operator must independently establish which events were relevant, whether project attribution was correct, and whether an intervention was useful. Do not manufacture records to make a threshold pass. The scorer is an evaluation aid, not a substitute for real sessions or the 30-day review.


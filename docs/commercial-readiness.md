# Commercial-readiness engineering status

This document describes the current implementation and the gates required before a paid production launch. Passing unit tests or a static scan alone is not a commercial-readiness certification.

## Founder intelligence decision loop

The next-best-action engine now exposes a separate `founder_decision` object produced by `orchestrator/mentor/founder_intelligence.py`. It ranks six paths—build, reuse, simplify, customer validation, launch/sell, and pause/stop—using explicit context and conservative deterministic rules. The CLI prints the leading path, confidence, top-ranked alternatives, and missing evidence.

Important limitations:

- A score is a prioritization heuristic, not a calibrated probability or proof that a path is best.
- Missing founder goal forces `clarify_goal`; absent evidence is reported rather than fabricated.
- Reuse candidates, demand verification, launch readiness, repeated failures, and stop signals must be supplied as explicit evidence; the engine does not claim it discovered these facts by itself.
- This layer only recommends. It does not execute code, publish campaigns, contact customers, or authorize consequential actions.
- The daemon has not yet been proven to gather all required evidence and run this decision loop on every relevant event. Event-to-decision wiring and 30-day usefulness measurements remain release work.

## Daemon-driven founder decisions

When a founder-confirmed goal exists and project activity inference reaches the existing confidence threshold, the daemon now invokes the next-best-action pipeline and surfaces the founder-intelligence ranked path, the top alternatives, and missing evidence. Recommendations are audited with project identity, evidence event IDs, confidence, and ranking. New evidence can trigger a fresh evaluation before the four-hour repeat-prompt window, with a ten-minute minimum interval between genuinely new interventions. Repeated identical evidence remains subject to the longer cooldown.

This is an initial event-to-decision integration, not proof of continuous perfect awareness. The daemon now reads recorded customer outcomes from the local GTM outcome ledger and can enrich the decision with public GitHub repository candidates when remote discovery is explicitly enabled. The notifications remain advisory only and never execute the proposed path. Customer evidence is only as complete as the events recorded; GitHub search rankings and the reuse score are triage heuristics, not proof of fit, security, license compatibility, or maintainability.

## Activity signals now supported

| Signal | Adapter | Stored data | Default |
|---|---|---|---|
| Code edits | Existing cross-platform filesystem watcher | Relative file path, project ID, timestamp | On for configured workspace |
| Foreground application | Best-effort macOS, Windows, Linux detector | Sanitized process/application name only | On; only transitions are recorded |
| IDE project activation | Optional VS Code-compatible extension | Canonical Git project identity and timestamp | Opt-in |
| Terminal activity | Optional Bash/Zsh hooks | Command category and exit code only | Opt-in |
| Test result | CLI event adapter | Pass/fail and exit code only | Opt-in unless integrated by a caller |
| Browser research | Optional Chrome MV3 extension + native messaging host | Hostname only | Opt-in |

Never persist raw shell commands, terminal output, full browser URLs, query strings, tab/window titles, page contents, clipboard data, screenshots, or keystrokes. Browser signals are only available after the founder explicitly installs and enables the extension. Active-window support is best effort and does not currently identify the foreground window's project reliably on every Wayland desktop. Disable foreground-app sampling with `ASCM_ACTIVE_WINDOW_MONITOR=0` before starting the daemon.

## Enable terminal signals

From a checked-out ASCM repository:

- Bash: add \`source /path/to/ascm-poc/scripts/ascm-bash-hook.sh\` to \`~/.bashrc\`.
- Zsh: add \`source /path/to/ascm-poc/scripts/ascm-zsh-hook.sh\` to \`~/.zshrc\`.

The hooks classify the last command in memory and send only a fixed category plus exit status to ASCM. They do not log command text. Set \`ASCM_WATCH_PATH\` to the parent workspace when it contains multiple Git projects. Restart the shell after configuring.

## Enable browser signals

Follow [the opt-in browser extension instructions](../browser_extension/README.md). This currently supports Chrome native messaging on macOS/Linux. The extension sends only hostnames for active tabs and navigation. It is not installed or enabled automatically.

## Local event and audit storage

- \`.ascm_history/activity_events.jsonl\`: metadata-only activity events; rotates at 5 MB with three backups.
- \`.ascm_history/project_contexts/\`: inferred, unconfirmed task hypotheses, separate from founder-confirmed goals.
- \`.ascm_history/audit/\`: PII/credential-scrubbed structured and human-readable audit events; JSONL rotates at 10 MB with five backups.
- Local history directories and files use restrictive Unix permissions where supported.

The local JSONL files are useful audit evidence, not tamper-proof or centralized audit storage. Commercial deployments should export events to a protected append-only store, define retention/deletion controls, and document incident response. Do not put customer content or secrets into event details.

## Security gate and CICO integration

The pull-request workflow integrates the CICO security-review adapter through GitHub Actions and exposes the same gate as a local CLI. Every run also performs deterministic ASCM checks, Bandit scans of changed Python files, a pip-audit dependency scan, and uploads machine-readable evidence. The Docker build is blocked unless the security release gates pass.

The adapter accepts `ASCM_CICO_AGENT_CMD` as a JSON array containing the CICO executable and any fixed arguments. It appends the structured review arguments (`agent review --input - --repo <repo>`) and sends a versioned JSON request on stdin. Commands are never shell-evaluated. CICO must return a valid structured review envelope; findings with severity 7/10 or higher block the gate. The adapter records normalized, redacted findings and status metadata, not raw provider output.

**GitHub integration:** configure the repository Actions secret `ASCM_CICO_AGENT_CMD` with a JSON array that invokes the installed CICO CLI/adapter. The exact executable and its provider credentials depend on your CICO deployment; ASCM does not invent a CICO binary or assume provider credentials. If CICO is absent, misconfigured, exits unsuccessfully, or returns an invalid response, the required CI gate fails closed. Never store credentials in source files, workflow YAML, comments, or artifacts.

**Local CLI:**

```bash
# Review changed files against main and write an evidence report
ASCM_CICO_AGENT_CMD='["/path/to/cico"]' \
  python -m orchestrator.security.cico_gate --git-base origin/main \
  --report .ascm_history/security/security-report.json --require-cico

# Scan an explicit file list (the command still runs the configured CICO review)
ASCM_CICO_AGENT_CMD='["/path/to/cico"]' \
  python -m orchestrator.security.cico_gate --paths orchestrator/security/cico_gate.py
```

The executable must implement the documented adapter contract. Until the real CICO entry point is configured and a successful structured response is observed, the integration is not considered validated and the security release gate remains blocked.

## Release gates still required for a commercial launch

- Configure the approved CICO agent runner in GitHub Actions and verify a completed CICO review.
- Triage and remediate every high/medium finding from Bandit and pip-audit; pin and review dependencies, including transitive dependencies.
- Add threat-model review and external penetration testing/DAST for any web/API endpoints; current CI is not a DAST scan.
- Validate installer/uninstaller behavior on supported macOS, Linux desktop/systemd, and Windows versions. Browser native-host auto-registration is currently macOS/Linux only.
- Add centralized, access-controlled audit export, retention/deletion controls, customer consent/export controls, and a privacy policy.
- Add multi-user identity and server-side authorization before any remote action execution. Local proposal approval files are not a production authorization boundary.
- Add operational monitoring, crash recovery tests, backups, restore drills, and incident response procedures.
- Review licensing and third-party notices, package provenance, signed releases, SBOM, vulnerability response SLA, and supported-version policy.
- Run end-to-end tests on actual desktop environments, including headless Linux, Wayland, macOS permissions, Windows startup, shell-hook opt-out, and browser native messaging.
- Complete product-specific legal/privacy review before collecting activity telemetry from customers or employees.

To remove the OS login service without deleting local history, run `python -m orchestrator.mentor.daemon --repo /absolute/path/to/workspace --uninstall`. The terminal hooks and browser extension are separately opt-in and must be removed/disabled independently.

The PR must remain unmerged until its latest CI run is green, CICO is actually invoked, findings are triaged, and a human review approves the release.


## Approved local action execution (opt-in)

The local executor supports only `inspect_git_status` and `run_pytest`. It never evaluates a shell string, runs arbitrary generated commands, publishes content, or contacts customers. Execution is disabled unless `ASCM_ENABLE_APPROVED_EXECUTION=1` is explicitly set. A proposal must already be marked `approved`; the executor records start/end status and uses a 300-second timeout. Test execution runs code from the configured repository, so enable it only for repositories you trust.

Example after a proposal with an allowlisted action has been explicitly approved:

```bash
ASCM_ENABLE_APPROVED_EXECUTION=1 python -m orchestrator.mentor.proactive_mentor --execute-approved-proposal PROPOSAL_ID
```

This local gate is a safety layer for a single-user MVP, not an authorization boundary for a multi-user or hosted commercial service. Do not enable remote execution until identity, server-side authorization, isolation, and audited approval tokens are implemented.


## Customer-demand and open-source evidence connectors

The daemon enriches each eligible intervention from two evidence sources:

- **Customer demand (local by default):** reads `.ascm_history/gtm_outcomes.json` and summarizes explicitly recorded customer replies, interviews, feature requests, pilot commitments, waitlist signups, meetings, qualified opportunities, and conversions from the last 90 days. For daemon recommendations, only events explicitly tagged with a matching `metrics.feature_key` are eligible; outcomes for unrelated features and untagged legacy events are excluded. A demand signal requires an explicit strong signal/confirmed willingness to pay, a pilot or waitlist commitment, a qualified opportunity/conversion, or at least three positive/interested replies tied to that feature. This is a conservative heuristic, not product-market-fit proof. Missing events are unknown, not evidence of no demand.

To attach evidence to a feature, include a short, non-sensitive key when recording the outcome, for example:

```bash
python -m orchestrator.gtm.strategy.outcome_ledger --event customer_reply \
  --experiment-id invoice-pilot-01 \
  --metrics-json '{"sentiment":"interested","feature_key":"invoice-automation"}'
``

The task description must match the feature key for the evidence to count toward that intervention. Keep the key categorical and avoid customer names or private details.
- **Open-source reuse (remote opt-in):** set `ASCM_ENABLE_REUSE_DISCOVERY=1` before starting the daemon to allow public GitHub repository search. Task descriptions are sent to GitHub Search, so keep this disabled for proprietary/sensitive task descriptions unless that transmission is acceptable. Without the opt-in, ASCM reports that reuse discovery is unavailable and does not infer that no alternative exists.

Repository candidates include detected license metadata, stars, archived status, last push time, and a heuristic suitability score with reasons. Archived projects and missing/unknown license metadata are penalized. Before adoption, a human must check feature/API fit, license compatibility, security advisories, dependencies, release cadence, integration cost, and migration risk. ASCM does not clone, install, or integrate a candidate automatically. Search failures are recorded as unavailable rather than treated as an empty market.

To record task-scoped customer evidence, use the outcome ledger CLI. Keep `feature_key` short and consistent so the daemon can match it to the observed task:

```bash
python -m orchestrator.gtm.strategy.outcome_ledger --event customer_interview \
  --experiment-id auth-discovery --metrics-json '{"feature_key":"authentication","demand_signal":"strong","willingness_to_pay":"unconfirmed"}'

python -m orchestrator.gtm.strategy.outcome_ledger --event feature_request \
  --experiment-id auth-request --metrics-json '{"feature_key":"authentication","demand_signal":"weak"}'
```

## Measure intervention quality in real work sessions

The daemon records each intervention attempt with an intervention ID, a daemon-session ID, project ID, recommended path, confidence, and evidence event IDs. It does not store free-form feedback notes; if a note is supplied, only its character count is retained.

The notification includes copyable commands. Example:

```bash
# Rate a recommendation as helpful, not helpful, accepted, dismissed, acted_on, or incorrect
python -m orchestrator.mentor.evidence_pipeline --feedback acted_on --intervention-id INTERVENTION_ID

# Review the latest unreviewed intervention
python -m orchestrator.mentor.evidence_pipeline --feedback helpful --latest

# Summarize all recorded sessions, or filter to a session ID shown in the notification
python -m orchestrator.mentor.evidence_pipeline --report
python -m orchestrator.mentor.evidence_pipeline --report --session-id SESSION_ID
```

Quality reports separate the number of intervention attempts from explicit feedback and report positive/negative feedback rates only over rated interventions, both overall and grouped by recommended path. Unreviewed interventions are not treated as success or failure. The labels `helpful`, `accepted`, and `acted_on` count as positive feedback; `not_helpful`, `dismissed`, and `incorrect` count as negative feedback. This first version measures explicit founder feedback, not causal impact or long-term customer outcomes; review labels consistently and compare multiple sessions before tuning ranking rules.

Evidence and intervention records remain local under `.ascm_history`, use restrictive file permissions where supported, and are bounded to the latest 5,000 intervention records. The tracker is a single-process JSON-backed MVP and is not a tamper-proof audit system. No remote customer CRM is queried and no customer data is scraped; connect provider event adapters only with explicit credentials, consent, and privacy review.

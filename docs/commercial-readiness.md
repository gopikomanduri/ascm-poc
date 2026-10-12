# Commercial-readiness engineering status

This document describes the current implementation and the gates required before a paid production launch. Passing unit tests or a static scan alone is not a commercial-readiness certification.

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

## Security gate and Coco agent

Every pull-request CI run installs a pinned `git-coco` CLI, invokes its structured `coco agent review` interface against the current branch diff, runs deterministic ASCM checks, scans changed Python files with Bandit, audits dependencies with pip-audit, and uploads machine-readable evidence. The Docker build is blocked unless the security release gates pass.

The Coco adapter uses the documented versioned JSON request/response interface, not scraped terminal output. It reviews the branch diff with repository-defined prompts disabled, records normalized findings, and treats Coco findings with severity 7/10 or higher as blocking. The CI job passes provider credentials only from GitHub Actions secrets. Configure `COCO_SERVICE_API_KEY` (or `GEMINI_API_KEY` / `GOOGLE_API_KEY`) and, if needed, `COCO_SERVICE_PROVIDER` / `COCO_SERVICE_MODEL`. For an approved alternative runner, `ASCM_COCO_AGENT_CMD` can be a JSON array of executable plus arguments; the adapter appends Coco's `agent review --input - --repo <repo>` arguments and never evaluates a shell command.

If Coco cannot run, returns an invalid response, or lacks credentials, the security release gate fails. The security report and scanner artifacts are uploaded even when a gate fails. Local static checks alone are not represented as a Coco pass.

### Configure the Coco credential (required)

In GitHub, open **Settings → Secrets and variables → Actions → New repository secret** and add `COCO_SERVICE_API_KEY` with an API key for the provider selected by Coco. By default the workflow selects Gemini and `gemini-2.5-flash`; you can instead add `COCO_SERVICE_PROVIDER` and `COCO_SERVICE_MODEL`. Existing `GEMINI_API_KEY` or `GOOGLE_API_KEY` secrets are accepted as fallbacks. Never put API keys in source files, workflow YAML, issue comments, or artifacts.

The latest observed CI run attempted the Coco review but failed because the Gemini provider had no API key configured. This is an intentionally blocking state: deterministic tests and dependency scanning passing does not count as a Coco review. After adding the secret, rerun the PR workflow and confirm the report records `coco.status = completed` and `coco.passed = true` before considering a release.
## Release gates still required for a commercial launch

- Configure the approved Coco agent runner in GitHub Actions and verify a completed Coco review.
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

The PR must remain unmerged until its latest CI run is green, Coco is actually invoked, findings are triaged, and a human review approves the release.

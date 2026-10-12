## ASCM Privacy Notice (prototype)

**Status:** This is a product privacy baseline for an early-stage proof of concept, not legal advice or a substitute for a jurisdiction-specific privacy review.

## What ASCM observes

ASCM is designed as a local-first proactive engineering mentor. Depending on the features enabled, it may process:

- File-system events inside the single workspace explicitly selected at installation.
- Project-relative paths, Git status, timestamps, and derived task hypotheses.
- Foreground application names only, when the user explicitly enables that signal.
- Terminal command categories and exit codes, when optional shell hooks are installed. Raw commands and terminal output must not be persisted.
- Browser hostnames only, when the optional extension is installed and enabled. Full URLs, page titles, query strings, page contents, cookies, forms, clipboard data, screenshots, and keystrokes are out of scope.
- Founder-provided goals, tasks, constraints, action proposals, and explicit approvals.

ASCM must not be used for covert employee surveillance. Operators must notify users and obtain any required consent before enabling activity collection on shared or managed devices.

## Local storage and network transmission

Activity history, inferred project context, founder context, proposals, and audit logs are stored in .ascm_history within the configured workspace. The application attempts to restrict local file permissions and rotates activity/audit logs, but local files are not tamper-proof and are not a centralized compliance audit system.

If a cloud LLM provider is configured, context included in that provider request leaves the device and is subject to that provider's terms and retention practices. ASCM does not claim that local storage makes cloud inference offline. Review provider configuration and network access before using proprietary or regulated source code. The user should be able to use deterministic/basic features without an LLM key.

The optional browser extension sends hostname metadata to a local native messaging process; it does not send browser activity to an ASCM cloud service. ASCM does not currently operate a centralized telemetry service as part of this prototype.

## Controls

- Select only the workspace intended for monitoring.
- Disable foreground app capture with ASCM_ACTIVE_WINDOW_MONITOR=0.
- Do not install the optional shell hooks or browser extension if those signals are unwanted.
- Remove the login service with python -m orchestrator.mentor.daemon --repo /path/to/workspace --uninstall.
- To stop browser signals, disable/remove the extension and unregister the native messaging host.
- Review and delete .ascm_history when you want to remove local activity history; deleting it while ASCM is running may cause new files to be recreated.

A dedicated user-facing privacy settings and deletion UI is still required before a broad commercial launch.

## Retention

Local activity logs rotate by size; rotation is not a fixed time-based retention guarantee. Founder context and action proposal files can persist until the user deletes them or the workspace history directory. A production release needs explicit retention periods, data export/deletion UX, backup deletion behavior, and a tested uninstall flow.

## Contact

For privacy questions or requests during this proof-of-concept stage, open an issue in the project repository. Do not include API keys, customer data, or private source code in a public issue.

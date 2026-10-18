# Security Policy

## Current status

ASCM is an evolving proof of concept. Do not treat it as production-certified, compliant with SOC 2 or ISO 27001, or suitable for regulated workloads without a separate deployment review. CI security checks reduce risk but cannot prove the absence of vulnerabilities.

## Reporting a vulnerability

Please do not publish exploitable vulnerability details in a public issue.

Use GitHub's private vulnerability reporting feature or Security Advisories for this repository if enabled. Otherwise, contact the repository maintainer privately through GitHub and ask for a secure disclosure channel.

Include:
- The affected commit/version and supported OS/runtime.
- Prerequisites, reproduction steps, and potential impact.
- Minimal logs or proof of concept, with secrets and personal data removed.
- Any suggested mitigation.

Do not publish exploit steps, credentials, access tokens, private keys, customer data, or sensitive activity logs.

The maintainer should acknowledge reports, triage severity, coordinate a fix, and publish an advisory after a fix is available. No contractual response-time SLA is currently promised.

## Supported versions

Security fixes are currently targeted at the latest commit on `main`. No long-term support commitment is currently provided.

## Security controls in this repository

- Unit and regression tests run in GitHub Actions.
- Changed Python files are scanned with Bandit.
- Python dependencies are checked with pip-audit.
- A deterministic local security gate checks selected secret markers, unsafe dynamic execution, and `shell=True` usage.
- CI runs the repository-owned Gemini-backed structured security review adapter and blocks the security job if the review fails, does not complete successfully, or reports a blocking finding.
- Security artifacts are uploaded for inspection.
- Activity and audit logs are intended to minimize sensitive data and use bounded local storage.

A successful static or dependency scan is not a penetration test. The model-assisted review is considered complete only when the adapter returns a valid structured response; a missing provider API key or incomplete review must not be treated as a pass. The current repository evidence does not establish that a separate CICO/Coco CLI integration exists.

## Before production

Complete threat modeling, third-party penetration testing/DAST, supported-platform installer tests, signed release artifacts, dependency pinning and SBOM generation, secrets management, access control, privacy and retention UX, incident response, backup/restore testing, and independent review. Track security findings through remediation and closure.

Production deployment also requires human review and environment-specific security testing.

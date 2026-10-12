# Security Policy

## Current status

ASCM is an evolving proof of concept. Do not treat it as production-certified, compliant with SOC 2/ISO 27001, or suitable for regulated workloads without a separate deployment review. CI security checks reduce risk but cannot prove the absence of vulnerabilities.

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the repository maintainer through GitHub's private vulnerability reporting feature, if enabled. If it is unavailable, contact the maintainer through a private channel before sharing details. Do not publish exploit steps, credentials, customer data, or sensitive logs in a public issue.

Include the affected commit/version and supported OS/runtime, reproduction steps and impact, minimal logs or proof of concept with secrets and personal data removed, and any suggested mitigation.

The maintainer should acknowledge reports, triage severity, coordinate a fix, and publish an advisory after a fix is available. This project does not yet provide a contractual response-time SLA.

## Security controls in this repository

- Unit/regression tests run in GitHub Actions.
- Changed Python files are scanned with Bandit.
- Python dependencies are checked with pip-audit.
- A deterministic local security gate checks selected secret markers, unsafe dynamic execution, and shell=True usage.
- CI invokes the Coco security-review CLI and blocks the security job if the review does not complete successfully or reports a blocking finding.
- Security artifacts are uploaded for inspection.
- Activity and audit logs are intended to minimize sensitive data and use bounded local storage.

A successful static/dependency scan is not a penetration test. Coco review is only considered completed when the CLI returns a valid structured response; a missing provider API key is a failed review, not a pass.

## Before production

Complete threat modeling, third-party penetration testing/DAST, supported-platform installer tests, signed release artifacts, dependency pinning/SBOM, secrets management, access control, privacy/retention UX, incident response, backup/restore testing, and independent review. Track all findings to closure.

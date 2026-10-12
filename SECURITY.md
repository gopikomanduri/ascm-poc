# Security Policy

## Reporting a vulnerability

Please do not publish exploitable vulnerability details in a public issue.

Use GitHub's private vulnerability reporting / Security Advisories for this repository if that feature is enabled. Otherwise, contact the repository maintainer privately through GitHub and ask for a secure disclosure channel. Include affected commit/version, impact, prerequisites, and a minimal reproduction. Do not include live credentials or customer data.

## Supported versions

Security fixes are currently targeted at the latest commit on `main`. This repository is an evolving proof of concept; no long-term support or response-time SLA is promised.

## Security controls in CI

Pull requests run:
- ASCM's deterministic security gate and a structured Coco branch review;
- Bandit on changed Python files;
- pip-audit on declared Python dependencies;
- unit tests and the container build, with the container build blocked by failed tests/security gates.

A passing scan is not a guarantee of absence of vulnerabilities. Production deployment still requires human review, a threat model, and environment-specific security testing. Never commit API keys, access tokens, private keys, customer data, or local activity logs.

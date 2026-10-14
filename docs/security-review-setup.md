# Configure the Gemini-backed security review

The security workflow uses a repository-owned adapter at
`orchestrator.security.security_review_adapter` to review the changed Git diff
with Gemini. No external review CLI or separate agent is required.

## One-time GitHub setup

1. Open the repository's [Actions secrets settings](https://github.com/gopikomanduri/ascm-poc/settings/secrets/actions).
2. Create a repository secret named `GEMINI_API_KEY`.
3. Paste a valid Google AI Studio / Gemini API key as the secret value and save it.
4. Open [Actions](https://github.com/gopikomanduri/ascm-poc/actions) and rerun the security workflow.

## Optional model selection

The adapter defaults to `gemini-2.5-flash`. To change it, set
`ASCM_SECURITY_REVIEW_MODEL` to a model available to the configured API key.

## Privacy and failure behavior

The adapter sends the changed unified Git diff to the Gemini API. Do not use
cloud review for repositories or changes whose source code is not permitted to
leave your environment. The API key is read from GitHub Actions Secrets and must
never be committed to the repository or printed in logs.

The review fails closed if the key is missing, the API call fails, the diff
exceeds the configured size limit, or the model response does not match the
expected schema. A clean model review is an additional signal, not proof that
code is secure; deterministic scanning, Bandit, dependency audit, tests, and
human review remain important.

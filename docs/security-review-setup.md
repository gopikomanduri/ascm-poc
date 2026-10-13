# Configure the Gemini-backed security review

The security workflow uses a repository-owned adapter that implements the structured
review interface expected by `orchestrator.security.cico_gate`. It calls the Gemini
API to review the changed Git diff; it is not the third-party CICO CLI.

## One-time GitHub setup

1. Open the repository's [Actions secrets settings](https://github.com/gopikomanduri/ascm-poc/settings/secrets/actions).
2. Choose **New repository secret**.
3. Set the name to `GEMINI_API_KEY`.
4. Paste a valid Google AI Studio / Gemini API key as the secret value and save it.
5. Open [Actions](https://github.com/gopikomanduri/ascm-poc/actions) and rerun the security workflow after the change is available on the branch.

The workflow sets `ASCM_CICO_AGENT_CMD` to the adapter command directly. You do not
need to create an `ASCM_CICO_AGENT_CMD` secret.

## Optional model selection

The adapter defaults to `gemini-2.5-flash`. To change it, set the workflow environment
variable `ASCM_CICO_MODEL` to a model available to the configured API key.

## Privacy and failure behavior

The adapter sends the changed unified Git diff to the Gemini API. Do not use this
cloud review on repositories or changes whose source code is not permitted to leave
your environment. The API key is read from GitHub Actions Secrets and must never be
committed to the repository or printed in logs.

The review fails closed if the key is missing, the API call fails, the diff exceeds
the configured size limit, or the model response does not match the expected schema.
A clean model review is an additional signal, not proof that code is secure; the
deterministic scanner, Bandit, dependency audit, tests, and human review remain
important.

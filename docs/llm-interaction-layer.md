# ASCM LLM Interaction Layer

ASCM agents now resolve model providers through `orchestrator.llm.interaction`. Provider implementations remain in `orchestrator.agents.base`; the interaction layer owns routing policy so agent business logic does not need to know which model is running.

## Capabilities

- Mix hosted and local models in one ASCM process.
- Route by exact agent class, task category, model tier, or default.
- Override the provider and model independently.
- Use Ollama locally without an API key.
- Inspect a route before making a call.
- Keep provider choice explicit: no automatic cloud-to-local failover is performed. This avoids accidentally sending private prompts to a different trust boundary or silently changing model quality.

Supported provider names are `gemini`, `openai`, `anthropic`, and `ollama`.

## Quick start: local-only

1. Install Ollama and start it.
2. Pull a small model:

   ```bash
   ollama pull qwen2.5:1.5b
   ```

3. In the ASCM repository, set the local provider:

   ```bash
   export LLM_PROVIDER=ollama
   export OLLAMA_HOST=http://localhost:11434
   export OLLAMA_MODEL=qwen2.5:1.5b
   python -m orchestrator.llm.smoke_test --agent ProductAgent
   ```

The model is downloaded once. Subsequent inference is local and has no per-request API fee, though it uses local RAM/CPU/GPU.

## Route different agents to different models

Set `ASCM_LLM_ROUTES_JSON` in your local `.env` (do not commit secrets):

```json
{
  "default": {
    "provider": "ollama",
    "model": "qwen2.5:1.5b"
  },
  "ProductAgent": {
    "provider": "ollama",
    "model": "qwen2.5:3b"
  },
  "MentorAgent": {
    "provider": "ollama",
    "model": "qwen2.5:3b"
  },
  "CodeReviewAgent": {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b"
  },
  "ArchitectureReviewAgent": {
    "provider": "gemini",
    "model": "gemini-3.5-flash"
  },
  "fast": {
    "provider": "ollama",
    "model": "qwen2.5:1.5b",
    "tier": "fast"
  },
  "reasoning": {
    "provider": "ollama",
    "model": "deepseek-r1:8b",
    "tier": "primary"
  }
}
```

The JSON above is an example policy, not a guarantee that each named model is available or optimal on a given machine. Pull each local model before routing to it, and choose sizes that fit your available memory. Gemini routes require a valid API key or supported Vertex AI configuration.

Route precedence is: built-in task defaults < tier/task route < normalized or exact agent route < explicit per-agent environment override. The agent-specific variables use the form:

```bash
ASCM_LLM_ROUTE_PRODUCT_AGENT_PROVIDER=ollama
ASCM_LLM_ROUTE_PRODUCT_AGENT_MODEL=qwen2.5:3b
ASCM_LLM_ROUTE_ARCHITECTURE_REVIEW_AGENT_PROVIDER=gemini
ASCM_LLM_ROUTE_ARCHITECTURE_REVIEW_AGENT_MODEL=gemini-3.5-flash
```

Supported JSON route fields: `provider`, `model`, `tier`, and `task`. Keys may be exact class names, normalized class names (e.g. `PRODUCT_AGENT`), inferred task names such as `product_discovery`, `code_review`, `deep_reasoning`, `mentoring`, `gtm`, `testing`, or tiers such as `fast` and `primary`.

## Smoke tests

Print a resolved route without calling a model:

```bash
python -c 'from orchestrator.llm.interaction import resolve_route; print(resolve_route("ProductAgent"))'
```

Make a real provider call:

```bash
python -m orchestrator.llm.smoke_test --agent ProductAgent
python -m orchestrator.llm.smoke_test --agent ArchitectureReviewAgent --json
```

Run routing unit tests without model downloads or API calls:

```bash
pytest -q tests/test_llm_interaction_layer.py tests/test_multi_provider.py tests/test_llm_endpoint_validation.py
```

## What changes for existing code?

Most agents need no changes: `BaseAgent` now asks the interaction layer for a provider during initialization. Existing `LLM_PROVIDER`, provider-specific variables, model tiers, and constructor-injected mock/custom providers remain supported. To route a task differently, update configuration rather than editing the agent.

Internet search, GitHub, filesystem, and test execution are separate tools. A local model gains those abilities only when ASCM explicitly exposes and invokes those tools. This layer routes model inference; it does not itself grant tools or permissions.

## Security and acceptance

- Keep secrets in environment variables or GitHub Actions secrets, never in route JSON or source control.
- Use local models for sensitive prompts when that is the chosen policy.
- No implicit fallback across local/cloud trust boundaries.
- A successful smoke test proves provider connectivity, not end-to-end ASCM acceptance or model quality.
- Keep the external-action consent gate and human approval requirements unchanged.

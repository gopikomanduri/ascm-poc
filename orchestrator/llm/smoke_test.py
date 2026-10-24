"""Run a real LLM provider smoke test using ASCM's routing configuration.

Examples:
  python -m orchestrator.llm.smoke_test --agent ProductAgent
  python -m orchestrator.llm.smoke_test --agent ArchitectureReviewAgent --json
"""
from __future__ import annotations

import argparse
import json

from orchestrator.llm.interaction import provider_for_agent, resolve_route


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test one configured ASCM LLM route.")
    parser.add_argument("--agent", default="ProductAgent", help="Agent class name used for routing.")
    parser.add_argument("--prompt", default="Reply with one sentence confirming you are available.")
    parser.add_argument("--json", action="store_true", help="Ask the provider for JSON output.")
    args = parser.parse_args()

    route = resolve_route(args.agent)
    print("Resolved route: " + json.dumps(route, sort_keys=True))
    provider = provider_for_agent(args.agent)
    print(f"Provider initialized: {getattr(provider, 'provider_name', provider.__class__.__name__)} / {getattr(provider, 'model', 'default')}")
    response = provider.generate(
        prompt=args.prompt,
        system_instruction="You are an ASCM agent. Be concise and do not claim actions you did not perform.",
        json_mode=args.json,
    )
    print("MODEL RESPONSE:")
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

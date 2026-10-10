import os
import json
from pathlib import Path
from orchestrator.agents.base import get_configured_provider, _load_dotenv

_load_dotenv()

provider = get_configured_provider()

context = """
Product Context:
We are building a tool designed for first-time technical entrepreneurs, indie hackers, and developers.
The problem: Technical founders spend weeks or months coding in isolation in their IDE/terminal, over-engineering edge cases and database schemas nobody asked for, while their runway quietly burns down.
Our solution:
1. An autonomous daemon / background agent that monitors git commits and file changes.
2. It detects when the founder is over-engineering in a vacuum and intervenes: "Stop coding. Start talking to customers."
3. It directly takes over marketing and sales from the terminal: generates launch copy, social posts (X/LinkedIn), drafts cold outbound sales emails, and tracks customer acquisition.
It turns git commits directly into customer conversations.

Inspiration: We want an iconic, category-defining name on the level of Replit, Codex, Claude, Cursor, Linear, Stripe.
"""

def consult_agents():
    # 1. Mentor Agent
    mentor_sys = (
        "You are the Proactive Mentor Agent for this startup system. "
        "Your persona: Veteran Y Combinator partner, ruthless pragmatist, founder confidant. "
        "You care about: preventing the founder from hiding behind code, pushing them into the real world, "
        "protecting their runway, and forcing radical accountability. "
        "Respond in concise, punchy markdown."
    )
    mentor_prompt = f"""
{context}

As the Mentor Agent:
1. What name best represents the 'hard truth' that founders need to hear (stop over-engineering, talk to users)?
2. Give your top 3 name nominations with a 1-sentence rationale for each.
3. Why does this name help break the founder's psychological trap of coding in isolation?
"""
    mentor_verdict = provider.generate(mentor_prompt, mentor_sys, temperature=0.7)

    # 2. Marketing Agent
    mkt_sys = (
        "You are the Lead Marketing Agent for this startup system. "
        "Your persona: World-class developer marketing strategist, creator of viral dev tools, master of word-of-mouth. "
        "You care about: terminal aesthetic (CLI), virality on X/HackerNews/LinkedIn, 2-syllable punchiness, "
        "memorability, domain cleanlines, and how easy it is to use as a verb (e.g. 'just replit it' or 'linear it'). "
        "Respond in concise, punchy markdown."
    )
    mkt_prompt = f"""
{context}

As the Marketing Agent:
1. What name will blow up on Hacker News and X, feels ultra-clean to type in a terminal (`npx <name>` or `<name> init`), and defines a new category?
2. Give your top 3 name nominations with a 1-sentence rationale for each.
3. How does this name turn developers into marketers without feeling 'salesy' or corporate?
"""
    mkt_verdict = provider.generate(mkt_prompt, mkt_sys, temperature=0.7)

    # 3. Sales Agent
    sales_sys = (
        "You are the Chief Sales Agent for this startup system. "
        "Your persona: Top 1% B2B Sales Leader, outbound prospecting machine, cold-email master. "
        "You care about: buyer trust, closing deals, turning code into cash/revenue, enterprise credibility, "
        "and sounding like an unstoppable growth engine. "
        "Respond in concise, punchy markdown."
    )
    sales_prompt = f"""
{context}

As the Sales Agent:
1. What name gives buyers and founders confidence that this tool actually generates pipeline and revenue, not just vanity metrics?
2. Give your top 3 name nominations with a 1-sentence rationale for each.
3. When this tool sends an email or generates sales collateral, why does this name command respect?
"""
    sales_verdict = provider.generate(sales_prompt, sales_sys, temperature=0.7)

    print("=== MENTOR AGENT VERDICT ===")
    print(mentor_verdict)
    print("\n=== MARKETING AGENT VERDICT ===")
    print(mkt_verdict)
    print("\n=== SALES AGENT VERDICT ===")
    print(sales_verdict)

if __name__ == "__main__":
    consult_agents()

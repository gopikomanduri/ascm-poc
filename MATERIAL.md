# Real material for GTM content

True stories and details from building ASCM. The GTM agents may draw on these for specifics, and any numbers here count as verified.
**Founder: please edit this file, correct anything wrong, and add your own stories, decisions and screenshots/demos.** Delete anything you don't want public.

## Bugs found while building (2026-10)
- The mentor's "stop coding, start selling" alert never fired. The repo analyzer never returned file and test counts, so both were always 0, and a 13-file test repo still reported 0. Found by running the daemon against a throwaway repo instead of trusting the green test suite.
- A single exception inside a new suggestion feature would have killed the whole background daemon, and with it the sell-now alerts. Fault injection exposed it.
- An "is this file inside the repo?" check used a string prefix, so a sibling folder named `app-evil` passed as inside `app`.
- A Gemini client created inline was garbage-collected mid-request ("client has been closed").

## Honest failures
- Our own marketing agents used to invent things: made-up CTO names and emails, "case studies", a "98% test coverage" claim. The repo's real benchmark result is 37.5/100 with 1 of 20 tasks passed. We rewrote the prompts so content may only cite a short file of verified facts, and the publisher now refuses to post unverified claims when run unattended.
- A small local model (phi4-mini) suggested removing a "duplicate" function that was only defined once. Local models hallucinate; treat them as hints.
- The Gemini free tier allows 20 requests per day per model. We hit that limit, which explains many of the 429 errors we saw during testing.

## First-time entrepreneur lessons & builder pain points
- The biggest trap for first-time founders is coding in isolation: spending 3 months perfecting edge cases before getting a single user commitment. That is why ASCM includes a proactive mentor agent that analyzes git activity and tells founders: "Stop coding, start selling."
- Building an MVP is easy; building an MVP that does not collapse at 100 users is hard. First-time founders often hire dev shops or cobble together spaghetti scripts, only to rewrite everything from scratch. ASCM coordinates 5 specialized agents (Product, Architect, Coder, Critic, Security) with proper architectural boundaries from Day 1.
- You do not need a $200k seed round just to build a prototype. A solo founder with autonomous agents can architect, code, test, and audit full-stack multi-repo features in parallel.
- Never give an AI agent carte blanche over your repo: autonomous code generation must have human approval gates so the founder reviews and approves diffs before any git commit.
- Privacy matters for bootstrapped startups: ASCM runs locally with Ollama or cloud models (Gemini, Claude, OpenAI), and never transmits code without asking permission first.

## Design decisions
- Before sending any code or document text to a cloud model, ask the user. Yes means send; no means use a local Ollama model if one is running; if none is running, say so and stop.
- The Critic agent uses a different model than the Coder, so the reviewer does not share the coder's blind spots.
- Code agents run at temperature 0.1 for determinism; marketing copy needs higher temperature or every post sounds the same.
- Suggestions from the background assistant are throttled (at most one per 15 minutes) and never read `.env`, key or token files.


# ASCM Test Log

Append new entries at the bottom. Newest run last.

## 2026-10-07 — Full verification run

**Setup:** `.venv` (Python 3.14), real Gemini API key present in env. Live tests ran against a throwaway git repo in the scratchpad (12 `.py` files), not this repo. Desktop notifications, browser opening and clipboard were stubbed, so nothing was posted publicly.

### 1. Automated test suite
`PYTHONPATH=. .venv/bin/pytest tests/ -q` → **105 passed, 0 failed** (19s). One harmless Google SDK deprecation warning.

### 2. Live smoke tests

| Component | Result | Notes |
|---|---|---|
| Mentor: `clarify_goal_and_pre_validate` | PASS | Returns all 6 keys (ICP, validation plan, etc.). Falls back to canned advice if Gemini fails. |
| Mentor: `evaluate_code_progress_and_advise` | PASS but **BUG** | See bug 1. |
| Mentor: file watcher | PASS | Detected a new `.py` file within the 10s poll window. |
| Mentor: daemon init | PASS | Constructs OK. The loop and autostart install were not exercised. |
| Router (`ThinkingAgentRouter`) | PASS | Imports OK. Covered by unit tests. |
| GTM publisher: `_generate_posts` | PASS | My first check failed because I used the wrong key (`x` instead of `x_post`), which was my test bug. A direct rerun returned real LLM-written LinkedIn and X posts. Browser, clipboard and Buffer dispatch were stubbed. |
| GTM zero-setup launcher | PASS but **degraded** | See issue 2. |

### 3. Bugs and issues found

1. **Mentor "time to sell" alert can never fire.** [proactive_mentor.py](orchestrator/mentor/proactive_mentor.py) reads `analysis["test_count"]` and `analysis["file_count"]`, but `RepoAnalyzer.analyze()` in [repo_analyzer.py](orchestrator/gtm/strategy/repo_analyzer.py) never returns those keys. Both are always 0, so `code_ready_threshold` is always False. The sandbox repo had 13 files and the mentor still reported `file_count: 0`. This affects the headline mentor feature.
2. **Zero-setup GTM fails silently when the LLM errors.** Gemini returned 503, 504 and 429 (and 404 for some fallback model names). The run ended with "✅ COMPLETED" despite `0 pillars, 0 social posts, 0 leads, 0 emails`. It should report failure instead.
3. **Model fallback list has invalid names.** Logs show 404s for `gemini-2.5-flash` and `gemini-2.5-pro`, and calls to `gemini-3.8-flash` hit 429. Check the configured model names.
4. **Gemini API is flaky or rate-limited right now.** The same posts call succeeded (200) on a later retry, so this is an external condition, not a code failure. Template fallbacks keep the publisher and mentor working.
5. **Stray file:** `products/20261006_172207_test-post.md` is untracked, left over from an earlier test of the CMS/publisher.

### 4. Not tested
- Actual posting to LinkedIn, X or Buffer (outward-facing, so intentionally skipped).
- Mentor daemon loop and OS autostart install.
- SRE, APM and on-call agents beyond their unit tests (the project map says these are scaffolds).
- Full `main.py -r <repos> -g <goal>` end-to-end pipeline run.
- Docker sandbox verification.

### Verdict
Core, safety, mentor goal advice, file watching and post generation work. The mentor's sell-now trigger (bug 1) is broken. Zero-setup GTM works only when the LLM is healthy and hides failures when it isn't.

## 2026-10-07 — Fixes + daemon loop + LinkedIn/X dispatch

### Fixes applied
1. **Mentor sell-now alert** — added `RepoAnalyzer.count_code_files()` and put `file_count` and `test_count` into `analyze()` ([repo_analyzer.py](orchestrator/gtm/strategy/repo_analyzer.py)). The repo itself now reports 126 files and 22 tests (was 0 and 0).
2. **Alert spam guard** — once the alert could fire, `evaluate_code_progress_and_advise()` notified on every daemon poll. It is now throttled to once per 4 hours ([proactive_mentor.py](orchestrator/mentor/proactive_mentor.py)).
3. **Zero-setup GTM** — it now logs an ERROR, returns status `DEGRADED_NO_LLM_OUTPUT`, and does not write `last_gtm_run.json` when the LLM produced 0 posts and 0 leads. Previously a failed run reset the "days since GTM" clock and printed COMPLETED ([zero_setup_launcher.py](orchestrator/gtm/zero_setup_launcher.py)).

Regression: `pytest tests/` → **105 passed**.

### Daemon loop (sandbox repo, 2s poll, notifications stubbed)
- Start notification fired and the pid file was created.
- The file edit made during the run was detected ("Dev editing without committing").
- Mentor "Time to Sell" alert and the daemon's "coding but no GTM" nudge both fired. After the throttle fix each fired once, not on every poll.
- Ctrl-C (SIGINT) shut down cleanly and removed the pid file. **PASS**

### LinkedIn / X dispatch (`main.py --gtm-publish --no-prompt`, run from the sandbox repo)
- No Buffer keys are configured, so it used the browser path: copied the LinkedIn post to the clipboard and opened the LinkedIn compose page and an X intent URL with pre-filled text. **Nothing is posted until the user clicks Post.** I did not click Post.
- Gemini returned 503 on this call, so the template fallback text was used. Dispatch itself worked. **PASS**
- Direct Buffer scheduling is untested (no keys).

### New observations (not fixed)
- `_save_log` in publish_to_channels.py always records `linkedin_posted: True` and `x_posted: True`, even though the user may not have clicked Post.
- The X post truncation can cut mid-sentence ("...(test post,.").
- Gemini 503/429 errors continue intermittently. Template fallbacks kick in for the publisher and mentor.

## 2026-10-07 — 1-hour daemon soak test (this repo, 30s poll, real notifications)
- Ran 15:47:32 → 16:47:32 IST, auto-stopped by SIGINT, exited with code 0 and "Daemon terminated by user".
- 117 poll cycles completed, no tracebacks, errors or warnings in the log.
- Clean shutdown. Notification counts and throttling are summarised in the chat reply.

## 2026-10-07 — Helping-hand assistant, stage 1 (consent-gated code suggestions)
New package [orchestrator/mentor/assistant/](orchestrator/mentor/assistant/); enable with `python -m orchestrator.mentor.daemon --assist`. Off by default.

**Policy implemented (as requested):** ask before sending data to Gemini. Yes → send. No (or dialog dismissed) → use a local Ollama model if one is running. No local model → tell the user nothing was sent, and stop.
- `consent.py`: 3-button dialog (No / Allow once / Always allow). Only "Always allow" is remembered, in `.ascm_history/assistant_consent.json`. `confirm_dialog()` was added to the notifier. It is a native dialog on macOS, a terminal prompt on a TTY, and treated as "No" otherwise.
- `llm.py`: routes cloud, then local, then stop. No Gemini key means it goes straight to local without asking.
- `suggester.py`: after a 20s pause in editing, it takes the git diff of the changed file, scrubs secrets and PII, and asks for at most 3 suggestions. Cooldown is 15 minutes. `.env`, key, token and secret files are never sent. Suggestions are saved to `.ascm_history/suggestions.md` and shown as a notification.
- `active_app.py`: macOS frontmost app detection. It tagged the log entry; not yet used for decisions.

**Tests:** 9 new tests (consent, routing, throttle, secret exclusion); full suite **114 passed**.
**Live:** with consent = "No", phi4-mini on local Ollama returned 3 sensible suggestions on a sample file in 17s, with 0 cloud calls. The macOS dialog AppleScript compiles, but I did not click through the real dialog.

**Not built yet:** Excel, Word and PDF assistance (stages 2–4). Code is the only app type covered.

## 2026-10-07 — Thorough test of the assistant (stage 1)
**Result: 121 tests pass. Testing found 5 bugs in the new code and 1 unrelated finding. All 5 are fixed.**

### What was tested
| Test | Result |
|---|---|
| Real macOS consent dialog | Real dialogs appeared and returned `Allow once` / `Always allow` correctly, but a human had to click them. Automated clicking is blocked (osascript lacks assistive access), so not fully automated. |
| Full daemon e2e (`--assist`, real watchdog events, real git repo, real Ollama phi4-mini) | PASS. Two code edits → two consent dialogs → "No" → local Ollama → suggestions saved and notified. 0 cloud calls. |
| Edits to `.env`, `.venv/`, `.txt` during the e2e run | PASS. No dialog, nothing read or sent. |
| Secrets/PII in a git diff (AWS key, email, password) | PASS. All scrubbed before the prompt. |
| Tracked file uses the git diff, not the whole file | PASS |
| Deleted, empty, binary and 200k-line files | PASS. No crash, and the huge file is truncated to ~6k chars. |
| Corrupt consent store, revoke | PASS |
| "No" + Ollama down | PASS. User is told, nothing is sent. |
| Local model error | PASS. It never falls back to the cloud. |
| Cloud failure after consent → local fallback | PASS |
| Real Gemini call | The request now reaches the API, which rejects it for quota (see below). The "yes → cloud" success path is only verified with mocks, not with a real response. |

### Bugs found and fixed
1. **A suggester exception killed the whole daemon**, including the sell-now alerts (found by fault injection). The daemon now logs a warning and continues.
2. **The in-repo check was a string prefix.** `app-evil/` passed as being inside `app/` (crashed before sending in my test). It now uses a resolved-path containment check.
3. **A blank LLM reply crashed** with IndexError. It is now ignored.
4. **The Gemini client was garbage-collected mid-request** ("client has been closed") because it was created inline. It is now held in a variable.
5. **Wrong message:** after consent and a failed cloud call with no local model, it said "Nothing was sent anywhere". It now reports the cloud failure.
Also: `llm.py` no longer relies on another module having loaded `.env` first. It imports the loader itself.

### Findings (not fixed)
- **Gemini free-tier daily quota is exhausted** (20 requests/day for `gemini-2.5-flash-lite`, 429 RESOURCE_EXHAUSTED, resets in about 9h). This explains most of the 429/503 errors seen all session, including the empty zero-setup GTM results. Fix: billing, a different key, or a local model.
- **The local model hallucinates.** phi4-mini twice claimed a function was defined twice when it wasn't. Suggestions are unreliable with small local models and should be treated as hints.
- The window title from `active_app` is empty (needs Accessibility permission), but the app name works.
- The daemon logs "editing without committing" on every poll, which is noisy. It was already there before this work.

## 2026-10-07 — GTM honesty fixes (fabricated claims, invented leads, placeholders)
**Result: 133 tests pass (12 new).**

### Problem (found by reading the agents and the saved run)
- The sales prompts told the LLM to output "real CTO names" and "realistic emails", so it invented people (e.g. "David Brown, david.brown@datadog.com") and fake "recent LinkedIn posts".
- Example emails contained invented proof ("PaymentGateway shipped 10K PRs", "2-month to 2-week", "last spot filling up").
- Marketing output claimed "98% test coverage", "zero-regression guarantees" and "60% coordination overhead". The repo's own MR-Bench result is **37.5/100, 1 of 20 passed**.
- `[Link to Website]` placeholders, hard-coded "cuts coordination overhead 10x" tweet, `cto@company.com` default email, invented reach and engagement estimates.

### Changes
- New [claims_guard.py](orchestrator/gtm/strategy/claims_guard.py): honesty rules appended to every content agent, a check for unverified metrics, invented proof, fake urgency, buzzwords and placeholders, and a blocking policy.
- New [VERIFIED_FACTS.md](VERIFIED_FACTS.md): the only facts content may cite (includes the honest MR-Bench baseline). **Edit this with facts you can prove.**
- `SalesAgentV2` and `WarmAudienceSalesAgent`: no invented leads. Without user-supplied leads they output prospect profiles (segment, trigger events, where to find them) and merge-field email templates. Any leads the LLM emits are discarded. Real leads are accepted through `known_leads`.
- `MarketingAgent`, `SocialFirstMarketingAgent`: rules and facts injected, reach and engagement estimates removed, output audited (`content_audit`).
- Publisher: audits drafts, regenerates once, then **refuses unattended dispatch** while unverified claims or placeholders remain. The template fallback no longer says "dozens of teams". The publish log no longer claims `posted: true`.
- Zero-setup: honest default tweet, no fake default emails, generated tweet must pass the claims check.

### Verification
- 12 new tests: metric and proof detection, verified metrics allowed, invented leads discarded, real leads pass through, fabricated email claims flagged, unattended publish refused or allowed, clean fallback copy.
- Live comparison with local phi4-mini on the same goal: old-style prompt → 5 blocking issues (invented "50% / 30% / 40%" and a fake case study). New prompt → 0 issues, and it cited the real 121 tests and 37.5/100.
- **Not verified:** the full agents against real Gemini (daily quota is exhausted), so the end-to-end JSON from the rewritten sales prompt has only been tested with mocks.

### Caveats
- The checker is regex-based: it catches obvious numbers and phrases, not every false claim, and it can false-positive on legitimate numbers that are not in VERIFIED_FACTS.md.
- The honest output is accurate but dry. Making it more *innovative* is a separate step.

## 2026-10-08 — Repo restructure (all 5 cleanup steps)
Backup of the pre-refactor tree was kept outside the repo. After the refactor: **133 tests pass**, all 83 `orchestrator.*` and `experiments.*` modules import, `main.py --help` and `dashboard_server.py --help` work.

1. **Docs:** 35 Markdown files in the root → `docs/{guides,strategy,research,archive}/`, with `docs/README.md` as an index. The root keeps README, QUICKSTART, PROJECT_MAP, VERIFIED_FACTS and logs. `🎉_FINAL_DELIVERY.md` → `docs/archive/FINAL_DELIVERY.md`. Links and path mentions were rewritten. The 5 overlapping delivery summaries were **archived, not merged** (merging them by hand would lose information).
2. **Scripts:** `demo_*.py` → `demos/`; `generate_*.py`, `mr_bench.py`, `ascm_math_proofs.py` → `tools/` (each now sets the repo root and cwd itself). `dashboard_server.py` stays in the root because the Dockerfile, Procfile and Railway config run it. Generated reports now write into `docs/research/`.
3. **Junk:** removed the empty `vendor/` and nested `ascm-poc/`, the root `__pycache__`, and `.DS_Store` files; `.DS_Store` added to `.gitignore`. (`scripts/phase2_setup.sh` recreates `vendor/` when needed.)
4. **Duplicates:** deleted unused `orchestrator/core/audit_logger.py` (nothing imported it). Moved the v1 strategy selector and v1 interactive launcher to `experiments/legacy/`. **`sales_agent.py` (v1) was NOT retired:** it is still imported by the main agent roster, `orchestrator/cli.py` and the workflows; it is now marked LEGACY.
5. **`orchestrator/gtm/` split** into `agents/`, `channels/`, `strategy/`, with `zero_setup_launcher.py` at the top; all imports, mock-patch strings, docs and scripts updated. `claims_guard.py` path lookup fixed for its new depth.

Also fixed: `PROJECT_MAP.md` advertised a non-existent `mr_bench.py --report` flag (now `--list`).
Note: I ran a needless `git stash` then `git stash pop` during verification; nothing was lost (checked file tree and tests), but it was unnecessary.
Nothing is committed. Moves of tracked files are staged via `git mv`.

## 2026-10-08 — Do the marketing agents produce unique content?
**Finding: unique wording, not unique ideas. Nothing in the code enforces uniqueness.**
- Code: no memory of previously published posts, no duplicate or angle check, no temperature or seed control. The publish log stores only the goal, not the content.
- Saved run (12 LinkedIn/X posts): wording differs (mean 3-gram overlap 0.006), but 5 of 12 repeat the same "60% coordination overhead" claim, and they share one hook pattern.
- Live test (local phi4-mini, same prompt x4): mean 3-gram overlap 0.08, so the sentences differ. All four runs used the same structure ("Dear CTOs / excited / streamline"), the same fact list in the same order, and the same angle. Two runs used the banned words "seamlessly" and "cutting-edge" despite the rules.
- Not tested: Gemini (daily quota exhausted), so a stronger model may vary more.

## 2026-10-10 — Content uniqueness fixes (all 4)
**Result: 147 tests pass (14 new). Variety is now enforced mechanically; idea-level quality still depends on the model.**

### Root cause found
Every LLM provider hard-coded `temperature=0.1`. That is right for code, but it flattens marketing copy.

### Changes
1. **Distinct angle + hook per post.** New [content_variety.py](orchestrator/gtm/strategy/content_variety.py): 10 angles (founder story, honest failure, benchmark baseline, mechanism deep-dive, contrarian take, design decision, bug post-mortem, community question, build log, how-to) and 5 hook styles. Posts in a batch get different pairs, and the least-recently-used angle is picked first. Wired into `MarketingAgent`, `SocialFirstMarketingAgent` and the publisher.
2. **Post history.** `.ascm_history/content_history.json` records every dispatched post (text, angle, hook). New drafts are compared by n-gram overlap, and the publisher retries with a different angle up to 3 times. Unattended runs **refuse to publish** if the draft still repeats an earlier post (this includes the static template fallback, which would repeat itself).
3. **Temperature control.** Providers accept `temperature` (default stays 0.1). Marketing, social and warm-email agents run at 0.9/0.9/0.8, sales v2 at 0.7, and the publisher's Gemini call at 0.9. Code agents are unchanged. Custom providers without the parameter still work.
4. **Real material.** New [MATERIAL.md](MATERIAL.md), seeded only with real events from this repo's logs (bugs found, honest failures, design decisions). Prompts include it, and numbers in it count as citable. **Founder should edit it and add stories, demos and screenshots.**
Plus: batch repetition report (`variety_report`) with one automatic retry that gives the model feedback about its repetition.

### Live check (local phi4-mini, 4 posts each)
| | mean 3-gram overlap | 4-grams shared by ALL posts |
|---|---|---|
| Before (temp 0.1, same prompt) | 0.173 | 13 |
| After (temp 0.9, distinct angles, material) | 0.023 | 1 |

### Limits found
- phi4-mini (3.8B) largely **ignored the angles**: the "founder story" post told no story, and the "honest failure" post admitted no failure. Mechanical variety worked, but depth of ideas did not. A stronger model (not testable now, Gemini quota exhausted) is needed to judge that.
- It also slipped in "tackles up to 10 repos" (invented) and "seamlessly". Claims guard tightened: counts of repos, services, agents, tasks and models now need to be in the verified facts, and buzzwords are now blocking.
- The Gemini-backed publisher fallback is still a single static template. With the LLM down it will now refuse to repeat itself unattended instead of re-posting the same text.
- Several of the existing tests make real network calls, so suite time varies from about 20s to 4 minutes depending on load.

## 2026-10-10 — Gemini key swap and model check
- `.env`: the old free-tier `GEMINI_API_KEY` is commented out (marked "disabled"), and the new key is active. A backup of the previous `.env` is in the session scratchpad. `.env` is git-ignored. The key itself is not recorded anywhere in the repo or these logs.
- New key works: 45 models listed, and generation succeeds.
- **`GEMINI_MODEL=gemini-2.5-flash-lite` (the configured model) is NOT usable with the new key:** 404 "no longer available to new users". The same is true for `gemini-2.5-flash` and `gemini-2.5-pro`.
- Working models tested (all returned a correct reply): gemini-3.8-flash (18s, slowest), 3.6-flash, 3.5-flash, 3.5-flash-lite (1.5s), 3.1-flash-lite, flash-latest, flash-lite-latest (1.3s).
- `GEMINI_MODEL` was NOT changed yet; the model decision is pending. Until it is changed, direct calls that read `GEMINI_MODEL` (mentor goal check, social publisher) will 404 and fall back to templates. The `BaseAgent` provider has its own candidate list.
- **Model chosen: `gemini-3.5-flash-lite`.** `.env` `GEMINI_MODEL` updated, and the 3 hard-coded fallback defaults (assistant LLM, mentor, publisher) changed from the dead `gemini-2.5-flash-lite`. Verified live with the new key: assistant "yes" path returned a real Gemini reply (first confirmed success of that path), the mentor goal check returned real (non-fallback) advice, and the publisher generated a post from MATERIAL.md with the assigned angle. Suite: all tests pass.

## 2026-10-10 — Full marketing and sales agents on live Gemini (gemini-3.5-flash-lite)
**Result: all 5 agents run on real Gemini in 3–13s each. Final run: 0 blocking issues, 12 marketing posts + 20 social-first posts (10 LinkedIn, 8 Twitter, 2 articles), no repeated openings, no invented leads. 159 tests pass in ~4s.**

### Why long content generation had been failing (shared plumbing bugs, found by this run)
1. **`GeminiProvider` had a hard-coded 10-second HTTP timeout.** A 20-post campaign needs longer even on the fastest model, so every candidate timed out in turn until the pro model, whose free-tier quota is 0. That produced the misleading "429 quota" errors. Now 120s, configurable with `GEMINI_TIMEOUT_SEC`.
2. **Candidate model fallback list contained retired models** (`gemini-2.5-*` return 404 for this key). Replaced with working ones.
3. **Strict `json.loads`** crashed on Gemini's malformed JSON (trailing commas, an unquoted key `slug:`, a key missing its opening quote, raw newlines in strings). New `parse_json_lenient` repairs these. It is used by all gtm agents.
4. **The variety check silently saw 0 posts** when the social-first JSON didn't parse. It now parses leniently, uses JSON mode, warns when nothing could be parsed, and retries when the batch is short (marketing returned only 3 of 12 posts the first time).

### Checker improvements driven by real output
- Blocks invented links (`github.com/example/...`), and verified scores followed by a noun (`37.5/100 Benchmarks`) are no longer false positives.
- Unresolved `[Link]` placeholders are auto-stripped from marketing output; email agents now sign as a given sender name instead of `[Your Name]`.
- Targeting numbers in prospect profiles ("teams with 5+ repos") are not treated as product claims.
- Repeated-number and repeated-opener checks scale with batch size, and years and tiny integers are ignored.

### Test-suite hygiene
- Tests that depended on the LLM failing: 2 domain-adaptation tests only passed because the LLM calls failed and the synthetic fallback produced the expected text. They broke as soon as the key worked. `tests/conftest.py` now blocks real LLM network calls by default (`ASCM_LIVE_TESTS=1` re-enables them). Suite time went from 20s–4min to ~4s, and results no longer depend on the API key.
- The social publisher test wrote fake "published" posts into the repo's real `.ascm_history/` (9 entries, now deleted) and then correctly refused to repeat them. It now runs in a temp directory.

### Observed content quality
Posts now tell real stories from MATERIAL.md (the marketing agents that invented case studies, the daemon-crash bug, the `app-evil` path bug, phi4-mini's false "duplicate function"), cite the honest 37.5/100 baseline, and avoid hype. Sales output is ICP profiles + merge-field templates; real leads pass through; invented ones are discarded. Output varies per run: an earlier run was flagged for an unverified "100%", a later one was clean.

### Still open
- **The new Gemini key is also on the free tier** (pro models have a limit of 0), so pro-quality runs need billing enabled.
- **`ALLOW_SYNTHETIC_FALLBACK` defaults to on:** if the LLM fails, `BaseAgent` quietly returns a synthetic stand-in response instead of raising. This hides failures and should probably default to off for production.
- Assigned angles are only loosely followed by the model (post 3 drifted from its plan once). Not tested: posting to LinkedIn or X, Buffer, and the Gemini-backed publisher end to end in interactive mode.

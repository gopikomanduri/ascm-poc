# Founder session intelligence

ASCM's mentor now has a session-level review layer that keeps three concepts distinct:

- **Observed activity:** privacy-minimized signals from the configured filesystem/IDE, terminal, test, active-window, and browser adapters.
- **Inferred task:** a low-confidence hypothesis from activity correlation. It is not the founder's confirmed intent.
- **Founder goal:** the explicitly stored goal. The mentor does not silently overwrite it.

## What it does

- Summarizes recent signal coverage and highlights absent adapters without interpreting absence as inactivity.
- Compares the observed task with the stated goal using transparent concept groups plus lexical overlap; sparse descriptions are not enough to trigger a goal-drift challenge. This reduces obvious synonym false positives but is not a semantic model.
- Keeps public repository search results as research leads. A candidate is eligible for a reuse recommendation only after explicit founder review records feature fit, license compatibility, security review, and integration-cost estimate for that exact repository.
- Surfaces a goal-drift challenge when task/goal overlap is low and matching customer evidence is absent.
- Prioritizes inspecting the smallest failing slice when recent test failures or repeated failures are observed.
- Carries the alignment status, similarity, and active source types into recommendation audit metadata.
- Provides both helpful and not-helpful feedback commands for each delivered intervention; session reports can summarize feedback.

The mentor may still recommend customer validation, reuse review, simplification, or another decision path through the existing evidence-driven decision engine. Public repository search remains opt-in and candidates are research leads until fit, license, security, and integration cost are reviewed.

## Privacy and correctness boundaries

The session summary persists only counts, source labels, project identifiers, and opaque event IDs. It does not copy file contents, browser URLs, page text, raw shell commands, or test output into the review. Existing activity adapters remain opt-in where documented.

The goal-alignment score is a heuristic, not a semantic proof of intent. Different wording can describe the same work; matching wording can still be irrelevant. It must be presented as a hypothesis, never a fact. The founder's explicit correction takes precedence.

Coverage is limited to signals from installed and enabled adapters. A missing browser or terminal signal does not mean the founder was not browsing or using a terminal. Before claiming reliable cross-application understanding, run end-to-end sessions on supported macOS, Windows, and Linux environments and verify adapter/project attribution, stale-event rejection, opt-out, and notification suppression.

## Measuring whether advice helps

Each recommendation gets an intervention ID and working-session ID. Delivery confirmation is recorded separately from usefulness feedback. The notification offers `helpful` and `not_helpful` feedback commands and a session report command. Only explicitly rated, confirmed-delivered interventions qualify for the bounded feedback adjustments in the decision engine.

Session reports flag interventions that remain unrated after 24 hours for follow-up. They remain unreviewed—not automatically negative—and never count as success.

Do not claim that the mentor improves founder outcomes based on notification counts or self-reported ratings alone. Review session reports and conduct the 30-day real-session evaluation, including ignored/dismissed interventions, false positives, missed goal drift, and whether founders acted on the advice.

## Suggested manual acceptance run

For each supported desktop, use a disposable workspace and explicitly enable the relevant adapters. Perform a short sequence that includes an IDE/project activation, a file edit, a terminal test run, a passing and failing test result, and opt-in browser research. Confirm that events correlate to the correct project, old/future events do not affect the current review, raw content is absent from persisted summaries, and disabling an adapter stops its events. Record false-positive prompts and feedback rates. This checklist is not evidence that these platform runs have already been performed.

# ASCM Founder Intelligence Operating Loop

ASCM's product loop has four cooperating capabilities:

1. **Founder mentorship** frames the current goal, task, constraints, milestone, and decision to make. A missing founder-confirmed goal triggers clarification rather than inferred intent.
2. **GTM intelligence** evaluates recorded customer demand and optional public open-source candidates. Customer events are scoped to an explicit feature key when a task is evaluated. GitHub discovery remains opt-in because a task description is sent to a remote service when enabled.
3. **Engineering and governed execution** ranks build, reuse, simplify, customer validation, launch/sell, and pause/stop. Proposals and consent are recorded separately; recommendations do not execute code, contact customers, or publish campaigns.
4. **Outcome learning** records whether a delivered recommendation was helpful, accepted, acted on, dismissed, or incorrect. The decision engine can use those labels as a weak, bounded preference signal for future ranking.

## Feedback learning policy

The MVP reads `.ascm_history/intervention_quality.json` and considers only records whose delivery was confirmed and whose feedback is one of the six supported labels. It uses positive labels (helpful, accepted, acted_on) and negative labels (not_helpful, dismissed, incorrect).

- A path needs at least five rated, delivery-confirmed interventions before its feedback affects ranking.
- A Beta(2,2)-smoothed positive-feedback rate shrinks small samples toward neutral.
- The resulting score adjustment is capped at +/-6 points. Current evidence and hard missing-evidence checks remain primary.
- The engine returns `learning_adjustments_applied`, and each adjusted path explains the feedback count and adjustment.
- Unreviewed and delivery-unconfirmed attempts are not counted as success or failure.
- Feedback is not causal evidence, a calibrated probability, or autonomous model training. Review multiple sessions before changing the policy.

For deterministic operation, feedback remains local. The engine reads the workspace under `ASCM_WATCH_PATH` when set, otherwise the current working directory. Run the mentor from the project workspace or set `ASCM_WATCH_PATH` to the intended workspace so learning reads the right ledger.

## Close the loop during a real session

1. Confirm the goal and target customer; keep hypotheses separate from founder-confirmed facts.
2. Record verified customer evidence using the GTM outcome ledger, with a short non-sensitive `feature_key` where relevant.
3. Review the proposed action and approve any consequential execution explicitly.
4. Use the feedback command included with a delivered recommendation, for example:

   ```bash
   python -m orchestrator.mentor.evidence_pipeline --feedback helpful --intervention-id INTERVENTION_ID
   ```

5. Inspect outcomes by working session:

   ```bash
   python -m orchestrator.mentor.evidence_pipeline --report --session-id SESSION_ID
   ```

6. Compare the next recommendation's `learning_adjustments_applied` and rationale. A score shift is a small feedback-informed preference, not proof that the system made a better decision.

## Remaining release work

This closes the first feedback-informed ranking loop, not all commercial gaps. Fully automatic customer outcome ingestion still requires explicit, privacy-reviewed provider adapters; milestone detection remains partly explicit/operator-driven; the current JSON ledgers are single-process local MVP stores; and production execution requires identity-backed authorization, isolation, durable audit retention, and security review. The PR must remain draft until the current CI run and required security review are verified.

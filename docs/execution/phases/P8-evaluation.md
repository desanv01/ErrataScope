# P8 — Frozen evaluation and evidence of limitations

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W09](../packets/W09-evaluation-production.md).

## Scope, deliverables, and exit conditions

**Inputs:** frozen supported corpus, schemas, and model configuration.

**Tasks:** finalize independent ground truth, split development/held-out source groups, run automated extraction separately from human-assisted outcomes, evaluate deterministic rules/change impact, record latency/cost, inspect all dangerous errors, and fix regressions.

**Deliverables:** versioned evaluation report, raw result records, reproducible commands, failure examples, honest supported-scope statement.

**Exit gate:** no unexplained false “not applicable” outcome in the release fixtures; deterministic and change-impact gates pass; failed extraction remains in denominators; the report distinguishes pre-review model performance from post-review workflow performance.

**If blocked:** narrow claims and supported coverage, repair the issue, and rerun affected evaluation. Do not repeatedly tune on the held-out set while continuing to call it unseen.

## Execution ownership

Read the [dispatch status](../STATUS.md) and assigned packet. This phase document is not a worker dispatch. Each packet pins its baseline, writable paths, detailed steps, and checks. A phase can span packets and is complete only when all its exit conditions are evidenced.

## Required evidence

- Attempt-numbered worker handoff listing actual changed files and checks.
- Source/model/fixture provenance where used; explicit failed or skipped checks.
- Codex independent review with each exit condition marked supported, failed, or unresolved.
- Accepted baseline and any contract decision record before dependent work starts.

## Failure handling

Preserve partial outputs and diagnostic evidence. Do not broaden scope or weaken the phase gate to clear a blocker. Codex consolidates repair instructions and records the resulting phase state. Workers cannot mark this phase complete.

## Completion record

No accepted implementation evidence yet. Codex will add review references after execution.


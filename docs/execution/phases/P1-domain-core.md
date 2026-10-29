# P1 — Domain contracts and pure evaluator

Phase specification revision 1. **Implementation status: ACCEPTED — W02 review 02, 30 October 2026.** Codex owns phase acceptance.

Implementation packet(s): [W02](../packets/W02-domain-core.md).

## Scope, deliverables, and exit conditions

**Inputs:** frozen initial vocabulary and selected source examples.

**Tasks:** define Pydantic contracts for identities, scopes, facts, rules, coverage, traces, and assessments; implement pure typed evaluation and canonical hashes; define exact truth tables; reject unsupported expressions; preserve all selector dependencies.

**Deliverables:** versioned JSON schemas, synthetic fixtures, evaluator package, example trace, domain error catalog.

**Exit gate:** truth tables, missing/contradictory evidence, irrelevant unknowns, units, scope, exceptions, unsupported predicates, and deterministic replay pass meaningful tests. Dependency tests include short-circuited and missing selectors.

**If blocked:** reduce the supported predicate vocabulary and label unsupported entries. Never coerce uncertainty to false merely to complete the pipeline.

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

Accepted under [W02 review 02](../reviews/W02-review-02.md); [acceptance manifest](../../evidence/W02/ACCEPTANCE.json) freezes code/contracts/tests. 92 tests and 46 independent assertions pass. No production deployment or electrical verification is implied.


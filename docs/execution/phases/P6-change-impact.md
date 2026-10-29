# P6 — Document changes and new-entry impact

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W07](../packets/W07-change-impact.md).

## Scope, deliverables, and exit conditions

**Inputs:** two source versions or clearly labeled controlled fixtures; existing assessments.

**Tasks:** implement stable entry correspondence, additions/removals/renumbering, candidate semantic diffs, correspondence review, dependency invalidation, identity subscriptions, and freshness projections.

**Deliverables:** change-review view, impact list with reasons, preserved history, new-baseline reassessment.

**Exit gate:** a changed existing rule reopens dependents; a new erratum reaches a matching product with no previous edge; an unrelated product stays unchanged when correspondence is established; ambiguous matches remain pending; old decisions retain their original input bundle.

**If blocked:** conservative family-level review pending is acceptable with a reason. Silently marking an uncertain source baseline current is not.

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


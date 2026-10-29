# P4 — Product identity, evidence, and applicability

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W05](../packets/W05-product-assessment.md).

## Scope, deliverables, and exit conditions

**Inputs:** accepted rules and working evidence viewer.

**Tasks:** implement snapshot sealing, exact component identity, scoped facts/fact sets, review of facts, assessment input bundles, trace rendering, coverage-aware lists, and provisional preview versus accepted assessment behavior.

**Deliverables:** product snapshot view, assessment list, evidence workspace, deterministic replay command or API.

**Exit gate:** demonstrate applicable, not-applicable, missing revision, contradictory evidence, and incomplete coverage cases; changing a fact creates a new assessment without changing the old one; a declared fact stays visibly declared.

**If blocked:** reduce supported product configuration fields, preserving unknown values and scope. Do not approximate exact silicon revision from a family/BOM match.

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


# P5 — Requirement consistency and evidence requests

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W06](../packets/W06-evidence-requirements.md).

## Scope, deliverables, and exit conditions

**Inputs:** stable accepted assessments and scoped evidence.

**Tasks:** add versioned product requirements, restricted incompatibility relationships, explanatory supporting facts, evidence request ownership/resolution, and transparent prioritization.

**Deliverables:** conflict-under-supplied-facts panel, unresolved alternative, request lifecycle, reassessment after accepted evidence arrives.

**Exit gate:** a complete accepted argument reports a scoped conflict; removing its causal evidence yields unresolved; different scopes do not create a false conflict; resolving one request reopens all appropriate blocked assessments.

**If blocked:** ship an explicit unresolved evidence request instead of an invented engineering conclusion. No simulation or execution workaround is added.

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


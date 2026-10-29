# P10 — Release and submission package

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W10](../packets/W10-release.md).

## Scope, deliverables, and exit conditions

**Inputs:** accepted release candidate, evaluation report, stable deployment.

**Tasks:** finalize README/license/setup/source manifests, clarify newly built work and any reuse, prepare a public video under three minutes, provide testing instructions, model/provider feedback, chosen track, and submission fields; record the release commit and deployment version.

**Deliverables:** reviewable submission package and link checklist. Actual external submission is a separate authorized action; preparing it is part of the implementation plan.

**Exit gate:** repository, demo, and video links work without the developer's session; reviewers can reproduce the main result; claims match the evaluated release; the provider/model integration is visible and accurate.

**If blocked:** fix access or documentation before submitting. Do not claim submission occurred until the platform confirms it.

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


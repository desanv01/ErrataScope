# W10 — Release and submission materials

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P10](../phases/P10-release.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W09 accepted; repository/deployment publication permissions and final release baseline bound by Codex.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [domain-invariants](../contracts/domain-invariants.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md), [security-and-operations](../contracts/security-and-operations.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

README/license/provenance/setup/release documentation and designated demo-script/media-source paths. Codex exclusively owns Git/GitHub/publication/submission actions.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Prepare accurate README, setup instructions, runtime NVIDIA/Nebius explanation, supported corpus/limits, evaluation links, licensing/provenance, and reuse/new-work disclosure.

2. Prepare a concrete sub-three-minute video script and shot list showing the accepted application lifecycle, with true live/cached labeling. Actual video creation requires the appropriate authorized media workflow.

3. Prepare submission fields, recommended track, testing instructions, model/provider feedback, and links with secrets excluded.

4. Check accessible repository/demo/video links supplied by Codex; report missing resources without creating accounts or publishing independently.

5. Record release commit/deployment references supplied by Codex and final operational needs through judging. Do not claim submission happened.

## Required acceptance evidence

- **W10-G1:** Claims match accepted implementation/evaluation and model metadata.
- **W10-G2:** Setup and demo instructions work from a clean reviewer context.
- **W10-G3:** Required links/media exist and are accessible, or explicitly remain blockers.
- **W10-G4:** No credential leakage or unauthorized vendor-source redistribution.
- **W10-G5:** Codex records actual publication/submission outcome separately from prepared materials.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Fix missing access/materials and preserve draft status. Preparing a script is not completing a video; preparing fields is not submitting.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W10-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

## Codex dispatch binding — must be completed later

- Accepted baseline: UNBOUND.
- Exact writable paths: UNBOUND.
- Frozen contract/schema/API versions: UNBOUND.
- Required design artifact and human approval (where applicable): UNBOUND.
- Exact build/test/startup commands: UNBOUND.
- Provider/deployment budgets or publication scope: UNBOUND.
- Current packet-specific repair/compatibility notes: UNBOUND.

Do not infer readiness from this plan. Codex changes Dispatch state and fills these fields before issuing the exact start prompt.

## Next eligible work after acceptance

Codex-owned release/publication/submission actions within explicit human authorization.


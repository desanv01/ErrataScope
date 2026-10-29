# W08 — Complete approved workflow, exports, and replay

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P7](../phases/P7-workflow-export.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W06 and W07 accepted; approved imagegen-derived design brief covers all five views.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [data-and-versions](../contracts/data-and-versions.md), [ui-and-design](../contracts/ui-and-design.md), [security-and-operations](../contracts/security-and-operations.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

assigned frontend routes/components; export/replay backend; browser tests; documentation/evidence. Shared contract changes require Codex.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Complete the five connected views using the approved visual direction, real APIs, and consistent states. Add loading/empty/error/permission/concurrency states and keyboard navigation.

2. Implement authorized JSON and Markdown review packets with exact input versions, source/anchor references, coverage, traces, decisions, requests, evaluator version, and hashes.

3. Respect source redistribution/access rights; restricted original bytes are omitted with explicit references/limitations, not silently assumed present.

4. Implement clean-environment replay of a complete authorized assessment bundle without model calls. Preserve canonical result identity.

5. Run one actual browser journey from product selection through evidence/review/change/export, including a failed or unresolved state.

## Required acceptance evidence

- **W08-G1:** All five views operate against real backend behavior and match approved design.
- **W08-G2:** Export includes uncertainty and coverage, not only favorable results.
- **W08-G3:** Authorized complete bundle replays to the same canonical hash.
- **W08-G4:** Restricted/missing artifacts are disclosed and access controls hold.
- **W08-G5:** No placeholder action is presented as implemented.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Keep JSON/Markdown and basic printable view; postpone ornamental export layout. Do not omit reproducibility or uncertainty.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W08-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W09 with a frozen release-candidate baseline.


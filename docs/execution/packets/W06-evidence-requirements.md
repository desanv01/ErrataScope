# W06 — Evidence requests and restricted requirement consistency

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P5](../phases/P5-requirements.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W05 accepted; approved requirement representation and design extension.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [domain-invariants](../contracts/domain-invariants.md), [data-and-versions](../contracts/data-and-versions.md), [rule-language](../contracts/rule-language.md), [ui-and-design](../contracts/ui-and-design.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

backend requirements/evidence-request/review modules and assigned UI panels; focused integration tests and evidence.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Implement versioned product requirements and explicit accepted relationships connecting documented actions to supplied incompatibility evidence.

2. Report conflict-under-supplied-facts only for a complete scoped argument; missing causal evidence produces unresolved.

3. Create evidence requests keyed to missing selector and exact scope, with ownership, blocking items, candidate response, reviewed resolution, and history.

4. After accepted evidence resolves a request, reassess the appropriate items without overwriting old decisions.

5. Implement transparent request ordering from dependent items, declared severity, and effort; no probabilistic confidence claims.

## Required acceptance evidence

- **W06-G1:** Complete accepted argument produces a bounded conflict explanation.
- **W06-G2:** Removing causal evidence yields unresolved; differing scopes do not create a false conflict.
- **W06-G3:** Uploading a file alone does not close an evidence request.
- **W06-G4:** One accepted response reaches all appropriate blocked assessments.
- **W06-G5:** No execution, simulation, or model-generated behavior is introduced.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

An explicit unresolved request is preferable to invented causality. Do not add a simulator to fill evidence gaps.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W06-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W07 after preserving accepted W06 outputs and binding its baseline.


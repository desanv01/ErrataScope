# W07 — Source changes and newly added errata impact

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P6](../phases/P6-change-impact.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W05 data contracts and W06 shared-folder baseline accepted; authentic source pair or labeled synthetic fixture established.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [domain-invariants](../contracts/domain-invariants.md), [data-and-versions](../contracts/data-and-versions.md), [api-and-jobs](../contracts/api-and-jobs.md), [ui-and-design](../contracts/ui-and-design.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

backend comparisons/change-impact/subscriptions modules; assigned change-review UI; deterministic fixtures and tests/evidence.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Implement source identity/hash comparison, stable erratum correspondence, additions, removals, renumbering, and ambiguous matches.

2. Use model explanations only as candidate interpretation; require review for changed rules or uncertain correspondence.

3. Implement dependency invalidation for existing entries and product identity subscriptions for brand-new entries without prior edges.

4. Handle newly supplied missing facts and changes to short-circuited selectors. Preserve all previous baseline decisions.

5. Expose review reasons and conservative pending-family status when correspondence is unresolved; create new assessments only from accepted inputs.

## Required acceptance evidence

- **W07-G1:** Changed rule reaches dependents; new erratum reaches matching products with no old dependency.
- **W07-G2:** Renumbering alone does not fabricate a new defect and removal does not imply resolution.
- **W07-G3:** Unrelated products remain unaffected when correspondence is established.
- **W07-G4:** Ambiguous matches cannot clear freshness automatically.
- **W07-G5:** Old assessment replay remains identical after the new baseline.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Mark scoped baseline review pending with a reason; never let the model alone declare no material change and clear the review.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W07-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W08 once W06/W07 integration is accepted.


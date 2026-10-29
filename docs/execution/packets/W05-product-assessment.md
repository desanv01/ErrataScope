# W05 — Product snapshots, facts, and applicability workflow

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P4](../phases/P4-assessment.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W04 accepted; schema/API contracts frozen; visual approval available for this packet's UI.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [domain-invariants](../contracts/domain-invariants.md), [data-and-versions](../contracts/data-and-versions.md), [rule-language](../contracts/rule-language.md), [ui-and-design](../contracts/ui-and-design.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

backend products/evidence/assessments modules; approved product/assessment/evidence UI features; generated API client via the agreed generator; tests/evidence.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Implement exact component identity and product snapshot sealing, fact provenance/scope, immutable fact sets, and evidence acceptance.

2. Connect accepted rules and facts to pinned assessment bundles and the deterministic evaluator. Explicitly label provisional preview policy separately.

3. Implement product snapshot and assessment list behavior with independent coverage, applicability, review, and freshness dimensions.

4. Connect trace inspection to source passages and fact evidence. Missing or contradictory selectors must explain what is needed next.

5. Support new evidence/changed snapshot producing a new assessment while preserving the prior result and hashes.

## Required acceptance evidence

- **W05-G1:** Applicable/not-applicable/unknown/contradictory scenarios match accepted fixtures.
- **W05-G2:** A BOM family match cannot silently establish silicon revision.
- **W05-G3:** Declared/extracted/measured/external provenance remains visible.
- **W05-G4:** Changed evidence creates a new immutable assessment; prior replay is unchanged.
- **W05-G5:** The approved UI uses actual API data and exposes incomplete coverage.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Reduce supported product fields while preserving explicit unknowns; do not approximate identity or hide unavailable evidence.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W05-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W06, then W07 under the single-writer policy.


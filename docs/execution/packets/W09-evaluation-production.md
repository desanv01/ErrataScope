# W09 — Frozen evaluation and production acceptance

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P8](../phases/P8-evaluation.md); also [P9](../phases/P9-production.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W08 accepted; release-candidate baseline; Codex-bound hosting/account/cost authority and P9 acceptance scope.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md), [security-and-operations](../contracts/security-and-operations.md), [provider-and-sources](../contracts/provider-and-sources.md), [data-and-versions](../contracts/data-and-versions.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

evaluation fixtures/scripts/results, designated integration/browser tests, deployment/runbook configuration, scoped fixes explicitly authorized by Codex. No uncontrolled refactor.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Freeze source-grouped development/held-out cases and independently reviewed expected results. Keep near-variants of the same condition together.

2. Measure pre-review extraction separately from reviewed workflow outcomes; include unsupported/failed entries, coverage, unknown rate, false-not-applicable errors, and change-impact misses.

3. Record actual latency/usage/cost and deterministic replay results. Fix identified defects within the accepted repair scope and disclose any held-out contamination.

4. Exercise the approved hosted deployment, correct migrations/connection modes, authenticated access, private artifacts, provider limits, queue recovery, backup/restore, and clean install.

5. Check reviewer-accessible curated demo and browser journey; preserve evidence and exact deployment/configuration versions.

## Required acceptance evidence

- **W09-G1:** Raw evaluation results support claims; no hidden failure denominators.
- **W09-G2:** Release fixtures have no unexplained false-not-applicable or missed-new-entry failures.
- **W09-G3:** Hosted isolation, model integration, restart/recovery, and clean setup pass.
- **W09-G4:** Production readiness includes unresolved P2 hosting gates; missing account access stays visibly blocked.
- **W09-G5:** No UI redesign or scope expansion bypasses user approval.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Narrow supported claims and repair defects; do not falsify metrics, disable mandatory security, or call local-only evidence a hosted pass.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W09-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W10 after Codex accepts P8 and P9 and records known limits.


# W03 — Persistence, authorization, artifacts, and durable jobs

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P2](../phases/P2-foundation.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W02 accepted; Codex binds persistence schemas, local runtime, auth adapter strategy, and API prefix.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [data-and-versions](../contracts/data-and-versions.md), [api-and-jobs](../contracts/api-and-jobs.md), [security-and-operations](../contracts/security-and-operations.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

backend API/auth/storage/jobs modules, migrations, local container/config templates, integration tests, evidence/handoff. Dependency manifests and migration ownership must be explicitly bound. No UI.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Implement relational ownership/version records and migrations around accepted domain types. Add transaction and uniqueness constraints for sealed versions, idempotency, and reviews.

2. Implement project membership, scoped service/database authorization, artifact authorization, and fail-closed hosted configuration. Loopback-only development identity is visibly separate.

3. Implement storage abstraction, durable job/attempt/outbox/event records, dispatch/reconciliation, and attempt-token protection. Broker remains a scheduler, not authoritative state.

4. Expose a thin API to create a project, store an artifact, enqueue a harmless job, and retrieve ordered status/results.

5. Create reproducible local startup/health commands. Perform only the hosted actions expressly bound by Codex; no account provisioning or spend by implication.

## Required acceptance evidence

- **W03-G1:** Clean database migration/startup and project/artifact/job flow work.
- **W03-G2:** Cross-project access is denied, including artifact URLs.
- **W03-G3:** Duplicate submissions and review races behave correctly.
- **W03-G4:** Worker restart/outbox redispatch preserves committed results without duplicates.
- **W03-G5:** Deployment prerequisites are recorded; any hosted P2 gate still untested remains open.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Resolve one local/host path. Private hosted uploads stay disabled until auth/storage checks pass. Do not add an unapproved alternate database.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W03-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W04; Codex must obtain the human's UI/imagegen approval before any interpretation-review UI work.


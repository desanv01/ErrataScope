# W04 — Source ingestion, live model drafts, and interpretation review

Packet revision: **2**
Dispatch state: **READY_TO_DISPATCH**
Dispatched portion: **backend only**, worker attempt **01**.
Phase: [P3](../phases/P3-ingestion.md). Full W04/P3 acceptance is not implied by backend completion.
Starting baseline: [W04-backend-v1-baseline.json](../baselines/W04-backend-v1-baseline.json).
Accepted predecessor: W03 local commit `99090c6aed74c0378eeae02860f33027b9cbca2d`, tag `w03-local-accepted`, [review 05](../reviews/W03-review-05.md).

## Required reading and executable assignment

Read [worker rules](../WORKER_RULES.md), [status](../STATUS.md), the complete [ingestion-v1 binding](../bindings/W04-ingestion-v1.md), [W01 freeze](../bindings/W01-observed-contracts.md), [W02 freeze](../bindings/W02-observed-contracts.md), [W03 freeze](../bindings/W03-observed-contracts.md), [data/version](../contracts/data-and-versions.md), [API/jobs](../contracts/api-and-jobs.md), [rule language](../contracts/rule-language.md), [security](../contracts/security-and-operations.md), and [testing](../contracts/testing-and-acceptance.md) contracts. The binding supplies exact source, writable paths, dependency pins, migration, routes, budgets, stages and verification commands.

Use [this exact start prompt](../prompts/W04-START.md). Verify the protected baseline and [starting inventory](../reviews/W04-starting-inventory.json), claim the single-worker lock, and back up the starting implementation. Do not run historical W03 repair assignments. Existing accepted evidence, W01 ledger and applied migrations remain immutable.

## Backend sequence

1. Install the bounded additive parser lock without changing base pins. Add forward migration 0004 and typed source/anchor/coverage records with project ownership and immutable history.
2. Implement durable source extraction using accepted W03 storage/jobs and the bounded genuine ES0620 subset. Preserve identity, table/footnote context, located geometry, selected scope and explicit failures.
3. Implement the Nebius adapter using W01's working no-thinking request shape, strict draft validation, private case-bound evidence and reservation-before-dispatch accounting. Offline failures first; then at most two separately bounded W04 live cases. Never reset W01 accounting.
4. Add explicit source-grounded conversion proposals and append-only authorized reviews. Accepted rules require all unchanged W02 invariants. Model draft validity is not human semantic approval.
5. Run real local integration, negative cases, existing regressions, fresh main-store sentinel and restart/duplicate/cancellation checks. Record partial/blocked gates honestly; preserve historical missing artifacts.

## Original packet gates retained

| Gate | Required result | Current dispatch coverage |
|---|---|---|
| W04-G1 | Real source to live draft to authorized human review to accepted rule | Backend mechanism and actual live evidence; final real semantic approval is Codex's decision |
| W04-G2 | Conditions resolve to exact source version/anchor context | API/CLI provenance and geometry now; UI highlighting later |
| W04-G3 | Unsupported/failed/unselected entries visible in coverage | Backend coverage/API now; UI later |
| W04-G4 | Model/parser failures cannot activate rules or disappear behind success | Required backend acceptance |
| W04-G5 | Approved UI matches brief and works against real API | NOT_RUN — UI/imagegen PENDING |

The [UI gate](../UI_APPROVAL_GATE.md) remains binding. No screen, shell, styles or frontend is authorized. Backend acceptance may be recorded separately; do not mark full W04/P3 complete by omitting UI. W05 remains unbound until Codex records exact prerequisites and scope.

## Handoff

Write `docs/execution/handoffs/W04-attempt-01.md` using [the template](../templates/HANDOFF.md). Include baseline/inventory checks, changed files, actual tests/exits, source/claim provenance, synthetic/mock/cached/live distinctions, all paid reservations and remaining caps, volume/sentinel results and unresolved semantic/UI/hosted work. Stop owned services retaining volumes, release your lock and stop editing. Return the [exact Codex review prompt](../prompts/W04-START.md). No Git, acceptance declaration, parallel agents or future packet work.

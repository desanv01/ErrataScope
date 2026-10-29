# W04 — Source ingestion, live model drafts, and interpretation review

Packet revision: **1**
Dispatch state: **PLANNED_NOT_DISPATCHABLE**
Phase: [P3](../phases/P3-ingestion.md)
Starting baseline: **UNBOUND — Codex must issue before work starts.**

## Prerequisites

W03 accepted; W01 provider path remains valid; accepted domain/API contracts. UI portion additionally requires UI_APPROVAL_GATE explicitly approved.

Required shared reading: [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [provider-and-sources](../contracts/provider-and-sources.md), [data-and-versions](../contracts/data-and-versions.md), [api-and-jobs](../contracts/api-and-jobs.md), [ui-and-design](../contracts/ui-and-design.md), [testing-and-acceptance](../contracts/testing-and-acceptance.md).

Human visual approval remains a separate prerequisite for all application UI work. See [UI approval gate](../UI_APPROVAL_GATE.md).

## Planned ownership

backend sources/extraction/rule-review modules; approved UI interpretation/source-viewer feature paths only after visual approval; relevant tests/evidence. Exact dependency and UI paths bound before dispatch.

No worker Git mutations, shared-plan edits, independent dispatch, or acceptance-status changes. Existing accepted code must be inspected before implementation; generated code is not assumed correct.

## Implementation sequence

1. Promote proven spike behavior into source ingestion, immutable bytes, inventory, anchors, coverage, parser provenance, and bounded worker execution.

2. Implement the actual Nebius adapter with approved current model/limits, redacted artifacts, usage accounting, explicit cache/live state, schema validation, and anchor verification.

3. Persist draft interpretations and append rule review actions tied to exact hashes. Schema-valid drafts cannot become accepted automatically.

4. Implement the user-approved source/interpretation review screen and source highlighting. If visual approval is pending, a separately scoped backend-only dispatch may proceed; full packet acceptance remains pending.

5. Exercise invalid JSON, nonexistent anchors, table/footnote ambiguity, prompt-injection source text, truncation, provider failure, and review race paths.

## Required acceptance evidence

- **W04-G1:** Real source → live draft → authorized human review → accepted rule works.
- **W04-G2:** All displayed conditions resolve to the correct source version and anchor context.
- **W04-G3:** Unsupported/failed entries remain visible in coverage.
- **W04-G4:** Model and parser failures cannot activate rules or disappear behind a success badge.
- **W04-G5:** Approved UI matches the design brief and works against the actual API.

Tests must check behavior, not merely mirror implementation. Codex binds exact command lines against the accepted predecessor code before dispatch. At minimum provide focused checks for the behaviors above and one connected flow when applicable. Record actual exit codes and artifacts; no claim that an unrun command passed.

## Failure response

Narrow to the proven source subset; retain explicit failures. No hand-authored output presented as live inference and no unapproved UI design.

Complete independent in-scope work and report the blocked dependency. Do not silently waive gates, change the stack, or add work from later packets.

## Required handoff

Write `docs/execution/handoffs/W04-attempt-NN.md` using [the template](../templates/HANDOFF.md). Record starting baseline, changed paths, exact checks/results, gate evidence, mocks/synthetic/live distinctions, deviations, and unresolved issues. Stop editing and release your own worker lock before returning to Codex.

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

W05 after the connected workflow and required review gates pass.


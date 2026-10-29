# P9 — Production acceptance and recovery

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W09](../packets/W09-evaluation-production.md).

## Scope, deliverables, and exit conditions

**Inputs:** release-candidate application and P8 evidence.

**Tasks:** exercise the hosted user journey, authorization boundaries, private artifacts, model budgets, queue recovery, failed provider calls, migrations, clean install, backup/restore, and mobile/keyboard review essentials. Verify actual runtime model/provider metadata.

**Deliverables:** deployment/runbook, known limitations, operational configuration, release acceptance record, stable demo URL.

**Exit gate:** the clean hosted demonstration and local reproduction both work; worker interruption cannot lose accepted work; repeated requests cannot create conflicting accepted results; demo access and spending limits behave as documented.

**If blocked:** disable only the failing optional capability and document it. Core grounding, access control, runtime eligibility, and the main review/change lifecycle cannot be waived.

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


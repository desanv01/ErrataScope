# P2 — Persistent foundation and thin deployment

Phase specification revision 1. **Implementation status: READY — W03 revision 2 local backend scope bound; worker not started. Hosted/UI exit conditions remain open.** Codex owns phase acceptance.

Implementation packet(s): [W03](../packets/W03-persistence-jobs.md), [W09](../packets/W09-evaluation-production.md).

## Scope, deliverables, and exit conditions

**Inputs:** stable core contracts.

**Tasks:** scaffold application packages and migrations; implement project authorization, artifact storage, job/outbox/attempt state, idempotency and event polling; configure local containers; create minimal frontend shell through the required design workflow; deploy a thin authenticated slice when hosting is authorized/available.

**Deliverables:** clean startup instructions, migrations, health checks, project/document/job APIs, role checks, local and hosted configuration templates, CI baseline.

**Exit gate:** a clean environment can create a project, store a private artifact, enqueue a harmless job, restart a worker, and retrieve the result; another project/user cannot access it; retries do not duplicate accepted artifacts.

**If blocked:** resolve one deployment path rather than supporting several providers at once. Use local artifacts for development while preserving the storage interface; private hosted uploads remain disabled until auth/storage gates pass.

## Execution ownership

The earlier master phase mentions a minimal UI shell. The human's 29 October instruction now gates all application UI behind research, imagegen mockups, and explicit approval. W03 implements the non-UI foundation; do not start a UI shell until [the approval gate](../UI_APPROVAL_GATE.md) is satisfied. Backend progress does not waive the remaining phase deliverables.

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


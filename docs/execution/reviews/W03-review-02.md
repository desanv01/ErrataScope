# W03 review 02 — storage repair required

Codex independent review, 30 October 2026. W03 revision 2 repair 01, worker attempt 02.
Decision: **CHANGES_REQUESTED. W03 is not accepted; W04 remains unbound.**
Next action: [repair 02](W03-repair-02.md), worker attempt 03, [exact prompt](../prompts/W03-REPAIR-02.md).

## Verified progress

- Repair-01 protected baseline passed before and after runtime checks, before Codex dispatch changes: **235 hashes / 294 links**. All **43** attempt-01 backup bytes independently match their inventory. Accepted W01/W02 remain protected and unchanged; all **92 domain tests pass**.
- Actual image source comparison: **38 Python files**, zero differences, covering service/domain/migrations/W03 tests. Main PostgreSQL migration is **0002_staging**. Applied 0001 and dependencies are unchanged.
- All **82 W03 tests pass** when run with `-e W03_ARTIFACT_ROOT=/tmp/w03-review-tests` in the test container. This override was necessary to avoid the shared-volume defect below. The first ordinary test run was stopped after discovering that defect and is not counted as a pass.
- Re-ran the [previous independent HTTP checker](W03-review-01-checks.py), with output redirected to the new review folder: **22/22 pass**. Actual API membership/replay denial, bound routes, nested errors, server UUID, concurrent upload convergence, pagination, real worker receipt and expired-heartbeat/cancellation assertions pass. [Results](W03-review-02-observations.json).
- Re-ran the [previous independent fault checker](W03-review-01-fault-checks.py): **8/8 pass**. Real PostgreSQL rejection cleans up; an exception raised immediately after actual successful `Session.commit()` preserves the original receipt, including on redelivery. [Results](W03-review-02-fault-observations.json).
- Connected `verify-foundation` passes **11/11** against actual API/worker/DB/broker. Runtime configuration confirms migrator DSN absent from api/worker/dispatcher and present only for migrate/test. JWT allowlist and membership/pagination repair tests pass.
- Worker attempt-02 crash/restart evidence was inspected. Its recovery script was not independently rerun: it overwrites attempt-02 outputs and the independently reproduced cleanup/finalization failure already blocks acceptance. Do not describe this as independent confirmation of the full crash matrix.

## Remaining blockers

### R1 — database/storage ownership is not isolated

`infra/w03/compose.yaml` points the test database at `erratascope_test` but mounts the same artifact volume/root used by the application's `erratascope` database. `reconcile_orphans()` scans that whole root using only its current database references. Thus a valid application file looks unreferenced to the test collector, and vice versa. Resetting the test database makes this worse.

Confirmed in a **new temporary directory**, using two genuinely separate PostgreSQL engines: bytes committed in one database were removed by the other database's collector. No application files were deleted by this isolated probe. The initial checker accidentally reused the service's process-global factory; it was corrected to use a separate engine and assert the second database name. The initial result is preserved privately and is not evidence for this finding.

The ordinary shared-storage suite had already been started when this defect was identified; Codex stopped it, then reran safely with an isolated root. A later read-only audit found **41/48 main artifact rows unreadable**. There is no pre-review byte inventory, and earlier reviews deliberately created some broken synthetic artifacts. Therefore neither the time nor cause of each missing file can be attributed to this run. The audit preserves IDs and error codes privately at `.local/reviews/W03-review-02/runtime-audit.json`. Named-volume preservation does **not** establish byte integrity. Do not silently restore or mint replacement evidence and call the historical receipt intact.

### R2 — cleanup can race receipt finalization

The new journal has a fixed staging lease, independent of the executing job's renewed lease. The collector deletes files of expired journal rows immediately, ignoring `grace_seconds` for that branch. Worker finalization fences the job but does not lock/revalidate staging ownership and byte integrity against that cleanup decision.

Independent controlled-timing probe: expire the receipt's staging lease at the actual pre-commit fence, collect using a fresh real PostgreSQL transaction, then allow execution to continue while its job lease remains valid. Observed: **job succeeded, artifact row committed, receipt unreadable**. This is a different failure from acknowledgement loss, which now passes.

A separate probe created fresh staging bytes with an expired lease and a one-hour grace; cleanup removed them immediately. Upload staging also lacks renewal during a slow stream. Repair the ownership/finalization protocol for both uploads and worker receipts. Examine cleanup calls that open a fresh session while the caller still holds the same staging-row lock; ensure all failure paths release locks and finish without self-blocking.

### R3 — path classification/checking is too permissive

- A new unknown `notes/keep.bin` file was deleted by orphan reconciliation. The classifier accepts arbitrary two-part `.bin` paths and everything under `.staging`, instead of exact generated UUID layouts.
- An internal symlink under `.staging` was followed successfully. `_path()` and `_check_components()` resolve paths before checking components, hiding the symlink. The existing external-symlink test passes because it escapes the root; it does not establish the required no-symlink property within the root.

These were reproduced only in newly created temporary storage. [Checker](W03-review-02-storage-checks.py), [observations](W03-review-02-storage-observations.json). Five safety assertions fail; one assertion confirms fault injection ran. These counts are targeted boundary probes, not an overall quality score.

## Decision and resource state

| Area | Decision |
|---|---|
| Repair-01 R1 current auth and R2 API contract | Verified positive; retain fixes and regressions |
| G1 migrations/domain persistence | Positive local evidence; preserved accepted domain |
| G2 private artifact safety | **FAIL** — storage ownership, lifecycle and paths |
| G3 idempotency/reviews | Positive replay/convergence/race evidence retained |
| G4 durable recovery | **FAIL** — GC/finalization race; prior acknowledgement-loss defect fixed |
| G5 hosted prerequisites | Documentation only; hosted P2 **NOT_RUN** |
| UI/imagegen | **PENDING**, no UI authorized |

No product source was edited by Codex. New synthetic review records were added; new fault probes used temporary storage. Worker evidence is preserved. Review-owned outputs live in `.local/reviews/W03-review-02/` with sanitized observations copied here. Services started for review were stopped; both existing named volumes retained, with the byte-integrity limitation above. No provider calls, credential search, hosted work, UI or W04 implementation.

No W03 completion commit/push or W04 binding. Latest accepted checkpoint remains W02 `210e606925e1a630b302a2d4c63da29268a15ce5` / `w02-accepted`. After repair acceptance Codex performs the Git/GitHub checkpoint and supplies the next bound prompt.

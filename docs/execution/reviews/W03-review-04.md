# W03 review 04 — prior repairs verified; descriptor lifecycle repair remains

Codex independent review, 30 October 2026. W03 revision 2 repair 03, worker attempt 04.
Decision: **CHANGES_REQUESTED** for one remaining resource-lifetime defect. W03 not accepted; W04 unbound.
Next action: [repair 04](W03-repair-04.md), [exact worker prompt](../prompts/W03-REPAIR-04.md), attempt 05.

## Verified results

- Repair-03 baseline passes before and after runtime checks: **266 hashes / 320 links**. **63/63** attempt-03 backup files verified. **50/50** accepted domain file hashes preserved; W01 frozen evidence protected and unchanged. No active worker lock.
- Deployed image matches **43 Python source/test/migration files**, zero differences. Actual PostgreSQL head is **0003_staging_fencing**; applied migrations and dependency pins unchanged.
- **101 W03 integration tests pass** on actual PostgreSQL/Valkey with physically separate test storage. Fresh main artifact/receipt sentinel survives isolated test reset/GC with identical bytes. **92 domain tests pass**.
- Independent prior HTTP/replay checker: **22/22 pass**; actual DB rejection/post-commit acknowledgement-loss checker: **8/8 pass**. Connected verify-foundation: **11/11 pass**. Reports linked below.
- Independently adapted prior boundary checker to the new descriptor API (previous checker remains unchanged). **All 11 prior-boundary assertions pass**: expired upload without GC is 409, unknown file survives, static symlink rejected, actual parent-swap delete stays confined, newline key rejected, actual mismatched session with omitted or forged hint refused, and receipt GC race preserves readable result. Two assertions confirm fault injection executed.
- Independently executed the worker crash/restart flow using a copied wrapper with review-owned paths. Actual crash exit **43**, recovery on **attempt 2**, ordered events, exactly one succeeded event, matching receipt digest, and retrieval after API restart all pass. Worker recovery script/evidence was not overwritten. Wrapper and logs are under `.local/reviews/W03-review-04/`.
- Current audit: **94 main rows, 41 unreadable**, with unreadable IDs matching the legacy audit exactly. Audit ran before final connected-flow additions. Historical loss remains explicit; fresh successes do not restore old files or prove past integrity.

## Remaining defect — pinned descriptors are not released

The new directory-relative operations fix the path redirection issue. They also introduce raw directory descriptors that require explicit closure.

Actual `jobs.verify_receipt()` was called **12 times** for a valid real-DB receipt in a disposable store. After forced Python garbage collection, **12 additional descriptors still pointed to that store root**. This is ordinary successful verification, without failure injection. `verify_receipt()` constructs a store and closes its DB session but never closes the store. The same ownership omission appears in `execute()`, `_settle_after_exception()` and `reconcile_once()`. The dispatcher repeatedly calls reconciliation and receipt verification, so usage grows with normal background work. We did not exhaust process limits or claim a measured time to failure.

Bounded error-path probes confirmed three additional cleanup omissions, each leaving **8 additional descriptors after 8 calls**:

1. Store construction rejected for mismatched identity leaks the root fd opened before marker validation.
2. Rejected symlinked staging project leaks the intermediate `.staging` fd when `_open_dir()` raises.
3. Duplicate staging-file creation leaks the pinned project fd when exclusive `os.open()` raises.

These are one consolidated lifecycle repair. The prior assignment explicitly required reliable descriptor closure; no new feature or architecture is requested. Keep the passing confinement behavior and add structured ownership/cleanup.

## Evidence and outcome

- [Boundary checker](W03-review-04-boundary-checks.py), [boundary results](W03-review-04-boundary-observations.json): 11 prior assertions pass; successful verification handle-release assertion fails (growth 12).
- [Failure-path handle checker](W03-review-04-handle-checks.py), [handle results](W03-review-04-handle-observations.json): three cleanup failures, growth 8 each. Only temporary files touched.
- [HTTP results](W03-review-04-observations.json), [fault results](W03-review-04-fault-observations.json), [connected flow](W03-review-04-connected-verification.json), [sentinel](W03-review-04-sentinel.json), [recovery](W03-review-04-recovery.json), [recovery receipt](W03-review-04-recovery-restart.json), [API restart](W03-review-04-recovery-api.json).

Repair-03 R1/R2/R3 behavioral boundaries are verified. Local G1/G3 and functional recovery evidence are positive; G2/G4 remain incomplete because steady-state storage/reconciliation leaks resources. G5 remains hosted-prerequisite documentation only; hosted P2 **NOT_RUN** and UI/imagegen **PENDING**.

No product source changed by Codex. All current worker implementation/evidence bytes are inventoried for the next repair. Services started for review are stopped; pgdata/artifacts/test_artifacts volumes retained. No provider calls, real credential search, hosted work, UI or W04 implementation. No W03 completion Git/GitHub checkpoint; latest accepted checkpoint remains W02 `210e606925e1a630b302a2d4c63da29268a15ce5` / `w02-accepted`.

# W03 review 03 — remaining lease, ownership and path boundaries

Codex independent review, 30 October 2026. W03 revision 2 repair 02, worker attempt 03.
Decision: **CHANGES_REQUESTED. W03 not accepted; W04 remains unbound.**
Next action: [one consolidated repair 03](W03-repair-03.md), [exact DeepSeek prompt](../prompts/W03-REPAIR-03.md), worker attempt 04.

## Verified progress

- Repair-02 protected baseline passes before/after runtime review: **251 hashes / 307 links**. **53/53** starting backup files independently match inventory. All **50** accepted W02 file hashes remain unchanged; W01 protected evidence unchanged.
- Current image matches **42 Python files**, zero differences. Actual application migration is **0003_staging_fencing**; applied 0001/0002 remain protected.
- Independent rerun: **93 W03 tests pass**, including the main artifact/receipt sentinel through isolated test reset/GC. **92 accepted domain tests pass**.
- First suite run encountered expired synthetic local development tokens (401). Refreshed only those three tokens with the same existing designated test signing key, preserving the old tokens privately and printing no values. The rerun passed. This environmental failure is not counted as a product defect or a passing run.
- Previous independent API checker: **22/22 pass**, [results](W03-review-03-observations.json). Previous actual PostgreSQL rejection/post-commit acknowledgement-loss checker: **8/8 pass**, [results](W03-review-03-fault-observations.json). Main DB operations explicitly used its matching application storage mount.
- Connected verify-foundation: **11/11 pass**, [results](W03-review-03-connected-verification.json).
- Independent controlled receipt-stage expiry/GC probe now preserves a readable successful receipt. Unknown files and static internal symlinks are handled correctly. These fix the main previous failures.
- Worker crash/restart evidence for attempt 03 inspected; recovery script not independently rerun because it overwrites worker evidence and the remaining boundary defects already block acceptance. No claim that all crash scenarios were independently revalidated this turn.

## R1 — expired upload ownership silently revives

`api.py::renew_staging()` updates any active row without requiring its existing lease to be current. Finalization calls it immediately before checking expiry, so that check sees a newly extended lease.

Controlled real-DB reproduction: after the upload file finishes, set that upload's lease ten seconds in the past, then let finalization continue without first deleting the row. Response is **201**, whereas the protected repair requires a bounded **409** for expired upload ownership. The worker's existing test first runs GC, removing the row; it does not cover expiry alone. No data-loss claim is made for this specific probe; this is a confirmed failure of the agreed stale-writer boundary.

## R2 — collector identity check can be bypassed by omission

`reconcile_orphans(..., database_identity=None)` does not derive the identity of its actual session. `store.assert_identity(None)` checks only that the store has some marker. The default call therefore accepts a different real database session.

Independent reproduction uses a new temporary store with an artifact registered in the test database, and a separately created engine connected to the application database. Calling the collector without the optional identity hint deletes that committed file. All bytes were disposable probe files; application artifact volume was untouched by this probe.

The normal dispatcher currently supplies the intended settings identity, and the new default test root is physically isolated. Those improvements remain valid. The callable collector still fails its required fail-closed boundary; its existing test passes a fabricated string mismatch, rather than checking the actual session. Check the actual bind/database, and do not let an optional caller assertion establish ownership.

## R3 — path checks do not pin directories

`_checked_path()` validates components but returns a pathname. Later operations use that pathname again. `O_NOFOLLOW` on the final file does not prevent following a replaced parent directory.

Controlled filesystem reproduction: immediately after the path check, rename the checked project directory and replace it with a symlink to another disposable directory. `store.delete()` deletes the external sentinel file. This is an actual deletion in an isolated temporary tree under a deterministic timing hook, not a demonstrated remote exploit. The protected repair explicitly requires avoiding a check/use redirection race for storage operations.

Additionally, regex `.match()` with `$` accepts a canonical-looking key followed by a newline. Exact layouts require full-string matching. The store root is also resolved before checking `is_symlink()`, hiding a symlink in the configured root; include the root in the same confinement repair.

[Independent boundary checker](W03-review-03-boundary-checks.py), [results](W03-review-03-boundary-observations.json): five positive assertions and five failed assertions across these three issues. Two positives confirm fault injections executed. These are focused probes, not a quality score.

## Historical bytes and resources

The worker correctly records the historical **41 missing** artifact rows without replacements. This review's read-only audit found **72 rows, 41 missing**; the missing artifact IDs exactly match the worker's legacy audit. Fresh sentinel objects survived isolated test reset/GC. No claim is made about when or why those historical losses occurred. The audit ran before the final connected flow added its additional fresh objects.

No product source was edited by Codex. Test token refresh affected only designated local synthetic configuration. Reviewer outputs are under `.local/reviews/W03-review-03/`; token values/history remain private. Services started for review were stopped and all three named volumes retained. No provider requests, real credential access, hosted provisioning, UI or W04 work.

## Gate decision

| Area | Decision |
|---|---|
| G1 migrations/domain | Positive local evidence retained |
| G2 auth/private artifacts | **FAIL** — actual-session ownership and filesystem confinement |
| G3 idempotency/reviews | Positive 22-check API evidence retained |
| G4 durable recovery | Original receipt GC race and ack-loss checks pass; **PARTIAL** pending stale upload/path safety |
| G5 hosted prerequisites | Documentation only; hosted P2 **NOT_RUN** |
| UI/imagegen | **PENDING** |

W03 completion Git/GitHub checkpoint and W04 binding await acceptance. Latest accepted checkpoint remains W02 `210e606925e1a630b302a2d4c63da29268a15ce5` / `w02-accepted`.

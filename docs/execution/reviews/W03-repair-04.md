# W03 repair 04 — close owned storage descriptors

**READY_TO_DISPATCH. W03 revision 2, worker attempt 05.** One focused resource-lifetime repair. All three previous behavioral boundaries are independently verified; retain them.

Read [review 04](W03-review-04.md), [repair 03](W03-repair-03.md), [packet](../packets/W03-persistence-jobs.md), [foundation binding](../bindings/W03-foundation-v1.md), and [worker rules](../WORKER_RULES.md).

## Preflight and scope

Require no worker lock or existing W03-attempt-05 handoff. Run `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-04-baseline.json`; require PASS. Verify every [attempt-04 inventory](W03-attempt-04-inventory.json) hash, claim the lock exclusively, back up all paths under `.local/w03/history/attempt-04-before-05/` and verify a SHA/size manifest. Do not overwrite history.

Use the original W03 writable service/tests/infra/evidence/local paths plus your own lock and new handoff. Codex plans/status/contracts/reviews/checkers/baselines, accepted W01/W02 code/tests/evidence, pins and applied migrations 0001–0003 remain read-only. No schema/stack changes are expected. Keep the isolated test DB/volume. Preserve main data, sentinel evidence and the historical 41 missing rows/events. No provider, `.env.local`, real credentials, Git, hosted, UI, W04, or delegation.

## R1 — explicit descriptor ownership on every path

1. Give ArtifactStore a deterministic lifetime (e.g. context manager plus idempotent close). Do not rely on garbage collection or process exit. Close the root fd if initialization fails after opening it, including marker mismatch/invalid marker/subdirectory setup errors.
2. Adopt that lifetime at every production owner: receipt verification, execute, exception settlement, reconciliation, CLI adoption/other one-shot commands, and the FastAPI application's lifespan. Close the app-owned store at application shutdown, not after each request. Ensure construction/early-return/exception paths also release what they own. Shared borrowed stores must not be closed by consumers.
3. Make `_project_fd` exception-safe: close intermediate staging directory fds whenever opening/creating the project fails. If a test hook raises after a project fd is opened but before ownership is returned, release it. Keep O_DIRECTORY/O_NOFOLLOW and directory-relative operations intact.
4. Make StagingUpload construction exception-safe if exclusive file creation, wrapping a file descriptor, or a hook fails. Close its pinned parent and any opened file exactly once. Preserve finish/promote/abort semantics and ensure promotion errors before the existing try block do not strand handles. Successful finish may retain the parent until promotion/abort; that intentional open lifetime is not a leak.
5. Audit descriptor ownership in identity-marker helpers and directory enumeration too. Idempotent cleanup must not accidentally close a descriptor number already reused elsewhere. Close borrowed/owned resources according to a clear contract rather than adding broad blanket-close code.

## Focused evidence

- Real database receipt: repeatedly call successful `jobs.verify_receipt()` after warm-up, measure `/proc/self/fd` entries targeting the test store, and require no growth. Preserve readable identical receipt bytes/ID/hash. The review observed +12 after 12 calls.
- Repeat actual `reconcile_once` in one process with real DB/store and a valid receipt. Require stable descriptor counts after each completed pass. Include early return, missing/corrupt receipt, cancelled/stale execute and settlement exception paths as relevant; no repeated success may accumulate handles.
- Repeat constructor identity mismatch, malformed marker, rejected staging symlink, and duplicate staging create. The confirmed three error paths each leaked +8 after 8 calls. Assert both bounded descriptors and preserved sentinel bytes/confinement. Include bounded hook/open failures and double-close safety.
- Verify application startup/shutdown releases its store root. Do not merely test close() directly while production callers still omit it.
- Test actual Linux descriptors, not mocked resource counters; use new disposable stores and the isolated test DB. Avoid exhausting process limits or long soak tests. Capture pre/post counts and file integrity. No skipped required cases.

Run all 92 accepted domain tests unchanged and all 101 current W03 tests plus the new regressions. Retain expiry-without-GC, actual-session omitted/forged-hint, parent-swap, isolated main sentinel, API/current-auth/replay, acknowledgement-loss and receipt-GC assertions. Run connected verify-foundation and bounded crash/restart recovery with **attempt-05** seed/evidence filenames. Do not overwrite attempt-01–04 outputs. No new features or unrelated hardening work.

If synthetic local test JWTs expire, use the existing designated test key/JWKS to refresh only local test tokens with private history, without printing values. Do not weaken expiry checks or rotate real credentials.

Update IMPLEMENTATION_REPORT and README lifetime notes with commands/exits, before/after handle counts, retained behavioral checks and legacy-loss limits. Recheck the repair-04 baseline. Write `docs/execution/handoffs/W03-attempt-05.md`, stop owned services/jobs retaining volumes, release your lock and stop editing. READY_FOR_REVIEW/PARTIAL/BLOCKED only; hosted P2 NOT_RUN, UI/imagegen PENDING.

Return this exact prompt:

> Review ErrataScope W03 revision 2 repair 04, worker attempt 05. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-05.md, docs/execution/reviews/W03-review-04.md and docs/execution/reviews/W03-repair-04.md. Verify the repair-04 protected baseline and starting backup. Independently check deterministic closure of owned storage/file descriptors in repeated real receipt verification/reconciliation, constructor/staging failures, early returns and application shutdown, while retaining verified expiry/session-identity/parent-swap/API/ack-loss behavior. Require real local integration/recovery and fresh sentinel preservation; keep legacy missing bytes explicit. Preserve accepted W01/W02 evidence, hosted P2 NOT_RUN and UI/imagegen PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt.

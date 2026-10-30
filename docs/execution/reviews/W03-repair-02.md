# W03 repair 02 — storage ownership and finalization

**READY_TO_DISPATCH. W03 revision 2, worker attempt 03.** One consolidated repair; retain the passing authorization/API/acknowledgement-loss fixes. No W04 work.

Read [review 02](W03-review-02.md), [packet](../packets/W03-persistence-jobs.md), [foundation binding](../bindings/W03-foundation-v1.md), [repair 01](W03-repair-01.md) and [worker rules](../WORKER_RULES.md). This assignment supersedes repair-01 dispatch/preflight, not its safety requirements.

## Preflight and ownership

1. Require no active lock and no existing W03-attempt-03 handoff. Run `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-02-baseline.json`; require PASS.
2. Verify every file in [attempt-02 inventory](W03-attempt-02-inventory.json), before edits. Claim `.local/coordination/ACTIVE_WORKER.json` exclusively.
3. Back up all inventoried paths to `.local/w03/history/attempt-02-before-03/`, preserving relative paths and recording SHA-256/size. Verify every backup. Do not overwrite previous history.
4. **Before running any test/reconciler**, fix or override storage isolation. The old test configuration can delete application artifacts. Read the review's main-storage audit limitation; do not assert historical files are intact without checking.

Writable paths: original W03 service/tests/infra/evidence/local paths, this attempt's handoff and your own lock. No changes to Codex reviews/checkers/baselines/contracts/status/prompts, W01/W02 accepted code/tests/evidence, or dependency pins. Applied migrations **0001 and 0002 are immutable**; add 0003 only if schema changes are needed. No database/volume reset outside the dedicated test database, no global cleanup, no provider/.env.local/hosted/Git/UI/W04 work. No delegation. Existing local Docker execution is authorized within this project.

## R1 — isolate and validate storage ownership

- Give test executions a physically separate artifact root from the application, including filesystem mounts. Do not simply use a nested directory that the application collector still walks. The dedicated test DB reset must not invalidate application file ownership.
- Bind each persistent store to its owning database/store identity and fail closed before collection on mismatches. Do not persist credentials in an identity marker. Establish a safe explicit adoption path for the existing application store using actual references; no silent automatic takeover of a store already bound to another identity.
- Update all test, CLI verification, recovery and README commands consistently. Recovery helpers that deliberately operate against the application DB must explicitly select its matching storage; an ordinary test command must remain safe. Preserve current main volumes and applied migrations.
- Add a sentinel integration regression: create a main artifact and receipt, capture IDs/digests/bytes, run the complete isolated test/reset/GC workflow, then verify the main objects remain byte-identical/readable. Test that a collector launched with a mismatched database/store identity refuses deletion. Use separate real engine connections; the current process-global factory ignores subsequent settings after first initialization.
- Inventory existing main missing/corrupt artifacts before changes. Preserve their recorded IDs/hashes/events and report legacy damage separately. Do not delete database rows to hide failures or fabricate replacement receipts. Exact restoration from an independently verified backup may be proposed with provenance; otherwise leave historical loss explicit and demonstrate future safety on fresh synthetic objects.

## R2 — make staging cleanup and finalization mutually safe

- Use explicit ownership/lease fencing shared by streaming uploads, receipt writers and GC. Renew live staging ownership as appropriate without holding a DB transaction during upload I/O. A job heartbeat alone does not protect the staged result.
- Finalization must lock/revalidate the same staging ownership/state that GC uses, and verify the actual ready bytes. Once GC has reclaimed/abandoned that ownership, the old writer must not commit a successful artifact or receipt. An expired/superseded writer cannot resurrect itself silently. Preserve one immutable result identity and existing attempt/job/outbox fencing.
- Apply configured grace and fresh-reference checks consistently to journaled and unjournaled candidates. Recheck after relevant locks; do not delete live, committed, ambiguous or unknown bytes. Keep reconciliation bounded and prevent permanently abandoned rows from monopolizing its batch.
- Make cleanup paths finish without self-deadlocking: do not hold a staging lock in one session and synchronously wait for another session to delete that row. Resolve rollback/commit uncertainty before cleanup, including streaming disconnect/cancellation. Keep receipt acknowledgement-loss settlement intact.
- Regressions using real PostgreSQL/storage and deterministic barriers or controlled clock: live upload across renewal; expired/abandoned upload completes with a bounded safe error; stale writer versus collector; finalizer-versus-GC in both lock orders; fresh expired stage within grace preserved; receipt-stage expiry with a valid job lease cannot produce succeeded/missing bytes; unknown commit preserves bytes. Test actual worker flow, not only helper return values.
- Retain/re-run previous crash, ack-loss, duplicate delivery, cancellation, stale attempt, heartbeat, bounded retries and outbox concurrency coverage. A valid receipt remains readable with unchanged ID/hash after redelivery/restart. Do not weaken assertions or convert required cases to skips.

## R3 — enforce exact generated paths without following links

- Recognize only exact canonical layouts: `<32 lowercase hex project UUID>/<32 lowercase hex artifact UUID>.bin` and `.staging/<project hex>/<artifact hex>.part`, plus any separately specified owned temporary layout. Unknown directories/extensions/names are preserved, not treated as garbage. A matching shape alone does not bypass ownership/reference/lease checks.
- Validate lexical components before resolution and reject symlink traversal for read/write/promote/delete, including links whose target remains inside the store. Keep the root confined and use no-follow/atomic filesystem operations where needed to avoid checking one path and later using a redirected path. Do not add broad recursive deletion.
- Test internal and external directory/file symlinks; unknown `.bin` and `.staging` contents survive; valid owned stale orphans are collected; committed artifacts remain immutable and readable. Run meaningful Linux filesystem tests without skipped cases.

## Completion evidence

Run the 92 accepted domain tests unchanged, all existing 82 W03 tests plus new regressions, and connected API/worker `verify-foundation` against actual services. Use the matching isolated store for each database. Test upgrade of the existing 0002 volume without reset and repeat migration safely. Regenerate schema/OpenAPI only as affected.

Recovery outputs must use **attempt-03** names and new local seed/output files; never overwrite attempt-01/02 evidence. Update IMPLEMENTATION_REPORT with commands/exits, root/database isolation, before/after sentinel hashes, each R1–R3 result, historical byte-loss limitations and actual recovery assertions. Worker code must not run Codex's checkers as-is or overwrite review-owned output; add equivalent regressions under tests_w03.

Recheck the repair-02 protected baseline, write `docs/execution/handoffs/W03-attempt-03.md`, stop only owned services/jobs while retaining volumes, release your lock and stop editing. Report READY_FOR_REVIEW/PARTIAL/BLOCKED, never ACCEPTED. Hosted P2 remains NOT_RUN; UI/imagegen approval PENDING.

Return this exact prompt:

> Review ErrataScope W03 revision 2 repair 02, worker attempt 03. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-03.md, docs/execution/reviews/W03-review-02.md and docs/execution/reviews/W03-repair-02.md. Verify the repair-02 protected baseline and starting backup. Independently check R1–R3 against actual PostgreSQL/Valkey/API/private storage: database/store isolation and sentinel preservation, staging lease/GC/finalization fencing, exact path and no-symlink handling. Preserve passing authorization/API/idempotency/ack-loss fixes and accepted W01/W02 evidence. Do not infer historical byte integrity from retained volumes or fresh successes; inspect legacy-loss reporting. Require real local integration and recovery evidence. Hosted P2 remains NOT_RUN and UI/imagegen approval PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt.

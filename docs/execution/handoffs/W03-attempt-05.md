# Worker handoff â€” W03 revision 2 repair 04, attempt 05

Status: **READY_FOR_REVIEW** (acceptance, Git/GitHub checkpoint and W04 binding remain Codex's decision)
Packet: W03-persistence-jobs revision 2, repair assignment `docs/execution/reviews/W03-repair-04.md`, attempt **05**
Started/finished (UTC): 2026-10-30T08:35:53Z / 2026-10-30T08:46:52Z (final checks)
Preflight baseline: **PASS** â€” `docs/execution/baselines/W03-repair-04-baseline.json`, **285 protected hashes, 339 links, 0 errors**, before edits and after.
Starting inventory: **70/70** files in `docs/execution/reviews/W03-attempt-04-inventory.json` matched SHA-256 before edits (0 missing/mismatches).
History backup: `.local/w03/history/attempt-04-before-05/` â€” 70 files with relative paths + `BACKUP_MANIFEST.json`; every copied hash matches (`all_match=true`). Attempt-01â€“04 evidence/history preserved.
Stack: pinned images/lock unchanged; Compose project exactly `erratascope-w03`; isolated test DB/volume retained. Migrations `0001_foundation`, `0002_staging`, `0003_staging_fencing` unchanged and head re-run idempotently; no schema change. Main volumes and legacy-loss records preserved.
No provider calls, real credentials/.env.local, package changes, Git, hosted, UI, W04 or delegation. Hosted P2 **NOT_RUN**; UI/imagegen **PENDING**.

## R1 â€” explicit descriptor ownership (PASS)

- `ArtifactStore` has idempotent `close()` and context-manager support. Initialization closes the pinned root fd on identity mismatch, malformed marker, or subdirectory setup failure. `close()` clears the stored fd before closing, so double-close cannot close a reused descriptor.
- `_project_fd` closes the intermediate `.staging` fd on project open/create failure, and closes a newly opened project fd if the post-open hook raises. `StagingUpload` construction closes its pinned parent and any partially opened file when exclusive create/fdopen/hook fails. Promotion closes source/destination descriptors on success and failure and removes its own staging entry on pre-rename failure. File-read and marker helpers close fds on failure.
- Production owners now close exactly what they own: `jobs.verify_receipt()` (including early returns), `execute()`, `_settle_after_exception()`, each `reconcile_once()` pass (wrapper + `finally`), FastAPI app lifespan shutdown (including startup failure), CLI `adopt-store` (`contextlib.closing`), and `export-openapi` one-shot store. Borrowed route stores are not closed by consumers.
- Behavior retained: expiry-without-GC 409, actual-session collector identity with omitted/forged hints refused, parent-swap no-follow confinement, receipt-GC/ack-loss, auth/API/idempotency/review races.

### Descriptor evidence (`descriptor-evidence-attempt-05.json`, actual `/proc/self/fd`)

| Path | Before | After | Calls |
|---|---|---|---|
| successful `verify_receipt` | 1 | 1 | 12 |
| `reconcile_once` with valid receipt | 1 | 1 | 8 |
| constructor identity mismatch (raises) | 0 | 0 | 8 |
| app startup/shutdown | 1 | 1 | â€” |

Also bounded: malformed marker construction, rejected staging symlink, duplicate staging create, hook failures (`after_project_dir_open`, `before_staging_create`, `before_promote_rename`), cancelled execution, missing-receipt reconciliation. Sentinel bytes/receipts remained readable/unchanged; no GC/process-exit reliance.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-04-baseline.json` (initial/final) | 0 / 0 | PASS, 285 hashes / 339 links |
| inventory SHA-256 verification (70 files) + verified backup | 0 / 0 | 70/70 match; `all_match=true` |
| `docker compose â€¦ config --quiet` / `build` | 0 / 0 | isolated storage; repaired image |
| `docker compose â€¦ run --rm migrate` (twice) | 0 / 0 | head `0003_staging_fencing`; idempotent |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests_w03` | 0 | **110 W03 tests OK** (50.9 s) |
| descriptor evidence capture | 0 | 1â†’1 verify (12), 1â†’1 reconcile (8), 0â†’0 constructor (8), 1â†’1 app lifespan |
| sentinel through isolated reset/GC | 0 | main artifact/receipt byte-identical (`sentinel-attempt-05.json`) |
| `verify-foundation` | 0 | **11/11 checks** |
| `export-openapi` | 0 | OpenAPI regenerated |
| `infra/w03/recover.ps1` | 0 | attempt-05: crash exit 43; recovered attempt 2; ordered events; one succeeded; receipt digest matches; API restart retrieval preserved |

## Historical byte loss

Final attempt-05 read-only audit: **110 main artifact rows, 69 readable, 41 missing**. The 41 missing IDs remain the same legacy losses; no pre-review byte inventory exists, so cause/time cannot be attributed. Rows/events were preserved; no replacement receipts/bytes were minted. Fresh sentinel/verification/recovery receipts are readable and demonstrate only future safety. `legacy-artifact-audit-attempt-05.json` and `store-isolation-attempt-05.json` record this without secrets.

## Gates

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | 0001â€“0003 immutable; head idempotent; domain/migration tests |
| G2 auth/private artifacts | **PASS** | descriptor ownership, session-derived identity, lease/path confinement, sentinel preservation |
| G3 idempotency/reviews | **PASS (retained)** | replay/current-auth, concurrent convergence, review races |
| G4 recovery/fencing | **PASS** | bounded descriptors in repeated verification/reconciliation, receipt/lease fencing, attempt-05 crash/restart evidence |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

## Changed files

- `backend/erratascope_service/artifacts.py` â€” idempotent close/context manager, exception-safe root/project/staging/file cleanup, fd-safe promotion/abort/read.
- `backend/erratascope_service/jobs.py` â€” close stores in verify/execute/settle and per-pass reconciliation.
- `backend/erratascope_service/api.py` â€” lifespan store close (startup failure included), cancellation/disconnect cleanup.
- `backend/erratascope_service/cli.py` â€” closing adoption store, one-shot OpenAPI store close.
- `backend/erratascope_service/storage_identity.py` â€” fdopen failure cleanup for marker helpers.
- Tests: `backend/tests_w03/test_descriptor_lifetime.py` (new, 9 regressions); sentinel output renamed attempt-05.
- Infra/docs: `infra/w03/recover.ps1` (attempt-05 names); `backend/README-W03.md`; evidence `descriptor-evidence-attempt-05.json`, `sentinel-attempt-05.json`, `store-isolation-attempt-05.json`, `legacy-artifact-audit-attempt-05.json`, `recovery-*-attempt-05.json`, regenerated `openapi.json`/`verification.json`, updated `IMPLEMENTATION_REPORT.md`; this handoff.

No accepted domain code/tests, W01/W02 evidence, protected documents/baselines/reviews/status, migrations, pins, `.env.local` or Git metadata was modified.

## Resources and limitations

- Only `erratascope-w03` services were used; at completion they were stopped (`Exited (0)`). Volumes `erratascope-w03_pgdata`, `erratascope-w03_artifacts`, `erratascope-w03_test_artifacts` retained; no deletion/global prune; no other project touched.
- Local single-host Linux evidence only; hosted auth/storage/broker/RLS not provisioned/tested; hosted P2 **NOT_RUN**.
- Legacy 41 missing bytes remain unexplained/unreplaced; no historical integrity claimed.
- Recovery covers local worker crash/restart and API restart; not multi-node/broker failover.
- No provider calls, credentials, package changes, Git, UI, hosted deployment, W04 or delegation. No blockers.

## Return prompt

> Review ErrataScope W03 revision 2 repair 04, worker attempt 05. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-05.md, docs/execution/reviews/W03-review-04.md and docs/execution/reviews/W03-repair-04.md. Verify the repair-04 protected baseline and starting backup. Independently check deterministic closure of owned storage/file descriptors in repeated real receipt verification/reconciliation, constructor/staging failures, early returns and application shutdown, while retaining verified expiry/session-identity/parent-swap/API/ack-loss behavior. Require real local integration/recovery and fresh sentinel preservation; keep legacy missing bytes explicit. Preserve accepted W01/W02 evidence, hosted P2 NOT_RUN and UI/imagegen PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt.


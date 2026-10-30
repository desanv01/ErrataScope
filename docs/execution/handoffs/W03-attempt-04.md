# Worker handoff â€” W03 revision 2 repair 03, attempt 04

Status: **READY_FOR_REVIEW** (acceptance, Git/GitHub checkpoint and W04 binding remain Codex's decision)
Packet: W03-persistence-jobs revision 2, repair assignment `docs/execution/reviews/W03-repair-03.md`, attempt **04**
Started/finished (UTC): 2026-10-30T07:58:06Z / 2026-10-30T08:08:32Z (final checks)
Preflight baseline: **PASS** â€” `docs/execution/baselines/W03-repair-03-baseline.json`, **266 protected hashes, 320 links, 0 errors**, before edits and after.
Starting inventory: **63/63** files in `docs/execution/reviews/W03-attempt-03-inventory.json` matched SHA-256 before edits (0 missing/mismatches).
History backup: `.local/w03/history/attempt-03-before-04/` â€” 63 files with relative paths + `BACKUP_MANIFEST.json`; every copied hash matches (`all_match=true`). Attempt-01/02/03 history/evidence preserved.
Stack: pinned images/lock unchanged; Compose project exactly `erratascope-w03`. Applied migrations `0001_foundation`, `0002_staging`, `0003_staging_fencing` untouched; no new migration required. Existing main/test volumes preserved; no reset/re-adoption of the application store.
No provider calls, credentials/.env.local access, package changes, Git, hosted, UI, W04 or delegation. Hosted P2 **NOT_RUN**; UI/imagegen **PENDING**.

## R1â€“R3 results

### R1 â€” expired upload ownership cannot revive (PASS)

- Renewal is a single atomic conditional UPDATE requiring the staging row to remain `active`, upload-owned, not job-owned, and **unexpired at the captured timestamp**. Missing/expired/reclaimed/superseded ownership raises `STAGING_LEASE_LOST`.
- Finalization no longer renews before checking. It locks the row, requires current state/owner/lease, verifies promoted bytes, and only then commits. Expired ownership returns a bounded **409** with no accepted artifact and no idempotency response; only that operation's uncommitted bytes are cleaned.
- Slow streams still renew via short fresh transactions (no transaction during I/O). Regressions: renewal across an app-side slow stream; expiry **without GC** â†’ 409; expiry followed by GC â†’ 409; no self-deadlock; receipt staging remains job/attempt-hearted.
- Review-03 red case (expire lease without GC, formerly 201) now returns 409.

### R2 â€” collector ownership from the actual database session (PASS)

- `reconcile_orphans` derives identity from its actual SQLAlchemy session (`get_bind()` host/port + `SELECT current_database()`). An optional caller identity is only an assertion; omitted/forged hints cannot override the session. Missing/invalid binding or marker mismatch fails closed before reference queries/deletion; collection never adopts or rewrites markers.
- Real two-engine regression (test DB + application DB): a committed test-DB artifact is preserved when collected from an app-DB session with **no hint**, with a **forged test-DB hint**, and via `jobs.reconcile_once` app settings against test storage. Matching sessions still collect stale owned orphans.
- Review-03 red case (default call with omitted hint deleting a different database's committed file) is refused; bytes preserved.

### R3 â€” directory-relative no-follow confinement (PASS)

- Root validated before resolution (symlinked configured root rejected) and pinned with `O_DIRECTORY|O_NOFOLLOW`. `.staging` and project directories are opened relative to pinned fds with no-follow; file open/create/unlink and stagingâ†’final promotion use relative operations with pinned source/destination descriptors. A parent swap after checking cannot redirect onto outside/unowned bytes.
- Abort unlinks only the pinned staging entry; promotion renames between pinned staging/final descriptors; read/delete use pinned parent descriptors. Canonical keys use full-string `fullmatch` only (trailing newline/control characters rejected); unknown names/extensions remain preserved.
- Real Linux parent-swap regressions for delete/read/promote/abort leave external sentinels untouched; symlinked root rejected; newline key rejected; canonical round-trip and stale-orphan cleanup remain green.
- Review-03 red cases (parent-swap delete of external sentinel; internal symlink followed; trailing-newline key) now fail closed.

## Historical byte loss

Attempt-04 read-only audit: **81 main artifact rows, 40 readable, 41 missing**. The 41 missing IDs exactly match the recorded legacy losses; newly added sentinel/verification/job receipts are readable. No pre-review byte inventory exists, so cause/time per legacy loss cannot be established. Rows/events were preserved and no replacement receipts/bytes were minted; legacy loss remains explicit. `legacy-artifact-audit-attempt-04.json` and `store-isolation-attempt-04.json` record this without secrets; fresh safety is demonstrated on new synthetic objects only.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-03-baseline.json` (initial/final) | 0 / 0 | PASS, 266 hashes / 320 links |
| inventory SHA-256 verification (63 files) + verified backup | 0 / 0 | 63/63 match; `all_match=true` |
| read-only main-store audit | 0 | 81 rows, 40 readable, 41 missing |
| `docker compose â€¦ config --quiet` / `build` | 0 / 0 | isolated test/app roots; repaired image |
| `docker compose â€¦ run --rm migrate` (twice) | 0 / 0 | head `0003_staging_fencing`; idempotent |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests_w03` | 0 | **101 W03 tests OK** (49.5 s) |
| sentinel test through isolated reset/GC | 0 | main artifact/receipt byte-identical; `sentinel-attempt-04.json` |
| `verify-foundation --output /local/verification.json` | 0 | **11/11 checks** |
| `export-openapi --output /local/openapi.json` | 0 | OpenAPI regenerated |
| `infra/w03/recover.ps1` | 0 | attempt-04: crash exit 43; recovered attempt 2; ordered events; one succeeded; receipt digest matches; API restart retrieval preserved |

## Gates

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | 0001â€“0003 immutable; 0003 head idempotent; domain/migration tests |
| G2 auth/private artifacts | **PASS** | session-derived ownership, expired-lease rejection, directory-relative confinement, sentinel preservation |
| G3 idempotency/reviews | **PASS (retained)** | replay/current-auth, concurrent convergence, review races |
| G4 recovery/fencing | **PASS** | upload/receipt lease fencing, GC/finalization, ack-loss/ambiguous preservation, attempt-04 crash/restart evidence |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

## Changed files

- `backend/erratascope_service/artifacts.py` â€” directory-fd confinement, full-string canonical validation, session-derived collector identity, fenced GC.
- `backend/erratascope_service/api.py` â€” conditional atomic renewal; no pre-finalization renewal; app-side streaming renewal test hook.
- `backend/erratascope_service/storage_identity.py` â€” fd-relative marker read/write/ensure.
- Tests: `backend/tests_w03/test_filesystem_confinement.py` (new), `test_storage_fencing.py` (expired without GC, slow renewal), `test_storage_isolation.py` (actual-session omitted/forged hints, service entry, attempt-04 sentinel); `test_storage_fencing` / `test_r3_staging` path API updates.
- Infra/docs: `infra/w03/compose.yaml` (test app-DB probe env), `infra/w03/recover.ps1` (app root, attempt-04 names), `backend/README-W03.md`; evidence `sentinel-attempt-04.json`, `store-isolation-attempt-04.json`, `legacy-artifact-audit-attempt-04.json`, `recovery-*-attempt-04.json`, regenerated `openapi.json`/`verification.json`, updated `IMPLEMENTATION_REPORT.md`; this handoff.

No accepted domain code/tests, W01/W02 evidence, protected documents/baselines/reviews/status, migrations 0001â€“0003, `.env.local` or Git metadata was modified.

## Resources and limitations

- Only this project's `erratascope-w03` services were used; at completion they were stopped (`Exited (0)`). Volumes `erratascope-w03_pgdata`, `erratascope-w03_artifacts`, `erratascope-w03_test_artifacts` are preserved; no volume deletion or global prune; no other project touched.
- Local single-host Linux evidence only; hosted auth/storage/broker/RLS not provisioned/tested; hosted P2 **NOT_RUN**.
- Legacy 41 missing bytes remain unexplained/unreplaced; no historical integrity is claimed. Future safety is demonstrated only on fresh sentinel objects.
- Recovery covers local worker crash/restart and API restart; not multi-node/broker-failover outages.
- No provider calls, credentials, package changes, Git, UI, hosted deployment, W04 or delegation occurred. No blockers.

## Return prompt

> Review ErrataScope W03 revision 2 repair 03, worker attempt 04. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-04.md, docs/execution/reviews/W03-review-03.md and docs/execution/reviews/W03-repair-03.md. Verify the repair-03 protected baseline and starting backup. Independently check expired upload renewal without GC, collector ownership against its actual database session with omitted/forged hints, and directory-relative no-follow filesystem operations under parent-swap races including abort/promotion/root/newline handling. Preserve passing API/auth/idempotency/ack-loss/receipt-GC fixes and accepted W01/W02 evidence. Require real local integration/recovery and fresh sentinel preservation; keep legacy missing bytes explicit. Hosted P2 remains NOT_RUN and UI/imagegen PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt.


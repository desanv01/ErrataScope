# Worker handoff â€” W03 revision 2 repair 02, attempt 03

Status: **READY_FOR_REVIEW** (acceptance, Git/GitHub checkpoint and W04 binding remain Codex's decision)
Packet: W03-persistence-jobs revision 2, repair assignment `docs/execution/reviews/W03-repair-02.md`, attempt **03**
Started/finished (UTC): 2026-10-30T07:04:36Z / 2026-10-30T07:20:49Z (final checks)
Preflight baseline: **PASS** â€” `docs/execution/baselines/W03-repair-02-baseline.json`, **251 protected hashes, 307 links, 0 errors**, before edits and after.
Starting inventory: **53/53** files in `docs/execution/reviews/W03-attempt-02-inventory.json` matched SHA-256 before edits (0 missing/mismatches).
History backup: `.local/w03/history/attempt-02-before-03/` â€” all 53 files with relative paths + `BACKUP_MANIFEST.json`; every copied hash matches (`all_match=true`). Attempt-01/02 history and evidence remain untouched.
Stack: pinned images/lock unchanged, Compose project exactly `erratascope-w03`. Applied migrations `0001_foundation`/`0002_staging` untouched; new `0003_staging_fencing` upgraded the existing volume in place. No volume reset/deletion.
No Nebius, hosted provisioning, `.env.local`, Git, UI or W04 work. Hosted P2 **NOT_RUN**; UI/imagegen approval **PENDING**.

## Pre-review storage audit (historical damage, recorded honestly)

A read-only audit ran **before** any repair test/collector touched the application store:

- `docs/evidence/W03/legacy-artifact-audit-attempt-03.json`: **50 main artifact rows, 9 readable, 41 missing** (`MISSING`), with IDs/storage keys/expected hashes/observed errors preserved; no bytes or secrets recorded.
- No pre-review byte inventory exists, so the time/cause of each missing file cannot be attributed. No rows were deleted, no replacement receipts were minted, and named-volume retention is not claimed to imply byte integrity. Only fresh synthetic objects are asserted intact.

## R1â€“R3 results

### R1 â€” storage isolation and ownership (PASS)

- Test executions now use a **physically separate** `test_artifacts` volume/root (`/var/lib/erratascope/test-artifacts`); application services keep `/var/lib/erratascope/artifacts`. The app volume is separately mounted at `/var/lib/erratascope/app-artifacts` only for explicit sentinel/recovery commands. Test DB reset/GC cannot walk application storage.
- Every persistent store has `.store-identity.json` (store UUID + credential-free `host:port/database`). Populated unmarked stores fail closed; collectors/finalizers refuse mismatched identities before deleting.
- Existing application store adopted explicitly via `adopt-store --confirm`: **9 owned files, 9 referenced, 0 unreferenced, 0 unknown**, identity `db:5432/erratascope`. Test store independently bound to `db:5432/erratascope_test` (`store-isolation-attempt-03.json`).
- **Sentinel regression:** main artifact + receipt created through the real API/worker, then full isolated test-DB reset + test-store GC, then byte-identical re-download (`sentinel-attempt-03.json`): artifact SHA-256 `2f45fe68â€¦a2bb`, receipt SHA-256 `45ab2c09â€¦d3a5`, both before/after equal.
- Mismatch test: collector with a different database identity raises `STORE_IDENTITY_MISMATCH` and deletes nothing.

### R2 â€” staging lease, GC and finalization fencing (PASS)

- Uploads stream in bounded chunks and **renew staging leases during slow streams** via short fresh sessions (no DB transaction during I/O). Receipt staging rows carry `owner_kind='result'`, `owner_job_id`, `owner_attempt_token` (migration `0003`); the real heartbeat renews job and staging leases.
- Finalizers lock/revalidate the same staging row (state, owner kind/job/token, unexpired lease), verify actual bytes, and commit only while ownership is current. Expired/lost staging yields a bounded upload 409 (`STAGING_LEASE_LOST`) or a safe worker retry/failure â€” never a succeeded job with missing receipt bytes.
- GC applies configured grace to journaled and unjournaled candidates, protects live job-owned staging (renewing it), preserves committed, ambiguous and unknown bytes, and releases journal rows after safe reclamation. No cleanup runs while another session holds the same staging lock; failure paths roll back before fresh-session cleanup.
- Ack-loss and ambiguous-commit outcomes preserve bytes/receipt identity; uploads that commit then raise return the verified committed artifact. New tests: slow upload across renewal; expired staging cannot finalize upload; receipt-stage expiry with valid job cannot produce succeeded/missing bytes; ambiguous committed upload preserved; existing ack-loss/duplicate/cancellation/heartbeat/retry/outbox coverage retained.

### R3 â€” exact paths and no symlink traversal (PASS)

- Only exact layouts are recognized: `<32 lowercase hex project>/<32 lowercase hex artifact>.bin` and `.staging/<32 project hex>/<32 artifact hex>.part`. Unknown names/extensions/directories (e.g., `notes/keep.bin`, unknown `.staging` contents) are preserved.
- Lexical component validation precedes resolution; `lstat`/`O_NOFOLLOW` checks reject symlinks for read/write/promote/delete, including internal symlinks whose target remains in the store. Final promotion verifies a regular file; deletion only removes exact owned regular files; no broad recursive deletion.
- Tests: unknown `.bin`/staging contents survive; internal file and directory symlinks are not followed/deleted; symlinked project directory rejected; valid stale orphans collected; committed artifacts remain immutable/readable.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-02-baseline.json` (initial/final) | 0 / 0 | PASS, 251 hashes / 307 links |
| inventory SHA-256 verification (53 files) + verified backup | 0 / 0 | 53/53 match; `all_match=true` |
| read-only main-store audit | 0 | 50 rows, 9 readable, 41 missing |
| `docker compose â€¦ config --quiet` | 0 | valid; test/app roots separated |
| `docker compose â€¦ build` | 0 | rebuilt pinned image |
| `docker compose â€¦ run --rm migrate` (twice) | 0 / 0 | `0002_staging -> 0003_staging_fencing`; second run idempotent |
| `adopt-store --confirm` against app DB/root | 0 | 9/9 present generated files referenced; identity bound |
| sentinel integration test | 0 | main artifact+receipt byte-identical after isolated reset/GC |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests_w03` | 0 | **93 W03 tests OK** (48.7 s) |
| `verify-foundation --output /local/verification.json` | 0 | **11/11 checks** |
| `export-openapi --output /local/openapi.json` | 0 | OpenAPI regenerated |
| `infra/w03/recover.ps1` | 0 | attempt-03: crash exit 43; recovered attempt 2; ordered events; one succeeded event; receipt digest matches; API restart retrieval preserved |

## Gates

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | 0003 upgrade of existing DB; 92 domain + migration tests; 0001/0002 immutable |
| G2 auth/artifacts | **PASS** | isolated identity-bound stores, adoption/sentinel, GC/lease safety, exact paths/no symlinks, 11/11 connected flow |
| G3 idempotency/reviews | **PASS (retained)** | replay/current-auth, concurrent convergence, review races |
| G4 recovery/fencing | **PASS** | heartbeat/staging renewal, GC/finalization race, ack-loss/ambiguous preservation, cancellation/stale/outbox fencing, attempt-03 crash/restart evidence |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

## Changed files

- Service: `backend/erratascope_service/storage_identity.py` (new), `artifacts.py` (identity/exact paths/no-follow/GC fencing), `jobs.py` (staging owner/heartbeat renewal/finalization/ambiguous settlement), `api.py` (store identity, upload lease renewal/finalization/ambiguous handling), `models.py` (`UploadStaging` owner/ambiguous), `cli.py` (`adopt-store`), `config.py` (staging/grace/retry limits retained).
- Migrations/tests/infra: `backend/migrations/versions/0003_staging_fencing.py` (new); `backend/tests_w03/test_storage_isolation.py` and `test_storage_fencing.py` (new) plus migration/store-path updates; `infra/w03/compose.yaml` (separate test/app volumes, test root, app API URL), `infra/w03/Dockerfile` (store dirs/ownership), `infra/w03/recover.ps1` (app-store selection, attempt-03 names), `backend/README-W03.md`.
- Evidence: `docs/evidence/W03/legacy-artifact-audit-attempt-03.json`, `sentinel-attempt-03.json`, `store-isolation-attempt-03.json`, `recovery-attempt-03.json`, `recovery-restart-attempt-03.json`, `recovery-api-retrieval-attempt-03.json`, regenerated `openapi.json`/`verification.json`/`schema-inventory.json`, `IMPLEMENTATION_REPORT.md`; this handoff.

No accepted domain code/tests, W01/W02 evidence, protected contracts/reviews/baselines/status, `.env.local` or Git metadata was modified.

## Resources and limitations

- At completion only this project's five `erratascope-w03` services were stopped; volumes `erratascope-w03_pgdata`, `erratascope-w03_artifacts` and `erratascope-w03_test_artifacts` are retained. No volume deletion/global prune; no other project touched.
- Historical byte loss: 41/50 pre-repair main artifact rows were already missing; no pre-review inventory, so cause/time cannot be attributed; no restoration/replacement evidence claimed. Legacy rows/events preserved; future safety demonstrated only on fresh sentinel objects.
- Local single-host evidence only; hosted auth/storage/broker/RLS were not provisioned or tested; hosted P2 remains **NOT_RUN**.
- Local development credentials/JWKS are synthetic; tests use dedicated `erratascope_test` DB/root and `w03-test` queue.
- Artifact limit 10 MiB, PDF/text/JSON; no rendering/parser, UI, deployment, provider call or W04 work.
- No blockers. No gate claimed beyond actual local observations.

## Return prompt

> Review ErrataScope W03 revision 2 repair 02, worker attempt 03. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-03.md, docs/execution/reviews/W03-review-02.md and docs/execution/reviews/W03-repair-02.md. Verify the repair-02 protected baseline and starting backup. Independently check R1â€“R3 against actual PostgreSQL/Valkey/API/private storage: database/store isolation and sentinel preservation, staging lease/GC/finalization fencing, exact path and no-symlink handling. Preserve passing authorization/API/idempotency/ack-loss fixes and accepted W01/W02 evidence. Do not infer historical byte integrity from retained volumes or fresh successes; inspect legacy-loss reporting. Require real local integration and recovery evidence. Hosted P2 remains NOT_RUN and UI/imagegen approval PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt.


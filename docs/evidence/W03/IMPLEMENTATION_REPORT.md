# W03 implementation report â€” local persistence, authorization, artifacts and durable jobs

Status: **worker implementation for Codex review** (not acceptance)
Packet: W03-persistence-jobs revision 2, worker attempt **W03-attempt-01**
Baseline: `docs/execution/baselines/W03-baseline.json` â€” PASS (223 protected hashes, 281 links) before and after
Mode: local Linux containers only; Compose project exactly `erratascope-w03`
Network: only the assigned Docker/PyPI dependency downloads and local services. **No Nebius, hosted provisioning, credentials, Git, UI or W04 work.**
Hosted P2 status: **NOT_RUN**; UI/imagegen gate remains PENDING.

## Runtime and artifacts

- Pinned images: `python:3.11.15-slim-bookworm@sha256:d29f48â€¦e0c3`, `postgres:17-bookworm@sha256:858bb5â€¦0d27`, `valkey/valkey:8.1.4-alpine@sha256:e706d1â€¦098b` (all present locally; inventory in `images.json`).
- `backend/requirements-service.lock` is a byte-for-byte copy of the protected Linux lock (SHA-256 `7d53a786â€¦d23`, 40 locked packages); the image installs with `--require-hashes --only-binary=:all:`. Installed freeze exactly matches the lock (40/40, `dependency-inventory.json`).
- Compose services: `db`, `broker`, `api`, `worker`, `dispatcher`, `migrate`, `test`; only `127.0.0.1:18080` published; no `container_name`, Docker socket mount or global prune. Named volumes `erratascope-w03_pgdata` and `erratascope-w03_artifacts` preserved.
- Test service isolates into the dedicated `erratascope_test` database and `w03-test` queue, reset per module; the main example database/queue are never consumed by tests.

## Implemented scope

| Area | Implementation |
|---|---|
| Migrations (G1) | Alembic `0001_foundation` creates `erratascope` tables for projects, memberships, artifacts, bundles, domain_versions, bundle_members, review_items/events, idempotency, jobs, job_attempts, outbox, job_events, stage_results. Migrator role owns the schema; app role gets USAGE + DML only. Immutability triggers block UPDATE/DELETE on sealed records; review candidates allow only `current_revision`. Applied twice successfully (`0001_foundation`). |
| Domain persistence | Bundles are validated by the accepted `parse_bundle`, normalized and hashed with accepted domain helpers; immutable per-entity version rows (snapshot, component, fact set/fact, document, anchor, rule, coverage, baseline) with payload hashes and unique project/kind/version constraints; reload reparses/revalidates and reproduces `input_hash`; altered reused versions return `DOMAIN_VERSION_CONFLICT`. |
| Auth (G2) | JWT verification (RS256/ES* allowlist, issuer/audience/expiry, â‰¤30 s leeway) against local public JWKS or bounded HTTPS hosted JWKS; subject UUID; PostgreSQL membership is authority. Foreign project â†’ 404; insufficient role â†’ 403; no client identity header bypass. Hosted startup raises `HOSTED_STORAGE_NOT_READY`. |
| Artifacts | Streaming upload (PDF/text/JSON, â‰¤10 MiB enforced while reading), SHA-256 and length computed, server-generated storage key, private atomic byte storage, metadata/content routes, safe disposition, `nosniff`, `no-store`; reads re-verify length+hash and return `ARTIFACT_INTEGRITY`/`ARTIFACT_MISSING` on corruption. Path traversal impossible from caller input. |
| Idempotency/races (G3) | `Idempotency-Key` scoped to project (nil for bootstrap), actor, operation and canonical request hash; identical replay returns stored status/body; changed body â†’ `IDEMPOTENCY_CONFLICT`; concurrent first writers converge through unique conflict + replay. Review decisions use `SELECT â€¦ FOR UPDATE` and exact `expected_revision`; one concurrent decision wins, the other gets `REVIEW_REVISION_CONFLICT`, with append-only revision events. |
| Jobs (G4) | Job + `queued` event + outbox inserted transactionally; dispatcher claims outbox with `FOR UPDATE SKIP LOCKED`, enqueues job ID over RQ JSON and marks sent; worker claims with attempt token/lease, verifies artifact bytes, stages receipt bytes, then commits stage result + result artifact + success only while its token owns the job. Duplicate delivery, stale lease requeue, lost broker redispatch, cancellation and terminal-state protection are covered. Bounded retries (max 3). |
| Recovery | `infra/w03/recover.ps1` stops only this project's worker, seeds a job, crashes after bytes are staged but before commit (`W03_TEST_FAILPOINT=crash_after_stage`, exit 43), expires the lease, reconciles/redispatches, restarts the worker with preserved volumes, verifies the committed receipt, then restarts the API and verifies retrieval. Failpoints are environment-gated (`W03_TEST_MODE=1`) with no HTTP endpoint. |
| Connected flow | `verify-foundation` drives the actual API and DB/broker-backed worker: health, project creation + idempotent replay/conflict, viewer membership, artifact upload/roundtrip, review decision + stale denial, job success with ordered events and receipt digest, foreign-user 404. `openapi.json` exported from the live app. |
| Hosted prerequisites (G5) | `infra/w03/hosted-prerequisites.md` lists required account/region/cost, managed DB roles/TLS, private storage, broker, asymmetric JWKS pinning, fail-closed startup, RLS/authorization, backup/restore and outstanding hosted adapters. Hosted execution is **NOT_RUN**. |

## Commands actually run (PowerShell, project root)

Docker commands worked through the harness permission mechanism. Environment for Python commands: `PYTHONPATH` = backend, `PYTHONDONTWRITEBYTECODE=1`.

| Command | Exit | Observed result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-baseline.json` (initial) | 0 | PASS, 223 hashes / 281 links |
| `docker version` | 0 (client/server) | Engine 29.8.1, Docker Desktop 4.93.0, Linux engine |
| `docker compose version` | 0 | v5.5.1 |
| `docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet` | 0 | valid Compose configuration |
| `docker compose â€¦ build` | 0 | built pinned image from lock |
| `docker compose â€¦ run --rm --no-deps test python -m erratascope_service.cli bootstrap-local --out /local/dev-auth` | 0 | generated local RSA JWKS/private key/3 synthetic user tokens under `.local/w03/dev-auth` |
| `docker compose â€¦ up -d --wait db broker` | 0 | PostgreSQL and Valkey healthy |
| `docker compose â€¦ run --rm migrate` (twice) | 0 / 0 | applied `0001_foundation`; second run idempotent |
| `docker compose â€¦ up -d --wait api worker dispatcher` | 0 | all healthy; worker/dispatcher consume only this project's queue |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests -v` | 0 | **92 accepted domain tests OK** |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests_w03 -v` | 0 | **37 W03 integration tests OK** (18.6 s) |
| `docker compose â€¦ run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json` | 0 | **11/11 checks passed**, `secrets_recorded=false` |
| `docker compose â€¦ run --rm test python -m erratascope_service.cli export-openapi --output /local/openapi.json` | 0 | `docs/evidence/W03/openapi.json` (48.9 KB) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1` | 0 | crash exit 43; recovery attempts=2; stage committed; API restart retrieval preserved |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-baseline.json` (final) | 0 | PASS, 223 hashes / 281 links |

Intermediate failures fixed in-scope (not skipped or mocked): PostgreSQL 15+ `public` CREATE privilege (moved Alembic metadata into the migrator-owned schema and created it in init), worker startup incorrectly requiring API JWKS (API-only requirement), RQ worker serializer mismatch (JSON serializer class on workers), UUIDs in JSONB idempotency bodies (JSON-safe response payloads), initial test isolation into a dedicated test DB/queue, and reconciler/event-order grace.

## Required gates

| Gate | Result | Evidence / limits |
|---|---|---|
| G1 migrations/flow | **PASS** | Migration applied twice; 15 tables + 8 immutable triggers; bundle round-trip reproduces domain `input_hash` and result hash; 92 domain + persistence tests |
| G2 auth/artifacts | **PASS** | JWT negative/positive tests, foreign 404, viewer write 403, private bytes, integrity/missing detection, oversize rejection, 11-check connected flow |
| G3 idempotency/review races | **PASS** | Replay/conflict, concurrent same-key convergence, concurrent review decisions one-winner, stale revision 409, append-only events |
| G4 actual recovery | **PASS** | Real crash after staging (exit 43), stale lease reconcile/redispatch, worker restart with preserved volumes, committed receipt (attempts=2), API restart retrieval |
| G5 hosted prerequisites | **PASS (documentation only)** | `infra/w03/hosted-prerequisites.md`; hosted execution **NOT_RUN** |

No gate is claimed beyond actual observations. W03 acceptance, Git checkpoint and W04 binding remain Codex's responsibility.

## Limitations and boundaries

- Hosted mode is intentionally fail-closed (`HOSTED_STORAGE_NOT_READY`); hosted auth/storage/broker and RLS were not provisioned or tested. Hosted P2 acceptance remains open.
- Local development credentials and synthetic JWT keys live only in local files/compose; they are not production secrets and must be replaced for hosted use.
- Test suite isolates into a dedicated test database/schema and queue; it does not test multi-node workers or broker failover.
- The recovery script covers worker crash-after-staging and API restart retrieval on one host; it does not test provider billing, multi-region or managed-service failover.
- Artifact size limited to 10 MiB and PDF/text/JSON only; no rendering/parser pipeline (W04+).
- No UI/imagegen work; UI approval is still PENDING. No W04 work started.

## Changed files

Created/modified only within W03 writable paths: `backend/erratascope_service/**`; `backend/migrations/**`, `backend/alembic.ini`, `backend/requirements-service.lock`, `backend/.dockerignore`, `backend/README-W03.md`; `backend/tests_w03/**`; `infra/w03/**` (Dockerfile, compose.yaml, db init, recovery script/helper, hosted prerequisites); `docs/evidence/W03/**` (OpenAPI, verification, recovery, inventories, this report); `.local/w03/**`; `docs/execution/handoffs/W03-attempt-01.md`; worker lock. No accepted domain code/tests, W01/W02 evidence, protected documents, baselines, reviews, `.env.local` or Git metadata was modified.

## Repair 01 (attempt 02) â€” R1â€“R4

Baseline: `docs/execution/baselines/W03-repair-01-baseline.json` â€” **PASS** (235 hashes, 294 links) before edits and after. Starting inventory: **43/43 SHA-256 matches**; verified history backup at `.local/w03/history/attempt-01-before-02/` with 43 files + manifest (all copied hashes match). Migration `0002_staging` was added; already-applied `0001_foundation` was not rewritten and the existing persistent volume was upgraded in place (no reset/deletion).

### Results

| Repair | Before (review 01 red case) | After / evidence |
|---|---|---|
| **R1 replay authorization** | Revoked actor's same-key review/job replay returned cached 201/202; viewer could list members; API/worker/dispatcher carried migrator config | Every mutation route authorizes current membership/action **before** replay and again on uniqueness-race fallback; create-project replay verifies continuing access to the cached project (revoked â†’ 404). Demotion â†’ 403; owner-only member list. Migrator DSN removed from api/worker/dispatcher (`migrator-boundary.json`); JWT allowlist narrowed to RS256/ES256. Tests: `test_r1_authorization.py` (10). |
| **R2 API contract** | Missing GET project / PUT / DELETE member; flat errors; caller X-Request-ID trusted; events unbounded bare list | Added GET project detail, owner-only PUT (200) and DELETE (204), self/last-owner guards with project-row locks and concurrent-owner tests. Nested `{error:{code,message,details},request_id}` with server UUID4, fresh per request and echoed on errors; caller header not trusted. All collection routes use stable keyset `{items,next_cursor}` pagination, limit 1â€“100; events use `after_seq`/limit and cursor = last returned sequence when more. OpenAPI regenerated. Tests: `test_r2_api_contract.py` (14). |
| **R3 staging/orphans** | DB rejection after staged bytes left an untracked file; upload buffered body under an open auth transaction | Bounded chunked staging with SHA/size, auth transaction closed before body I/O, new `upload_staging` journal with lease/state, short finalization transaction and fresh re-authorization. Proven rollback cleans only own unreferenced bytes; ambiguous results are left for reconciliation. Reconciler honors leases/grace/fresh references, skips symlinks/unknown paths, preserves committed and live bytes, and collects abandoned/unreferenced generated files; non-ASCII disposition via RFC 5987. Tests: `test_r3_staging.py` (11), including real PostgreSQL CHECK rejection and interrupted/live/concurrent staging. |
| **R4 receipts/fencing** | Ack-loss after real commit deleted the committed receipt bytes; heartbeat revived expired attempts; cancellation left attempt running; outbox ignored claim token | Commit/ack-loss settlement uses a fresh independent session: committed stage/result keeps original bytes/identity; redelivery/reconciliation detects missing/corrupt receipts via one `receipt_integrity_failed` event without minting a replacement. Real heartbeat thread; heartbeat and commit fence on fresh status/token/valid lease; expired attempts cannot revive; cancellation closes the attempt with `ended_at`/`outcome=cancelled` and blocks commit. Bounded retry delays 1s/5s; outbox finalization fenced by claim token/lease; per-job generation/event allocation under row locks. Tests: `test_r4_fencing.py` (9). |

### Commands and exits

| Command | Exit | Evidence |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-01-baseline.json` (initial/final) | 0 / 0 | PASS, 235 hashes / 294 links |
| inventory SHA-256 check (43 files) + verified backup | 0 / 0 | 43/43 match; manifest `all_match=true` |
| `docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet` | 0 | valid; migrator DSN only on migrate/test |
| `docker compose â€¦ build` | 0 | rebuilt pinned image |
| `docker compose â€¦ run --rm migrate` | 0 | upgraded existing volume `0001_foundation -> 0002_staging` |
| `docker compose â€¦ up -d --wait api worker dispatcher` | 0 | healthy |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests_w03` | 0 | **82 W03 tests OK** (32.5 s) |
| `docker compose â€¦ run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json` | 0 | **11/11 checks** |
| `docker compose â€¦ run --rm test python -m erratascope_service.cli export-openapi --output /local/openapi.json` | 0 | `openapi.json` regenerated |
| `powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1` | 0 | crash exit 43; recovered on attempt 2; events ordered with exactly one succeeded; receipt digest matches; API restart retrieval preserved |
| `python scripts/verify_execution_framework.py --baseline â€¦W03-repair-01-baseline.json` (final) | 0 | PASS, 235 hashes / 294 links |

### Gate status after repair

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/flow | **PASS** | 0002 upgraded an existing 0001 DB preserving data; 92 domain + persistence/migration tests |
| G2 auth/artifacts | **PASS** | replay authorization, owner-only listing, nested errors, bounded pagination, staged/orphan lifecycle, connected flow 11/11 |
| G3 idempotency/reviews | **PASS** | replay/current-auth, concurrent same-key, concurrent review one-winner, stale 409 |
| G4 recovery/fencing | **PASS** | real crash/reconciliation, ack-loss preservation, missing/corrupt receipt detection, heartbeat expiry/thread, cancellation, bounded retries, outbox token fencing, duplicate delivery |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI remain pending |

Attempt-01 evidence files remain untouched; attempt-02 recovery files are `recovery-attempt-02.json`, `recovery-restart-attempt-02.json`, `recovery-api-retrieval-attempt-02.json`. No provider call, credential access, Git, UI, hosted deployment or W04 work occurred. Limits: single-host local stack; no multi-node/broker-failover or hosted storage/RLS validation; local development credentials only.


## Repair 02 (attempt 03) — storage ownership, GC fencing and exact paths

Baseline: `docs/execution/baselines/W03-repair-02-baseline.json` — **PASS** (251 hashes, 307 links) before edits and after. Starting inventory: **53/53 SHA-256 matches**; history backup `.local/w03/history/attempt-02-before-03/` (53 files + manifest, all copied hashes match). Applied migrations `0001_foundation` and `0002_staging` were left immutable; **`0003_staging_fencing`** adds staging owner kind/job/attempt columns and the `ambiguous` state and upgraded the existing volume in place without reset.

### R1 — storage ownership isolation (PASS)

- **Physically separate storage:** test executions mount `erratascope-w03_test_artifacts` at `/var/lib/erratascope/test-artifacts` and default `W03_ARTIFACT_ROOT` there. The application volume is mounted separately at `/var/lib/erratascope/app-artifacts` for explicit sentinel/recovery use. Application API/worker/dispatcher retain `/var/lib/erratascope/artifacts`. A test-database reset can no longer invalidate application ownership.
- **Identity binding:** `.store-identity.json` (store UUID + credential-free `host:port/database`) is required for populated stores. Collectors and finalizers refuse mismatched identities before deletion; a populated unmarked store fails closed. Adoption is explicit and reference-validated.
- **Adoption of existing app store:** `adopt-store --confirm` reported 9 owned files, 9 referenced, 0 unreferenced, 0 unknown; bound to `db:5432/erratascope`. Test root independently bound to `db:5432/erratascope_test` (`store-isolation-attempt-03.json`).
- **Sentinel:** `sentinel-attempt-03.json` records a main artifact and receipt created via the real API/worker, a full isolated test-DB reset + test-store GC, then byte-identical re-download: artifact SHA-256 `2f45fe68…a2bb`, receipt SHA-256 `45ab2c09…d3a5`, `before_after_artifact_equal=true`, `before_after_receipt_equal=true`.
- **Historical byte loss:** read-only pre-change audit `legacy-artifact-audit-attempt-03.json`: **50 main artifact rows, 9 readable, 41 missing** (`MISSING`). No pre-review byte inventory exists; cause/time per row cannot be established. Rows/hashes are preserved, no rows were deleted and no replacement receipts minted. Only fresh sentinel objects claim future intactness.

### R2 — staging cleanup/finalization mutual safety (PASS)

- Uploads renew staging ownership during slow streams via short fresh sessions (no DB transaction during I/O). Receipt staging rows are owned by `owner_kind='result'`, `owner_job_id`, `owner_attempt_token`; the real job heartbeat renews both job and staging leases.
- Finalization locks/revalidates the same staging row (state, owner kind/job/token, unexpired lease), verifies actual promoted bytes, and commits only while ownership is current. Expired/lost staging cannot produce a successful upload or receipt: upload returns bounded `STAGING_LEASE_LOST`/409; worker attempt retries/fails safely.
- GC applies grace to journaled and unjournaled candidates; protects staging owned by a running/current job (renewing the lease), preserves committed artifacts, ambiguous/unknown bytes and live leases, and deletes journal rows after safe reclamation so abandoned rows cannot monopolize a batch. No cleanup runs while another session holds the same staging lock; failure paths roll back before fresh-session cleanup.
- Commit-uncertainty paths preserve bytes: uploads that commit then raise return the committed artifact (bytes verified); worker ack-loss settlement keeps the original receipt; truly ambiguous rows are marked `ambiguous` and retained. `ack_loss_after_commit` and `ambiguous_after_commit` regressions pass.
- Tests: `test_storage_fencing.py` (7) — slow upload across renewal; expired staging cannot finalize upload; receipt-stage expiry with a valid job lease cannot produce succeeded/missing bytes (GC protects/renews, receipt readable); unknown notes/staging contents preserved; internal symlink not followed; symlinked project dir rejected; ambiguous committed upload preserved. Existing ack-loss/duplicate/cancellation/heartbeat/retry/outbox tests retained.

### R3 — exact generated paths and no symlink traversal (PASS)

- Only exact layouts are recognized: `<32 lowercase hex project>/<32 lowercase hex artifact>.bin` and `.staging/<32 project hex>/<32 artifact hex>.part`; unknown names/extensions/directories are preserved. A matching shape still requires store identity/reference/lease checks.
- Path components are validated lexically before any resolution, then `lstat`-checked; reads/writes use `O_NOFOLLOW`, promotion verifies the final regular file, deletes refuse symlinks, and directory traversal does not follow links. Internal symlinks (including targets still inside the store) are rejected/ignored for read/write/promote/delete; no broad recursive deletion.
- Tests cover internal/external links, unknown `notes/keep.bin` and unknown `.staging` contents, valid stale orphans collected, committed artifacts immutable/readable.

### Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-02-baseline.json` (initial/final) | 0 / 0 | PASS, 251 hashes / 307 links |
| inventory SHA-256 verification (53 files) + verified backup | 0 / 0 | 53/53 match; `all_match=true` |
| read-only main-store audit (`audit_main_store.py`) | 0 | 50 rows, 9 readable, 41 missing |
| `docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet` | 0 | valid; test/app roots separated by volume |
| `docker compose … build` | 0 | rebuilt pinned image |
| `docker compose … run --rm migrate` (twice) | 0 / 0 | existing volume upgraded `0002_staging -> 0003_staging_fencing`; second run idempotent |
| store adoption (`adopt-store --confirm`, app DB/root) | 0 | 9/9 present generated files referenced; identity `db:5432/erratascope` |
| sentinel integration (`test_storage_isolation.MainDataSentinelTests`) | 0 | main artifact+receipt byte-identical after isolated reset/GC |
| `docker compose … run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose … run --rm test python -m unittest discover -s tests_w03` | 0 | **93 W03 tests OK** (48.7 s) |
| `docker compose … run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json` | 0 | **11/11 checks** |
| `docker compose … run --rm test python -m erratascope_service.cli export-openapi --output /local/openapi.json` | 0 | OpenAPI regenerated |
| `powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1` | 0 | attempt-03: crash exit 43, recovered attempt 2, ordered events, one succeeded event, receipt digest matches, API restart retrieval preserved |

### Gate status after repair-02

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | 0003 upgraded existing DB; 92 domain + migration tests; 0001/0002 unchanged |
| G2 auth/artifacts | **PASS** | isolated storage/identity, sentinel preservation, GC/lease safety, exact paths/no-symlinks; 11/11 connected flow |
| G3 idempotency/reviews | **PASS (retained)** | replay/current-auth, concurrent convergence, review races |
| G4 recovery/fencing | **PASS** | heartbeat/staging renewal, GC/finalization race, ack-loss/ambiguous preservation, stale/cancellation/outbox fencing, attempt-03 crash/restart evidence |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

Historical loss limitation: 41/50 pre-repair main artifact rows were already missing before this attempt; there is no pre-review byte inventory, so cause/time cannot be attributed and no restoration is claimed. Named-volume retention does not imply byte integrity. Legacy rows/events are preserved; future safety is demonstrated only on fresh synthetic objects. No provider calls, credentials, Git, UI, hosted deployment or W04 work occurred; no volumes or applied migrations were reset.

## Repair 03 (attempt 04) — lease, session ownership and filesystem confinement

Baseline: `docs/execution/baselines/W03-repair-03-baseline.json` — **PASS** (266 hashes, 320 links) before edits and after. Starting inventory: **63/63 SHA-256 matches**; verified backup `.local/w03/history/attempt-03-before-04/` (63 files + manifest, all copied hashes match). Applied migrations `0001_foundation`, `0002_staging`, `0003_staging_fencing` were left immutable; no new migration was needed. Main/test stores and all prior volumes/evidence preserved.

### R1 — expired upload ownership cannot be renewed (PASS)

- `renew_staging()` is now one atomic conditional UPDATE: row must be `active`, `owner_kind='upload'`, not job-owned, and have `lease_until > captured_now`. A reclaimed/expired/superseded row returns `STAGING_LEASE_LOST`.
- Finalization no longer renews first. It locks the staging row and requires current state/owner/lease before promotion, then verifies actual bytes and commits. Expired ownership → bounded **409**, no artifact, no idempotency row, only the operation's own uncommitted bytes cleaned up.
- Slow streams still renew via short fresh transactions with no DB transaction across body I/O. Tests: slow upload across renewal (app-side streaming delay, lease 3 s, total >3 s) succeeds; expiry **without GC** → 409 with no artifact/idempotency/staging; expiry followed by GC → 409. Received receipt staging remains tied to job/attempt heartbeat and existing GC protection.

### R2 — collector identity derived from the actual session (PASS)

- `reconcile_orphans` derives ownership from its actual SQLAlchemy session: `session.get_bind()` host/port plus `SELECT current_database()`. An optional caller-supplied identity is only a secondary assertion; omitted/forged values cannot override the real session. Absent binding/mismatched marker fails closed before any reference query/deletion; collection never adopts or rewrites a marker.
- Real two-engine regressions use the test database and the application database: a committed artifact registered in the test DB is preserved when the collector runs on an application-DB session (a) with no hint and (b) with a forged test-DB hint; (c) `jobs.reconcile_once` with app-DB settings against the test-root store refuses before deletion. Matching test-DB sessions still collect valid stale orphans.
- Store roots remain physically separate (`test-artifacts` vs `app-artifacts`), each identity-bound; no credentials appear in markers/errors/evidence.

### R3 — directory-relative no-follow confinement (PASS)

- Configured root is validated for symlink traversal **before** resolution, required to be a directory, and pinned with an `O_DIRECTORY|O_NOFOLLOW` descriptor. `.staging`/project directories are opened relative to pinned descriptors with no-follow; file open/create/unlink and staging→final promotion use parent-relative operations and pinned destination/source descriptors. Read/delete/promotion/abort all use the pinned components, so a parent swap after checking cannot redirect onto external bytes.
- Abort unlinks only the pinned staging entry; promotion renames between pinned staging/final project descriptors; a swapped destination parent cannot receive/redirect the rename. Canonical keys are validated with full-string regex only (`fullmatch`), rejecting trailing newline/control characters; unknown on-disk names/extensions remain untouched.
- Real Linux tests with deterministic fault hooks: delete/read/promote/abort after a parent directory swap never touch external sentinels; symlinked configured root rejected; trailing-newline key rejected; canonical round-trip and stale orphan cleanup remain green; unknown `notes/keep.bin` survives.

### Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-03-baseline.json` (initial/final) | 0 / 0 | PASS, 266 hashes / 320 links |
| inventory SHA-256 verification (63 files) + verified backup | 0 / 0 | 63/63 match; `all_match=true` |
| read-only main-store audit (attempt-04) | 0 | 81 rows, 40 readable, 41 missing (same historical IDs) |
| `docker compose … config --quiet` / `build` | 0 / 0 | isolated volumes; repaired image built |
| `docker compose … run --rm migrate` (twice) | 0 / 0 | head `0003_staging_fencing`; idempotent |
| `docker compose … run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose … run --rm test python -m unittest discover -s tests_w03` | 0 | **101 W03 tests OK** (49.5 s) |
| sentinel test through isolated reset/GC | 0 | main artifact/receipt byte-identical; `sentinel-attempt-04.json` |
| `verify-foundation --output /local/verification.json` | 0 | **11/11 checks** |
| `export-openapi --output /local/openapi.json` | 0 | OpenAPI regenerated |
| `infra/w03/recover.ps1` | 0 | attempt-04 crash exit 43; recovered attempt 2; ordered events, one succeeded, receipt digest matches, API restart retrieval preserved |

### Historical byte-loss status

Attempt-04 audit: **81 main artifact rows, 40 readable, 41 missing**. The 41 missing IDs exactly match the previously recorded legacy losses; the additional 40 rows are fresh sentinel/verification/job receipts and are readable. No pre-review byte inventory exists, so the time/cause of each legacy loss cannot be attributed. Rows/events were preserved; no replacement receipts/bytes were minted and no historical integrity is claimed. `store-isolation-attempt-04.json` records app/test root identities, marker store IDs, sentinel hashes and the audit counts without secrets.

### Gate status after repair-03

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | 0001–0003 unchanged; 0003 head idempotent; domain/migration tests |
| G2 auth/private artifacts | **PASS** | session-derived ownership, expired-lease rejection, directory-relative confinement, sentinel preservation |
| G3 idempotency/reviews | **PASS (retained)** | API/auth/replay/review-race tests unchanged |
| G4 recovery/fencing | **PASS** | upload/receipt lease fencing, GC/finalization, ack-loss/ambiguous preservation, attempt-04 crash/restart evidence |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

Limitations: local single-host Linux evidence only; no hosted storage/RLS/broker; legacy 41 missing bytes remain unexplained and unreplaced; recovery covers deterministic local crash/restart, not multi-node failures. No provider calls, credentials, package changes, Git, UI, hosted deployment or W04 work occurred.

## Repair 04 (attempt 05) — deterministic descriptor lifetime

Baseline: `docs/execution/baselines/W03-repair-04-baseline.json` — **PASS** (285 hashes, 339 links) before edits and after. Starting inventory: **70/70 SHA-256 matches**; verified backup `.local/w03/history/attempt-04-before-05/` (70 files + manifest, all copied hashes match). No migrations or schema changes; applied `0001`–`0003` remain immutable.

### R1 — explicit descriptor ownership (PASS)

- `ArtifactStore` gained idempotent `close()` and context-manager support. Initialization wraps root open, identity-marker validation, and subdirectory setup; any failure closes the pinned root descriptor. `close()` clears the stored fd before `os.close`, making double-close safe and unable to close a reused descriptor.
- `_project_fd()` now closes its intermediate `.staging` fd whenever project open/create fails, closes a newly opened project fd if the post-open hook raises, and preserves O_DIRECTORY/O_NOFOLLOW semantics. `StagingUpload` construction closes its pinned parent and partially opened file on exclusive-create/fdopen/hook failure. Promotion closes destination/source descriptors on success and failure and removes its own staging entry on pre-rename failure.
- Production owners close exactly what they own: `jobs.verify_receipt()` (including early returns), `execute()`, `_settle_after_exception()`, every `reconcile_once()` pass (wrapper + `finally`), the FastAPI app store at lifespan shutdown (including startup failure), CLI `adopt-store` (contextlib.closing), and `export-openapi` (one-shot store close). Route consumers use the app-owned/borrowed store and do not close it. Marker read/write and file-read fdopen paths close descriptors on failure.
- Behavioral boundaries retained: expiry-without-GC 409, session-derived collector identity (omitted/forged hints refused), parent-swap confinement, lease/GC/receipt fencing, auth/API/idempotency/ack-loss tests all still pass.

### Real descriptor evidence

`descriptor-evidence-attempt-05.json` (actual `/proc/self/fd` entries targeting the test store, real test DB):

| Path | Before | After | Calls |
|---|---|---|---|
| successful `verify_receipt` | 1 | 1 | 12 |
| `reconcile_once` with valid receipt | 1 | 1 | 8 |
| constructor identity mismatch (raises) | 0 | 0 | 8 |
| app lifespan startup/shutdown | 1 | 1 | — |

Additional regressions assert bounded descriptors for malformed marker construction, rejected staging symlink, duplicate staging create, hook failures at `after_project_dir_open` / `before_staging_create` / `before_promote_rename`, cancelled execute, and missing-receipt reconciliation; sentinel bytes and readable receipts remain unchanged. No garbage collection or process exit is relied on.

### Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-04-baseline.json` (initial/final) | 0 / 0 | PASS, 285 hashes / 339 links |
| inventory SHA-256 verification (70 files) + verified backup | 0 / 0 | 70/70 match; `all_match=true` |
| `docker compose … config --quiet` / `build` | 0 / 0 | isolated test storage; repaired image |
| `docker compose … run --rm migrate` (twice) | 0 / 0 | head `0003_staging_fencing`; idempotent |
| `docker compose … run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose … run --rm test python -m unittest discover -s tests_w03` | 0 | **110 W03 tests OK** (50.9 s) |
| descriptor evidence capture | 0 | 1→1 verify (12), 1→1 reconcile (8), 0→0 constructor (8), 1→1 app lifespan |
| sentinel through isolated reset/GC | 0 | fresh main artifact/receipt byte-identical (`sentinel-attempt-05.json`) |
| `verify-foundation` | 0 | **11/11 checks** |
| `export-openapi` | 0 | OpenAPI regenerated |
| `infra/w03/recover.ps1` | 0 | attempt-05: crash exit 43, recovered attempt 2, ordered events, one succeeded, receipt digest matches, API restart retrieval preserved |

### Historical byte-loss status

Final attempt-05 audit: **110 main artifact rows, 69 readable, 41 missing**. The 41 missing IDs remain the same legacy losses; no pre-review byte inventory exists, so cause/time cannot be attributed. Rows/events were preserved; no replacement receipts/bytes were minted. New sentinel/verification/recovery receipts are readable and demonstrate only future safety.

### Gate status after repair-04

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | 0001–0003 immutable; head idempotent; domain/migration tests |
| G2 auth/private artifacts | **PASS** | descriptor ownership, session-derived identity, lease/path confinement, sentinel preservation |
| G3 idempotency/reviews | **PASS (retained)** | replay/current-auth, concurrent convergence, review races |
| G4 recovery/fencing | **PASS** | bounded descriptors in repeated verification/reconciliation, receipt/lease fencing, attempt-05 crash/restart evidence |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

Limitations: local single-host Linux evidence only; no hosted storage/RLS/broker; legacy 41 missing bytes remain unexplained/unreplaced; recovery is deterministic local crash/restart, not multi-node. No provider calls, real credentials, package changes, Git, UI, hosted deployment, W04 or delegation occurred.

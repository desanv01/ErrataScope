# W03 local foundation service

Offline local PostgreSQL/Valkey/FastAPI foundation for ErrataScope. This implements the
non-UI P2 slice only: migrations and immutable version persistence, JWT/project
authorization, private local artifacts, typed routes, idempotency and review concurrency,
durable RQ jobs with attempt tokens/outbox/reconciliation, and a connected synthetic
artifact-digest flow. Hosted P2 readiness is documented but **not executed**.

## Prerequisites

- Docker Desktop with the Linux engine (observed Engine 29.8.1, Compose v5.5.1).
- Pinned images (all verified locally):
  - `python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3`
  - `postgres:17-bookworm@sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27`
  - `valkey/valkey:8.1.4-alpine@sha256:e706d1213aaba6896c162bb6a3a9e1894e1a435f28f8f856d14fab2e10aa098b`
- `backend/requirements-service.lock` is a byte-for-byte copy of the protected
  `W03-linux-requirements.lock`; the image installs it with `--require-hashes --only-binary=:all:`.

Compose project is exactly `erratascope-w03`; only `127.0.0.1:18080` is published. Build
context is `backend/`, so credentials and root-only files cannot enter the image.

## Setup and verification sequence

```powershell
docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet
docker compose -p erratascope-w03 -f infra/w03/compose.yaml build
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm --no-deps test python -m erratascope_service.cli bootstrap-local --out /local/dev-auth
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait db broker
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait api worker dispatcher
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests -v
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w03 -v
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json
```

`bootstrap-local` refuses to overwrite existing dev keys/tokens unless `--force` is passed.
The private key and synthetic tokens live only under `.local/w03/dev-auth/` (git-ignored,
never published). The API mounts only `jwks.json`; worker/dispatcher/migrate never see keys.

## Local services and data

- `api` — FastAPI/uvicorn on `127.0.0.1:18080`; OpenAPI at `/openapi.json`, docs UI disabled.
- `worker` — RQ worker using the JSON serializer for the `w03` queue.
- `dispatcher` — claims the PostgreSQL outbox and reconciles stale jobs.
- `db` — PostgreSQL with the `erratascope` schema; main example data is preserved.
- `broker` — Valkey without persistence.
- `migrate` — one-shot Alembic upgrade (idempotent; can be rerun).
- `test` — same image, mounts `.local/w03` at `/local`, uses the dedicated
  `erratascope_test` database and `w03-test` queue so the running example stack is never
  consumed or reset by tests.

Named volumes `erratascope-w03_pgdata` and `erratascope-w03_artifacts` are preserved when
services stop. Never delete volumes or run global Docker prune for this packet.

## Recovery script

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1
```

The script stops only this project's worker, seeds a synthetic job, crashes after artifact
bytes are staged but before the transaction commit (`W03_TEST_FAILPOINT=crash_after_stage`,
exit 43), expires the lease, reconciles/redispatches, restarts the worker with existing
volumes, verifies the committed receipt and then restarts the API and verifies retrieval.
Failpoints are reachable only through local container environment variables; there is no
HTTP failpoint endpoint. Evidence is written to `docs/evidence/W03/recovery*.json`.

## Local development roles

The Compose database init script creates local-only credentials for two roles:

- `erratascope_migrator` owns the `erratascope` schema and runs Alembic.
- `erratascope_app` has schema USAGE and table DML only; it cannot create schemas/tables.

These known local-development passwords must never be reused for hosted deployments.
The migration adds immutability triggers that block UPDATE/DELETE on artifacts, bundles,
domain versions, bundle members, review events, job events and stage results; review
candidates allow only `current_revision` to change.

## Auth and authorization

JWT bearer tokens are verified in local mode against `.local/w03/dev-auth/jwks.json`
(RS256, issuer/audience/expiry pinned). Hosted mode requires an HTTPS JWKS and fails
startup with `HOSTED_STORAGE_NOT_READY`; there is no client identity-header bypass.
Membership in PostgreSQL is the authorization authority: foreign projects return 404,
insufficient roles return 403, and viewers cannot mutate.

## Jobs

Job creation writes job + `queued` event + outbox row in one transaction. The dispatcher
claims outbox rows with `FOR UPDATE SKIP LOCKED`, enqueues the job ID over RQ/JSON and marks
it sent. The worker claims with an attempt token and lease, verifies artifact bytes, stages
the receipt bytes, then commits stage result + result artifact + success event only if its
token still owns the job. Duplicate delivery, stale leases, lost broker messages and
cancellation are covered by tests and the reconciliation loop. Receipts are idempotent.

## Evidence

- `docs/evidence/W03/openapi.json` — exported contract.
- `docs/evidence/W03/verification.json` — connected flow observations (sanitized).
- `docs/evidence/W03/recovery*.json` — real crash/restart/API-restart evidence.
- `docs/evidence/W03/IMPLEMENTATION_REPORT.md` — gates, commands/exits, limitations.
- `docs/execution/handoffs/W03-attempt-01.md` — worker handoff.

No provider calls, credentials, hosted provisioning, Git, UI or W04 work are part of W03.

## Repair 01 (attempt 02) contract notes

- **Errors:** every handled error returns `{"error":{"code","message","details"},"request_id":<uuid>}`. The service generates a fresh UUID4 per request, ignores caller `X-Request-ID` as authoritative, and echoes the generated UUID in the response header (including handled errors). Validation, auth, routing, DB and runtime errors use the same envelope.
- **Routes:** `GET /api/v1/projects/{p}` returns project detail/role. `PUT /api/v1/projects/{p}/members/{actor}` (owner-only, body `{"role": ...}`) creates or updates and returns 200; `DELETE` revokes and returns 204. Both require `Idempotency-Key` and re-check current authorization on replay. `POST .../members` remains a documented compatibility add route. Self-demotion/removal and last-owner removal are rejected (409); project-row locking serializes concurrent owner changes. Member listing is owner-only.
- **Pagination:** project, artifact, bundle, member, job-event and review-event listings return `{items, next_cursor}` with `limit` 1–100 (default 50). Entity listings use opaque keyset cursors over `(created_at, id)` (members use `(created_at, actor_id)`); event listings use `after_seq` and return the last returned sequence as `next_cursor` when more rows exist, otherwise `null`. Invalid/oversized limits return 422; malformed cursors return 400 `INVALID_CURSOR`.
- **Uploads:** authorization runs before body I/O and its transaction is closed; bytes stream in bounded chunks to a private staging file while SHA-256/length are computed. `upload_staging` (migration `0002_staging`) journals ownership, lease and state (`active`/`finalized`/`abandoned`). Finalization uses a short transaction, re-checks current authorization, promotes bytes atomically and exposes only committed artifacts. Proven rollbacks delete only that operation's unreferenced files; ambiguous outcomes are left/quarantined. `reconcile --once`/the dispatcher reclaim abandoned and unreferenced generated files after the configured grace, using fresh artifact references and lease fences; symlinks and unknown paths are never followed/deleted. `Content-Disposition` carries an RFC 5987 UTF-8 filename.
- **Jobs:** execution runs a real heartbeat thread; heartbeat/commit fencing reloads current status/token/lease and refuses expired or superseded attempts. Cancellation closes the running attempt with `ended_at`/`outcome=cancelled`. A commit acknowledgement loss or commit error is settled through a fresh session: committed stage/result metadata keeps its original receipt bytes and identity; uncommitted own bytes are removed and retried with bounded `1s/5s` delays; uncertain states are retained for reconciliation. Redelivery/reconciliation verifies succeeded receipts and records an idempotent `receipt_integrity_failed` event for missing/corrupt bytes without minting a replacement or altering success history. Outbox finalization is fenced by the dispatcher's claim token/lease; per-job generation/event allocation happens under the job row lock.
- **Privilege boundary:** `W03_MIGRATOR_DATABASE_URL` is present only for the explicit `migrate` and `test` services; API, worker and dispatcher receive only the app DSN. The app role still has schema USAGE + DML, not DDL/ownership.
- **Recovery evidence:** `recover.ps1` writes attempt-specific files `recovery-attempt-02.json`, `recovery-restart-attempt-02.json`, `recovery-api-retrieval-attempt-02.json`; attempt-01 evidence remains preserved in the verified history backup under `.local/w03/history/attempt-01-before-02/`.
- **JWT:** allowlist is limited to RS256/ES256; issuer/audience/expiry/signature checks and hosted fail-closed startup remain enforced.

## Repair 02 (attempt 03) storage ownership notes

- **Physically isolated test storage:** the `test` service mounts a dedicated `test_artifacts` volume at `/var/lib/erratascope/test-artifacts` and defaults `W03_ARTIFACT_ROOT` there. The application volume is mounted separately at `/var/lib/erratascope/app-artifacts` for explicit recovery/sentinel use only. Ordinary tests, the test database reset and test GC can never walk the application store. Application services keep `/var/lib/erratascope/artifacts`.
- **Store identity binding:** every persistent store contains `.store-identity.json` with a random store UUID and a credential-free database identity (`host:port/database`). A populated store without a marker fails closed; a collector whose database identity does not match the marker refuses to run/deletes nothing. The existing application store was adopted explicitly with `adopt-store --confirm`, after validating that every present generated file is referenced by actual application artifact/staging rows (9/9 referenced; no unknown files). The test store is lazily bound to the dedicated test database identity.
- **Adoption command:** `python -m erratascope_service.cli adopt-store --confirm` (runs as the privileged migrate/test context against the intended database/root). Unreferenced generated files or unknown files require explicit `--accept-unreferenced-generated`/`--accept-unknown`; nothing is deleted by adoption.
- **Exact generated layouts only:** `<32 lowercase hex project>/<32 lowercase hex artifact>.bin` and `.staging/<32 hex project>/<32 hex artifact>.part` (plus the store marker). Unknown directories/extensions/names such as `notes/keep.bin` are preserved. Checks are lexical before resolution and use `lstat`/`O_NOFOLLOW`; symlinks are rejected for read/write/promote/delete and never followed, even when their target stays inside the root. No broad deletion.
- **Lease/GC/finalization fencing:** uploads renew their staging lease during slow streams without holding a DB transaction; receipts are registered with `owner_kind='result'`, `owner_job_id`, `owner_attempt_token` (migration `0003_staging_fencing`) and renewed by the job heartbeat. Finalizers lock and revalidate the same row (state/owner/lease), verify the actual bytes, and cannot commit after GC/lease loss. GC applies grace to journaled and unjournaled candidates, protects live job-owned staging, never deletes ambiguous/committed/unknown bytes, and removes journal rows after safe reclamation. Ambiguous commit outcomes are marked `ambiguous` and retained. Upload finalization with an expired/lost staging lease returns a bounded 409 rather than success.
- **Historical byte loss:** a read-only audit before this repair found **50 main artifact rows, 9 readable, 41 missing** (`legacy-artifact-audit-attempt-03.json`). No pre-review byte inventory exists; the cause/time of each loss cannot be attributed. Rows/events are preserved, no replacement receipts were minted, and no missing history is claimed intact. New sentinel objects demonstrate future safety only.
- **Sentinel:** `sentinel-attempt-03.json` records a main artifact+receipt created through the real API/worker, then a full isolated test-database reset plus test-store GC, then byte-identical retrieval of both main objects.

## Repair 03 (attempt 04) boundary notes

- **Upload lease renewal (R1):** renewal is one atomic conditional UPDATE requiring the row to still be `active`, upload-owned, not job-owned, and to have an **unexpired** lease at the captured timestamp. Finalization no longer renews before checking; it locks the row and requires a current lease/state/owner, otherwise returns bounded `STAGING_LEASE_LOST`/409 with no artifact or idempotency response. Slow streaming renewal continues via short fresh transactions; expiry without GC, expiry followed by GC, and slow uploads across renewal are covered by real-DB tests.
- **Collector ownership (R2):** `reconcile_orphans` derives the store identity from the **actual SQLAlchemy session** (`bind` host/port + `current_database()`), not a process-global settings value. An optional caller identity is only an additional assertion; omitted or forged hints cannot override the session. Mismatched test/app-database sessions refuse before any deletion, including through `jobs.reconcile_once`. Matching sessions still collect stale owned orphans.
- **Directory-relative confinement (R3):** the configured root is validated before resolution (symlink root rejected) and pinned with an `O_DIRECTORY|O_NOFOLLOW` descriptor. Reads/writes/promotion/abort/deletion descend through directory fds and operate relative to verified parent descriptors (`openat`/`unlinkat`-style), so a parent directory swapped after a check cannot redirect onto external bytes. Abort and promotion use pinned staging/destination descriptors. Canonical keys use full-string regex only (trailing newline/control characters rejected); unknown on-disk names remain untouched. Deterministic parent-swap hooks exercise read/delete/promote/abort.
- **Evidence (attempt 04):** `sentinel-attempt-04.json`, `store-isolation-attempt-04.json`, `legacy-artifact-audit-attempt-04.json`, `recovery-attempt-04.json`, `recovery-restart-attempt-04.json`, `recovery-api-retrieval-attempt-04.json`. The read-only audit found **81 main rows, 40 readable, 41 missing**; the 41 missing IDs are the same historical legacy losses and remain explicit. Attempt-01/02/03 evidence is preserved.

## Repair 04 (attempt 05) descriptor lifetime notes

- `ArtifactStore` now has explicit, idempotent `close()` and context-manager support. It closes the pinned root descriptor on every initialization failure (identity mismatch, malformed marker, subdirectory setup error) and never relies on garbage collection/process exit. Descriptor cleanup is guarded by attribute reset before `os.close` so double-close cannot close a reused descriptor.
- `_project_fd` closes the intermediate `.staging` descriptor when opening/creating the project fails, and closes a freshly opened project descriptor if the post-open test hook raises. `StagingUpload` construction closes its pinned parent and any partially opened file on exclusive-create/fdopen/hook failures. Promotion closes source/destination descriptors on every path and removes its own staging entry when promotion fails before the existing try block.
- Production owners close what they own: `verify_receipt`, `execute`, `_settle_after_exception` and each `reconcile_once` pass; the FastAPI app closes its long-lived store at shutdown (startup failure included); CLI `adopt-store` uses `contextlib.closing`; `export-openapi` closes the one-shot app store. Borrowed stores (e.g. the app store used by routes) are never closed by consumers.
- Real `/proc/self/fd` evidence (`descriptor-evidence-attempt-05.json`, test DB/store): after warm-up, 12 successful `verify_receipt()` calls keep store descriptors at **1→1**; 8 `reconcile_once` passes keep **1→1**; 8 constructor identity-mismatch failures keep **0→0**; app startup/shutdown keeps **1→1**. Staging symlink/duplicate-create, hook failures, malformed markers, cancelled execution and missing-receipt reconciliation are all bounded with preserved sentinel bytes.
- Evidence uses attempt-05 names only: `descriptor-evidence-attempt-05.json`, `sentinel-attempt-05.json`, `store-isolation-attempt-05.json`, `legacy-artifact-audit-attempt-05.json`, `recovery-*-attempt-05.json`. The final read-only audit shows **110 main rows, 69 readable, 41 missing**; the 41 missing IDs are the same legacy losses and remain explicit. Attempt-01–04 evidence is preserved.

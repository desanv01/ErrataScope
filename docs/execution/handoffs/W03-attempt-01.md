# Worker handoff — W03 revision 2, attempt W03-attempt-01

Status: **READY_FOR_REVIEW** (acceptance, Git/GitHub checkpoint and W04 binding remain Codex's decision)
Packet: W03-persistence-jobs revision 2, attempt **01**
Started/finished (UTC): 2026-10-30T04:01:45Z / 2026-10-30T05:33:00Z (final checks)
Starting baseline and recheck: **PASS** — `docs/execution/baselines/W03-baseline.json`, **223 protected hashes, 281 links, 0 errors**, before and after.
Compose project: exactly `erratascope-w03` (services `db`, `broker`, `api`, `worker`, `dispatcher`, `migrate`, `test`); only `127.0.0.1:18080` published; no `container_name`, Docker socket, unrelated mounts or global prune.
Runtime: pinned `python:3.11.15-slim-bookworm@sha256:d29f48…e0c3`, `postgres:17-bookworm@sha256:858bb5…0d27`, `valkey/valkey:8.1.4-alpine@sha256:e706d1…098b`; protected Linux lock copied byte-for-byte (SHA-256 `7d53a786…d23`) and installed with hashes; installed freeze exactly matches 40/40 locked packages.
Harness: DeepSeek `deepseek-flash`, single worker, DSH Web GUI. Docker Engine 29.8.1 / Compose v5.5.1 (Docker access required the harness permission mechanism; no Docker configuration changed).
Network/credentials: only authorized image/PyPI dependency pulls and this project's local services. **No Nebius, hosted provisioning, `.env.local`, Git, UI or W04 work.** Hosted P2 remains NOT_RUN; UI/imagegen approval remains PENDING.

## Implemented behavior

- **Migrations/persistence (G1):** Alembic `0001_foundation` creates the `erratascope` schema tables/constraints (projects, memberships, artifacts, bundles, domain_versions, bundle_members, review_items/events, idempotency, jobs, job_attempts, outbox, job_events, stage_results). Migrator owns the schema; app role has USAGE + DML only. Immutability triggers block UPDATE/DELETE on sealed records; review candidates permit only `current_revision`. Migration applied twice (`0001_foundation`) with no error. Bundles are validated by the accepted W02 parser, normalized and hashed with accepted domain helpers; entity versions are immutable; reload reparses/revalidates and reproduces `input_hash`; altered reused versions return `DOMAIN_VERSION_CONFLICT`.
- **Auth/artifacts (G2):** JWT signature/issuer/audience/expiry/algorithm verification against local JWKS (hosted HTTPS variant coded but unverified); PostgreSQL membership is the authorization authority; foreign project → 404, insufficient role → 403, no identity-header bypass. Private artifact bytes with streaming 10 MiB limit, SHA-256/length verification, atomic writes, safe disposition, `nosniff`/`no-store`; corruption/missing bytes produce stable integrity errors. Hosted startup fails closed with `HOSTED_STORAGE_NOT_READY`.
- **Idempotency/review races (G3):** project/actor/operation/body-hash idempotency with exact replay, changed-body `IDEMPOTENCY_CONFLICT`, concurrent same-key convergence. Review decisions use row locks and exact `expected_revision`; concurrent decisions yield one 201 and one `REVIEW_REVISION_CONFLICT`; revision events are append-only.
- **Jobs/outbox (G4):** job + queued event + outbox in one transaction; dispatcher claims `FOR UPDATE SKIP LOCKED`, enqueues job ID with RQ JSON serializer and marks sent; worker claims with attempt token/lease, verifies artifact bytes, stages receipt bytes, then commits stage result + result artifact + success only if the token still owns the job. Duplicate delivery is a no-op; stale leases are requeued; lost broker messages are redispatched; cancellation removes the attempt token and blocks late commits; retries are bounded (3).
- **Recovery:** `infra/w03/recover.ps1` (with environment-gated failpoints; no HTTP failpoint endpoint) stops only this project's worker, seeds a synthetic job, crashes after staged bytes before commit (exit 43), expires the lease, reconciles/redispatches, restarts the worker with existing volumes, verifies the committed receipt, restarts the API and verifies retrieval.
- **Evidence:** `docs/evidence/W03/openapi.json` (live app, docs UI disabled), `verification.json` (11 connected checks, no secrets), `recovery.json` / `recovery-restart.json` / `recovery-api-retrieval.json`, `images.json`, `dependency-inventory.json`, `schema-inventory.json`, `IMPLEMENTATION_REPORT.md`. `infra/w03/hosted-prerequisites.md` documents the unrun hosted prerequisites.

## Commands actually run (project root; Docker project `erratascope-w03`, Compose file `infra/w03/compose.yaml`)

| Command | Exit | Observed result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-baseline.json` (initial and final) | 0 / 0 | PASS, 223 hashes / 281 links |
| `docker version` / `docker compose version` | 0 / 0 | Engine 29.8.1; Compose v5.5.1 |
| `docker compose … config --quiet` | 0 | valid isolated configuration |
| `docker compose … build` | 0 | image built from pinned Python base + protected lock |
| `docker compose … run --rm --no-deps test python -m erratascope_service.cli bootstrap-local --out /local/dev-auth` | 0 | fresh RS256 JWKS/private key/3 synthetic user tokens; API was stopped to avoid the bind-mount race |
| `docker compose … up -d --wait db broker` | 0 | both healthy |
| `docker compose … run --rm migrate` (twice) | 0 / 0 | `0001_foundation` applied; idempotent |
| `docker compose … up -d --wait api worker dispatcher` | 0 | all healthy; JSON-serialized RQ worker |
| `docker compose … run --rm test python -m unittest discover -s tests -v` | 0 | **92 accepted domain tests OK** |
| `docker compose … run --rm test python -m unittest discover -s tests_w03 -v` | 0 | **37 W03 integration tests OK** (19.1 s) |
| `docker compose … run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json` | 0 | **11/11 checks**, `secrets_recorded=false` |
| `docker compose … run --rm test python -m erratascope_service.cli export-openapi --output /local/openapi.json` | 0 | OpenAPI exported (48.9 KB) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1` | 0 | crash exit 43; job succeeded on attempt 2; stage result committed; receipt digest matches; API restart retrieval preserved |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-baseline.json` (final) | 0 | PASS, 223 hashes / 281 links |

Intermediate defects fixed in-scope (not mocked/skipped): PostgreSQL 15+ `public` CREATE restriction (Alembic metadata moved into migrator-owned schema), worker incorrectly requiring API JWKS, RQ worker JSON serializer mismatch, UUIDs in JSONB idempotency bodies, dedicated test DB/queue isolation, and reconciler/event-order grace.

## Required gates

| Gate | Result | Evidence / limits |
|---|---|---|
| G1 migrations/flow | **PASS** | Migration twice; schema/trigger inventory; bundle round-trip reproduces domain `input_hash` and result hash; 92 domain + persistence tests |
| G2 auth/artifacts | **PASS** | JWT negative/positive, foreign 404, viewer 403, private artifacts, integrity/missing/oversize checks, 11-check connected flow |
| G3 idempotency/review races | **PASS** | Replay/conflict, concurrent same-key convergence, concurrent review one-winner, stale 409, append-only events |
| G4 actual recovery | **PASS** | Real crash after staging (exit 43), stale-lease reconcile/redispatch, worker restart with preserved volumes, committed receipt (attempts=2), API restart retrieval |
| G5 hosted prerequisites | **PASS (documentation only)** | `infra/w03/hosted-prerequisites.md`; hosted execution **NOT_RUN**, P2 hosted/UI pending |

## Changed files

Created/modified only in W03 writable paths:

- `backend/erratascope_service/` — `__init__.py`, `config.py`, `errors.py`, `db.py`, `models.py`, `auth.py`, `artifacts.py`, `domain_adapter.py`, `schemas.py`, `services.py`, `jobs.py`, `api.py`, `cli.py`.
- `backend/migrations/env.py`, `script.py.mako`, `versions/0001_foundation.py`; `backend/alembic.ini`; `backend/requirements-service.lock`; `backend/.dockerignore`; `backend/README-W03.md`.
- `backend/tests_w03/` — `__init__.py`, `helpers.py`, `test_auth.py` (9), `test_artifacts.py` (7), `test_persistence.py` (6), `test_idempotency_review.py` (5), `test_jobs_recovery.py` (8), `test_connected_flow.py` (2) — 37 tests.
- `infra/w03/` — `Dockerfile`, `compose.yaml`, `db-init/01-roles.sh`, `recover.ps1`, `recover_helper.py`, `hosted-prerequisites.md`.
- `docs/evidence/W03/` — `openapi.json`, `verification.json`, `recovery.json`, `recovery-restart.json`, `recovery-api-retrieval.json`, `images.json`, `dependency-inventory.json`, `schema-inventory.json`, `IMPLEMENTATION_REPORT.md`.
- `.local/w03/**` (dev keys/tokens, test data/logs); `docs/execution/handoffs/W03-attempt-01.md`; worker lock.

No accepted domain code/tests, W01/W02 evidence, protected documents/baselines/reviews, `.env.local`, or Git metadata was modified.

## Resources and limitations

- Stopped only this attempt's Compose services (`docker compose -p erratascope-w03 -f infra/w03/compose.yaml stop`); named volumes `erratascope-w03_pgdata` and `erratascope-w03_artifacts` preserved. No container, job, server or other project left running by this attempt.
- Tests use a dedicated `erratascope_test` database and `w03-test` queue reset per module; the main example database/queue are untouched by tests.
- Hosted mode is fail-closed and unrun; local development credentials/synthetic keys must never be reused for hosted. No RLS/managed storage/managed broker was provisioned or validated.
- Recovery evidence covers worker crash-after-staging, redispatched work, worker restart and API restart on one host; not multi-node/broker-failover.
- Artifact limit 10 MiB, PDF/text/JSON only; no rendering/parser, UI, deployment, provider call or W04 work.
- No blockers. No gate claimed beyond actual observations.

## Return prompt

> Review ErrataScope W03 revision 2, worker attempt 01. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-01.md, docs/execution/packets/W03-persistence-jobs.md and docs/execution/bindings/W03-foundation-v1.md. Verify the W03 protected baseline, preserving accepted W01/W02 evidence and domain code. Independently check actual PostgreSQL migrations/version integrity, JWT/project/artifact authorization, idempotency and review races, RQ/outbox/attempt-token recovery and the connected local API flow. Mocks or skipped services do not establish integration pass. Hosted P2 acceptance remains open unless separately authorized and evidenced; no UI approval is implied. If W03 passes, record acceptance, perform the Git/GitHub checkpoint, bind eligible W04 scope and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt. Preserve the UI/imagegen approval gate.

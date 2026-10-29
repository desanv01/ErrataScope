# W03 foundation-v1 — bound implementation contract

Codex-owned, 30 October 2026. W03 revision 2, attempt 01. Prerequisite: [W02 acceptance](../reviews/W02-review-02.md) and [domain freeze](W02-observed-contracts.md). This implements the non-UI local P2 foundation; hosted acceptance remains an explicit later gate. Shared data/API/security contracts remain binding.

## Runtime, dependencies and local boundaries

Use Linux Docker containers through the already available Docker Desktop engine; do not run the RQ worker natively on Windows. Docker Engine 29.8.1 and Compose v5.5.1 were observed. Restricted shells may need their harness's permission mechanism to reach the Docker pipe; do not treat permission denied as proof Docker is absent.

Use these existing local images, pinned by their observed repository digests in Compose/Dockerfile:

| Purpose | Image |
|---|---|
| API/worker/test base | `python:3.11.15-slim-bookworm@sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3` |
| PostgreSQL | `postgres:17-bookworm@sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27` |
| Valkey | `valkey/valkey:8.1.4-alpine@sha256:e706d1213aaba6896c162bb6a3a9e1894e1a435f28f8f856d14fab2e10aa098b` |

Direct dependencies: FastAPI 0.162.0; Uvicorn 0.54.0; SQLAlchemy 2.1.6; Alembic 1.20.1; psycopg/binary 3.3.6; RQ 3.0.0; redis 8.1.0; PyJWT 2.15.1; cryptography 50.0.2; httpx 0.28.1; Pydantic 2.14.1. Dependency metadata resolution succeeded in the pinned Linux Python image. This establishes resolvability, not application compatibility; integration checks remain mandatory. The protected `W03-linux-requirements.lock` beside this binding freezes the complete observed Linux wheel set with hashes, including build tools. Copy it byte-for-byte to `backend/requirements-service.lock`; install with `pip install --require-hashes --only-binary=:all: -r ...`. No silent upgrades, Windows lock substitution or changes to the W01 environment. If a pin genuinely conflicts at runtime, report the precise error/proposed minimal correction to Codex.

Use sync SQLAlchemy/psycopg service transactions and FastAPI sync handlers for blocking DB work. Avoid unnecessary async/ORM mixing. Standard-library unittest plus httpx is sufficient for tests. Module root `backend/erratascope_service/`: config, auth, db/models, schemas, repositories/services, artifacts, jobs, API, CLI and helpers. Domain imports are one-way; the accepted domain package stays pure and protected.

Compose project exactly `erratascope-w03`; services `db`, `broker`, `api`, `worker`, `dispatcher`, `migrate`, `test`. No `container_name`, host Docker socket mount, unrelated project mount or global prune. Build context is `backend/` so root credentials/private source artifacts cannot enter the image. Dedicated named volumes for PostgreSQL and artifact bytes; all names belong to this Compose project. Expose only API `127.0.0.1:18080:8000`; no host DB/broker port needed. Never delete volumes or stop another project's services. Worker/dispatcher use the same built image. Default API docs UI disabled; expose OpenAPI JSON only. No frontend shell or visual design.

Network authorization: PyPI/files.pythonhosted.org and official image/documentation hosts for these dependencies, plus this project's local Docker services. No Nebius calls, account provisioning, hosted Supabase/Render writes, external project data or paid services. Synthetic inputs only. If package/image download or Docker access is blocked, report it; do not replace PostgreSQL with SQLite or claim integration pass from mocks.

## Authentication and authorization

Use JWT verification in both local and future hosted modes, with membership in PostgreSQL as authorization authority. Do not add a client-controlled identity header bypass. `W03_MODE=local` loads a locally generated public JWKS file; a CLI bootstrap generates an RSA test signing key under ignored `.local/w03/dev-auth/` and tokens for two synthetic users. Mount **only public JWKS** into API/worker, never the private key. Label local credentials development-only. Use HTTP only on the bound loopback local endpoint; do not publish these tokens or keys. The bootstrap must not overwrite existing keys without explicit operator action.

Hosted adapter config: `W03_MODE=hosted`, fixed HTTPS issuer and corresponding JWKS URL, audience, algorithm allowlist `RS256`/`ES256`, signature/issuer/audience/expiry validation, required UUID subject. No `none`, HS256, user-provided JWKS URLs, decode-only success or trusting user_metadata for permissions. Bound JWKS timeout and cache (<=10 minutes), one bounded refresh for unknown kid, no redirect to arbitrary hosts; fail closed on invalid configuration/key verification. Tests use a generated key/local JWKS transport; this does not establish real Supabase account integration. Current hosted storage adapter is absent: **hosted startup remains disabled** with explicit `HOSTED_STORAGE_NOT_READY`, even when JWT config is syntactically valid. No private hosted uploads until later authorized validation.

Membership roles: `owner`, `editor`, `reviewer`, `viewer`. Owner manages membership; owner/editor mutate project artifacts/bundles/jobs; owner/reviewer submit reviews; all members can read authorized resources. Do not derive project membership from token metadata. Removal/change of membership affects the next request. Auth missing/invalid ->401; known member lacking action role ->403; unknown/foreign project resources ->404. Never leak whether a foreign artifact/job exists. Owner self-removal/last-owner removal rejects409.

All service entry points require an actor and project, including artifact download/job events. Background execution uses only DB-pinned project/job context; it does not accept an actor/project from arbitrary broker payload. No Supabase Data API exposure: application schema `erratascope` is private. Use an app DB role with DML only and a separate migrator; revoke schema/table PUBLIC privileges. Membership checks remain mandatory even with server DB access. No user/auth schema modifications to a hosted Supabase project.

## Persistence and transactions

Implement Alembic migration(s) under `backend/migrations/`; configuration `backend/alembic.ini`. PostgreSQL is authoritative; no in-memory substitute for acceptance. UUID IDs, UTC timestamptz, bounded states, JSONB for validated payloads, SHA-256 for immutable payload/byte hashes. Require project-qualified composite foreign keys, unique constraints and explicit indexes supporting the following records:

| Record | Required fields and constraints |
|---|---|
| projects | id, name, created_by, created_at; create owner membership in same transaction |
| memberships | project_id, actor_id, role, created_at; unique project+actor |
| artifacts | id, project_id, server-generated storage_key, sha256, byte_length, media_type, original_name, state, created_by/at; ready bytes immutable; project+id unique |
| bundles | id, project_id, domain input_hash, schema/evaluator versions, canonical JSON bundle, created_by/at; immutable, project+input_hash unique |
| domain_versions | project_id, kind, version_id text, canonical payload/hash; unique project+kind+version_id; same ID/different content rejects409 |
| bundle_members | project_id, bundle_id, kind, version_id, payload_hash; composite refs to bundle and version records |
| review_items | id, project_id, artifact_id, content_hash, annotation text, current_revision integer starting0; immutable candidate fields |
| review_events | id, project_id, review_item_id, revision, actor_id, decision accepted/rejected, rationale, created_at; unique item+revision; append-only |
| idempotency | project_id, actor_id, operation, key, request_hash, response_status/body, resource_id; unique scope+key; transactionally stored with mutation |
| jobs | id, project_id, actor_id, kind artifact_digest, artifact_id, status, attempt_count, max_attempts, current_attempt_token, lease_until, next_event_seq, result_artifact_id/hash, created/updated timestamps |
| job_attempts | id, project_id, job_id, attempt_number, token UUID, start/end, outcome/error_code; unique job+number/token |
| outbox | id, project_id, job_id, dispatch_generation, available_at, claim/lease metadata, sent_at; unique job+generation |
| job_events | id, project_id, job_id, seq, event_type, safe payload, created_at; unique job+seq, ordered stable cursor |
| stage_results | project_id, job_id, stage_key, input_hash, result_artifact_id/hash; unique job+stage_key; immutable committed result |

`domain_versions` adapters extract snapshots, component instances, fact sets, fact versions, document versions, anchors, rules, coverage and source baseline from a **whole W02-validated bundle**; kinds are an explicit allowlist. No individual free-form version mutation endpoints in W03. Persist relational ownership/version IDs plus immutable payloads, then reconstruct and revalidate a complete bundle on read. Reject conflicting reuse of a domain ID across imports; match exact project. Treat display labels as content, not IDs. W03 only persists accepted synthetic fixture bundles; full ingestion/draft activation belongs to W04.

For immutable tables, block UPDATE/DELETE through migrations (trigger or equivalent role restrictions) and service logic; mutable job/membership/review projections are separate. JSONB representation is not the domain's canonical byte/hash algorithm: use accepted helpers. Reviews are metadata annotations of a fixed artifact candidate only; `accepted` here does **not** activate a RuleVersion or certify a device. Race check uses `expected_revision` and a locked row/conditional UPDATE in the same transaction as append event; exactly one competing revision wins, the other409. No transaction may commit half a review or half a job/outbox operation.

## Artifact storage

`LocalArtifactStore` with put/read/exists methods behind an interface; the API authorizes before reads. Maximum 10 MiB, enforced while streaming even without Content-Length. W03 accepts application/pdf, text/plain and application/json as opaque bytes, with harmless synthetic fixtures; **no PDF parsing or URL import**. Reject mismatch/unsupported media type and unsafe paths; original filename is display-only and sanitized for download disposition. Never accept filesystem paths/storage keys from callers, follow symlinks outside the configured volume, or expose the volume through static files. Stream bytes with SHA-256, write a unique temp file and atomic final rename, commit ready metadata only after bytes are durable. Handle transaction failure with orphan reconciliation; no read of uncommitted/staged bytes. No cross-project deduplication or public/signed download URL in W03; use authorized streaming GET. Missing/tampered bytes are explicit ARTIFACT_INTEGRITY failures. Store no model payloads in this packet.

## API foundation-v1

Prefix `/api/v1`. JSON requests forbid extras and use strict field types. Return stable errors `{error:{code,message,details},request_id}`; request IDs generated server-side UUIDs, echoed header `X-Request-ID`. No SQL, tokens, paths or tracebacks in responses/logs. Pagination uses bounded limit<=100 and stable cursors. Health endpoints are outside prefix: `/health/live`, `/health/ready`; readiness checks migrations, DB and broker without leaking connection strings. Export `/openapi.json` to evidence after implementation.

| Route | Request and result |
|---|---|
| POST /projects | name string1..120, Idempotency-Key; 201 project+owner membership. Bootstrap scope for idempotency is actor+create_project before project exists |
| GET /projects; GET /projects/{p} | only caller membership projects |
| PUT /projects/{p}/members/{actor} | owner-only role; GET members for owner; DELETE same path with last-owner protection |
| POST /projects/{p}/artifacts | raw bounded body, Content-Type, optional X-Filename, Idempotency-Key; 201 id/hash/size/type |
| GET /projects/{p}/artifacts/{a}; GET .../{a}/content | authorized metadata and streaming bytes; content is attachment with nosniff |
| POST /projects/{p}/bundles | whole W02 bundle, Idempotency-Key; validate exact route project and parser; 201 id/input_hash |
| GET /projects/{p}/bundles/{b} | reconstruct validated whole bundle; unchanged normalized hash |
| POST /projects/{p}/review-items | artifact_id, content_hash, annotation text <=4000; verify exact current artifact hash; 201 revision0 |
| POST /projects/{p}/review-items/{r}/decisions | expected_revision>=0, decision, rationale1..4000, Idempotency-Key; 201 event/new revision or409 |
| GET /projects/{p}/review-items/{r} | candidate, current revision and ordered events |
| POST /projects/{p}/jobs | kind=artifact_digest, artifact_id, Idempotency-Key; 202 job_id/status_url |
| GET /projects/{p}/jobs/{j} | DB state, attempt count, result ref/hash or safe failure |
| GET /projects/{p}/jobs/{j}/events?after_seq=0&limit=100 | ascending committed event sequence, next cursor |
| POST /projects/{p}/jobs/{j}/cancel | idempotent request; terminal committed success is not undone |

All mutations use Idempotency-Key (16..128 bounded printable ASCII); include operation/resource path, actor, project and canonical request/body hash. Equal scoped key+body returns original response/resource, changed body409. Auth check occurs on replay too. Concurrent first writers must converge using DB uniqueness/transaction handling, not process locks. Avoid holding a DB transaction throughout file upload; reserve/finalize consistently and reconcile failed staging. OpenAPI must match actual responses.

## Durable job execution and recovery

Only job kind `artifact_digest`: verify input bytes, produce a small JSON receipt `{schema_version:1, artifact_id, sha256, byte_length}` as an authorized project result artifact. No arbitrary callable/job type/URL supplied by clients. RQ schedules `erratascope_service.jobs.execute(job_id)` with **JSONSerializer**; the registered callable loads all trusted inputs from PostgreSQL. Broker access stays internal.

1. Enqueue writes job, queued event and outbox row in one transaction. The dispatcher claims due outbox rows using short DB transactions and SKIP LOCKED, enqueues, then marks sent. Crash between enqueue and mark is deliberately at-least-once; duplicate execution must be harmless.
2. Executor atomically claims an eligible job, sets running and a fresh attempt token/lease, increments attempts, appends start event. If completed/cancelled or an active valid lease already exists, duplicate invocation exits without side effects.
3. Default lease60s, heartbeat<=15s, max attempts3, retry delays1/5 seconds for this harmless local job; injectable clocks/barriers for deterministic tests. No sleep-heavy tests. Attempt token guards every commit/heartbeat/finalization. Cancellation invalidates an active token; stale workers cannot overwrite later success or cancellation.
4. Stage receipt bytes first, then transactionally commit stage_results, authorized result artifact metadata, success state and event if token still current. Same stage/input reuses a committed receipt; mismatched input fails. A crash after bytes but before DB may leave an orphan, never a visible accepted result.
5. Reconciler expires stale DB leases and redispatches eligible jobs, and redispatches queued jobs whose old broker delivery is lost. Bound dispatch generations/retry rate; broker's own registry is not authority. Exceeding attempts yields terminal failed event. Losing all broker data must not lose committed work or silently strand queued jobs.
6. Event sequence allocation is serialized per job, committed with its state transition. Never emit success before commit. Once stage/success is committed, duplicates/restarts return the same result and cannot produce a second accepted receipt.

Expose CLI subcommands `migrate`, `bootstrap-local`, `worker`, `dispatch --once`, `reconcile --once`, `health`, `verify-foundation`. A supervised dispatcher service loops bounded dispatch/reconciliation with configurable intervals and clean shutdown; no framework mega-orchestrator. RQ worker commands must use the actual pinned library CLI/API, not remembered options from another version.

## Mandatory tests and evidence

Create `backend/tests_w03/` with unittest modules for auth, persistence, artifacts, idempotency/review races, jobs/recovery, and one connected flow. Integration tests use actual isolated PostgreSQL and Valkey in this Compose project, not SQLite/fakeredis/in-memory repositories. Generated signing keys and tokens are test-only; keep private bytes out of reports. Separate DB transactions/connections/processes must exercise the races.

- Clean migrations and second idempotent migrate; service startup with missing/hosted config fails closed; ready checks.
- Create two users/projects, owner/editor/reviewer/viewer rights and revocation; foreign IDs across every resource route denied, including artifact content and job events; forged/expired/wrong issuer/audience/algorithm tokens rejected. Token subject is identity only, DB determines membership.
- Upload/download/hash, no-length oversize request, path/symlink confinement, missing/corrupt artifact, uncommitted upload failure; no private filesystem route.
- Whole synthetic bundle persistence/reload yields same domain input/result hashes; foreign-project bundle and reused version ID with altered payload rejected; immutable row updates denied.
- Same-key replay and changed-body conflict; concurrent duplicate creates yield one job/outbox/resource; competing review revisions yield one committed event and one409.
- Real worker restart/kill before stage commit, after stage commit/before broker acknowledgement, stale token versus newer attempt, duplicate broker delivery, queued redispatch after broker loss, cancellation; one accepted receipt, durable ordered events. Use deterministic barriers/time injection around real transactions rather than merely calling identical functions twice.
- Connected HTTP client -> JWT auth -> membership -> upload -> job/outbox -> actual RQ worker -> committed result -> authorized download. Include API/worker restart with existing DB/artifact volumes and successful retrieval.
- Run the 92 accepted domain tests unchanged in the new Linux image. Export OpenAPI, resolved package versions, image digests, actual commands/exits, clean startup/restart logs and precise synthetic/local/hosted distinctions.

W03-G1 local migrations/flow PASS; G2 authorization/artifacts PASS; G3 idempotency/review race PASS; G4 restart/redispatch PASS; G5 hosted prerequisites documented, **hosted execution NOT_RUN**. Local W03 acceptance may progress to W04, but P2 overall hosted/UI exit conditions are not thereby complete. No worker may mark the hosted gates passed from local tests.

## Verified references and later hosted constraints

Official sources checked 30 October 2026: [RQ workers/JSON serializer](https://python-rq.org/docs/workers/), [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/21/), [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts). Supabase asymmetric keys are published via the project's JWKS; token verification must pin issuer/audience and allowed algorithms. HS256 hosted fallback is not included in W03.

The [Supabase changelog](https://supabase.com/changelog) was checked. [CBC TLS retirement](https://supabase.com/changelog/cbc-tls-ciphers-deprecated) affects old HTTPS clients; use the modern pinned TLS runtime. [Postgres extension compatibility changes](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes) concern extensions/custom operators not used by this packet. These checks do not authorize creating a Supabase project or assert a hosted instance's settings/version. Later hosting must bind account, region, private storage, auth key configuration and costs before deployment.

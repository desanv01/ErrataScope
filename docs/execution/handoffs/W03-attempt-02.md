# Worker handoff â€” W03 revision 2 repair 01, attempt 02

Status: **READY_FOR_REVIEW** (acceptance, Git/GitHub checkpoint and W04 binding remain Codex's decision)
Packet: W03-persistence-jobs revision 2, repair assignment `docs/execution/reviews/W03-repair-01.md`, attempt **02**
Started/finished (UTC): 2026-10-30T06:09:57Z / 2026-10-30T06:27:36Z (final checks)
Starting baseline and recheck: **PASS** â€” `docs/execution/baselines/W03-repair-01-baseline.json`, **235 protected hashes, 294 links, 0 errors**, before edits and after.
Starting inventory: **43/43** files in `docs/execution/reviews/W03-attempt-01-inventory.json` matched their SHA-256 before edits (0 missing/mismatches).
History backup: `.local/w03/history/attempt-01-before-02/` â€” all 43 files with relative paths + `BACKUP_MANIFEST.json`; every copied hash matches (`all_match=true`). Attempt-01 evidence files remain preserved there (including the original recovery/verification/OpenAPI outputs).
Compose: exactly `erratascope-w03`; pinned images/lock unchanged; existing `erratascope-w03_pgdata` and `erratascope-w03_artifacts` volumes upgraded in place. New Alembic revision `0002_staging`; already-applied `0001_foundation` was not rewritten and no volume was reset.
Network/credentials: no Nebius, hosted provisioning, `.env.local`, Git, UI or W04 work. Hosted P2 remains **NOT_RUN**; UI/imagegen approval remains **PENDING**.

## R1â€“R4 results

### R1 â€” authorization on every path, including replay (PASS)

- Every mutation route performs current membership/action authorization **before** replay lookup, again on the uniqueness-race fallback, and re-authorizes after upload body staging before finalization. Cached responses cannot bypass revocation/demotion.
- `create_project` replay verifies continuing access to the previously created project; revoked creator â†’ 404.
- Owner-only member listing; editor/reviewer/viewer role separation enforced (reviewer cannot write artifacts; editor cannot review; viewer cannot mutate).
- Migrator DSN removed from API/worker/dispatcher environments (present only in `migrate`/`test`; evidence `migrator-boundary.json`: api/worker/dispatcher=false, migrate/test=true). App role still has USAGE + DML.
- JWT allowlist narrowed to RS256/ES256; signature/issuer/audience/expiry checks and hosted fail-closed behavior retained.
- Tests: `test_r1_authorization.py` (10): current-member replay, revoked replay (404), demoted replay (403), job replay demotion, project-create replay access, owner-only listing, role matrix, JWT allowlist.

### R2 â€” complete bound API, envelopes and pagination (PASS)

- Added `GET /api/v1/projects/{p}`; owner-only `PUT /projects/{p}/members/{actor}` (200 membership) and `DELETE` (204); `POST` add retained as documented compatibility route.
- Project-row locks plus owner-count checks enforce self-demotion/removal rejection (409) and last-owner protection; concurrent owners changing/removing each other serialize (tested with two real HTTP clients/DB).
- All handled errors use `{"error":{"code","message","details"},"request_id":<uuid>}`. The server generates a fresh UUID4 per request, ignores caller `X-Request-ID` as authoritative and echoes the server UUID in the response header including errors; no SQL/paths/secrets are exposed.
- Project/artifact/bundle/member/job-event/review-event listings use bounded stable pagination (`limit` 1â€“100, default 50; `{items,next_cursor}`). Entity cursors are opaque keyset `(created_at,id)` (members `(created_at,actor_id)`); event listings use `after_seq` and return the last returned sequence when more rows exist, else `null`. Invalid limits â†’ 422; malformed cursor â†’ 400 `INVALID_CURSOR`.
- OpenAPI regenerated from the live app; new routes/page/error schemas present.
- Tests: `test_r2_api_contract.py` (14), including exact methods/paths, owner/viewer matrix, self protections, concurrent owners, nested errors/server UUID, zero/oversized/invalid limits, multi-page traversal without duplicates/omissions, and OpenAPI agreement.

### R3 â€” bounded staging and safe orphan reconciliation (PASS)

- Upload authorization runs before body processing and its transaction is closed; the body streams in bounded chunks to a private staging file while SHA-256/size are computed (no full-body buffering, no DB transaction across I/O).
- New `0002_staging.upload_staging` journal records ownership, staging key, lease and state (`active`/`finalized`/`abandoned`); migration upgraded the existing 0001 database without reset and a test upgrades 0001â†’0002 while preserving existing rows.
- Finalization is a short transaction that re-checks current authorization, locks the staging row, promotes bytes atomically, inserts the artifact and idempotency response, and exposes only committed artifacts. Proven rollbacks delete only that operation's unreferenced files; ambiguous outcomes are retained/quarantined.
- Reconciliation (`reconcile --once`/dispatcher) uses fresh artifact references, active leases and grace; it preserves live staging, committed artifacts and linked receipts, collects abandoned/interrupted generated files, skips symlinks/unknown paths, and never recursively deletes external paths. Symlinked staging directories are rejected.
- `Content-Disposition` uses an ASCII fallback plus RFC 5987 UTF-8 `filename*`.
- Tests: `test_r3_staging.py` (11): real PostgreSQL CHECK rejection after staging leaves no orphan; streaming state; non-ASCII disposition; chunked oversize without content length; stale interrupted staging collected; live staging survives; committed bytes survive; untracked stale file collected but recent kept; symlink safety; concurrent finalize/cleanup.

### R4 â€” durable receipts, heartbeat/attempt/cancellation/outbox fencing (PASS)

- Confirmed acknowledgement-loss defect fixed: after a commit/acknowledgement exception execution settles through a **fresh independent session**. If stage/result metadata committed, the original receipt bytes and identity are preserved (no deletion, no new success); if uncommitted, own unreferenced bytes are removed and the job retries within bounds; if outcome cannot be established, bytes are retained for reconciliation.
- Redelivery/reconciliation verifies succeeded receipts. Missing/corrupt receipt bytes produce one idempotent `receipt_integrity_failed` event and preserve the original result identity; no replacement success is minted.
- Execution now runs a real bounded heartbeat thread; heartbeat and commit fencing reload fresh status/token/lease (`populate_existing` + row locks). Expired/superseded attempts cannot revive or overwrite newer work; stage input hashes are validated before reuse.
- Cancellation closes the running attempt (`ended_at`, `outcome=cancelled`), clears the token/lease and prevents later commits. Retries are bounded (max 3) and use the bound local delays `1s/5s`; configured limits are honored.
- Outbox finalization is fenced by the dispatcher's claim token and lease; generation/event allocation is serialized under the job row lock. Concurrent dispatcher/reconciler runs cannot lose events, strand work or create unbounded redispatch records.
- Recovery matrix evidence: real crash after staging (exit 43) â†’ attempts=2 â†’ committed receipt; ack-loss-after-commit test; missing/corrupt receipt detection; duplicate delivery; stale-vs-newer attempt fencing; cancellation during execution; real heartbeat thread extension; bounded retry delays; concurrent dispatcher claims; outbox token fencing; concurrent reconciler redispatch. Recovery script now writes attempt-specific evidence (`*-attempt-02.json`), leaving attempt-01 files untouched in the verified backup.
- Tests: `test_r4_fencing.py` (9) plus existing job/recovery tests; `test_migrations.py` (1).

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-01-baseline.json` (initial/final) | 0 / 0 | PASS, 235 hashes / 294 links |
| inventory SHA-256 verification (43 files) + backup manifest | 0 / 0 | 43/43 match; `all_match=true` |
| `docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet` | 0 | valid; migrator DSN only on migrate/test |
| `docker compose â€¦ build` | 0 | rebuilt pinned service image |
| `docker compose â€¦ up -d --wait db broker` | 0 | healthy |
| `docker compose â€¦ run --rm migrate` | 0 | existing volume upgraded `0001_foundation -> 0002_staging` |
| `docker compose â€¦ up -d --wait api worker dispatcher` | 0 | healthy |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests` | 0 | **92 accepted domain tests OK** |
| `docker compose â€¦ run --rm test python -m unittest discover -s tests_w03` | 0 | **82 W03 tests OK** (32.5 s) |
| `docker compose â€¦ run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json` | 0 | **11/11 checks**, no secrets |
| `docker compose â€¦ run --rm test python -m erratascope_service.cli export-openapi --output /local/openapi.json` | 0 | `openapi.json` regenerated |
| `powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1` | 0 | crash exit 43; recovered attempt 2; ordered events with one succeeded; receipt digest matches; API restart retrieval preserved |
| `python scripts/verify_execution_framework.py --baseline â€¦W03-repair-01-baseline.json` (final) | 0 | PASS, 235 hashes / 294 links |

Red cases from review 01 now pass: revoked same-key review replay â†’ 404; revoked job replay â†’ 404; demoted replay â†’ 403; project detail 200; PUT member 200; DELETE member 204; viewer member listing 403; nested error envelope with server UUID; event limit/cursor envelope; DB-rejection upload leaves no orphan; committed receipt survives ack loss; expired heartbeat returns false; cancelled attempt closed.

## Gates

| Gate | Result | Limits |
|---|---|---|
| G1 migrations/persistence | **PASS** | `0002_staging` upgrades existing 0001 without reset; domain bundle round-trip tests unchanged |
| G2 auth/artifacts | **PASS** | replay authorization, owner-only listing, nested API contract, bounded pagination, staging/orphan lifecycle |
| G3 idempotency/reviews | **PASS** | replay current-auth, concurrent same-key convergence, review one-winner, stale 409 |
| G4 recovery/fencing | **PASS** | real crash/restart, ack-loss receipt preservation, missing/corrupt detection, heartbeat/attempt/cancellation/outbox fencing, bounded retries |
| G5 hosted prerequisites | **PASS (documentation only)** | hosted execution **NOT_RUN**; P2 hosted/UI pending |

## Changed files

- `backend/erratascope_service/`: `api.py` (rewritten contract), `services.py` (membership/upsert/delete/cancel), `jobs.py` (fencing/heartbeat/receipt/orphan integration), `artifacts.py` (staging/symlink/disposition/reconcile), `models.py` (`UploadStaging`), `config.py` (allowlist, staging/grace/retry limits), `schemas.py` (nested errors/pages/role update), `cli.py` (event envelope/reconcile counts).
- `backend/migrations/versions/0002_staging.py` (new); `infra/w03/compose.yaml` (migrator boundary/staging env); `infra/w03/recover.ps1` + `recover_helper.py` (attempt-specific evidence, events/receipt checks); `backend/README-W03.md`.
- Tests: `backend/tests_w03/test_r1_authorization.py`, `test_r2_api_contract.py`, `test_r3_staging.py`, `test_r4_fencing.py`, `test_migrations.py` (new); existing W03 tests updated for the bound envelopes/events.
- Evidence: `docs/evidence/W03/openapi.json`, `verification.json`, `recovery-attempt-02.json`, `recovery-restart-attempt-02.json`, `recovery-api-retrieval-attempt-02.json`, `schema-inventory.json`, `migrator-boundary.json`, `IMPLEMENTATION_REPORT.md`; this handoff.

No accepted domain code/tests, W01/W02 evidence, protected documents, baselines, reviews, `.env.local` or Git metadata was modified. Attempt-01 evidence is preserved in the verified backup and its original files remain.

## Resources and limitations

- Only this project's services were used; at completion the five `erratascope-w03` services were stopped, preserving `erratascope-w03_pgdata` and `erratascope-w03_artifacts`. No volume deletion or global prune; no other project touched.
- Local single-host evidence only. Hosted auth/storage/broker/RLS were not provisioned or tested; hosted P2 remains **NOT_RUN**.
- Recovery covers worker crash-after-staging, stale-lease reconciliation, heartbeat extension, ack-loss commit, cancellation, and API restart retrieval; not multi-node/broker-failover or managed-service outages.
- Local development credentials/JWKS are synthetic and non-production; tests use the dedicated `erratascope_test` database/schema and `w03-test` queue.
- Artifact limit remains 10 MiB with PDF/text/JSON only; no rendering/parser, UI, deployment, provider call or W04 work.
- No blockers. No gate is claimed beyond actual local observations.

## Return prompt

> Review ErrataScope W03 revision 2 repair 01, worker attempt 02. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-02.md, docs/execution/reviews/W03-review-01.md and docs/execution/reviews/W03-repair-01.md. Verify the repair protected baseline and independently check R1â€“R4 against actual PostgreSQL/Valkey/API/storage behavior: current authorization before idempotent replay, complete membership/API contract, safe staged/orphan artifact lifecycle, and committed-receipt preservation with lease/attempt/outbox fencing. Preserve accepted W01/W02 evidence and domain code. Require real local integration/recovery evidence; hosted P2 remains NOT_RUN and UI/imagegen approval remains PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair assignment and prompt.


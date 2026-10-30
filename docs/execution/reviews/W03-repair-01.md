# W03 repair 01 — authorization and durable persistence boundaries

Codex assignment, 30 October 2026. **READY_TO_DISPATCH**, W03 revision 2, worker attempt **02**. Repair the current implementation; do not restart W03 or implement W04. The original foundation-v1 contract remains binding.

## Preflight and history

Read [review 01](W03-review-01.md), [original packet](../packets/W03-persistence-jobs.md), [foundation binding](../bindings/W03-foundation-v1.md) and [worker rules](../WORKER_RULES.md).

1. Require no active worker lock and no W03-attempt-02 handoff.
2. Run: python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-01-baseline.json. Require PASS before writes.
3. Verify every SHA-256 in [the starting inventory](W03-attempt-01-inventory.json). This pins actual reviewed W03 code/evidence **before repair**, not after authorized edits.
4. Claim .local/coordination/ACTIVE_WORKER.json exclusively. Back up all inventoried files with relative paths under .local/w03/history/attempt-01-before-02/, write a manifest and verify all copied hashes. Do not overwrite history.

Original W03-baseline.json and W03-attempt-01 handoff are immutable historical records. Codex verified the old baseline before changing status/dispatch files; use the new repair baseline for pre/post checks.

Writable paths remain the original W03 packet's service/migration/test/infra/evidence/local paths, plus the new handoff docs/execution/handoffs/W03-attempt-02.md and your own lock. Accepted domain code, its tests/fixtures, W01/W02 evidence, all contracts/reviews/checkers/baselines/status and credentials remain read-only. Do not run Codex's checkers as-is; they write to review-owned paths. Implement equivalent regressions in tests_w03.

Use the same pinned images/lock and isolated Compose project. No package/pin change, provider call, .env.local access, hosted provisioning/deployment, Git, UI or W04 work. Local Docker/runtime permission handling remains authorized. Preserve all existing volumes, examples and prior evidence. Where schema changes are needed, add a new Alembic revision (e.g. 0002) and test upgrading the existing 0001 database as well as clean startup. **Do not rewrite already-applied 0001 or delete/recreate persistent volumes to make migration tests pass.**

## R1 — authorization on every path, including replay

- Perform the route's current membership/action-role authorization **before returning either an original or replayed mutation response**, including uniqueness-race fallback. Keep actor/project/resource identity in the idempotency scope and body hash. Cached data cannot bypass revocation or demotion. For create-project replay, also verify continuing access to the previously created project before returning its cached private resource metadata.
- Audit every mutation route: membership, review-item creation, review decisions, jobs, cancellation, artifacts and bundles. Preserve correct fresh-request denial and idempotent convergence. Do not solve the bug by disabling idempotency.
- Owner-only member listing must reject viewer/editor/reviewer. Every externally reachable service operation must enforce authorization through its service/API boundary; internal lookup helpers may remain internal.
- Remove migrator connection configuration from API, worker and dispatcher environments. Keep it only in explicitly privileged migration/test containers. App role must still lack DDL/schema ownership.
- Keep JWT allowlist within the binding's RS256/ES256; no expanded algorithms by silent configuration. Preserve signature/issuer/audience/expiry validation and hosted fail-closed behavior.
- Tests: current-member replay succeeds; revoked actor same-key replay denied; demoted actor denied for former write/review/member-management action; fresh requests agree; cached race fallback cannot bypass; owner-only listing; role separation verified without printing secrets.

## R2 — complete the bound API, not an alternative one

- Implement GET /api/v1/projects/{project_id}.
- Implement owner-only PUT /projects/{p}/members/{actor} to create/update a role, and DELETE on the same path to revoke. For concrete response choices use PUT200 with membership body and DELETE204. Add idempotency to both and make replay authorization current. Preserve existing POST-add only as a documented compatibility route if desired, not a substitute.
- Enforce self-removal/last-owner protections transactionally, including concurrent owners changing/removing each other. Reject conflict409; membership revocation must affect the next request. Test using actual routes/DB, not only direct table edits.
- Use the specified nested envelope {error:{code,message,details},request_id} consistently for validation/auth/resource/HTTP/DB/runtime errors. Generate a fresh server UUID per request; do not trust caller X-Request-ID as the authoritative value. Echo it in the response header, including handled errors; never expose SQL, secrets or internal paths.
- Implement bounded, stable pagination for collection routes. Events use after_seq and limit<=100 and return {items,next_cursor}; next_cursor is the last returned sequence when more data exists, otherwise null. Project/artifact/bundle/member/review-event listings need stable keys/cursors rather than unlimited reads. Document their exact v1 envelopes in README/OpenAPI; this implements the existing bounded-list requirement.
- Regenerate OpenAPI and align existing clients/tests with the **protected contract**, not the current wrong flat envelope/route shapes. This is a legitimate contract correction, not permission to weaken tests.
- Tests: exact methods/paths, owner/viewer matrix, revocation/upsert/last-owner races, nested errors/server UUID, zero/oversized/invalid limits, stable multi-page traversal without duplicates/omissions, and request/response OpenAPI agreement.

## R3 — bounded staging and safe orphan reconciliation

- Stream bounded uploads to private staging files while computing SHA/size; do not retain the entire body or hold a DB transaction across the upload. Perform authorization before body processing, close that short transaction, then recheck current authorization at finalization.
- Journal/track staging ownership and finalization sufficiently to distinguish active staging, committed bytes, abandoned writes and unknown commit outcomes. Use short transaction finalization; expose only ready committed artifacts. Keep exact idempotent responses, integrity checks and project isolation.
- On a proven DB rollback, remove or schedule cleanup of only that operation's unreferenced files. On uncertain outcome, do not guess and delete. Reconciliation must inspect fresh committed references, honor active leases/age/grace, and safely reclaim abandoned/unreferenced files in this application's storage root.
- Reconciliation must not remove another active upload's bytes, accepted W01/W02 source artifacts, linked receipts, or unknown external paths. No broad recursive deletion. Reject escaping symlinks, including temporary-directory placement, and safely encode non-ASCII display filenames in Content-Disposition.
- Tests: actual DB constraint/transaction failure after staging leaves no permanent orphan; duplicate upload rollback; interrupted staging; stale orphan collected after controlled grace; live staging/committed bytes survive; concurrent finalization versus cleanup; no-length oversize input; path/symlink confinement. Controlled fault injection may coordinate real DB/filesystem boundaries; it is not a substitute for actual persistence.

## R4 — durable receipts and lease/attempt fencing

- Fix the confirmed acknowledgement-loss defect: after commit raises, re-establish transaction state through a fresh independent session before cleanup/retry. If stage/result metadata committed, preserve its bytes and result. If outcome cannot be established, retain/quarantine for reconciliation. Never unconditionally delete staged_key on an ambiguous commit.
- A succeeded job must have an intact referenced receipt. Redelivery/reconciliation must detect corruption/missing data explicitly and preserve accepted history; do not silently mint a different successful receipt or claim a missing file is success. For the synthetic acknowledgement-loss case, the original committed receipt must remain readable and its identity/hash unchanged.
- Wire real bounded heartbeats into execution, not merely a helper called by tests. A heartbeat/commit must verify current status, token and valid lease. An expired/stale attempt cannot revive itself or overwrite newer work. Re-lock/reload fresh DB state; do not rely on cached SQLAlchemy identity-map values or event uniqueness for fencing.
- Cancellation must close the affected running JobAttempt with ended_at/outcome and prevent later commits. Bound retries and use the bound local retry delays (1/5 seconds); ensure configured limits are actually honored.
- Fence outbox finalization with its current claim token/lease. Serialize per-job dispatch generation/event allocation; concurrent reconciliation and worker transitions cannot lose events, strand work or create unbounded redispatch records. Validate existing stage input hashes before reuse.
- Required recovery matrix on actual PostgreSQL/Valkey/private storage: restart/kill before stage commit; kill after successful commit before delivery acknowledgement; acknowledgement-loss exception after a real commit; duplicate broker delivery; stale attempt versus newer attempt; cancellation during execution; stalled work with heartbeats; broker loss/redispatch; bounded exhausted retries; concurrent dispatcher/reconciler claims. Use deterministic barriers/clock injection and real transactions, not sleep-heavy or purely mocked tests.
- Update recovery scripts to write attempt-specific evidence; preserve attempt-01 output in the verified backup. Assert one accepted result, original hash/bytes readable, coherent attempts and durable ordered events. No production HTTP failpoint routes. Failpoints enabled only for explicit local tests.

## Completion checks

Run the original build/startup/migration/test/connected-flow commands with this repair's baseline substituted for the old one. Existing volumes must upgrade successfully without reset. Run all 92 accepted domain tests unchanged, retain meaningful W03 regression coverage and add R1–R4 tests. Missing actual DB/broker/services must fail, not skip. Keep credentials/tokens out of logs and reports.

Regenerate OpenAPI/dependency/schema inventories as relevant. Update docs/evidence/W03/IMPLEMENTATION_REPORT.md with exact commands/exits, assertions and evidence paths for each repair, including prior red cases that now pass. Record G1–G5 honestly; hosted P2 remains NOT_RUN. Do not claim live-provider or hosted success from local tests.

Recheck the repair baseline, write docs/execution/handoffs/W03-attempt-02.md, stop only your owned project services/jobs while preserving volumes, release your lock and stop editing.

Return this exact prompt:

> Review ErrataScope W03 revision 2 repair 01, worker attempt 02. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-02.md, docs/execution/reviews/W03-review-01.md and docs/execution/reviews/W03-repair-01.md. Verify the repair protected baseline and independently check R1–R4 against actual PostgreSQL/Valkey/API/storage behavior: current authorization before idempotent replay, complete membership/API contract, safe staged/orphan artifact lifecycle, and committed-receipt preservation with lease/attempt/outbox fencing. Preserve accepted W01/W02 evidence and domain code. Require real local integration/recovery evidence; hosted P2 remains NOT_RUN and UI/imagegen approval remains PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair assignment and prompt.

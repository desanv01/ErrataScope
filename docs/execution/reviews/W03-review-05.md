# W03 review 05 — local foundation accepted

Codex independent review, 30 October 2026. W03 revision 2 repair 04, worker attempt 05.
Decision: **ACCEPTED — non-UI local W03 scope**. P2 hosted execution remains **NOT_RUN**; UI/imagegen remains **PENDING**. This does not accept the full hosted/UI phase.

## Independent evidence

- Protected repair-04 baseline passed before and after runtime verification: 285 hashes, 339 links. All 70 starting backup files match inventory hashes and manifest lengths. Worker lock absent. Accepted W01/W02 evidence and domain implementation remain unchanged.
- Actual service image matches 44 Python source/test/migration files; PostgreSQL head is 0003_staging_fencing. No dependency or applied migration changes.
- 110 W03 tests and 92 accepted domain tests pass in actual PostgreSQL/Valkey containers. Fresh main artifact and receipt remain byte-identical across isolated test database reset and test-store collection.
- Independent HTTP checks 22/22; actual rollback/post-commit acknowledgement-loss checks 8/8; connected API/worker flow 11/11.
- Repeated former leak probes: eight constructor mismatch, staging-symlink rejection and duplicate-create failures each have zero descriptor growth (3/3). Twelve successful real receipt verifications have zero root-handle growth. Extended real database/lifetime checks pass 16/16, including eight reconciliations, eight missing-job verification/settlement cycles and four app startup/shutdown cycles. No process-limit exhaustion or GC-based cleanup is assumed.
- Prior expiry-without-GC, actual-session ownership with omitted/forged hints, no-follow parent-swap confinement, newline-key rejection, unknown-file preservation and receipt-GC protection remain passing. Worker regressions additionally cover malformed markers, staging/promotion hooks and cancellation.
- Independent recovery wrapper actually crashed at the post-staging failpoint (exit 43), recovered on attempt 2, produced one ordered succeeded event and a readable committed receipt with matching digest. Retrieval after API restart passed. Reviewer paths kept worker evidence unchanged.

## Gates and limits

G1 migrations/persistence, G2 current authorization/private storage, G3 idempotency/review concurrency and G4 local crash/recovery/resource lifetime **PASS**. G5 hosted prerequisites **PASS for documentation/configuration only**; hosted execution remains NOT_RUN. No provider calls, credential search, UI or hosted provisioning occurred.

The read-only main-store audit found 112 rows and the same **41 missing** legacy artifact IDs. It preceded later fresh test additions. Their bytes were not restored or replaced; historical integrity is not claimed. Fresh sentinel and recovery successes establish only the measured current behavior.

Nonblocking cleanup observations: ArtifactStore contains a duplicate close definition (the later one is effective); current synchronous/idempotent closure passes the actual lifetime probes. OpenAPI export closes its store on the successful one-shot path, rather than via finally on export failure. The test runner emitted one psycopg connection ResourceWarning at process teardown; all required assertions passed, and no production storage-descriptor growth was observed. These are not represented as tested guarantees for arbitrary injected resource-exhaustion or concurrent close calls.

## Records and next action

[Observed contract freeze](../bindings/W03-observed-contracts.md), [acceptance manifest](../../evidence/W03/ACCEPTANCE.json).
Independent reports: [lifetime](W03-review-05-lifetime-observations.json), [failure handles](W03-review-05-handle-observations.json), [HTTP](W03-review-05-observations.json), [ack-loss](W03-review-05-fault-observations.json), [connected](W03-review-05-connected-verification.json), [sentinel](W03-review-05-sentinel.json), [runtime audit](W03-review-05-runtime-audit.json), [backup](W03-review-05-history-check.json), [recovery](W03-review-05-recovery.json), [receipt](W03-review-05-recovery-restart.json), [API restart](W03-review-05-recovery-api.json). Extended [checker](W03-review-05-lifetime-checks.py) supplements preserved prior checkers. Logs/wrapper remain private under .local/reviews/W03-review-05/.

No product code was changed by Codex. Only this Compose project's services were started/stopped; pgdata, artifacts and test_artifacts volumes remain. All owned services are stopped. Codex completes the accepted Git/GitHub checkpoint and binds W04 backend ingestion/review next; no UI authorization is implied and no W04 implementation starts in this review.

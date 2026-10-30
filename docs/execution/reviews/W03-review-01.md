# W03 review 01 — changes required

Codex independent review, 30 October 2026. W03 revision 2, worker attempt 01.
Decision: **CHANGES_REQUESTED. W03 is not accepted; W04 remains unbound.**
Next action: [one consolidated repair](W03-repair-01.md), [exact worker prompt](../prompts/W03-REPAIR-01.md).

## Evidence actually checked

- Original protected baseline passed before and after runtime review, before Codex coordination updates: **223 hashes, 281 links**, no errors. W01/W02 accepted source/evidence unchanged; worker lock absent.
- Started only the existing erratascope-w03 local stack, preserving its volumes. Actual PostgreSQL and Valkey were used. Re-ran **37 W03 integration tests** and **92 accepted domain tests**: all passed.
- Compared the running image's service/domain/migration bytes with the actual reviewed source: **25 files, zero mismatches**.
- [Independent HTTP/database checker](W03-review-01-checks.py): **10/22 assertions passed**, [observations](W03-review-01-observations.json).
- [Controlled failure checker](W03-review-01-fault-checks.py): **4/8 assertions passed**, [fault observations](W03-review-01-fault-observations.json). It used a real PostgreSQL constraint rejection after staging and a deliberately raised acknowledgement-loss error after an actual successful commit. Persistence was not mocked. This is controlled fault injection, not a claim that a spontaneous network outage occurred.
- Positive independent results include actual HTTP artifact round-trip, denial of fresh requests after revocation, same-key upload DB convergence, real RQ receipt success/hash verification and duplicate execution retaining one committed stage.
- The concurrent HTTP upload probe happened to leave no orphan in that run. The separate forced PostgreSQL failure **did** leave an orphan; findings below do not claim every duplicate upload leaks.
- Worker crash-after-staging evidence was inspected, but its script was not rerun because it overwrites worker evidence and the new independent commit-boundary failure already blocks G4. No claim of independently passing every recovery scenario.

The 30 independent assertions are targeted boundary probes, not an accuracy benchmark. No product implementation was changed by Codex during this review.

## R1 — authorization must precede replay

Confirmed over the actual API: remove the actor's membership from a newly created synthetic project in PostgreSQL. Fresh artifact reads and new job requests correctly return404. Replaying the same actor's original idempotency key returns **201 for review creation and 202 for job creation**, bypassing current membership. This exposes cached successful responses; it does not demonstrate creation of a new job after revocation.

Cause: api.py idempotent() returns a stored response before the protected operation's callback runs. Several route callbacks contain their only role check. Additionally, a viewer can GET the membership list (200), whereas the binding reserves that list for owners. Runtime Compose services also receive the migrator DB configuration through the common environment; separate it from API/worker/dispatcher as required by the intended app/migrator boundary.

## R2 — bound API contract is incomplete

Actual HTTP/OpenAPI behavior differs from foundation-v1:

- GET project detail, PUT member and DELETE member return404 because the bound routes are missing. Current POST-add-only behavior cannot support membership change/revocation and last-owner protection.
- Errors are flat objects rather than the bound nested error envelope.
- Caller-supplied X-Request-ID is trusted; otherwise the service generates a truncated hex identifier rather than a server UUID.
- Events ignore limit=1 and return multiple events in a bare list, without the required cursor envelope. Other listing services are also unbounded.

These affect the next packet's API integration; they are not visual/UI requests.

## R3 — uncommitted artifact lifecycle is incomplete

Injected an actual PostgreSQL CHECK rejection after private upload bytes were staged. The API returned409, but **one unreferenced artifact file remained**. Running the reconciler did not remove it. Source inspection confirms no bounded orphan/staging reconciliation path. Upload also holds a DB transaction opened by the authorization query while reading the body and buffers the full upload; the binding calls for bounded streaming staging and short DB transactions.

Fix rollback and orphan handling without deleting live or ambiguously committed result bytes. The next finding demonstrates why unconditional deletion is unsafe.

## R4 — committed result can lose its bytes; leases/attempts need completion

Controlled acknowledgement-loss probe: perform the real success commit, then raise an error as though its acknowledgement were lost. The handler deletes staged_key before establishing whether it is already referenced by committed rows.

Observed: job and stage remain **succeeded/committed**, but the result artifact file is missing. Redelivery is a no-op for succeeded jobs, so the receipt stays missing. This violates the durable-result guarantee and blocks acceptance.

Other confirmed lease/attempt observations: an expired attempt's heartbeat returns true and revives its lease; cancellation leaves that attempt marked running with no end time. Static inspection shows heartbeat() exists but execute() never schedules it. Re-locking an already-loaded Job in a session with expire_on_commit=False does not by itself refresh its cached token/state. Outbox finalization also ignores the claimed token. These paths require explicit fencing tests rather than relying on unrelated event uniqueness to reject stale commits.

## Gate decision and resources

| Gate | Decision |
|---|---|
| G1 migrations/persistence | Positive local migration/domain round-trip evidence retained; overall incomplete API/resource contract is repaired below |
| G2 auth/artifacts | **FAIL** — replay authorization, owner-only membership list, artifact lifecycle |
| G3 idempotency/reviews | Existing duplicate/review-race tests pass; **PARTIAL**, cached replay violates current authorization |
| G4 durable recovery | **FAIL** — committed receipt deleted after ambiguous acknowledgement; lease/attempt gaps |
| G5 hosted prerequisites | Documentation present; actual hosted execution **NOT_RUN** |

Stopped the five services started for review (api, worker, dispatcher, db, broker). No erratascope-w03 service remains running. Both named volumes are preserved. Only new synthetic review records and controlled failure artifacts were added; their IDs are in the review observations. No account provisioning, provider call, credentials search, UI work or W04 implementation occurred.

No W03 completion commit/push was made. Latest accepted checkpoint remains W02 commit 210e606925e1a630b302a2d4c63da29268a15ce5. After passing repair review, Codex performs the checkpoint and binds the eligible next scope. Hosted P2 and UI/imagegen approval remain open.

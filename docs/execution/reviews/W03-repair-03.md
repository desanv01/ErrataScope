# W03 repair 03 — complete the existing storage boundaries

**READY_TO_DISPATCH. W03 revision 2, worker attempt 04.** Implement only this consolidated repair. Retain the passing isolated-volume/sentinel, receipt-GC, API/auth/idempotency/ack-loss work. No new product scope.

Read [review 03](W03-review-03.md), [repair 02](W03-repair-02.md), [packet](../packets/W03-persistence-jobs.md), [foundation binding](../bindings/W03-foundation-v1.md) and [worker rules](../WORKER_RULES.md).

## Preflight

1. Require no active worker lock and no existing W03-attempt-04 handoff.
2. Run `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-repair-03-baseline.json`; require PASS.
3. Verify all [attempt-03 inventory](W03-attempt-03-inventory.json) hashes. Claim the lock exclusively, then make a verified relative-path backup in `.local/w03/history/attempt-03-before-04/` with SHA/size manifest. Preserve all prior history.
4. Use the separate test DB and test artifact volume. Existing main storage is identity-bound; never reset/delete/re-adopt it to make tests pass. Preserve historical missing rows/events and keep legacy loss explicit.

Original W03 writable paths remain in force, plus this attempt's handoff and own lock. Accepted W01/W02 code/tests/evidence and Codex documents/checkers/reviews/status/baselines stay read-only. **Applied migrations 0001, 0002 and 0003 and dependency pins are immutable.** Add a forward migration only if demonstrably needed; these fixes should primarily be code/regressions. No provider calls, `.env.local`, real credentials, package changes, Git, UI, hosted work, W04 or delegation.

Synthetic local development JWTs may expire. Verify expiry without printing values; if necessary refresh only the designated `.local/w03/dev-auth/tokens.json` using its existing synthetic key/JWKS and preserve prior tokens privately. Do not rotate keys, alter auth expectations, search credentials or bypass expiry verification.

## R1 — upload renewals must not resurrect expired ownership

- Make upload renewal one atomic conditional update that requires the current upload identity/state and an unexpired existing lease at the same captured timestamp. A missing, expired, reclaimed or superseded owner returns 409 STAGING_LEASE_LOST and cannot finalize.
- Preserve successful timely streaming renewal, short DB transactions, actual byte verification and rollback/ambiguous-outcome handling. Do not hold transactions across body I/O. Do not weaken the prior lease contract to accommodate current code.
- Add independent regressions for expiry **without GC**, expiry followed by GC, renewal before expiry, and renewal racing collection. Assert bounded error, no accepted artifact/idempotency response for rejected ownership, no self-deadlock and cleanup of only that operation's uncommitted bytes.
- Receipt ownership is additionally tied to a valid job/attempt; retain its existing tested heartbeat/GC protection and stale-attempt fencing.

## R2 — derive collector ownership from the actual session

- Require the store marker to match the actual database session used for reference/lease queries before destructive work. Derive from the actual session bind/connection, not a process-global settings object or optional caller string. An optional expected identity can be an additional assertion, never the authority.
- Fail closed for absent/invalid markers, unknown session binding or mismatches, including the default collector call with the identity argument omitted. Never silently adopt/overwrite an identity marker during collection.
- Use two distinct real SQLAlchemy engines/databases in regressions. In a new disposable store, commit a sentinel artifact in DB A. Invoke the collector with DB B (a) with no hint, (b) with a forged A hint, (c) through the service's real reconciliation entry point as relevant. All mismatches must refuse deletion and preserve bytes. A matching real session still collects valid stale owned orphans.
- Preserve safe explicit adoption and separate volume defaults. No credentials in markers, errors, logs or evidence.

## R3 — use directory-relative operations for confinement

- On the bound Linux runtime, open/pin the configured storage root and descend through directory file descriptors with O_DIRECTORY/O_NOFOLLOW. Perform file open, rename/promotion and unlink relative to verified parent descriptors. Pathname prechecks alone are insufficient. A parent swap after checking must either leave the operation on its original owned directory or reject it; never redirect onto outside/unowned bytes.
- Cover all read/write/promote/delete/abort paths. In particular, abort must not unlink a path through a replaced parent, and promotion must not follow redirected source/destination parents. Retain bounded file sizes and immutable artifact verification.
- Validate the configured root before resolution; reject symlink traversal in the root/components. Use full-string validation for canonical keys; reject trailing newline/control characters, unknown names and wrong shapes. Unknown on-disk contents remain preserved.
- Regressions with deterministic barriers/hooks and disposable files: swap parent after check before read/delete/open/promote/abort; internal/external file and directory symlinks; symlinked configured root; trailing-newline key; unknown paths survive; ordinary canonical round-trip and stale orphan cleanup still work. Use actual Linux filesystem operations, no skipped required cases. Keep filesystem capabilities confined and close descriptors reliably.

## Verification and handoff

Run the unchanged 92 domain tests, all 93 existing W03 tests plus new regressions, main artifact/receipt sentinel through complete isolated test reset/GC, connected verify-foundation, and focused real PostgreSQL/Valkey/storage recovery. Retain prior auth/replay/API/race/ack-loss/receipt-GC evidence and tests. No mocks establish persistence success.

Recovery and local seed/verification outputs use **attempt-04** names; preserve attempt-01/02/03 artifacts. Update README and IMPLEMENTATION_REPORT with actual commands/exits and R1–R3 assertions, distinguishing controlled injections from spontaneous outages. Keep historical 41 missing objects explicit; demonstrate safety with fresh sentinel objects, not replacement historical receipts.

Recheck the new baseline. Write `docs/execution/handoffs/W03-attempt-04.md`, stop only owned services/jobs while retaining all volumes, release your lock and stop editing. Report READY_FOR_REVIEW/PARTIAL/BLOCKED; acceptance belongs to Codex. Hosted P2 remains NOT_RUN; UI/imagegen PENDING.

Return this exact prompt:

> Review ErrataScope W03 revision 2 repair 03, worker attempt 04. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-04.md, docs/execution/reviews/W03-review-03.md and docs/execution/reviews/W03-repair-03.md. Verify the repair-03 protected baseline and starting backup. Independently check expired upload renewal without GC, collector ownership against its actual database session with omitted/forged hints, and directory-relative no-follow filesystem operations under parent-swap races including abort/promotion/root/newline handling. Preserve passing API/auth/idempotency/ack-loss/receipt-GC fixes and accepted W01/W02 evidence. Require real local integration/recovery and fresh sentinel preservation; keep legacy missing bytes explicit. Hosted P2 remains NOT_RUN and UI/imagegen PENDING. If W03 passes, record acceptance, perform its Git/GitHub checkpoint, bind eligible W04 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt.

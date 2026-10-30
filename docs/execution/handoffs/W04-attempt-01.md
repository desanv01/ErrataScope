# Worker handoff â€” W04 backend revision 2, attempt 01

Status: **PARTIAL** (backend mechanism ready for review; one bounded live case failed after consuming its reservation; full W04/P3 is not accepted)
Packet: `W04-ingestion-review` revision 2, backend portion. Binding: `W04-ingestion-v1`.
Started/finished (UTC): 2026-10-30T09:26:18Z / 2026-10-30T10:27:03Z (final checks)
Accepted predecessor: W03 local `99090c6aed74c0378eeae02860f33027b9cbca2d`, tag `w03-local-accepted`. No W03 repair was reopened.
Preflight baseline: **PASS** â€” `docs/execution/baselines/W04-backend-v1-baseline.json`, **377 protected hashes, 373 links, 0 errors**, before and after.
Starting inventory: **83/83** SHA-256 matches. Verified backup `.local/w04/history/before-attempt-01/` â€” 83 files + manifest, all copied hashes match; no history overwritten.
Lock: claimed exclusively at start, released at finish. No W04-attempt-01 handoff existed before this attempt.
No provider calls beyond the two authorized W04 reservations; no real credentials displayed, no package changes to W03 pins, no Git/hosted/UI/W05/delegation. Hosted P2 **NOT_RUN**; UI/imagegen **PENDING**.

## What is implemented

- **Source ingestion:** immutable `source_versions` derived from an authorized artifact hash/length; declared vs parsed identity exposed; same-project predecessor; project-qualified refs.
- **Bounded extraction:** `pdfplumber` subprocess (120 s, 512 MiB, sanitized env, 100-page/10 MiB bounds), real selected 2.2.18/2.2.5 anchors with located normalized bbox, identity/revision-header/legend/footnote context, summary statuses, coverage with `inventory_complete=false`, unselected/missing/ambiguous/failed visible.
- **Durable jobs:** `source_extract` parseâ†’draftâ†’final manifest stage results; short finalization fence; stale/cancelled attempts cannot publish; duplicate delivery does not duplicate anchors/draft; artifact_digest path retained.
- **Provider/accounting:** fixed endpoint/model, no-thinking request shape, reservation under DB row lock before dispatch, per-call 16,000/8,192 bounds, DB + append-only JSONL history, cache lookup, 2 MiB response limit, no redirects/retries/model switch, private evidence artifacts, separate validation, rejected drafts visible.
- **Draft boundary:** W04 prompt version with matching hashes; strict identity/citation/relevance, workaround-vs-exception, safety/placeholder checks; model data is never an active rule.
- **Conversion/review:** W02 `RuleVersion`/AST/selector/unit validation, evidence anchor provenance, content hashes, expected revision/hash conflicts, current-role-before-replay, accepted rule inserted only with successful guarded review, immutable accepted rows.
- **API/CLI:** typed source/extraction/anchor/coverage/draft/proposal/review/rule routes; `check-key`, `verify-ingestion` (offline/live), `verify-evidence`, `export-openapi`.
- **Migration 0004** applied to the existing main volume; 0001â€“0003 untouched; head re-run idempotent. Only permitted W03 test change: final-head literal â†’ `0004_ingestion`.

## Verification

- **W04 tests: 11 passed** on real PostgreSQL/storage.
- **W03 tests: 110 passed**; **domain tests: 92 passed** unchanged.
- Connected offline CLI: real source **pass** (39 anchors, 53 coverage entries, both selected supported, identity ES0620/Rev 5) and synthetic missing-revision **pass** (2 anchors, identity null/unresolved).
- Fresh main sentinel: `f6ea27bb44d74bd7b69cf407e60281a3004b326f50063ab4a027666b39fe49cd`, 57 bytes; readback identical before/after suites.
- Main audit: **147 rows, 106 readable, 41 missing**; 41 IDs exactly match the legacy loss set, **no new missing IDs**. No replacement receipts/bytes.
- Migration head `0004_ingestion`, idempotent. Existing accepted W03 recovery evidence is preserved byte-for-byte; a W04-time recovery rerun itself passed but overwrote protected attempt-05 outputs, which were restored from the verified starting backup. No new W03 recovery evidence is claimed.
- W01 ledger unchanged: 4/4 consumed, SHA-256 `028084e43708460cc0e6a35cc03000bbbf2c756c6c87f235bf52d333a84e55a6`.
- W04 ledger: 6 append-only lines, SHA-256 `f18b87a5c37dbcdf3aa2686f9e7a7784dcdf19d55c4d49e7eda48f67cd1ec1a9`.

## Live budget â€” exact history

Budget `W04-backend-v1`: **2/2 reservations used**, **$0.0165930** reserved estimate (cap $0.25). W01 stays exhausted at 4/4.

| Attempt | Case | Reservation | Actual usage | Outcome |
|---|---|---|---|---|
| 1 | real_source | succeeded; bound 3,768/8,192; $0.00850320 | 3,247 prompt / 1,587 completion / 4,834 total | Provider success; strict draft validated; CLI **pass** |
| 2 | synthetic_missing_revision | succeeded; bound 2,390/8,192; $0.00808980 | 1,335 prompt / 173 completion / 1,508 total | Provider success; worker validation rejected (`DRAFT_REJECTED`); CLI **fail** |

Real-source live draft: 9 claims, 34 anchor references, validates identity/revision separation and source qualifiers. It is a model draft, not human approval.

Synthetic live failure: the paid response arrived completely, but the worker's own draft validator rejected it because its unresolved-field allowlist omitted `source_document_id`/`source_revision`. That validator bug was fixed and the offline synthetic path now passes, but the binding forbids a third reservation/retry, so the live synthetic case remains failed. Provider request ID `8c86a58e8db4b2ea0aed99dab3dd536d`, response SHA-256 `51084d88â€¦bdee7`, reservation attempt 2 preserved. No response body was persisted before the rejection-persistence fix; no new live call was made.

## Gates

| Gate | Status | Evidence/limits |
|---|---|---|
| B1 source/parse/anchors/coverage | **PASS** | pinned hash, 38 pages, 2.2.18/2.2.5, located geometry/context, failures visible |
| B2 strict provider/evidence/accounting | **PARTIAL** | exact reservation accounting; live real pass; live synthetic rejected after paid success; no third call |
| B3 reviewed conversion/authorization | **PASS (mechanism only)** | synthetic accepted/stale/foreign/immutable tests; no faithful real-source rule with unchanged selectors; Codex decides semantics |
| B4 persistence/restart/idempotency/regressions | **PASS** | 11/110/92, duplicate/cancel, migration, recovery, sentinel, no new loss; reservation crash path residual limit |
| W04-G1 live sourceâ†’reviewed rule | **PARTIAL** | live cited draft; no real semantic acceptance/conversion |
| W04-G2 source context | **PASS backend** | API geometry/provenance; UI highlighting NOT_RUN |
| W04-G3 coverage visibility | **PASS backend** | unselected/ambiguous/missing visible |
| W04-G4 failures cannot activate rules | **PASS** | no failure path writes accepted_rules |
| W04-G5 approved UI | **NOT_RUN** | UI/imagegen PENDING |

**Hosted P2 NOT_RUN; UI/imagegen PENDING; full W04/P3 not accepted.** No Git, hosted, frontend, W05, credential or delegation work.

## Evidence

`docs/evidence/W04/`: `IMPLEMENTATION_REPORT.md`, `gate-report.json`, `usage.json`, `provenance.json`, `coverage-summary.json`, `openapi.json`, `schema-inventory.json`, `dependency-inventory.json`, `w04-sentinel.json`, `main-audit-w04.json`, `legacy-loss-comparison.json`, `verify-offline-real-attempt-01.json`, `verify-offline-synthetic-attempt-01.json`, `verify-live-real-attempt-01.json`, `verify-live-synthetic-attempt-01.json`, `ledger.jsonl`.

## Resources

- Only `erratascope-w03` services were used. At finish API/worker/dispatcher/broker/db were stopped (`Exited (0)`).
- Volumes `erratascope-w03_pgdata`, `erratascope-w03_artifacts`, `erratascope-w03_test_artifacts` retained; no deletion/global prune; no other project touched.
- W04 live override is `infra/w04/compose.live.yaml`; it mounts `.env.local` read-only only into the worker. `check-key` printed `CONFIGURED` only. No secret value was printed or persisted.

## Return prompt

> Review ErrataScope W04 revision 2 backend-v1, worker attempt 01. The worker has stopped editing. Read docs/execution/handoffs/W04-attempt-01.md, docs/execution/packets/W04-ingestion-review.md and docs/execution/bindings/W04-ingestion-v1.md. Verify the protected baseline and starting backup. Independently check real source/anchor/coverage fidelity, strict provider and case-bound evidence, durable reservation accounting without resetting W01 or W04 history, reviewed conversion and project/current-role authorization, immutable persistence and restart/replay/cancellation behavior. Require actual provider evidence for live gates; mock/cached/edited outputs are not new live success. Distinguish synthetic review-mechanism tests from genuine semantic acceptance. Preserve accepted W01/W02 evidence, W03 foundation behavior, the known 41 legacy missing artifacts, hosted P2 NOT_RUN and UI/imagegen PENDING. Record backend acceptance or one consolidated repair; full W04/P3 remains incomplete until its UI and semantic gates pass. Perform the appropriate Git/GitHub checkpoint for accepted scope under the standing public-repository authorization and give the exact next eligible prompt or concrete UI-approval step. Do not start an unbound future packet.


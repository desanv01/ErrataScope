# W04 backend implementation report â€” revision 2, attempt 01

Status: **PARTIAL** (backend mechanism ready for review; one live case failed after consuming its bounded reservation; final semantic acceptance and UI remain outside this attempt)
Packet: W04-ingestion-review revision 2, backend portion only. Binding: `W04-ingestion-v1`. Accepted predecessor: W03 local commit `99090c6aed74c0378eeae02860f33027b9cbca2d`, tag `w03-local-accepted`.
Protected baseline: **PASS** â€” 377 hashes / 373 links, before and after (`W04-backend-v1-baseline.json`).
Starting inventory: **83/83 SHA-256 matches**; verified backup `.local/w04/history/before-attempt-01/` (83 files + manifest, all copied hashes match).

## Delivered backend

- Migration `0004_ingestion` (`down_revision=0003_staging_fencing`): source versions, extractions/status projection, immutable extraction outputs, source anchors, coverage entries, model drafts, conversion proposals, append-only reviews, accepted rules, provider reservations/events/budget. W03 migrations 0001â€“0003 unchanged; app-role immutable triggers; state projection mutable only by fence.
- Source ingestion: server-derived artifact hash/length, declared-versus-parsed identity exposed, same-project predecessor chain, project-qualified references, immutable source rows.
- Bounded parser: `pdfplumber 0.11.10` subprocess with 120 s deadline, 512 MiB RLIMIT_AS, sanitized environment, 100-page/10 MiB bounds, explicit cancellation/timeout kill, real located geometry (zero-based page, normalized top-left bbox, dimensions/rotation), identity/revision-header/legend/footnote context, summary-row statuses, `inventory_complete=false`, unselected/missing/ambiguous coverage visible.
- Durable `source_extract` job kind: parse â†’ draft â†’ final manifest staged artifacts; short finalization fence; stale/cancelled attempts cannot publish; duplicate delivery reuses no new anchors/draft; existing artifact_digest behavior retained.
- Strict provider path: fixed endpoint/model, no-thinking request shape, reservation **before** dispatch under PostgreSQL row lock, per-call 16,000/8,192 bounds, DB reservation/event history plus append-only local JSONL mirror, cache lookup, 2 MiB response cap, no redirects/retries/model fallback, private request/response artifacts, validation separately persisted, rejected drafts remain visible.
- Draft boundary: W01-derived prompt with explicit W04 version/hash, `value`/`citations` schema, strict identity/citation/relevance checks, workaround-versus-exception and safety/placeholder rejection, model content never executable.
- Conversion/review: W02 `RuleVersion`, bounded AST preflight, selector/unit validation, anchor/source checks, content hash, `expected_revision`/`expected_content_hash` conflicts, current-role check before replay, accepted rule inserted in the same guarded transaction as its review, immutable accepted versions and past events. Real entry not forced into absent selectors.
- API: typed `/sources`, `/extractions`, `/anchors`, `/coverage`, `/drafts`, `/proposals`, `/reviews`, `/rules`; strict requests, membership checks, 404 for foreign resources, 403 role, 409 stale/ineligible.
- CLI: `check-key` (presence only), `verify-ingestion` (offline/live real/synthetic), `verify-evidence`, `export-openapi`.

## Offline and connected evidence

- **W04 tests: 11 passed** (real test PostgreSQL/storage): real PDF anchors/coverage/draft; source immutability/foreign refs; malformed PDF; parser size/cancellation; synthetic missing-revision mechanism; duplicate delivery; cancellation; provider budget/mirror/failures; accepted/stale/immutable review; foreign-anchor ineligibility.
- **W03 tests: 110 passed**, only permitted change is the final-head literal `0004_ingestion`. **Domain tests: 92 passed** unchanged.
- Connected offline CLI against real API/worker:
  - real source `pass`: 39 anchors, 53 coverage entries, 2/2 selected supported, identity ES0620/Rev 5, validated offline-labeled draft.
  - synthetic missing revision `pass`: 2 anchors, identity null, `source_document_id`/`source_revision` unresolved, validated offline-labeled draft.
- Fresh main sentinel: artifact `f6ea27bbâ€¦e49cd`, 57 bytes; readback identical before/after the full suites (`w04-sentinel.json`).
- Main audit after tests: **147 rows, 106 readable, 41 missing**; the 41 IDs exactly match the known legacy losses, **no new missing IDs**, no replacement bytes/receipts (`legacy-loss-comparison.json`).
- Migration head `0004_ingestion`, re-run idempotently. Existing accepted W03 recovery evidence is preserved byte-for-byte; a rerun passed but overwrote protected attempt-05 outputs and was restored from the verified starting backup, so no new W03 recovery evidence is claimed.
- W01 ledger unchanged: 4/4 consumed, SHA-256 `028084e4â€¦e55a6`. W04 ledger: 6 append-only lines, SHA-256 `f18b87a5â€¦1ec1a9`.

## Live W04 budget (both reservations consumed; no third call)

Budget `W04-backend-v1`: **2/2 reserved**, **$0.0165930** reserved estimate (cap $0.25). W01 remains 4/4.

| Attempt | Case | Reservation | Actual usage | Result |
|---|---|---|---|---|
| 1 | real_source | succeeded, input bound 3,768 / output bound 8,192, $0.00850320 | prompt 3,247 / completion 1,587 / total 4,834 | **HTTP/provider success; strict draft validated; CLI pass** |
| 2 | synthetic_missing_revision | succeeded, input bound 2,390 / output bound 8,192, $0.00808980 | prompt 1,335 / completion 173 / total 1,508 | **HTTP/provider success; worker draft validation rejected (`DRAFT_REJECTED`); CLI fail** |

The real-source live draft cites 34 anchor references across 9 claims, keeps document revision separate from Z/B/X silicon rows, preserves may/might qualifiers, and treats the example address as non-mandatory. It is a model draft, not semantic acceptance.

The synthetic live response was rejected by the worker's **own** draft validator because its `unresolved_fields` allowlist omitted `source_document_id`/`source_revision`; that validator bug was fixed and the offline synthetic path now passes. No third request was made because the binding forbids a third reservation and automatic retries. The failed live attempt, reservation, request ID, response hash and usage are preserved rather than relabeled as a pass. This is the exact B2 partial blocker.

## Gates

| Gate | Status | Evidence/limits |
|---|---|---|
| B1 source/parse/anchors/coverage | **PASS** | pinned PDF hash, 38 pages, selected 2.2.18/2.2.5, located bbox/context, inventory_complete=false, malformed/limit failures visible |
| B2 strict provider/evidence/accounting | **PARTIAL** | reservation-first accounting exact; real-source live pass; synthetic live provider response rejected by a since-fixed validator bug; no third call; offline/mock failures fail closed |
| B3 reviewed conversion/authorization | **PASS (mechanism only)** | synthetic accepted rule, stale 409, foreign/ineligible rejection, immutable accepted rule, current-role checks; no real-source accepted rule because unchanged selectors cannot represent NRST reset-mode/DBGMCU register; real semantics are Codex's decision |
| B4 persistence/restart/idempotency/regressions | **PASS** | 11/110/92 tests, duplicate/cancel, migration head, W03 recovery, sentinel, no new missing artifacts; reservation crash-after-dispatch remains a documented residual limitation |
| W04-G1 real source â†’ live draft â†’ authorized rule | **PARTIAL** | live cited draft exists; no real semantic approval or faithful real conversion yet |
| W04-G2 source context | **PASS backend** | exact source version/anchor geometry/API; UI highlighting NOT_RUN |
| W04-G3 coverage visibility | **PASS backend** | unselected/ambiguous/missing/failed visible |
| W04-G4 failures cannot activate rules | **PASS** | no failure path writes `accepted_rules`; rejected draft/ineligible proposal/stale review fail closed |
| W04-G5 UI | **NOT_RUN** | UI/imagegen PENDING |

**Hosted P2: NOT_RUN. UI/imagegen: PENDING. Full W04/P3: NOT accepted.** No Git mutation, hosted account, provider retry/model switch, frontend, delegation or W05 work occurred.

## Commands/exits

| Command | Exit | Result |
|---|---|---|
| framework baseline (initial/final) | 0 / 0 | PASS 377/373 |
| inventory hash check + backup | 0 / 0 | 83/83; `all_match=true` |
| compose config / build | 0 / 0 | pinned stack; additive parser lock |
| migrate (twice) | 0 / 0 | `0004_ingestion` head idempotent |
| W04 unittest discover | 0 | 11 tests OK |
| W03 unittest discover | 0 | 110 tests OK |
| domain unittest discover | 0 | 92 tests OK |
| offline real / synthetic CLI | 0 / 0 | both pass |
| live real CLI | 0 | pass; reservation 1 |
| live synthetic CLI | 2 | failed after reservation 2 as described |
| main sentinel before/after | 0 / 0 | byte-identical |
| main audit + legacy comparison | 0 / 0 | 147/106/41; no new missing |
| W03 recovery script | 0 | restart/retrieval pass |
| `check-key` in worker | 0 | `CONFIGURED` only |

## Residual limits

- The synthetic live case failed on a worker validation allowlist bug after the paid response; fixed code exists but the exhausted budget forbids another request, so live synthetic evidence is not claimed.
- No real-source accepted rule: the source's trigger/measurement vocabulary is outside the unchanged W02 selectors; forcing a constant/empty predicate would be unfaithful. Future contract extension is required.
- The W04-time rerun of the W03 recovery script overwrote protected W03 attempt-05 outputs; the verified backup was restored and the final protected baseline passes. No new W03 recovery evidence is claimed.\n- W04 reservation crash-after-dispatch/no-response settlement is implemented conservatively (uncertain, no retry) but not exercised against a real provider crash; duplicate/cancel paths are covered on real DB.
- Local single-host Linux only; hosted storage/RLS/broker P2 NOT_RUN; UI G5 NOT_RUN.
- Historical 41 missing artifacts remain unreplaced; fresh successes do not prove past integrity.

## Changed files

New ingestion package (`backend/erratascope_service/ingestion/{models,schemas,prompt,parser_worker,parser,draft,fixture,provider,service,jobs,api,cli}.py`, versioned prompts), migration `0004_ingestion.py`, additive `requirements-ingestion.lock`, Dockerfile lock install, isolated test/W04 mounts, `infra/w04/compose.live.yaml`, `backend/tests_w04/`, `backend/README-W04.md`, single head-literal change in `tests_w03/test_migrations.py`, README/service model/config/jobs/api additive changes, and W04 evidence/handoff. No accepted domain/W01/W02/W03 evidence, applied migration, credential file, or Git metadata was modified.


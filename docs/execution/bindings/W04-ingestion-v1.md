# W04 ingestion-v1 — backend dispatch binding

Codex-owned, 30 October 2026. W04 revision 2, **backend portion only**, attempt 01. Prerequisite: accepted W03 commit `99090c6aed74c0378eeae02860f33027b9cbca2d`, tag `w03-local-accepted`, [review 05](../reviews/W03-review-05.md), [foundation freeze](W03-observed-contracts.md). W01/W02 freezes remain authoritative. UI/imagegen is PENDING; full W04/P3 acceptance requires the later approved UI and semantic review. No W05 dispatch is implied.

## 1. Outcome and boundary

Build the connected local backend: authorized existing artifact → immutable source version → bounded extraction job → cited draft → explicit reviewed conversion proposal → append-only review decision and accepted domain rule version. Expose source context, selected coverage, diagnostics, provenance and review state over typed API/CLI. The model interprets manufacturer documents; it never runs firmware, simulations, arbitrary code, repairs or VerifForge workflows.

Use the existing FastAPI/SQLAlchemy/PostgreSQL/RQ/Valkey service and private storage. Preserve its authorization, replay, staging/GC/fd lifetime, recovery and error contracts. Do not create another server/queue/store or generic agent framework. No UI pages, CSS, frontend shell, design work, hosted accounts or deployments.

Deliver a complete backend path even if the live provider or a source semantic conversion remains blocked. Report the exact incomplete gate; never label a mocked/edited/cached response as a new live success. No fresh inference in W01, no resetting its four consumed reservations.

## 2. Preflight, inventory and ownership

Run `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W04-backend-v1-baseline.json`. Require PASS, no active worker lock and no W04-attempt-01 handoff. Verify every file in [starting inventory](../reviews/W04-starting-inventory.json) before edits. Claim the exclusive lock and create `.local/w04/history/before-attempt-01/` with copies and a verified SHA-256/length manifest. This includes all accepted W03 source files that may be extended, W01 provider/source inputs, and the acceptance evidence. Never overwrite existing history. A mismatch is a stop-for-review condition, not permission to refresh the baseline.

Writable scope:

- New `backend/erratascope_service/ingestion/**` modules and versioned prompts; new `backend/tests_w04/**` with original synthetic fixtures; `backend/README-W04.md`.
- Existing `backend/erratascope_service/{api,cli,config,models,schemas,services,jobs}.py` only for additive ingestion routing/configuration/models and durable job integration. Keep existing public shapes and artifact_digest behavior. Prefer a separate router and job-handler helper over rewriting foundation code.
- New migration `backend/migrations/versions/0004_ingestion.py`, revision `0004_ingestion`, down_revision `0003_staging_fencing`. No edits to applied migrations 0001–0003, migration environment, DB role setup or existing immutable content.
- `backend/tests_w03/test_migrations.py`: the **sole permitted change** is expected final head string `0003_staging_fencing` → `0004_ingestion`. All existing behavioral assertions and every other W03/domain test stay unchanged. This accommodates a forward migration; it is not a waiver.
- New `backend/requirements-ingestion.lock`; `infra/w03/Dockerfile` only to install that additive hashed lock after the unchanged service lock. `infra/w03/compose.yaml` only for bounded W04 config and a separate `.local/w04` scratch mount for test tooling. Preserve project name, isolation, existing volume mounts, role separation, image digests and loopback binding.
- New `infra/w04/**` for optional local live override and verification/recovery helpers; new `.local/w04/**`; new `docs/evidence/W04/**`; own handoff `docs/execution/handoffs/W04-attempt-01.md` and lock.

All other files are read-only: accepted domain, W01 spike/results/provider ledger, W02/W03 evidence, existing W03 tests except the one head literal, storage/auth/db/domain adapter modules, execution docs/contracts/baselines/reviews, previous handoffs, real credential files and Git metadata. Do not run old review scripts that overwrite their historical outputs. No worker delegation. Propose any necessary scope exception in the handoff instead of silently applying it.

## 3. Runtime and dependencies

Keep the exact W03 Python 3.11.15 and 40-package service lock. The approved parser family is the proven lightweight W01 fallback: pdfplumber **0.11.10**, pdfminer.six **20260107**, pillow **13.0.0**, pypdfium2 **5.14.0**, charset-normalizer **3.5.2**, reusing cryptography **50.0.2** and the rest of the existing environment. Resolve/download compatible Linux wheels only into `.local/w04/dependencies/`, record SHA-256 in the new additive lock, install with `--require-hashes --only-binary=:all:`. Do not upgrade base dependencies. Verify installed versions; report an actual incompatibility before changing pins. Do not bring in Docling/Torch/OCR/GPU downloads for this bounded digital-text scope.

Network: existing local Docker services; PyPI/files.pythonhosted.org for these packages; official provider documentation; the fixed Nebius endpoint only within section 7 budget. No arbitrary URL importer. Use the existing accepted PDF bytes; only the exact ST source URL may be fetched if the pinned local PDF is missing, with redirects restricted to HTTPS st.com/www.st.com and no private IP destinations. A changed hash is a new source version/blocker, never silently substituted.

## 4. Immutable source data and parser

Use accepted `.local/w01/sources/st-es0620.pdf` or `es0620.pdf` only after SHA-256 equals `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`. Copy to W04 private scratch before processing; upload through the actual API to a fresh local synthetic project. ST ES0620 Rev 5, August 2026, 38 pages; selected entries **2.2.18 and 2.2.5**. Derive actual page positions from contents. Source URL: `https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf`. Existing W01 anchors/drafts are comparison evidence, not newly generated W04 outputs.

New source-version request fields: `artifact_id`, nullable `document_id`, `revision`, `manufacturer`, `source_url`, `published_at`, `predecessor_id`; `authority` manufacturer/forum/synthetic; `synthetic` bool. Derive project/actor/byte hash and length server-side from authorized artifact. Return immutable UUID, schema_version=1, content_hash, retrieval/creation UTC metadata. Preserve declared versus parsed identity and expose discrepancies; don't relabel user metadata as verified manufacturer identity. Predecessor must exist in the same project and logical document chain. No cross-project hash-dedup signal.

Add relational records for source versions, immutable extraction outputs, source anchors, per-entry coverage, model drafts and conversion proposals/review events; a separate mutable run/status projection may reference them. Use project-qualified foreign keys and app-role immutability triggers for sealed outputs. Store parser/version/configuration, source hash, exact selected scope and output hashes. Reparse creates a new extraction version, never overwrites anchors or prior review targets. Do not treat the existing generic W03 review annotation as proof a typed rule was accepted.

Production source/anchor shapes must adapt to W02 `DocumentVersion`/`SourceAnchor`: zero-based physical page index distinct from printed label, top-left normalized bbox, page dimensions/rotation, parser name/version, geometry_kind. Namespace local anchor IDs by source/extraction identity; reparse IDs need not stay stable. Identity footer, revision table headers, Z/B/X rows, A/N/P legends and applicable footnotes are separate citable context, not free-text hints. No guessed coordinates. A full PDF text inventory may discover entry headings; selected processing still does not establish full-document support. Coverage must retain discovered/selected/supported/reviewed/failed/unsupported distinctions and `inventory_complete=false` unless the complete inventory has actually been checked. Expose unselected entries and reasons; never count them as assessed.

Bounds: existing upload max 10 MiB; PDF max 100 pages; inspect at most 12 selected/context pages for detailed anchors; <=10,000 anchors, <=2 MiB extracted text, <=120 seconds parse subprocess wall time, <=512 MiB parser memory, one active parser per worker. Reject encrypted/malformed/over-limit files with stable diagnostics. Digital text only; scanned, ambiguous table or absent geometry becomes visible unsupported/partial coverage. No shell execution or fetching URLs embedded in documents. Parser subprocess receives only explicit temporary input/output paths, has no provider credentials in its environment, and is killed/reaped on timeout/cancellation. Technical PDF renders for coordinate validation are allowed; application UI is not.

## 5. API and persistence contract

Keep `/api/v1/projects/{project_id}` and current JWT/role/error/idempotency/pagination patterns. All reads check membership, all writes reauthorize before replay and before final commit; owner/editor submit sources/extractions/proposals, owner/reviewer decide. Cross-project/foreign resources return 404; known insufficient role 403; stale review/content revision 409. Use the current `Idempotency-Key` behavior and stable `{items,next_cursor}` lists.

Add these routes, with strict Pydantic request/response models and regenerated W04 OpenAPI evidence:

| Route suffix | Behavior |
|---|---|
| POST /sources | 201 immutable document version from an existing authorized PDF/text artifact |
| GET /sources and GET /sources/{source_id} | Paginated sources/detail, source metadata, explicit current coverage status |
| POST /sources/{source_id}/extractions | 202; request `selected_entries` (bounded nonempty unique strings), `mode` offline/live; returns durable job ID/status URL |
| GET /extractions/{extraction_id} | Exact source/run/parser/status/diagnostics/provenance, no secret or full raw provider response |
| GET /extractions/{extraction_id}/anchors and /coverage | Paginated immutable anchor/context and coverage data |
| GET /extractions/{extraction_id}/drafts and GET /drafts/{draft_id} | Exact draft content/hash, citations, unresolved fields, validation/review state and live/cache/mock provenance |
| POST /drafts/{draft_id}/proposals | 201 immutable explicit rule conversion candidate, tied to exact draft/source/anchors and payload hash |
| GET /proposals/{proposal_id} | Candidate, unresolved blockers, current review revision and full source references |
| POST /proposals/{proposal_id}/reviews | 201 append-only decision with `expected_revision`, `expected_content_hash`, accepted/rejected decision and nonblank rationale; conflict 409 |
| GET /proposals/{proposal_id}/reviews and GET /rules/{rule_version_id} | Authorized history and immutable accepted rule representation |

Existing job read/event/cancel endpoints cover ingestion jobs. No client-supplied storage path, provider URL, secret, price or budget override. Any proposal missing representable target/trigger/exceptions stays ineligible; accepted API records derive reviewer_id from authenticated actor, never request text. Rejection does not mutate or erase source/draft/proposal; corrections create successor proposals. Accepted rule content is inserted only in the same transaction as the successful guarded review event. Later decisions cannot mutate accepted versions or past evidence.

## 6. Draft conversion and review semantics

Copy/adapt W01's accepted draft shape/prompt v4 into the new ingestion package with an explicit new W04 prompt version and matching hash. Do not import the spike as a production dependency or edit it. Every claim has a relevant supplied anchor; unavailable information belongs in unresolved_fields. Reject wrong document/revision, foreign/nonexistent anchors, malformed types, truncation, empty content and invented identity. Persist raw response and validation separately; an HTTP 200 alone is not draft acceptance. Model content is untrusted data, never instructions or executable AST.

Conversion is a separate explicit operator-authored candidate using the **unchanged W02 AST/selector/unit vocabulary**. Preserve source entry, exact draft hash, evidence mapping for each technical predicate, source identity, consequence, optional workaround text/restrictions and every qualification. Workaround is not an exception; optional/example details are not requirements. Do not mechanically turn free-text claims into accepted predicates. Unknown trigger/exception is not true/empty. Empty exceptions and explicit constant triggers require a recorded source-grounded reviewer rationale. If the real entry cannot be faithfully expressed in existing selectors, keep it unsupported and document the needed future contract extension; do not add selectors or erase conditions to force success.

Use W02 bounded AST validation before recursive parsing, strict RuleVersion model, selector validation, all source/project/anchor reference checks and canonical hash helpers. A valid draft is not an executable rule. Demonstrate persisted review/concurrency with original labeled SYNTHETIC proposals and a genuine source-backed proposed conversion where representable. The worker may exercise the review endpoint as a **synthetic local test actor**, but must label that as mechanism testing, not actual human technical approval. Codex reviews the real-source semantics before declaring G1 semantically accepted. Do not invent a fake product snapshot solely to hide invalid source/rule references; W05 supplies the real product-assessment workflow.

## 7. Provider integration and separately bounded W04 budget

The user has authorized Nebius runtime integration using the credited project account. This assignment bounds **new W04** integration work, not a W01 retry or cap reset. Fixed endpoint `https://api.tokenfactory.nebius.com/v1/chat/completions`, exact model `nvidia/Nemotron-3.5-Super-VL`, text only, temperature 0, stream false, max_tokens 8192, top-level `chat_template_kwargs: {enable_thinking: false}`. Retain the observed working wire shape; do not introduce an untested response_format change merely because generic docs support it. Official [quickstart](https://docs.tokenfactory.nebius.com/quickstart) and [JSON guidance](https://docs.tokenfactory.nebius.com/ai-models-inference/json) were checked 30 October; generic JSON support does not establish this model's schema compatibility.

Use httpx already installed; no new SDK needed. 180-second request deadline; redirects disabled; bounded response size 2 MiB; no automatic HTTP or paid-job retries. Offline tests must default to no live network. Live mode is a separate explicit local configuration, unavailable by default. Runtime worker alone receives the designated `.env.local` as a read-only secret-file mount, outside the image. Read only NEBIUS_API_KEY using the proven literal .env parsing behavior, with explicitly supplied process environment precedence; no eval/interpolation/whole environment dump. Never pass secret values in argv, persist them in DB, run `docker compose config` with expanded secrets, or print the file/value. API/dispatcher/parser/test processes should not inherit it. A key-presence check prints only CONFIGURED/MISSING.

W04 budget identity `W04-backend-v1`: **at most 2 paid reservations total across all attempts/restarts; max cumulative reserved estimate $0.25; max 16,000 bounded input tokens and 8,192 output tokens per call**. Preserve every reservation, including timeouts, errors and uncertain outcomes. Accepted W01 remains 4/4 consumed; its estimated usage total $0.0128994 remains a separate historical record. No refund/reset on job retry or test-DB reset. The W04 cap is an engineering limit based on recorded pricing, not a provider-enforced billing guarantee.

Reserve durably under a PostgreSQL row lock before network dispatch and record an append-only attempt identifier, project/job/case, source/context/request/prompt/schema hashes, endpoint/model, conservative token bound, price basis, maximum estimated cost, status and timing. Mirror public-safe reservation/settlement metadata append-only to `.local/w04/provider/ledger.jsonl`; if DB and local history disagree, fail closed rather than reinitialize. Keep actual live accounting in the main DB/store, never the resettable test DB. Offline tests use explicitly separate synthetic ledgers. W01 observed price basis is $0.30/M input and $0.90/M output; record it as observed 29 October, verify a public provider price before sending, and stop if changed/unverifiable rather than silently substitute. Conservative UTF-8 input bound including message overhead must be <=16,000. At full bounds each reservation is $0.0121728 on that price basis; 2 reserve at most $0.0243456, below $0.25.

Paid sequence only after offline suite and connected mock tests pass:

1. One **real_source** request containing the bounded selected source/context anchors. Record actual complete wire request (without authorization), response, validation and usage privately with hash binding. If nonpassing/uncertain or obvious source distortion, stop paid execution; keep the second reservation unused.
2. Only on a structurally passing and provisionally source-faithful result, one **synthetic_missing_revision** request from an original deliberately incomplete labeled fixture with at least one supported statement and no document ID/revision. Both fields must remain null and missing information unresolved. Preserve exact provenance; synthetic live is not manufacturer-source evidence.

No third request, model switch, account change, purchase, automatic repair/retry or automatic expansion. Cache key includes source/extraction/context hash, endpoint/model, prompt/schema/request settings. Cache hit performs no paid call, is labeled cached with original live attempt provenance, and is revalidated; cache does not count as new live evidence. Missing key/model access completes independent offline work and reports PARTIAL. Never run the W01 probe CLI to accomplish W04 integration.

## 8. Durable execution and private evidence

Add job kind `source_extract` with server-pinned immutable input/config and stage results for parse, draft and final extraction manifest. Preserve existing artifact_digest behavior. The broker delivers IDs only; handlers load and validate job/project/context from DB. Worker attempts use W03 lease/heartbeat/token fences. All generated bytes use accepted staged storage and owned descriptor lifetimes; do not bypass storage with ad-hoc raw final paths. Finish file writes outside long transactions; short finalization locks/checks authority, source/hash and ownership before inserting immutable outputs. Stale/cancelled attempts cannot publish results. Awaiting review is business state, not a running job.

Crash after reservation/before response cannot safely retry inference: mark provider outcome uncertain, retain reservation, stop paid work; resume parsing/review or settle a previously persisted valid response without issuing another request. Distinguish retryable offline parse/infrastructure failure from non-retryable/uncertain paid outcomes. Duplicate delivery and API replay cannot duplicate source outputs/review events or paid reservations. Cancellation may not refund a completed call. Keep failed and unsupported coverage visible even when a job reaches a terminal execution state.

Raw PDF, complete text, request/response/validation bundles and test tokens stay private. Public W04 evidence contains hashes, versions, request IDs, usage/cost metadata, status/diagnostic summaries, synthetic cases and small necessary source excerpts only. Never publish full provider reasoning text or authorization headers. Reuse the accepted secret-redaction pattern and test logs/errors for fake secret leakage without loading the real key during offline tests.

## 9. Concrete verification and finish

Use actual local Postgres, Valkey, API/worker and private files. Keep isolated test DB/storage and a fresh main-store artifact/receipt sentinel before/after tests. Preserve the 41 known historical missing IDs; record any additional missing ID as failure, not historical noise. Apply 0004 to the existing main volume without reset; verify data/receipts across upgrade and idempotent repeat. Test reset is permitted only for the designated test DB/store. Do not overwrite W03 recovery/sentinel reports.

Implement test modules for source persistence/immutability/project references; real PDF anchors/coverage and malformed/scanned/over-limit parser cases; provider validation/budget/concurrency/cache/redaction/uncertain outcomes; review conversion/current authorization/replay/races; durable stage/crash/cancel/receipt recovery. Mock transport is permitted for deterministic provider failures and must be labeled. Required negative cases: foreign anchors/artifact/predecessor; wrong revision; missing/null/uncited claims; source instruction injection; table/footnote ambiguity; examples made mandatory; workaround-as-exception; wrong claim hash; unsupported selector/unit; stale/concurrent review; revoked role replay; parse timeout; truncated/empty/wrong-model response; ledger exhaustion/concurrent reservation; restart after reserved request with no response. No failure may activate a rule.

Provide `python -m erratascope_service.ingestion.cli` commands: `check-key` (presence only, only in explicit live runtime); `verify-ingestion --mode offline|live --case real_source|synthetic_missing_revision --output PATH`; `verify-evidence --manifest PATH`; `export-openapi --output PATH`. The CLI drives the actual authorized API/jobs and recomputes artifact hashes/validation; it must not assert acceptance from a stored boolean. Exit 0 for required checks passing, 2 for invalid/blocked/partial evidence, 1 for runtime failure. Offline mock success must be labeled and cannot satisfy a live gate. README must contain exact working start/test/live/recovery commands.

Required commands (adapt only output mounts to private W04 paths; inspect each exit):

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W04-backend-v1-baseline.json
docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet
docker compose -p erratascope-w03 -f infra/w03/compose.yaml build
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait db broker
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait api worker dispatcher
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests -q
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w03 -q
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w04 -q
```

Run the W03 sentinel suite with W03_SENTINEL_OUTPUT redirected to `/w04/sentinel-attempt-01.json`, not historical `/local` output. New Compose test scratch mount maps `.local/w04` to `/w04`. After suites, run connected `verify-foundation --output /w04/foundation-attempt-01.json` and new ingestion offline CLI; then invoke the separate live override only for the two bounded cases. Record exact commands in the report; no real key in tests or logs. If test JWTs expire, refresh only designated synthetic local tokens with existing key/JWKS and private history, without printing values.

Write `docs/evidence/W04/IMPLEMENTATION_REPORT.md`, sanitized OpenAPI/schema/provenance/coverage/usage summaries and machine-readable gate report. Report backend gates B1 source/parse/anchors/coverage, B2 strict provider/evidence/accounting including actual live cases, B3 reviewed conversion/authorization, B4 persistence/restart/idempotency/old-regression retention separately. Real semantic acceptance remains Codex's decision. Original W04-G5 UI is NOT_RUN (approval pending), so full W04/P3 cannot be accepted yet.

Recheck protected baseline; document all changes relative to starting inventory. Stop owned services, retain all volumes, release only your lock, write attempt-01 handoff and stop. Status READY_FOR_REVIEW/PARTIAL/BLOCKED only. Return the exact review prompt from [W04 start prompt](../prompts/W04-START.md). No Git mutation, no self-dispatch and no future packet implementation.

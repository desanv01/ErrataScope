# S01 revision 1 — runnable cited-review submission

**READY_TO_DISPATCH once `python scripts/verify_submission_baseline.py --starting` passes.** This is the only active implementation assignment. Read the W04 review and this complete binding; do not execute the original W05–W10 chain or reopen all W04 ambitions.

## 1. Result to deliver

Implement one coherent, attractive workspace reproducing the approved image, connected to the real local API:

1. Open the prepared real source and its **recorded live Nemotron interpretation**.
2. Select an entry/claim; inspect its exact source excerpts and physical/printed page metadata.
3. See source version/hash, selected coverage, incomplete inventory and unresolved fields.
4. Explicitly mark the interpretation reviewed or rejected, with a note; persist the decision with current authorization and optimistic concurrency.
5. Export a truthful JSON/Markdown review summary from current authorized data.
6. Demonstrate an original synthetic missing-information case, visibly labeled synthetic/offline. Never relabel it a passing W04 live omission case.

No executable applicability results, fact editor, VerifForge functionality, broad rule conversion, arbitrary PDF import or team-admin screens. Existing domain code stays available but these features are not in the submitted UI. A reviewed interpretation is not an accepted executable rule.

Feature freeze: **30 October 21:30 MYT**. If that time arrives before everything is complete, finish the core journey and report release-critical gaps; do not expand scope. Preserve 22:30–00:15 for release/video/submission. This is a deadline checkpoint, not authority to skip correctness.

## 2. Baseline, ownership and backup

Run `python scripts/verify_submission_baseline.py --starting`. It checks both protected hashes and current starting inventory. Back up every starting-inventory file to `.local/submission/history/before-attempt-01/<relative path>` and write a manifest of actual hashes before edits. Verify the backup. Read `docs/execution/WORKER_RULES.md` for the exclusive lock format; claim `.local/coordination/ACTIVE_WORKER.json` with packet S01 and attempt S01-attempt-01. This binding supersedes its old dispatch assumptions but preserves single-writer and secret rules. If a live owner exists, stop without changing their files. Never overwrite another worker lock.

Allowed existing edits: `backend/erratascope_service/api.py`, `backend/erratascope_service/config.py`, `backend/erratascope_service/ingestion/{api,cli,models,schemas,service,provider,jobs}.py`, `backend/tests_w03/test_migrations.py` **only expected migration-head assertions**, `infra/w03/Dockerfile`, `infra/w03/compose.yaml`, root `README.md` and `.gitignore`. Existing tests remain meaningful; no removing assertions. Ingestion provider/jobs edits are limited to truthful provenance/response persistence, idempotency and integration needs, not a new provider architecture.

Allowed new paths: `frontend/**`, `backend/erratascope_service/submission/**`, `backend/migrations/versions/0005_interpretation_review.py`, `backend/tests_submission/**`, `infra/submission/**`, `scripts/submission/**`, `docs/submission/release/**`, `docs/submission/evidence/S01/**`, `docs/submission/handoffs/S01-attempt-01.md`, root `LICENSE`. Private outputs only in `.local/submission/**`, designated existing dev-auth refresh files if needed, and the worker lock. If new integration tests belong in `backend/tests_submission`, they may import existing helpers without editing them.

Protected: all domain code/schemas, migrations 0001–0004, existing tests except the one allowed head assertion, all accepted W01/W02/W03 evidence, all historical W04 evidence/handoff, W01/W04 ledgers and live artifacts, all execution contracts/baselines and this binding/prompt, approved design image/decision. Do not reset DBs or volumes, rerun scripts which overwrite accepted recovery evidence, or edit old reports to turn red gates green. Tests use the existing test DB and physically isolated test store.

`python scripts/verify_submission_baseline.py` verifies protection after editing. Starting inventory is preflight-only, not a post-edit constraint. The manifest protects local provider histories as well as public files. Do not refresh it yourself.

## 3. Actual backend integration

Existing stack: `docker compose -p erratascope-w03 -f infra/w03/compose.yaml`; API `http://127.0.0.1:18080`; current migration `0004_ingestion`. Base compose has live inference disabled. Preserve database/store identity binding, role separation, staging ownership, descriptor lifetime, private artifact confinement and current membership checks.

Observed real routes (prefix `/api/v1`):

| Route | Use |
|---|---|
| `GET /projects` | Authorized project selection |
| `GET /projects/{project_id}/sources` | Authorized source list |
| `GET /projects/{project_id}/sources/{source_id}` | Source metadata |
| `GET /extractions/{extraction_id}` | Extraction status and coverage summary |
| `GET /extractions/{extraction_id}/anchors` | Paginated real excerpts/geometry |
| `GET /extractions/{extraction_id}/coverage` | Paginated selected/unprocessed inventory |
| `GET /extractions/{extraction_id}/drafts` | Actual draft records |
| `GET /drafts/{draft_id}` | Actual interpretation/validation/provenance |

Read actual OpenAPI and schemas before implementing the client; do not invent field names. Follow all cursors: there are 53 coverage entries, more than the default page. Claims use `citations`, not `anchor_ids`. Anchor pages are zero-indexed internally; display physical page +1 while preserving printed labels. Filter claim context by actual cited anchors, not guessed associations.

Existing demonstration IDs (local convenience, not hard-coded universal application data): project `8b497e89-40f7-421d-a76f-9573f3c2e57b`, source `8f3d777f-9e83-4cd7-b805-669825152c7b`, extraction `4ec4379e-16c9-4e72-a373-8734c6453f91`, draft `075a2625-862f-4d9a-b932-83f94358cb3d`. Discovery/bootstrap returns IDs so fresh installations do not depend on these UUIDs.

Add `GET /projects/{project_id}/submission-context` in the submission router: authorize project membership, return available source/extraction/draft IDs, recorded provenance and review state. Derive from DB, not decorative fixture data. This provides the missing navigation linkage without redesigning ingestion.

### Interpretation review contract

Add append-only interpretation-review rows via migration 0005. Store UUID, project/draft IDs, monotonically increasing revision per draft, exact draft `response_hash`, decision `reviewed` or `rejected`, required trimmed note (1–2000 chars), actor, UTC time. Unique `(draft_id, revision)`. No UPDATE/DELETE grant on review history; use the existing migration/app role pattern. Do not change ModelDraft or AcceptedRule state.

- `GET /drafts/{draft_id}/interpretation-reviews`: member access; ordered paginated history and current revision.
- `POST /drafts/{draft_id}/interpretation-reviews`: owner or reviewer only; require `Idempotency-Key`, `expected_revision` (0 initially), `expected_response_hash`, decision and note. Check current membership before replay. Lock draft row, verify revision/hash, append once; stale request 409. Same key/same body returns original result; different body 409; concurrent decisions cannot silently overwrite each other.
- `GET /drafts/{draft_id}/review-summary?format=json|markdown`: member access; source URL/hash/revision, actual model/provenance/time, claims with citation identifiers and page metadata, unresolved fields, selected/incomplete coverage, latest review and history, known limitations. No raw response, API key, JWT, full PDF or fabricated result. `reviewed` is human acknowledgement only.

Use existing structured errors/request IDs and authorization helpers. Do not weaken auth for a demo. The frontend may hold a short-lived local dev JWT in memory; never put provider keys or private signing keys in browser code. Local demo bootstrap may use existing generated dev-auth tools, bind localhost, and clearly label development auth. Hosted production acceptance is out of scope.

## 4. Consolidated W04 corrections in this slice

**A. Truthful evidence CLI.** `verify-evidence` must return nonzero for partial/blocked/failing/missing gate evidence, distinguish integrity from gate acceptance, require nonempty well-formed file bindings, and fail closed on malformed input. Add negative tests for empty files, partial status, failed nested gate, missing artifact and mismatched hash. Do not claim that a manifest alone validates live provenance. Preserve old worker reports; write new correction evidence separately.

**B. Provenance.** Historic W04 response artifacts contain normalized JSON; historic wire hashes cannot be re-derived from them. Preserve both original histories; expose that limitation in technical evidence, not as a fabricated verified-wire badge. For any future adapter response, retain bounded raw response bytes before draft validation and record separate raw-byte and normalized-artifact hashes. Tests use controlled mocked transport only. If implementing this would expand into a large provider rewrite, keep calls disabled and document the unresolved limitation instead; do not stall the UI over deferred fresh-call qualification.

**C. Extraction action.** Prefer no start-extraction control in this deadline UI: load the existing recorded live result. If exposing start, first implement and test idempotency plus authorization-before-replay; include clear budget denial. Never trigger inference automatically on mount/retry/refresh. No enabled button that cannot complete its advertised action.

## 5. Provider authorization and evidence

**ZERO paid calls in S01.** W01 remains 4/4, W04 remains 2/2. Do not reset counters, delete ledger rows, change budget IDs to evade limits, use another model/account, or run the live compose override. Do not open `.env.local` or need the Nebius key for this assignment.

Display the real case as **Recorded live Nemotron result**, with its actual request metadata; loading it is not a fresh call. Synthetic omission is **Synthetic / offline example**. Fresh installation may import a carefully labeled recorded demonstration snapshot but must not fabricate provider reservations or mark imports as newly live. The real adapter remains in the application for a user-configured fresh installation; instructions must explain paid generation requires their own authorized credits and budget. Do not run that path now.

## 6. Approved design and frontend

Authoritative image: `docs/submission/ui/approved-workspace-v1.png`, SHA256 `ef1fd06799767a526db678e6c47e7a97edc1944c883baab86e9155571bf2eeef`. Read `ui/APPROVED_DESIGN_BRIEF.md`. Dark compact workspace, narrow entry navigator, light source excerpt pane, adjacent review pane, amber unresolved states. No new visual approval needed for this direction. Remove facts/assessment controls in fallback. All pictured prose/pages are illustrative; use real data.

Use React/TypeScript/Vite; npm registry pins resolved30 October 2026: runtime `react=19.3.1`, `react-dom=19.3.1`; dev `vite=8.3.5`, `typescript=7.0.2`, `@vitejs/plugin-react=6.1.2`, `@types/react=19.3.0`, `@types/react-dom=19.3.0`. Node installed 24.14.1 / npm 11.19.0. Use exact package versions and commit lockfile. Run install/build to verify peer compatibility; ordinary compatible patch pin corrections are permitted if the actual resolver identifies incompatibility, with reasons in handoff. No extra UI framework required; plain CSS and small accessible components suffice.

Paths: `frontend/package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json`, `src/**`. Vite dev proxy forwards `/api` to localhost18080; localhost-only dev host. Production build served by the existing FastAPI app at `/` through a narrowly scoped static mount; register API before catch-all, unknown `/api` paths must remain JSON404. Add a multistage build to existing Dockerfile or an explicitly documented submission Dockerfile without breaking the existing service image/tests. No second backend server.

12ui skill applied by Codex: `12ui convert ... --engine codex --out-dir .local/submission/ui-conversion` and resume both failed before producing UI (`EPERM` cache, then Windows `spawn EINVAL` even after cache access). No generated HTML exists and no API fallback was used. Do not spend the submission window debugging the design tool. Implement against the actual approved image and brief, preserving its layout; compare real browser screenshots at desktop and narrow widths. If 12ui becomes usable, reuse the saved run and use its output, never buy/restart redundant conversions or replace the approved design. Record the unavailable-tool deviation honestly.

Required states: loading, no data, server failure, unauthorized/expired local token, known recorded result, synthetic unknown, citation selected, review success/rejection and stale conflict. Keyboard-operable controls, visible focus, labels and status text, readable contrast. On mobile collapse navigator/stack source and review; no horizontal clipping. Export must download real content. No hardcoded success counts or placeholder tabs.

## 7. Reproducible test build and release materials

Primary distribution is the public repository plus a reproducible **local test build**, not an unverified hosted URL. Add a single documented PowerShell launcher `scripts/submission/start.ps1` and stop helper; it builds, migrates in place, starts only project services, prepares explicit local dev auth and opens/prints localhost UI. Fresh setup uses an isolated compose project/database/store with its own correctly derived store identity; never reset or copy the current main DB. Reuse existing bootstrap mechanisms. No credentials in Git.

Provide two paths: current retained live-evidence workspace and a clean judge/demo installation. Download vendor PDF from its actual source URL with expected SHA256; on network/source change fail with a clear user-supplied-PDF option. Do not commit the full PDF. A small normalized recorded-demo snapshot may contain selected necessary cited excerpts/interpretation and actual provenance, with attribution and a visible recorded label; no full raw provider envelope or private account payload. Import it as recorded data through an explicit bounded bootstrap path, never an auth bypass exposed to arbitrary network callers. Missing provenance stays missing; never invent new live request IDs/history. A fully separate original synthetic demo is also useful but cannot substitute for the real runtime integration evidence.

Add root MIT license for original project code, explicit third-party source/model attribution, setup/test commands, product scope and honest limitations to README. Vendor documents/model outputs are not re-licensed as original code. Write `docs/submission/release/{TESTING,DEMO_SCRIPT,SUBMISSION_COPY,KNOWN_LIMITATIONS}.md`; demo script under 3 minutes, showing actual journey. No video upload or Devpost submission by this worker. Those are release actions for the user/Codex after review. No cloud provisioning or hosted claim.

## 8. Verification: focused, then hand off

1. Preflight baseline and verified backup.
2. New backend tests: review role denials/revoked-role replay, stale/hash conflict, concurrent review, immutable history, summary actual content/no secrets, evidence CLI negative cases. Use real PostgreSQL on test DB/store. Preserve existing W04 tests.
3. `npm --prefix frontend ci`, `npm --prefix frontend run build`, typecheck (script `typecheck`). Test actual UI against API, not just component mocks. A desktop browser journey and narrow viewport suffice; use Playwright if available, save screenshots privately and sanitized result metadata publicly. Test citation selection, recorded provenance, unknowns, review then rejection/history, stale conflict and export.
4. At integration checkpoint run retained 92 domain, 110 foundation and 11 W04 tests once plus new tests; do not repeat full suites after CSS-only changes. A meaningful new backend change/failure justifies affected reruns.
5. Before/after main artifact byte inventory; require readable sentinels stay byte-identical and legacy 41 missing remains unchanged. Never overwrite historical recovery JSON. Restart API and verify review/history/export persists.
6. Clean local test-build setup in separate project/store, one browser journey. Record exact commands and any remaining setup manual steps; don't claim tested fresh install if only using retained DB.
7. Recheck protected baseline and unchanged provider ledgers; sanitize outputs; release worker lock, stop only owned processes (retain volumes), then stop editing. No Git actions by worker.

Do not make screenshots look finished by replacing backend failures with constants. Fix release-critical gaps in this single assignment; report remaining noncritical issues explicitly. Do not start another packet or require another planning phase before implementing this bound scope.

## 9. Handoff

Write `docs/submission/handoffs/S01-attempt-01.md`: actual delivered route/UI/release paths; commands, counts and outputs; real/synthetic/cache distinction; mutation authorization/concurrency; source/coverage/unknown fidelity; baseline/backup results; unchanged ledgers; sentinel/legacy audit; screenshots; build/run instructions; spent resources; incomplete gates. Use READY_FOR_REVIEW only if the complete advertised journey and test build work. Acceptance remains Codex's decision.

Return this exact prompt:

> Review ErrataScope S01 revision 1 fallback submission slice, attempt 01. The worker has stopped editing. Read docs/submission/handoffs/S01-attempt-01.md, docs/submission/S01_BINDING.md and docs/execution/reviews/W04-review-01.md. Verify the S01 baseline and actual backend/browser/test-build flow. Independently check source citations and provenance, unknown handling, interpretation-review authorization/concurrency, truthful evidence gates and real export; preserve W01/W04 paid histories and legacy 41 missing artifacts. Distinguish recorded live data from new live calls and synthetic tests. Apply small release-critical fixes directly when safe, avoid a broad new audit cycle, then perform the public Git/GitHub checkpoint and give exact release/video/submission steps. Do not declare full W04/P3 or hosted P2 accepted. The imagegen direction is approved.

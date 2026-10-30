# S01 submission handoff — attempt 01

Status: **READY_FOR_REVIEW** (complete cited-review journey works in the retained local test build and in an isolated clean fresh-volume installation; public release actions remain for the user/Codex)
Assignment: S01 revision 1 fallback submission slice. Approved UI direction; no new design exploration requested.
Started/finished (UTC): 2026-10-30T11:04:27Z / 2026-10-30T11:37:41Z (final checks)
Feature-freeze checkpoint: 21:30 MYT.

## Preflight and preservation

- `python scripts/verify_submission_baseline.py --starting`: **PASS**, 467 checked, 0 errors.
- Starting inventory: **14/14** SHA-256 matches; verified backup `.local/submission/history/before-attempt-01/` (14 files + manifest, all match).
- No active worker lock; no prior S01 handoff. S01 lock claimed and later released.\n- Final protected baseline: **PASS**, 453 checked, 0 errors (`python scripts/verify_submission_baseline.py`).
- W01 ledger: 4/4, SHA-256 `028084e43708460cc0e6a35cc03000bbbf2c756c6c87f235bf52d333a84e55a6`. W04 ledger: 2/2, SHA-256 `f18b87a5c37dbcdf3aa2686f9e7a7784dcdf19d55c4d49e7eda48f67cd1ec1a9`.
- **ZERO new paid calls.** `.env.local` was not opened, no key was accessed, no budget was reset, no live compose override was used. W04 remains 2/2; W01 remains 4/4.

## Delivered

### Backend
- Migration `0005_interpretation_review` adds append-only `interpretation_reviews`: UUID, project/draft, monotonic revision, exact draft response hash, `reviewed`/`rejected`, required trimmed 1–2000-char note, actor, UTC, unique `(draft_id, revision)`, app-role insert-only and immutable trigger. ModelDraft/AcceptedRule state is untouched.
- New typed routes:
  - `GET /api/v1/projects/{project_id}/submission-context` — authorized project membership; DB-derived source/extraction/draft cases, recorded/synthetic labels, provenance, review state.
  - `GET /drafts/{id}/interpretation-reviews` — member, ordered/paginated history, current revision.
  - `POST /drafts/{id}/interpretation-reviews` — owner/reviewer; `Idempotency-Key`, `expected_revision`, `expected_response_hash`, decision, note; current membership checked before replay; draft row locked; stale/hash conflicts 409; same-key replay; different body 409.
  - `GET /drafts/{id}/review-summary?format=json|markdown` — source URL/hash/revision, actual recorded provenance/model/request ID/usage/hashes, claims with resolved citation identifiers and physical/printed page metadata, unresolved fields, selected/incomplete coverage, latest review and full history, known limitations. No raw response, key, JWT or PDF.
  - `GET /api/v1/submission/dev-session` — local-only development auth bootstrap; unavailable without explicit dev-auth dir; no signing key in browser.
- A reviewed interpretation is acknowledgement only and never creates an `AcceptedRule`.

### Frontend (approved direction)
- React 19.3.1 / Vite 8.3.5 / TypeScript 7.0.2, exact pins in `frontend/package.json`; lockfile generated.
- Dark compact workspace, narrow source/entry navigator, light located source pane, adjacent interpretation/review pane, amber unresolved treatment, blue action accent; desktop and narrow responsive behavior.
- Actual API data: real source identity/selected entries, page-labelled citations, claim citation chips, source context, 53-entry coverage with incomplete/unselected disclosure, provenance card, review note/actions, append-only history, stale conflict, JSON/Markdown download.
- Synthetic case appears as **Synthetic / offline example** with an explicit non-live limitation; real case is **Recorded live Nemotron result** with actual request ID/usage. No extraction-start button; no auto inference.
- Static production build is served by the existing FastAPI app at `/`; unknown `/api` paths remain JSON 404. Multistage Node build added to the existing Dockerfile; no second backend server.

### Evidence CLI correction
- `verify-evidence` now fails closed on malformed/empty manifests, non-pass status, non-pass or missing gates, empty file bindings, missing files and hash mismatches; reports `integrity_pass` and `gate_pass` separately; a manifest pass is explicitly not new live success.
- Negative tests cover partial/failed gate, missing/mismatched file, malformed and empty manifest. S01's own partial gate manifest correctly returns exit **2**.

### Release materials
- Root `LICENSE` (MIT for original code; vendor/model exclusions).
- Root README updated with current submission status, local start, scope and limitations.
- `scripts/submission/start.ps1` and `stop.ps1`; local browser launcher.
- `docs/submission/release/{TESTING,DEMO_SCRIPT,SUBMISSION_COPY,KNOWN_LIMITATIONS}.md`.
- Sanitized evidence under `docs/submission/evidence/S01/` including desktop/narrow screenshots, browser results, export, audit, sentinel, clean-install evidence, gate report and evidence-command output.
- Isolated clean demo path: `scripts/submission/start-clean.ps1` creates project `erratascope-s01-demo`, fresh database/storage volumes, imports `docs/submission/demo/recorded-demo.json` through `backend/erratascope_service/submission/demo_import.py`, serves at port 18081 and makes **zero provider calls**. It was exercised in a real browser.

## Verification results

| Check | Result |
|---|---|
| `verify_submission_baseline.py --starting` | PASS (467) |
| Starting inventory/backup | 14/14 match |
| `npm --prefix frontend ci` | PASS |
| `npm --prefix frontend run typecheck` | PASS |
| `npm --prefix frontend run build` | PASS (dist built) |
| Docker Compose build (with frontend stage) | PASS |
| Migration 0005 to main/test | PASS, head `0005_interpretation_review` |
| S01 backend tests | **6/6 PASS** |
| W04 backend tests | **11/11 PASS** |
| W03 foundation tests | **110/110 PASS** |
| Domain tests | **92/92 PASS** |
| Real browser journey | **22/22 checks PASS**; desktop 1586×992, narrow 390×844, no horizontal overflow |
| Clean isolated install | **PASS**: project `erratascope-s01-demo`, fresh volumes, port 18081, recorded-demo snapshot imported; clean browser journey 7/7 |
| Review persistence across API restart | PASS: 2 cases, revision 8, 8 history rows, 8,911-byte Markdown export |
| Main sentinel | PASS: `f6ea27bb44d74bd7b69cf407e60281a3004b326f50063ab4a027666b39fe49cd`, byte-identical |
| Main artifact audit | 157 rows, 116 readable, **41 missing**; IDs match legacy exactly, no new missing |
| Evidence command on partial S01 manifest | exit 2 (truthful; integrity pass, gate partial) |
| `scripts/submission/start.ps1 -NoBuild` | PASS; UI at `http://127.0.0.1:18080/` |

Browser checks included: recorded live label, real ES0620/Rev 5 identity, no illustrative 12/48, real NRST/DBGMCU content, incomplete coverage, citation selection highlight, synthetic case offered/labelled, review recorded, external revision conflict visible, Markdown export downloaded with real content and no secret material, narrow no-overflow, no unexpected console errors (expected stale 409 only).

## Real vs synthetic distinction

- **Recorded live Nemotron result:** ES0620 Rev 5, extraction `4ec4379e-16c9-4e72-a373-8734c6453f91`, draft `075a2625-862f-4d9a-b932-83f94358cb3d`; actual provider request ID, usage (3247 prompt / 1587 completion) and response hash retained from the W04 history. Loading is not a new call. The normalized-artifact/original-wire-byte hash limitation is shown in the UI/details and export.
- **Synthetic / offline example:** original synthetic missing-information source/draft (source `a1e067e8-57c4-4b6d-aea3-b797bcb6a1a0`), visibly labelled; it is not a live omission pass and is not manufacturer applicability.
- W04's failed synthetic live attempt and W01 history remain unchanged in their historical evidence.

## Authorization/concurrency evidence

- Owner/reviewer writes; editor gets 403; unrelated user cannot access the project.
- Review requires current membership before idempotent replay; a revoked reviewer replay is denied.
- `expected_revision`/`expected_response_hash` conflicts return 409; concurrent duplicate decisions produce one 201 and one 409; review rows are immutable (UPDATE trigger rejected).
- Summary/export are member-only and contain no bearer token/API key material.

## UI verification and deviations

- Approved image dimensions: 1586×992; implemented desktop and narrow screenshots are under `docs/submission/evidence/S01/screenshots/`.
- The 12ui conversion tool was already unusable per binding (EPERM cache then Windows spawn EINVAL); no generated output existed. Implementation was done directly against the approved brief/image; no design restart or new approval.
- The live project initially was not found because project discovery stopped at the first page/newer offline project; fixed to follow all project cursors and prefer a project containing the recorded live case. The browser journey then passed.
- Citation chips from the raw draft are strings in the API; the UI resolves them against actual anchors before rendering page metadata/highlights.
- Browser runs created multiple genuine append-only review rows on the retained demo draft; history is truthful and not fabricated.

## Incomplete release-critical gates

1. Public video, public Git/GitHub checkpoint and Devpost submission were explicitly out of worker scope; release copy/demo script are drafted only. The S01 gate manifest therefore remains `partial` and `verify-evidence` correctly exits 2; integrity passes and all implementation gates pass.
2. Full W04/P3 remains not accepted; hosted P2 NOT_RUN. Applicability/facts assessment and executable rule acceptance remain out of scope.
3. Historical 41 missing artifacts remain unreplaced.
4. The clean install imports the recorded live case only; the synthetic/offline example is verified in the retained workspace, not yet in the clean snapshot import.

The core implementation and both local test-build paths are ready for independent review; remaining items are release operations and the explicitly separate W04/P3 acceptance.

## Resource state

Services built from pinned images; retained `erratascope-w03` volumes and isolated `erratascope-s01-demo` demo volumes are retained. At finish all owned API/worker/dispatcher/broker/db processes for both projects were stopped (`Exited (0)`). No Git, cloud, video upload or Devpost action. No other project touched.

## Return prompt

> Review ErrataScope S01 revision 1 fallback submission slice, attempt 01. The worker has stopped editing. Read docs/submission/handoffs/S01-attempt-01.md, docs/submission/S01_BINDING.md and docs/execution/reviews/W04-review-01.md. Verify the S01 baseline and actual backend/browser/test-build flow. Independently check source citations and provenance, unknown handling, interpretation-review authorization/concurrency, truthful evidence gates and real export; preserve W01/W04 paid histories and legacy 41 missing artifacts. Distinguish recorded live data from new live calls and synthetic tests. Apply small release-critical fixes directly when safe, avoid a broad new audit cycle, then perform the public Git/GitHub checkpoint and give exact release/video/submission steps. Do not declare full W04/P3 or hosted P2 accepted. The imagegen direction is approved.




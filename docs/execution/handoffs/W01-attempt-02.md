# Worker handoff — W01 repair 01, attempt 02

Status: **PARTIAL**
Packet revision: W01-feasibility revision 1 + repair 01 (W01-R01)
Started/finished (UTC): 2026-10-29T10:19:25Z / 2026-10-29T10:29:46Z (last report); final baseline recheck timestamped below
Starting baseline and verification result: **PASS** before any write — `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-01-baseline.json` exit 0, 56 protected hashes, 163 links, 0 errors. Recorded for this attempt in `.local/w01/results/baseline_check.json`. Recheck after execution: **PASS**, same counts.
Worker/harness: DeepSeek harness (`deepseek-flash`), single implementation worker in the DSH Web GUI. No subagents, no delegated workers.
Worker stopped editing: yes
Coordination lock released: yes — `.local/coordination/ACTIVE_WORKER.json` removed after this file was written.
Owned processes stopped / remaining process IDs: **none**. No server, container, background process, or paid request was started; every case preflight exited before dispatch.

## Implemented behavior (repair dispositions)

The source/parser work from attempt 01 is preserved: same downloaded bytes, same SHA-256, same 78 anchors (68 preserved + 10 new context anchors), same bounded selected sections and page renders. Docling was **not** re-converted (cached items reused); `parse-source` re-verified the sealed hash before writing.

### R1 — Reserve before dispatch; preserve uncertain attempts — implemented

- New `spikes/w01/erratascope_w01/ledger.py`: a validated ledger schema (`LedgerState`, `AttemptReservation`, `PricingEvidence`) with **atomic fsync + `os.replace`** writes. `run_case` calls `ledger.reserve(...)` and persists attempt number, case, prompt version, provider/model identity, input-token bound and method, max output tokens, conservative cost, and pricing snapshot **before** writing the request artifact and before `mark_dispatched`.
- Attempt numbers are derived from stored attempts and never reused; the ledger is never reset by any command. If the process dies after dispatch, the attempt remains `dispatched`/`uncertain` and still consumes budget.
- Timeouts/transport errors finalize as `uncertain` (`mark_uncertain`), HTTP errors as `http_error`, malformed bodies as `invalid_json`, empty/truncated completions as `empty`/`truncated`, schema failures as `schema_invalid`, and wrong returned models as `model_mismatch`. None erase the reservation or its cost.
- Caps are unchanged and enforced in one place: **3 attempts total**, 16,000 input tokens, 8,192 output tokens, **US$0.25** aggregate. `ledger.load_pricing` validates finite, non-negative rates, USD currency, provider/model/base-URL match, an http(s) source URL, an ISO verification date, and text-only modality scope; invalid configuration exits 2 with a visible message.
- The chars/4 heuristic is gone. `ledger.bound_input_tokens` documents a UTF-8 byte bound (`tokens <= UTF-8 bytes` for byte-level BPE), ×1.1 for JSON escaping, +8 tokens/message, +64 framing. If the bound exceeds the cap the reservation is refused rather than underestimated. Measured bounds: real-source payload **8,838**, synthetic payload **5,075** (both well under 16,000).
- `record_blocked` only appends a `blocked_events` entry; it never rewrites attempts or `requests_reserved`. Six blocked preflights are recorded in this attempt, all *after* zero attempts existed, so history is intact.

### R2 — Evidence-derived gate results — implemented

- `report.compute_gates` and `report.derive_case_gate` are pure functions over records. G1 reads `.local/w01/results/baseline_check.json`; G5's local half reads `selftest.json`; G4 and the live half of G5 read only the latest attempt for their own case from the ledger.
- Records are only accepted for this attempt: `_is_current` compares timestamps with `WORKER_ATTEMPT_START_UTC` (10:19:25Z), so attempt-01 or stale records cannot become PASS. A missing or old record is NOT_RUN / PARTIAL, never PASS.
- The live gate requires: `execution_mode == live`, state `finalized`, outcome `success`, HTTP 200, exact configured model (alias map is empty and documented), `finish_reason == stop`, accepted JSON/schema/citation validation artifact present, and request/response/validation artifacts that exist on disk tied to that case.
- Mocks are recorded with `execution_mode="mock"` and are excluded from live gates. Usage missing from a response stays `available: false`, never zero. Hard-coded baseline/local-test success claims were removed; the report prints the recorded verifier counts and timestamps.

### R3 — Source identity and citation context — implemented

- Payload identity is read from the sealed manifest record (`cases.source_identity_from_manifest`), not literals: document ID, revision, publication date, manufacturer, SHA-256, page count, and the identity anchor IDs.
- New `context.py` adds 10 located context anchors to `anchors.json`, with `context_kind` and real pdfplumber geometry: `source_identity` (`ES0620 - Rev 5 - August 2026`), three `revision_header` cells (`Rev. Z/B/X`), four `status_legend` rows (`A/N/P/-`), and two `footnote` spans (datasheet identification, `REV_ID[15:0]`). The derived revision matrix in the prompt names its row anchor and governing header anchors, so it is no longer uncited authority.
- `validate.py` now takes an expected sealed identity and rejects: a document ID that does not match, a missing sealed revision, a revision not grounded in a cited identity anchor, a revision asserted against an identity that has none, and `affected_revision` claims that do not cite a revision-matrix row, revision header, or status-legend anchor (document revision cannot stand in for silicon revision). Context rules apply only when identity context exists, so the attempt-01 fixtures remain valid.
- Prompt version is `draft-v2`; the system prompt requires copying identity from the identity anchor and separating document revision from silicon revision.

### R4 — Runnable cases and validated pricing — implemented

- `probe-provider` now requires exactly one `--case {real-source, synthetic-missing-revision}` per invocation and accepts `--pricing-file PATH` (default: protected `docs/execution/reviews/W01-pricing-evidence.json`). It never runs both cases and never retries.
- The protected Codex pricing evidence validated through `load_pricing`: model `nvidia/Nemotron-3.5-Super-VL`, base `https://api.tokenfactory.nebius.com/v1/`, input **$0.30/1M**, output **$0.90/1M**, verified 2026-10-29, source URL recorded, `account_access_verified=false`. This is persisted as ledger metadata, not as an attempt; no human edits any counter.
- Offline regression checks ran **before** either preflight (41 checks). With `NEBIUS_API_KEY` absent, both cases recorded a blocked preflight and exited 2 without a request.

## Changed files

Created:

- `spikes/w01/erratascope_w01/ledger.py` — reservation ledger, pricing validation, token bound
- `spikes/w01/erratascope_w01/cases.py` — case builders, manifest identity, omission expectation
- `spikes/w01/erratascope_w01/context.py` — identity/header/legend/footnote anchors
- `spikes/w01/prompts/draft_v2_system.md`, `draft_v2_user.md`, `draft_v2_schema.md`
- `spikes/w01/prompts/synthetic_missing_user.md`

Modified:

- `spikes/w01/run.py` (case/pricing args, `verify-baseline`, attempt-tagged command log, attempt metadata)
- `spikes/w01/erratascope_w01/provider.py` (reservation-first dispatch; case execution; structural live gate; mock labelling)
- `spikes/w01/erratascope_w01/report.py` (evidence-derived gates; current-attempt checks; repair dispositions; current-vs-historical commands)
- `spikes/w01/erratascope_w01/validate.py` (sealed identity, silicon-vs-document revision, context citation rules)
- `spikes/w01/erratascope_w01/selftest.py` (41 offline checks)
- `spikes/w01/erratascope_w01/schemas.py` (`context_kind`, `geometry_kind`, nullable document ID)
- `spikes/w01/erratascope_w01/config.py` (pricing path, repair baseline, attempt identity, alias map)
- `spikes/w01/erratascope_w01/util.py` (`atomic_write_json`)
- `spikes/w01/erratascope_w01/anchors.py` (context anchors, measured page inventory)
- `spikes/w01/erratascope_w01/context.py`, `extract_pdfplumber.py`, `envprobe.py` (small lint/robustness fixes)
- `spikes/w01/README.md` (repair behavior, cases, pricing, ledger, updated limits)
- `docs/evidence/W01/FEASIBILITY_REPORT.md`, `docs/evidence/W01/ENVIRONMENT.json` (regenerated for this attempt)
- `fixtures/manifests/w01/sources.json` (selection counts refreshed by `parse-source`; source bytes/hashes unchanged)
- `.local/w01/results/*` — anchors (78), coverage, revision matrix, inventory, renders, baseline_check, selftest, report summary, command log, `provider/ledger.json`, `provider/cases/**` request/response/validation artifacts, `tmp/selftest/**`

Preserved, not modified: `docs/execution/handoffs/W01-attempt-01.md`, `docs/execution/reviews/**` (including the protected attempt-01 checker and pricing evidence), `.local/reviews/**`, plans/contracts/status/baselines, all reference/visual assets. No Git repository exists and no Git command was run.

## Checks actually run

Working directory for every row: `C:\Users\Dv\Desktop\ErrataScope`.

| Command | Exit code | Result/log path | Interpretation |
|---|---|---|---|
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline` (initial) | 0 | `.local/w01/results/baseline_check.json` | Repair baseline PASS: 56 protected hashes, 163 links |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py parse-source` | 0 | `.local/w01/results/anchors.json` etc. | 78 anchors (10 context), 2/2 sections anchored, sealed hash re-verified |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test` (first run) | 1 | `.local/w01/results/selftest.json` | 1 failing check: attempt-01 fixture lacked a context anchor identity citation; rule tightened, then fixed |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test` (final) | 0 | `.local/w01/results/selftest.json` | **41 checks: 40 PASS, 0 FAIL, 1 SKIP** (secret scan skipped, no key) |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source` | 2 | `.local/w01/results/provider/ledger.json` | BLOCKED preflight: `NEBIUS_API_KEY` not configured; zero dispatches |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision` | 2 | `.local/w01/results/provider/ledger.json` | BLOCKED preflight: same; zero dispatches |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env` | 0 | `docs/evidence/W01/ENVIRONMENT.json` | Refreshed for this attempt; Python 3.11.15, docling 2.144.0, pdfplumber 0.11.10; Docker daemon not reachable; WSL access denied |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py report` (final) | 0 | `docs/evidence/W01/FEASIBILITY_REPORT.md` | Gates computed from records: G1 PASS, G2 PASS, G3 PASS, G4 NOT_RUN, G5 PARTIAL, G6 PASS, G7 PASS |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-01-baseline.json` (final) | 0 | stdout + `baseline_check.json` | Repair baseline unchanged after execution |

Two intermediate `self-test` runs exited 1 while the new identity and timestamp rules were being corrected (fixture-side issues, not waivers); the final suite is green with no expectations loosened. Every run is timestamped and attempt-tagged in `.local/w01/results/command_log.json`.

## Required gates

| Gate ID | PASS / FAIL / NOT_RUN / PARTIAL | Supporting artifact | Limits |
|---|---|---|---|
| W01-G1 | **PASS** | `.local/w01/results/baseline_check.json` (exit 0, 56 hashes, 163 links, recorded this attempt) | Final recheck identical |
| W01-G2 | **PASS** | `fixtures/manifests/w01/sources.json`, `.local/w01/results/anchors.json` | Selected-entry coverage only; inventory text-layer, incomplete |
| W01-G3 | **PASS** | `anchors.json` + `.local/w01/pages/*.png` | 13 selected-section anchors with bbox; 6 rendered pages, overlays visually checked |
| W01-G4 | **NOT_RUN (BLOCKED)** | `.local/w01/results/provider/ledger.json` (0 attempts, blocked event for `real_source`) | `NEBIUS_API_KEY` absent; no HTTP, no usage/latency/request ID exists |
| W01-G5 | **PARTIAL** | `selftest.json` (40 pass / 0 fail / 1 skip) + blocked `synthetic_missing_revision` event | Local half passes; live omission case not executed |
| W01-G6 | **PASS (synthetic fallback)** | `spikes/w01/fixtures/synthetic/SYNTHETIC_{old,new,missing_revision}.md`; manifest records `synthetic: true` | No authentic manufacturer pair; NXP PCN still HTTP 404 |
| W01-G7 | **PASS** | `FEASIBILITY_REPORT.md`, `ENVIRONMENT.json` (both current) | Account/model availability remains unverified by design |

## Repair verification mapping (R1–R4)

| Repair | Checks that demonstrate it | Result |
|---|---|---|
| R1 | `four_timeouts_stop_at_three` (4 simulated timeouts → 3 dispatches, 3 uncertain reservations, 1 guard refusal), `restart_reads_reservations`, `malformed_response_consumes_attempt`, `history_survives_blocked_preflight`, `atomic_ledger_write`, `token_bound_documented`, `invalid_pricing_rejected` (NaN, negative, infinite, wrong model, wrong base URL, missing source) | PASS |
| R2 | `gate_401_not_pass`, `gate_500_not_pass`, `gate_wrong_model_not_pass`, `gate_truncated_not_pass`, `gate_empty_not_pass`, `gate_malformed_json_not_pass`, `gate_invalid_draft_not_pass`, `gate_mock_not_live`, `gate_missing_artifacts_not_pass`, `gate_well_formed_record_passes`, `gate_no_negative_case_partial`, `gate_failing_local_check_not_pass`, `baseline_missing_record_not_pass` | PASS |
| R3 | `identity_correct_accepted`, `identity_unrelated_document_rejected`, `identity_wrong_revision_rejected`, `identity_missing_revision_unresolved`, `identity_silicon_revision_not_from_document`, `context_anchors_present` | PASS |
| R4 | `pricing_evidence_accepted`, `invalid_pricing_rejected`, plus both real CLI preflights exiting 2 without dispatch | PASS (offline); live BLOCKED |

### Attempt-01 checker compatibility

The protected `docs/execution/reviews/W01-review-01-checks.py` was **not run and not modified**. It imports `provider.probe`, `provider.build_draft_payload`, and `report._gate_rows`, which the repair deliberately replaced, and it writes into protected `.local/reviews/W01-review-01/`. Equivalent regressions above cover each defect it reproduced:

| Attempt-01 checker observation | Repair regression |
|---|---|
| `timeout_budget`: 4 dispatches, 0 recorded | `four_timeouts_stop_at_three`: 3 dispatches, 3 reservations, 4th refused |
| `report_on_failed_request`: G4/G5 PASS on HTTP 401 | `gate_401_not_pass`, `gate_500_not_pass` |
| `gate_accepts_truncated_wrong_model`: true | `gate_truncated_not_pass`, `gate_wrong_model_not_pass` |
| `wrong_source_id_validation`: accepted | `identity_unrelated_document_rejected` (+ `identity_correct_accepted` positive control) |

## Source/model evidence

- **Source bytes unchanged** (no re-download): ST ES0620 Rev 5, August 2026, 38 pages, `application/pdf`, 1,674,378 bytes, SHA-256 `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`; `parse-source` re-verified the file hash against the manifest before anchoring.
- **Anchors:** 78 total (68 preserved Docling/pdfplumber anchors + 10 context anchors). Context spans: identity (page 0), `Rev. Z`, `Rev. B`, `Rev. X` headers, four legend rows, two footnotes — all with top-left normalized bboxes and original coordinates. Selected sections remain 2.2.18 (Z=A, B=A, X=-) and 2.2.5 (Z=N, B=A, X=A).
- **Provider:** **no live request was made.** Ledger: `requests_reserved=0`, `spend_reserved_usd=0`, `live_requests_made=false`. Both case preflights were blocked by the missing `NEBIUS_API_KEY` (verified absent in process, user, and machine scopes by name only).
- **Pricing:** validated from the protected Codex evidence (input $0.30/1M, output $0.90/1M, verified 2026-10-29, source URL retained, account access not verified). Conservative per-attempt cost bound from the measured token bounds is ≈ **$0.0100** (real) and ≈ **$0.0089** (synthetic), well under the $0.25 aggregate cap.
- **Mock/cache distinction:** mocks exist only inside the offline self-test, are recorded with `execution_mode="mock"`, and `passes_live_gate` returns False for them (asserted). No cached or mock output is presented as live anywhere.
- **Usage honesty:** missing usage is recorded as `available: false`, never zero.

## Deviations and blockers

1. **`NEBIUS_API_KEY` is absent** from the worker process (also absent at user/machine scope; names checked only). This blocks W01-G4 and the live half of W01-G5. No request was made; no fixture substitutes for it.
2. **Account/model availability remains unverified.** Published pricing is now recorded, but HTTP 401/public pricing does not prove that `nvidia/Nemotron-3.5-Super-VL` is enabled on the account or that the full endpoint behaves as documented. A real call is the only evidence.
3. **Protected attempt-01 checker not rerun** (removed public signatures and protected output path); equivalence table above. `.local/reviews/W01-review-01/` was left untouched.
4. **Intermediate in-scope failures were fixed, not waived:** an over-strict identity-citation rule broke the attempt-01 fixture (fixed by applying the rule only when identity context exists), and two gate tests initially lacked a current `generated_utc` (fixture fixed; product rule unchanged). Final suite: 40 PASS / 0 FAIL / 1 SKIP.
5. **Carried limitation from attempt 01:** Docling's table-structure model reported 1 of 1,462 summary-table cells dropped from its own table; the revision matrix continues to come from pdfplumber word bands, cross-checked on the render.
6. **NXP PCN remains HTTP 404**, so no authentic old/new manufacturer pair exists; the labeled synthetic fallback is retained (G6 fallback only).
7. **Not attempted, by scope:** no Git mutations, UI, infrastructure, deployment, W02, or control-document edits.

## Reproduction

Working directory: `C:\Users\Dv\Desktop\ErrataScope`.

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe spikes/w01/run.py fetch-source
.local\w01\venv\Scripts\python.exe spikes/w01/run.py parse-source
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-01-baseline.json
```

`probe-provider` accepts `--pricing-file PATH`; the default is the protected Codex pricing evidence. Required variable name only: `NEBIUS_API_KEY` (live cases only). `HF_HOME`, `HF_HUB_DISABLE_XET`, `TEMP`, `TMP` are set by `run.py` for Docling.

## Protected baseline recheck

**PASS** after execution: `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-01-baseline.json` → exit 0, `protected_hashes_checked: 56`, `local_links_checked: 163`, `errors: []` (recorded in `.local/w01/results/baseline_check.json`). No protected file was modified; every created/modified path is listed above and lies inside `spikes/w01/**`, `fixtures/manifests/w01/**`, `docs/evidence/W01/**`, `docs/execution/handoffs/W01-attempt-02.md`, or `.local/w01/**`. No acceptance claim is made; Codex decides.

## Return prompt

> Review ErrataScope W01 repair 01, worker attempt 02. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-02.md and docs/execution/reviews/W01-repair-01.md. Verify the repair protected baseline and independently check R1–R4 against actual files and artifacts. Require real provider evidence for G4 and the live part of G5. Record acceptance or remaining repairs; W02 stays unbound until all required W01 gates pass. Preserve the UI/imagegen approval gate.

# W01 feasibility report — worker repair draft (W01-attempt-06)

Status: **worker draft for Codex review**. Gate values below are computed from records written by this attempt; this file does not accept a gate or change canonical status.

- Generated: 2026-10-29T15:07:31Z
- Packet: W01-feasibility revision 1; evidence attempt: W01-attempt-06
- Configured worker baseline: W01-live-v4-baseline.json; see recorded baseline below for the actual verification target
- Source document: ES0620 Rev 5 (August 2026), 38 pages
- Source SHA-256: `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`
- Selected sections: 2.2.18, 2.2.5

## Gate table (computed from this attempt's records)

| Gate | Status | Reason | Evidence |
|---|---|---|---|
| W01-G1 | **PASS** | 142 protected hashes / 233 links checked at 2026-10-29T15:07:29Z | protected baseline record from this attempt |
| W01-G2 | **PASS** | source hash bound to anchors; 2 selected sections anchored | sealed source + anchor bundle + coverage |
| W01-G3 | **PASS** | 13 selected-section anchors with bbox and 6 rendered pages | selected anchors with bbox + page renders |
| W01-G4 | **PASS** | attempt 3 evidence PASS: artifacts bound to case/attempt/model/endpoint; hashes match; completion stop; recomputed validation accepted | real_source case artifacts in the ledger |
| W01-G5 | **PASS** | local checks pass and the live omission case evidence passed | local self-test + synthetic_missing_revision case |
| W01-G6 | **PASS** | 3 labeled synthetic fixtures with hashes; no manufacturer pair claimed | synthetic fixtures + manifest records |
| W01-G7 | **PASS** | environment, baseline, and local-check records are current for this attempt; provider/account gaps listed below | environment/baseline/self-test records; uncertainties below |

A live gate requires a real dispatched request, the configured model binding, a complete non-truncated completion, accepted schema/citation validation, and case-bound artifacts. Mocks, caches, failed requests, unexecuted cases, and missing records are nonpassing.

## Repair dispositions (R1–R4)

| Repair | Disposition | Evidence | Limit |
|---|---|---|---|
| R1 reservation/uncertainty | Implemented and regression-tested offline | `spikes/w01/erratascope_w01/ledger.py` (atomic reservation before dispatch, never reused); checks `timeouts_stop_at_request_cap`, `restart_reads_reservations`, `malformed_response_consumes_attempt`, `history_survives_blocked_preflight`, `atomic_ledger_write`, `token_bound_documented`, `invalid_pricing_rejected` | See the provider ledger below for actual dispatch and reservation evidence; offline tests alone do not prove live behavior |
| R2 evidence-derived gates | Implemented with a shared artifact-content validator; gate values computed from records | `report.compute_gates` calls `evidence.evaluate_case` (same path as the CLI) for G4/live G5: case/attempt binding, artifact JSON contents, recorded SHA-256 replacement checks, HTTP status, returned model, `finish_reason=stop`, response/draft agreement, recomputed schema/citation/identity validation against pinned inputs, and the synthetic omission expectation; checks `gate_401_not_pass`, `gate_500_not_pass`, `gate_wrong_model_not_pass`, `gate_truncated_not_pass`, `gate_empty_not_pass`, `gate_malformed_json_not_pass`, `gate_invalid_draft_not_pass`, `gate_empty_artifact_not_pass`, `gate_directory_artifact_not_pass`, `gate_wrong_case_not_pass`, `gate_wrong_attempt_not_pass`, `gate_replaced_artifact_not_pass`, `gate_draft_disagreement_not_pass`, `gate_synthetic_bundle_passes`, `gate_synthetic_expectation_required`, `gate_mock_not_live`, `gate_missing_artifacts_not_pass`, `gate_well_formed_record_passes`, `cli_report_gate_consistency`, `gate_no_negative_case_partial`, `baseline_missing_record_not_pass` | See current gate table: historical credential failures do not override executed evidence |
| R3 source identity/context | Implemented; identity read from the sealed manifest and citable | `cases.py` payload identity; `context.py` identity/revision-header/legend/footnote anchors; `validate.py` identity + silicon-vs-document revision checks; checks `identity_correct_accepted`, `identity_unrelated_document_rejected`, `identity_wrong_revision_rejected`, `identity_missing_revision_unresolved`, `identity_silicon_revision_not_from_document`, `context_anchors_present` | Identity consistency is structural, not semantic proof |
| R4 runnable cases/pricing | Implemented; explicit per-case selection and validated pricing input | `run.py probe-provider --case ... --pricing-file ...`; `ledger.load_pricing` against the protected Codex pricing evidence; checks `pricing_evidence_accepted`, `invalid_pricing_rejected` | Live cases blocked: `NEBIUS_API_KEY` absent from the worker process |

## R2 evidence binding (repair 02)

Both `probe-provider` and this report now call one validator, `evidence.evaluate_case`. It does not trust ledger summary flags or artifact existence:

1. The ledger record case must equal the expected gate case, and the attempt must be the finalized attempt reserved in the intended ledger (mock/uncertain/failed records cannot pass).
2. The request, response, and validation JSON files are read and parsed; empty objects, directories, missing files, malformed JSON, and paths outside the provider artifact tree are rejected.
3. Each artifact carries its own case, attempt, kind, and schema version, and its SHA-256 recorded in the ledger at creation; a later replacement is detectable and fails.
4. The response must be HTTP 200 with the configured model returned, nonempty content, and `finish_reason=stop`; the same conditions are enforced in execution, CLI, and report.
5. The saved draft must equal the response content, and schema/citation/identity validation is recomputed against pinned document hash, anchor fingerprint, and identity; a stored `accepted` string cannot overrule the recomputation.
6. The synthetic case must independently reproduce its missing-information expectation; a real-source result cannot substitute for it.

Attempt-02 behavior was: gate PASS if `live_requests_made`/`validation.status` were optimistic and the artifact paths existed; its positive test used `{}` files. Attempt-03 replaces that with the content-bound validator and a genuine consistent fixture bundle, and maps missing cases to NOT_RUN, mocks to NOT_RUN, incomplete/contradictory executed evidence to FAIL, and missing credentials to a recorded BLOCKED preflight. A structural PASS remains provisional pending Codex semantic review.

## Protected baseline record

- Command: `verify_execution_framework.py --baseline W01-live-v4-baseline.json`
- Exit code: 0
- Recorded: 2026-10-29T15:07:29Z
- Result: PASS; protected hashes 142; links 233; errors []

## Environment (measured)

- Python 3.11.15 (CPython) in `.local/w01/venv/Scripts/python.exe`
- Platform: Windows-10-10.0.26300-SP0

| Package | Version |
|---|---|
| docling | 2.144.0 |
| httpx | 0.28.1 |
| pdfplumber | 0.11.10 |
| pillow | 13.0.0 |
| pydantic | 2.14.1 |
| pymupdf | 2.0 |
| pypdfium2 | 5.14.0 |

- Docker client: Docker version 29.8.1, build 4a63305; daemon: not reachable (exit 1)
- WSL: exit 4294967295 (Access is denied.)

## Source provenance

| Field | Value |
|---|---|
| source_key | st-es0620 |
| manufacturer | STMicroelectronics |
| document_id | ES0620 |
| revision | Rev 5 |
| publication_date | August 2026 |
| http_status | 200 |
| byte_size | 1674378 |
| page_count | 38 |
| sha256 | dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd |
| final_url | https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf |
| redistribution | unknown |

## Identity and context anchors (R3)

| Context | Anchor | Page | Text |
|---|---|---|---|
| source_identity | `st-es0620:p00:ctx-identity` | 0 | ES0620 - Rev 5 - August 2026 www.st.com |
| revision_header | `st-es0620:p01:ctx-rev-Z` | 1 | Rev. Z |
| revision_header | `st-es0620:p01:ctx-rev-B` | 1 | Rev. B |
| revision_header | `st-es0620:p01:ctx-rev-X` | 1 | Rev. X |
| status_legend | `st-es0620:p01:ctx-legend-A` | 1 | A Limitation applicable. Workaround available |
| status_legend | `st-es0620:p01:ctx-legend-N` | 1 | N Limitation applicable. No workaround available |
| status_legend | `st-es0620:p01:ctx-legend-P` | 1 | P Limitation applicable. Partial workaround available |
| status_legend | `st-es0620:p01:ctx-legend--` | 1 | - Limitation not applicable. |
| footnote | `st-es0620:p00:ctx-footnote-datasheet` | 0 | 1. Refer to the device datasheet for how to identify this code on different types of package. |
| footnote | `st-es0620:p00:ctx-footnote-rev-id` | 0 | 2. REV_ID[15:0] bitfield of DBGMCU_IDCODE register. |

The derived revision matrix below is not authority: each value is checked against the row anchor and the governing `Rev. Z / Rev. B / Rev. X` header anchors listed above, and the status letters require their legend anchors.

| Section | Status | Title | Pages | Revision matrix | Row anchor |
|---|---|---|---|---|---|
| 2.2.18 | anchored | Incorrect reset behavior when using NRST pin | [1, 9] | Rev. Z=A, Rev. B=A, Rev. X=- | `st-es0620:p01:row-2-2-18` |
| 2.2.5 | anchored | Incorrect DBGMCU_IDCODE register value | [1, 6] | Rev. Z=N, Rev. B=A, Rev. X=A | `st-es0620:p01:row-2-2-5` |

## Parsing and coverage

| Parser | Version | Mode |
|---|---|---|
| docling | 2.144.0 | bounded-page-items |
| pdfplumber | 0.11.10 | word-band-table-row |

- Anchors persisted: **78** (context anchors: 10)
- Coverage counts: `{"ambiguous_revision_rows": 0, "anchored_sections": 2, "anchors_total": 78, "context_anchors": 10, "inventory_entries": 53, "missing_sections": 0, "pages_parsed": [0, 1, 2, 3, 6, 9], "selected_sections": 2}`
- Page renders: `.local/w01/pages` (6 pages)
- Printed page labels remain separate from physical zero-based page indexes.

## Provider cases, ledger, and pricing (R1/R4)

- Validated pricing: model `nvidia/Nemotron-3.5-Super-VL`, input $0.3/1M, output $0.9/1M, verified 2026-10-29, source https://nebius.com/blog/posts/three-new-open-weight-models-from-us-companies-give-builders-more-choice, account_access_verified=False.
- Ledger: 4 attempt(s) reserved, $0.040466 reserved, live_requests_made=True.

| Attempt | Case | State | Outcome | HTTP | Model returned | Validation | Cost USD |
|---|---|---|---|---|---|---|---|
| 1 | real_source | finalized | empty | 200 | nvidia/Nemotron-3.5-Super-VL | rejected | 0.0100242 |
| 2 | real_source | finalized | schema_invalid | 200 | nvidia/Nemotron-3.5-Super-VL | rejected | 0.0100242 |
| 3 | real_source | finalized | success | 200 | nvidia/Nemotron-3.5-Super-VL | accepted | 0.010773 |
| 4 | synthetic_missing_revision | finalized | success | 200 | nvidia/Nemotron-3.5-Super-VL | accepted | 0.0096441 |

Blocked preflight events (history preserved, prior attempts untouched):

- 2026-10-29T10:25:22Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'real_source' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:25:23Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'synthetic_missing_revision' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:25:32Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'real_source' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:25:33Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'synthetic_missing_revision' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:25:53Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'real_source' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:25:54Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'synthetic_missing_revision' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:41:58Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'real_source' blocked; no request was made and no fixture output is reported as live.
- 2026-10-29T10:41:58Z: NEBIUS_API_KEY is not configured for this process. Live provider case 'synthetic_missing_revision' blocked; no request was made and no fixture output is reported as live.

**Live / mock distinction:** every ledger attempt records `execution_mode`. Mock executions are labelled and cannot satisfy G4 or the live part of G5.

## Local regression checks

- 51 passed, 0 failed, 0 skipped (51 total); generated 2026-10-29T15:07:28Z; network_used=False.
- Raw results: `.local/w01/results/selftest.json`

| Check | Status | Detail |
|---|---|---|
| anchors_fixture_valid | PASS | 2 anchors validated |
| valid_draft_accepted | PASS | accepted with 3 anchor references |
| malformed_json_rejected | PASS | invalid JSON at line 2 column 1: Expecting value |
| schema_violation_rejected | PASS | rejected: missing claims |
| nonexistent_anchor_rejected | PASS | rejected: nonexistent anchor |
| bbox_out_of_range_rejected | PASS | rejected: normalized bbox outside [0,1] |
| page_out_of_range_rejected | PASS | rejected: page_index outside page_count |
| missing_revision_unresolved | PASS | revision None and listed unresolved |
| invented_revision_rejected | PASS | rejected: revision not grounded |
| synthetic_fixtures_labeled | PASS | 3 files labeled; 3 manifest records synthetic=true |
| source_hash_mismatch_detected | PASS | mismatch detected after byte change |
| token_bound_documented | PASS | bound=78 tokens >= 4 utf8 bytes (utf8_bytes_plus_message_overhead_v1) |
| atomic_ledger_write | PASS | atomic replace, no temp residue, reload valid |
| timeouts_stop_at_request_cap | PASS | 5 simulated timeouts -> 4 dispatches, 4 uncertain reservations, 1 guard refusal |
| restart_reads_reservations | PASS | restart sees 4/4 reserved and refuses another attempt |
| malformed_response_consumes_attempt | PASS | malformed provider body finalized as invalid_json and consumed attempt 1 |
| history_survives_blocked_preflight | PASS | blocked preflight appended history without erasing the prior dispatch |
| invalid_pricing_rejected | PASS | rejected 6 invalid pricing configurations |
| pricing_evidence_accepted | PASS | accepted model=nvidia/Nemotron-3.5-Super-VL input=$0.3/1M output=$0.9/1M verified 2026-10-29 |
| gate_401_not_pass | PASS | HTTP 401 in actual response despite 200 ledger flag: evidence FAIL and report FAIL (response HTTP status is 401, not 200) |
| gate_500_not_pass | PASS | HTTP 500 in actual response: evidence FAIL and report FAIL (response HTTP status is 500, not 200) |
| gate_wrong_model_not_pass | PASS | wrong returned model despite optimistic ledger: evidence FAIL and report FAIL (returned model 'nvidia/other-model' is not the configured model) |
| gate_truncated_not_pass | PASS | finish_reason=tool_calls (no approved equivalence): evidence FAIL and report FAIL (finish_reason is 'tool_calls', not 'stop') |
| gate_empty_not_pass | PASS | empty completion content: evidence FAIL and report FAIL (completion content is missing or empty) |
| gate_malformed_json_not_pass | PASS | malformed response artifact JSON: evidence FAIL and report FAIL (response: malformed JSON: Expecting property name enclosed in double quotes at 2) |
| gate_invalid_draft_not_pass | PASS | draft missing required schema fields: evidence FAIL and report FAIL (recomputed validation rejected the response draft: ['schema: claims: Field required']) |
| gate_empty_artifact_not_pass | PASS | empty {} request artifact: evidence FAIL and report FAIL (request: artifact file is empty) |
| gate_directory_artifact_not_pass | PASS | artifact path is a directory: evidence FAIL and report FAIL (request: artifact path is not a regular file) |
| gate_wrong_case_not_pass | PASS | request artifact bound to a different case: evidence FAIL and report FAIL (request: artifact case 'synthetic_missing_revision' does not match expected 'real_source') |
| gate_wrong_attempt_not_pass | PASS | response artifact bound to a different attempt: evidence FAIL and report FAIL (response: artifact attempt 99 does not match record attempt 1) |
| gate_replaced_artifact_not_pass | PASS | artifact replaced after its hash was recorded: evidence FAIL and report FAIL (response: artifact content was replaced or corrupted after recording) |
| gate_draft_disagreement_not_pass | PASS | saved draft disagrees with response content: evidence FAIL and report FAIL (saved draft disagrees with the response content) |
| gate_synthetic_bundle_passes | PASS | synthetic omission bundle passes only with its own recomputed expectation |
| gate_synthetic_expectation_required | PASS | synthetic bundle without a passing omission expectation: evidence FAIL and report FAIL (stored omission expectation is not pass) |
| gate_mock_not_live | PASS | mock execution record -> evidence MOCK_ONLY, report NOT_RUN |
| gate_missing_artifacts_not_pass | PASS | response artifact missing: evidence FAIL and report FAIL (response: artifact file missing) |
| gate_well_formed_record_passes | PASS | consistent hash-bound bundle passes evidence and report structurally |
| cli_report_gate_consistency | PASS | CLI/report statuses agree for 3 bundles |
| legacy_summary_flags_not_evidence | PASS | legacy summary-flag path fails closed; non-stop finish rejected |
| gate_no_negative_case_partial | PASS | local pass + no omission case -> G5 PARTIAL |
| gate_failing_local_check_not_pass | PASS | failing local check -> G5 FAIL |
| baseline_missing_record_not_pass | PASS | missing baseline record -> G1 NOT_RUN |
| identity_correct_accepted | PASS | identity ES0620 Rev 5 accepted with cited identity anchor |
| identity_unrelated_document_rejected | PASS | unrelated document ID rejected |
| identity_wrong_revision_rejected | PASS | wrong document revision rejected |
| identity_missing_revision_unresolved | PASS | missing identity/revision stays null and unresolved |
| identity_silicon_revision_not_from_document | PASS | silicon revision cannot be sourced from the document identity anchor |
| context_anchors_present | PASS | identity + 3 headers + 4 legend entries + 2 footnotes, located geometry |
| mock_response_execution_recorded | PASS | valid mock validated, evidence MOCK_ONLY, report NOT_RUN, execution_mode=mock recorded |
| missing_usage_unknown_not_zero | PASS | usage reported unavailable |
| no_secret_values_in_public_evidence | PASS | scanned 55 text artifacts; no secret value present |

## Commands actually run

### This attempt (W01-attempt-06)

| Command | Exit code | Finished (UTC) |
|---|---|---|
| `verify-baseline` | 0 | 2026-10-29T15:06:17Z |
| `inspect-env` | 0 | 2026-10-29T15:06:19Z |
| `self-test` | 0 | 2026-10-29T15:06:23Z |
| `probe-provider` | 0 | 2026-10-29T15:06:44Z |
| `probe-provider` | 0 | 2026-10-29T15:07:07Z |
| `self-test` | 0 | 2026-10-29T15:07:28Z |
| `verify-baseline` | 0 | 2026-10-29T15:07:29Z |

### Historical records preserved (84 attempt-01 command records)

Attempt-01 command history remains in `.local/w01/results/command_log.json` and its evidence snapshot in `.local/reviews/W01-review-01/`; it is not counted as this attempt's evidence.

## Hosting feasibility (read-only)

- No container, registry, cluster, or cloud resource was created; Docker/WSL status is in `docs/evidence/W01/ENVIRONMENT.json`.
- Proposed route for Codex to freeze: Python 3.11 Linux container with pinned wheels, Docling models baked at image build, provider keys injected as runtime secrets. Account/region verification remains a Codex/human decision.

## Unresolved decisions for Codex

1. Live provider evidence: `NEBIUS_API_KEY` is required in the worker process. Published pricing is now recorded in the protected pricing evidence; account/model access is still unverified until a real call, and HTTP 401 alone proves neither the model nor full endpoint behavior.
2. Whether selected-section evidence (2.2.18, 2.2.5) is sufficient for P0's parser/source exit gate.
3. Anchor identity for W02: document hash + parser version + extraction configuration; anchor IDs are page-scoped ordinals and are not stable across parser upgrades.
4. Redistribution rights for ES0620 remain unknown; the public bundle keeps metadata and short quotations only.

## Reproduction

```powershell
.local/w01/venv/Scripts/python.exe spikes/w01/run.py verify-baseline
.local/w01/venv/Scripts/python.exe spikes/w01/run.py inspect-env
.local/w01/venv/Scripts/python.exe spikes/w01/run.py fetch-source
.local/w01/venv/Scripts/python.exe spikes/w01/run.py parse-source
.local/w01/venv/Scripts/python.exe spikes/w01/run.py self-test
.local/w01/venv/Scripts/python.exe spikes/w01/run.py probe-provider --case real-source
.local/w01/venv/Scripts/python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
.local/w01/venv/Scripts/python.exe spikes/w01/run.py report
```

`probe-provider` requires `NEBIUS_API_KEY` and validated pricing evidence; without them it records a blocked preflight and exits 2 without dispatching.


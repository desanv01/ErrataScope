# Worker handoff — W01 repair 02, attempt 03

Status: **PARTIAL**
Packet revision: W01-feasibility revision 1 + focused repair 02 (W01-R02)
Started/finished (UTC): 2026-10-29T10:38:17Z / 2026-10-29T10:43:37Z (last report); final baseline recheck timestamped below
Starting baseline and verification result: **PASS** before any write — `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-02-baseline.json` exit 0, **62 protected hashes, 170 links, 0 errors**. Recorded for this attempt in `.local/w01/results/baseline_check.json`.
Worker/harness: DeepSeek harness (`deepseek-flash`), single implementation worker in the DSH Web GUI. No subagents.
Worker stopped editing: yes
Coordination lock released: yes — `.local/coordination/ACTIVE_WORKER.json` removed after this file was written.
Owned processes stopped / remaining process IDs: **none**. No server, container, background process, or paid request was started.

## The required repair: one evidence-validation path (R2)

**Before (attempt 02, confirmed by review 02).** `report.derive_case_gate` trusted ledger summary flags and only checked that artifact paths existed. Consequences reproduced by Codex: three `{}` files → G4 PASS; a response artifact saying attempt 99 / synthetic / HTTP 401 while the summary claimed attempt 1 / real / HTTP 200 → G4 PASS; a synthetic ledger record submitted as real-source G4 → PASS; `provider.passes_live_gate` accepted `finish_reason=tool_calls`. The worker's own positive test literally wrote `{}` files and expected PASS.

**After (attempt 03).** New `spikes/w01/erratascope_w01/evidence.py` is the single validator, and both `run.py probe-provider` and `report.compute_gates` call `evidence.evaluate_case`. It requires:

1. **Case and attempt binding.** The expected gate case must equal the ledger record case; the attempt must be the finalized attempt reserved in the intended ledger. Mock executions return `MOCK_ONLY`; reserved/dispatched/uncertain or non-success records FAIL.
2. **Actual artifact contents.** The request, response, and validation JSON files are opened and parsed. Missing files, directories, empty `{}` objects, malformed JSON, unsupported shapes, absolute paths, `..` traversal, and paths outside `.local/w01/results/provider/**` are rejected.
3. **Artifact identity and replacement detection.** Each artifact is now a wrapper carrying `schema_version=2`, `artifact_kind`, `case`, `attempt`, `model_requested`, endpoint, and prompt version. Its SHA-256 is recorded in the ledger at creation (`request_sha256`/`response_sha256`/`validation_sha256`); a later replacement, truncation, or corruption fails even if ledger flags stay optimistic.
4. **Completion and model binding.** Response HTTP status must be 200, the returned model must be the configured model, content must be nonempty, and `finish_reason` must be exactly `stop` — enforced identically in execution (any other reason finalizes as `truncated`), CLI, and report. No finish-reason equivalence is approved.
5. **Content-derived validation.** The saved draft must equal the response content, and schema/citation/identity validation is **recomputed** against the pinned document hash, anchor fingerprint, identity, and prompt version recorded in the validation artifact and ledger. A stored `accepted` flag cannot overrule a contradictory response; stored validation status/errors must match the recomputation.
6. **Synthetic expectation independent.** For `synthetic_missing_revision`, the omission expectation is recomputed from the response draft and must pass; the stored and ledger expectation flags must also be `pass`. A real-source result cannot substitute.
7. **Truthful states.** Missing/unrun case → NOT_RUN; incomplete or contradictory executed evidence → FAIL; missing credentials → recorded BLOCKED preflight; structural PASS stays provisional for Codex semantic review.

A `passes_live_gate(record)` compatibility shim remains only so older diagnostics fail closed: it always returns False because summary flags are not evidence. `report.derive_case_gate` called without pinned case inputs also fails closed.

## Changed files

Created:

- `spikes/w01/erratascope_w01/evidence.py` — shared artifact-content validator, artifact hashing, pinned-input recomputation.

Modified:

- `spikes/w01/erratascope_w01/ledger.py` — artifact SHA-256 fields and `record_artifact_hash()`.
- `spikes/w01/erratascope_w01/provider.py` — metadata artifact wrappers, creation-time hashes, strict `finish_reason=stop` in execution, fail-closed compatibility shim.
- `spikes/w01/erratascope_w01/report.py` — G4/live-G5 now call `evidence.evaluate_case`; pinned case inputs built per case; G5 FAILs on contradictory executed evidence; new "R2 evidence binding (repair 02)" report section.
- `spikes/w01/run.py` — CLI gate uses the same validator; passes the ledger and case inputs; attempt-03 metadata.
- `spikes/w01/erratascope_w01/selftest.py` — `{}`-artifact positive test replaced by a genuine consistent hash-bound fixture; 10 new evidence regressions (51 checks total).
- `spikes/w01/erratascope_w01/config.py` — attempt 03 metadata; repair-02 baseline path.
- `spikes/w01/README.md` — evidence-gate semantics, artifact hashing, updated limits.
- `docs/evidence/W01/FEASIBILITY_REPORT.md`, `docs/evidence/W01/ENVIRONMENT.json` — regenerated for this attempt.
- `.local/w01/results/` — `baseline_check.json`, `selftest.json`, `report_summary.json`, `command_log.json`, provider ledger blocked-event history; request/response/validation wrappers apply to future attempts.

Reused, not recomputed: downloaded source bytes (SHA-256 unchanged), Docling/pdfplumber anchors (78, 10 context), coverage, revision matrix, page renders. No download or full conversion was repeated.

Preserved, not modified: `docs/execution/handoffs/W01-attempt-01.md`, `W01-attempt-02.md`, `docs/execution/reviews/**` (both checkers and pricing evidence), `.local/reviews/**`, plans/contracts/status/baselines. No Git command was run.

## Checks actually run

Working directory for every row: `C:\Users\Dv\Desktop\ErrataScope`.

| Command | Exit code | Result/log path | Interpretation |
|---|---|---|---|
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test` (first run) | 1 | `.local/w01/results/selftest.json` | 2 failing fixture-side checks: a stale `live_gate` assertion and a replacement test that rewrote identical bytes; both fixed in the tests |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test` (intermediate) | 1 | same | same two checks during edit cycle |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test` (final) | 0 | `.local/w01/results/selftest.json` | **51 checks: 50 PASS, 0 FAIL, 1 SKIP** (secret scan skipped, no key) |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline` | 0 | `.local/w01/results/baseline_check.json` | repair-02 baseline PASS: 62 hashes, 170 links |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env` | 0 | `docs/evidence/W01/ENVIRONMENT.json` | refreshed for this attempt |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source` | 2 | provider ledger | BLOCKED preflight (no `NEBIUS_API_KEY`); zero dispatches |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision` | 2 | provider ledger | BLOCKED preflight; zero dispatches |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py report` | 0 | `docs/evidence/W01/FEASIBILITY_REPORT.md` | Gates: G1 PASS, G2 PASS, G3 PASS, G4 NOT_RUN, G5 PARTIAL, G6 PASS, G7 PASS |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-02-baseline.json` (final) | 0 | stdout + `.local/w01/results/baseline_check.json` | 62 hashes, 170 links, 0 errors after execution |

Every run is timestamped and attempt-tagged in `.local/w01/results/command_log.json` (14 records for this attempt; earlier attempt records preserved).

## Required regressions (review 02 defects)

| Required regression | Test (all PASS) |
|---|---|
| Empty `{}` artifacts rejected | `gate_empty_artifact_not_pass` |
| Malformed JSON rejected | `gate_malformed_json_not_pass` |
| Directory artifact rejected | `gate_directory_artifact_not_pass` |
| Missing artifact rejected | `gate_missing_artifacts_not_pass` |
| Wrong case in ledger/artifact rejected | `gate_wrong_case_not_pass` + `legacy_summary_flags_not_evidence` |
| Wrong attempt in artifact rejected | `gate_wrong_attempt_not_pass` |
| HTTP 401 / 500 in actual response rejected despite optimistic ledger | `gate_401_not_pass`, `gate_500_not_pass` |
| Wrong returned model rejected despite optimistic ledger | `gate_wrong_model_not_pass` |
| Response/draft/validation disagreement rejected | `gate_draft_disagreement_not_pass` |
| Post-recording artifact replacement rejected | `gate_replaced_artifact_not_pass` (hash mismatch) |
| Missing/empty/truncated/non-stop completion rejected by CLI **and** report | `gate_empty_not_pass`, `gate_truncated_not_pass` (length and `tool_calls`), each asserting both `evidence.evaluate_case` FAIL and `derive_case_gate` FAIL |
| Valid complete real-source-shaped bundle passes structural checks | `gate_well_formed_record_passes` (genuine consistent bundle: request/response/validation wrappers, hashes, pinned inputs) |
| Explicit mock transport stays mock and cannot pass | `mock_response_execution_recorded`, `gate_mock_not_live` |
| Valid synthetic bundle requires its own passing omission expectation | `gate_synthetic_bundle_passes`, `gate_synthetic_expectation_required` |
| CLI and report agree | `cli_report_gate_consistency` (PASS/401/replaced bundles) |
| Existing R1 timeout/restart and R3 identity coverage | `four_timeouts_stop_at_three`, `restart_reads_reservations`, `malformed_response_consumes_attempt`, `history_survives_blocked_preflight`, `identity_*`, `context_anchors_present` — all still PASS |

The Codex `W01-review-02-checks.py` was **not run** because it writes into protected `.local/reviews/W01-review-02/`. Its four reproduced defects map as follows: `empty_artifacts_gate` → FAIL; `contradictory_artifacts_gate` → FAIL; `wrong_case_record_gate` → FAIL; `cli_accepts_nonstop_finish` → false (strict execution plus fail-closed shim). Equivalent evidence is in `selftest.json` (tests above).

## Required gates

| Gate ID | Status | Supporting artifact | Limits |
|---|---|---|---|
| W01-G1 | **PASS** | `baseline_check.json` (exit 0, 62 hashes, 170 links, current attempt) | Final recheck identical |
| W01-G2 | **PASS** | sealed source + `anchors.json` + `coverage.json` | Selected-entry coverage only; inventory incomplete |
| W01-G3 | **PASS** | 78 anchors (10 context) + 6 page renders | Inspected overlays; not general parser accuracy |
| W01-G4 | **NOT_RUN (BLOCKED)** | provider ledger: 0 attempts, blocked event for `real_source` | `NEBIUS_API_KEY` absent; no live response exists |
| W01-G5 | **PARTIAL** | `selftest.json` 50/0/1 + blocked synthetic preflight | Local evidence checks pass; live omission case not executed |
| W01-G6 | **PASS (synthetic fallback)** | 3 labeled fixtures + manifest records | No authentic manufacturer pair |
| W01-G7 | **PASS** | report + current environment/baseline/self-test records | Account/model availability unverified |

## Live / mock status

- **Zero provider attempts, zero spend, zero live responses.** The ledger has `requests_reserved=0`, `spend_reserved_usd=0.0`; two attempt-03 blocked-preflight events were appended for `real_source` and `synthetic_missing_revision`; earlier blocked events are preserved.
- Mocks exist only inside the offline self-test; they are recorded with `execution_mode="mock"` and the evidence gate returns `MOCK_ONLY` → NOT_RUN.
- Missing usage is recorded as unavailable, never zero.

## Remaining input names

- `NEBIUS_API_KEY` — absent from the worker process (also absent at user/machine scope; names checked only). Required before G4 and live G5 can be attempted.
- Authenticated account/model availability is still unverified; the protected pricing evidence is unchanged and proves published rates only.

## Reproduction

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-02-baseline.json
```

## Protected baseline recheck

**PASS** after execution: exit 0, `protected_hashes_checked: 62`, `local_links_checked: 170`, `errors: []`. No protected file was modified; every change lies inside `spikes/w01/**`, `fixtures/manifests/w01/**`, `docs/evidence/W01/**`, `docs/execution/handoffs/W01-attempt-03.md`, or `.local/w01/**`. No acceptance claim is made.

## Return prompt

> Review ErrataScope W01 repair 02, worker attempt 03. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-03.md and docs/execution/reviews/W01-repair-02.md. Verify the repair-02 protected baseline and independently test artifact-content/case binding and consistent CLI/report gates. Require actual live evidence for G4 and live G5. Record acceptance or remaining blockers; W02 stays unbound until all W01 gates pass. Preserve the UI/imagegen approval gate.

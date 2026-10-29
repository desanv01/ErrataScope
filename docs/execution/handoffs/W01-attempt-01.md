# Worker handoff — W01-feasibility attempt 01

Status: **PARTIAL**
Packet revision: 1
Started/finished (UTC): 2026-10-29T06:42:39Z / 2026-10-29T07:00:52Z (last verified run)
Starting baseline and verification result: **PASS** before any write — 49 protected hashes, 146 local links, 0 errors, exit 0 (`python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json`). Recheck after execution: **PASS**, identical counts, exit 0.
Worker/harness: DeepSeek harness (`deepseek-flash`), single implementation worker in the DSH Web GUI. No subagents, no delegated workers.
Worker stopped editing: yes
Coordination lock released: yes — `.local/coordination/ACTIVE_WORKER.json` was created exclusively at start and removed after this file was written.
Owned processes stopped / remaining process IDs: **none**. No server, container, or long-running process was started. All background jobs used during setup finished before the handoff.

## Implemented behavior

A narrow, runnable spike under `spikes/w01/` proves the source → parser → anchor → draft-validation path and leaves the live model call explicitly blocked rather than mocked.

- **Isolated environment.** `.local/w01/venv` created with `uv 0.11.25` (`uv venv --seed --python 3.11`), CPython 3.11.15, `pip 26.2.2`. Direct pins in `spikes/w01/requirements.txt`; full 115-package freeze in `spikes/w01/requirements.lock`. Docling 2.144.0 installed and executed successfully.
- **Real source fetched.** `GET` on the contract ST URL returned `200 application/pdf`, 1,674,378 bytes, SHA-256 `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`, 38 pages. The document itself identifies `ES0620 - Rev 5 - August 2026`; that identity is parsed from page 1, not assumed from planning notes. Bytes are private at `.local/w01/sources/st-es0620.pdf`. NXP `https://www.nxp.com/pcn/202609010I` returned **HTTP 404**, so no notice metadata or linked historical/current errata candidates could be identified.
- **Anchored parsing.** Docling is the primary prose parser on bounded pages (1-based 2, 3, 4, 7, 10); pdfplumber is the recorded fallback for the text-layer heading inventory and for summary-table cell coordinates. 68 anchors persisted with document hash, zero-based page index, printed page label, section, text, normalized bbox `[left, top, right, bottom]` in `[0,1]` on a top-left/y-down convention, original parser coordinates, page size/rotation, and per-anchor parser provenance.
- **Selected coverage, explicit.** Candidate labels 2.2.18 and 2.2.5 were **located by document contents**, not page offsets: 2.2.18 is physical page 9 (printed 10) and 2.2.5 is physical page 6 (printed 7). Both are anchored; coverage counts: 2 selected, 2 anchored, 0 missing, 0 ambiguous. The 53-entry heading inventory is declared incomplete (text-layer only) and the full document was not interpreted.
- **Revision matrix.** Summary-table rows were resolved by aligning status letters to the `Rev. Z / Rev. B / Rev. X` header centers: **2.2.18 → Z=A, B=A, X=-**; **2.2.5 → Z=N, B=A, X=A**. Rows that fail the alignment are rejected rather than guessed.
- **Page renders inspected.** Five pages rendered plain and with anchor rectangles under `.local/w01/pages/`. The 2.2.18 rectangles were visually checked against the rendered page and cover the description, workaround steps, and both code blocks without covering text that was not located.
- **Provider adapter implemented, live gate blocked.** Text-only OpenAI-compatible `chat/completions` call to the documented base URL, `max_retries`-free transport, 16k estimated-input-token guard, 8,192 output cap, 3-request ledger, and US$0.25 aggregate spend guard. `probe-provider` exits **2** with a configured-variable message because `NEBIUS_API_KEY` is absent; it records the blocked gate and makes **no** request.
- **Draft validation.** Pydantic schema v1 plus anchor-existence, document-hash binding, revision grounding, placeholder, and safety-verdict checks. A schema-valid draft is explicitly not a semantic acceptance.
- **Self-test.** 18 local checks, no network and no credentials: 17 passed, 0 failed, 1 skipped (secret-value scan skipped because no key is configured).

## Changed files

Created (all inside the packet's allowed paths):

- `spikes/w01/run.py`
- `spikes/w01/erratascope_w01/` — `__init__.py`, `config.py`, `util.py`, `schemas.py`, `envprobe.py`, `fetch.py`, `extract_pdfplumber.py`, `extract_docling.py`, `anchors.py`, `validate.py`, `provider.py`, `selftest.py`, `report.py`
- `spikes/w01/prompts/` — `draft_v1_system.md`, `draft_v1_user.md`, `draft_v1_schema.md`
- `spikes/w01/fixtures/` — `anchors_fixture.json`, `anchors_invalid_bbox.json`, `anchors_page_out_of_range.json`, `draft_valid.json`, `draft_missing_revision.json`, `draft_invented_revision.json`, `draft_nonexistent_anchor.json`, `draft_schema_invalid.json`, `draft_malformed.json`, `synthetic/SYNTHETIC_old.md`, `synthetic/SYNTHETIC_new.md`, `synthetic/SYNTHETIC_missing_revision.md`
- `spikes/w01/README.md`, `spikes/w01/requirements.txt`, `spikes/w01/requirements.lock`
- `fixtures/manifests/w01/sources.json`
- `docs/evidence/W01/FEASIBILITY_REPORT.md`, `docs/evidence/W01/ENVIRONMENT.json`
- `docs/execution/handoffs/W01-attempt-01.md` (this file)
- Private artifacts under `.local/w01/` — `venv/`, `sources/`, `pages/`, `results/` (anchors, coverage, revision matrix, inventory, renders, self-test, command log, provider budget), `hf/` (Docling model cache), `tmp/`, `scratch/`, `uv-cache/`
- `.local/coordination/ACTIVE_WORKER.json` (created, then removed)

Modified: **none** outside the above. No protected file, plan, contract, status, baseline, or existing asset was edited. Generated `__pycache__` directories were removed before handoff. No Git repository exists and no Git command was run.

## Checks actually run

Working directory for every row: `C:\Users\Dv\Desktop\ErrataScope`.

| Command | Exit code | Result/log path | Interpretation |
|---|---|---|---|
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json` | 0 | stdout (`PASS`, 49 hashes, 146 links) | Protected baseline intact before any write |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env` | 0 | `docs/evidence/W01/ENVIRONMENT.json` | Python 3.11.15; docling 2.144.0, pdfplumber 0.11.10, pydantic 2.14.1, httpx 0.28.1, pymupdf 2.0; Docker client 29.8.1 (daemon not reachable); WSL access denied |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py fetch-source` | 0 | `fixtures/manifests/w01/sources.json`, `.local/w01/results/fetch.json` | ST 200/1,674,378 B/38 pages/Rev 5; NXP 404; community thread 200 (not parsed); 3 synthetic fixtures registered |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py parse-source` | 0 | `.local/w01/results/{anchors,coverage,revision_matrix,inventory,renders}.json`; `.local/w01/pages/*.png` | 68 anchors; 2/2 selected sections anchored; both revision rows resolved |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test` | 0 | `.local/w01/results/selftest.json` | 18 checks: 17 PASS, 0 FAIL, 1 SKIP |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider` | 2 | `.local/w01/results/provider/budget.json` | Blocked: `NEBIUS_API_KEY` not configured; zero requests made |
| `.local\w01\venv\Scripts\python.exe spikes/w01/run.py report` | 0 | `docs/evidence/W01/FEASIBILITY_REPORT.md` | Gate table G1–G7 written from artifacts |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json` (final) | 0 | stdout (`PASS`, 49 hashes, 146 links) | Baseline unchanged after execution |

Supporting setup runs, all exit 0: `uv venv --seed`; `uv pip install pydantic httpx pdfplumber pymupdf`; `uv pip install docling`; `python -m pip freeze` (lockfile). Two intermediate `parse-source` runs also exited 0: one after narrowing the summary-page detector (it had matched the table-of-contents page), one after recording measured inventory counts in the manifest. `probe-provider` was run only in its no-key state. Every run is timestamped in `.local/w01/results/command_log.json`.

## Required gates

| Gate ID | PASS / FAIL / NOT_RUN | Supporting artifact | Limits |
|---|---|---|---|
| W01-G1 | PASS | Baseline verifier output (initial + final); `spikes/w01/requirements.lock`; file list above | Final recheck is this table's last row; no protected edits |
| W01-G2 | PASS | `fixtures/manifests/w01/sources.json`; `.local/w01/results/inventory.json` | Selected-entry coverage only (2.2.18, 2.2.5); inventory text-layer, incomplete |
| W01-G3 | PASS | `.local/w01/results/anchors.json`; `.local/w01/pages/page-09-anchors.png`; `revision_matrix.json` | Condition and governing revision row anchored; coordinates visually checked, not OCR-verified |
| W01-G4 | **NOT_RUN** | `.local/w01/results/provider/budget.json` (blocked) | `NEBIUS_API_KEY` absent; no request; no usage, latency, request ID, or spend exists |
| W01-G5 | **PARTIAL** | `.local/w01/results/selftest.json` (17 pass / 0 fail / 1 skip) | Local invalid-input and missing-revision checks pass; the live synthetic-omission request was not run |
| W01-G6 | PASS (synthetic fallback) | `spikes/w01/fixtures/synthetic/SYNTHETIC_{old,new,missing_revision}.md`; manifest records `synthetic: true` | No authentic manufacturer pair; NXP 404; fixture proves availability only, not the change engine |
| W01-G7 | PASS | `docs/evidence/W01/FEASIBILITY_REPORT.md`; `docs/evidence/W01/ENVIRONMENT.json` | Provider pricing/model availability and hosted account remain unverified by design |

## Source/model evidence

- **Source.** STMicroelectronics **ES0620 Rev 5, August 2026**, 38 pages, `application/pdf`, final URL `https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf` (no credentials in URL), retrieval 2026-10-29T06:53:54Z, SHA-256 `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`, 1,674,378 bytes. Redistribution status **unknown**, with the contract reference recorded; no full PDF is in the public bundle.
- **NXP.** `https://www.nxp.com/pcn/202609010I` returned **HTTP 404** in the recorded run (an earlier attempt failed at the transport layer). No notice metadata, no linked old/new documents, no invented revision.
- **Community thread.** Contract URL returned HTTP 200 and was stored privately as an HTML reference; it was **not** used as technical authority and **not** parsed.
- **Parser provenance.** Docling 2.144.0 (`bounded-page-items`, bottom-left → top-left conversion recorded per anchor) and pdfplumber 0.11.10 (`word-band-table-row`). Docling's table-structure model reported that 1 of 1,462 summary-table cells matched neither a row nor a column band and was dropped from *its* table; the revision matrix was therefore produced from pdfplumber word bands and cross-checked on the render. This limitation is recorded in the report.
- **Model.** No live call. `nvidia/Nemotron-3.5-Super-VL` over `https://api.tokenfactory.nebius.com/v1/` is **unverified**; `GET /v1/models` returned HTTP 401, proving the endpoint exists but not account/model binding. Public quickstart and JSON pages returned 200 but exposed neither a model catalog nor pricing.
- **Mock/cache distinction.** Only the self-test uses `httpx.MockTransport`; its response is labeled `live: false` and `passes_live_gate()` returns False for it. No cached or mock output is presented as a live result anywhere. Missing usage is recorded as unavailable, never zero.
- **Synthetic labeling.** Every synthetic object carries a `SYNTHETIC FIXTURE — NOT A MANUFACTURER DOCUMENT` banner and a fictional device name; manifest records are `kind: synthetic_fixture`, `synthetic: true`.

## Deviations and blockers

1. **`NEBIUS_API_KEY` is not configured** (process, user, and machine scopes checked by name only; no value was read or printed). This is the blocking input for W01-G4 and the live half of W01-G5. No fixture was substituted.
2. **Verified pricing is unavailable** from the accessible public documentation. The spend cap therefore cannot be bounded, so the adapter refuses to make a paid request even if a key were present. A key plus verified per-1M-token input/output pricing (with source URL) is required before the probe can run.
3. **NXP notice unavailable** (HTTP 404), so no authentic older/newer pair exists in this bundle; the packet's synthetic fallback is used and labeled.
4. **Hosting evidence is read-only and partial.** Docker client 29.8.1 is present but the daemon is not reachable; WSL reports "Access is denied". No container or cloud resource was created. A container route is proposed in the report for Codex to freeze.
5. **Sandbox environment quirks** (recorded in `ENVIRONMENT.json` and README): the platform temp root is unwritable, and directories created with POSIX mode `0700` cannot be reopened, so `python -m venv` fails at `ensurepip` (used `uv venv --seed` instead) and Docling runs with `HF_HUB_DISABLE_XET=1`.
6. **Anchor identity caveat.** Anchor IDs are page-scoped ordinals and can shift if the parser is upgraded; the document hash plus parser version is the durable identity. Flagged for the W02 schema decision.
7. **Not attempted, by scope:** no UI, API, database, queue, deployment, evaluator, or W02 work was started; no Git mutation, no infrastructure, no account changes.

## Reproduction

Working directory: `C:\Users\Dv\Desktop\ErrataScope`.

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe spikes/w01/run.py fetch-source
.local\w01\venv\Scripts\python.exe spikes/w01/run.py parse-source
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider   # exits 2 without key/pricing
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json
```

Required variable names only: `NEBIUS_API_KEY` (live probe only); `HF_HOME`, `HF_HUB_DISABLE_XET`, `TEMP`, `TMP` are set by `run.py` for the Docling runtime. Environment creation: `uv venv --seed --python 3.11 .local/w01/venv` then `uv pip install --python .local/w01/venv/Scripts/python.exe -r spikes/w01/requirements.txt`.

## Protected baseline recheck

**PASS** after all execution: `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json` → exit 0, `protected_hashes_checked: 49`, `local_links_checked: 146`, `errors: []`. No protected file was modified; every created path is listed above and lies inside `spikes/w01/**`, `fixtures/manifests/w01/**`, `docs/evidence/W01/**`, `docs/execution/handoffs/W01-attempt-01.md`, or `.local/w01/**`. No acceptance claim is made here; Codex decides.

## Return prompt

> Review ErrataScope packet W01 revision 1. The DeepSeek worker has stopped editing. Read docs/execution/handoffs/W01-attempt-01.md and inspect the actual spike, source manifest, and local artifacts against docs/execution/packets/W01-feasibility.md and its protected baseline. Run focused independent checks; do not infer a live-provider pass from mocks or a handoff claim. Record acceptance, partial findings, or one consolidated repair assignment. If all required gates pass, freeze the observed contracts and prepare W02 with its accepted baseline. Do not start an unbound future packet.

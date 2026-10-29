# W01 feasibility spike â€” real source, parser, and Nebius path (repair 01)

Configuration update: the CLI explicitly reads project-root `.env.local` for NEBIUS_API_KEY (process environment takes precedence). Run `python spikes/w01/run.py check-key` for presence only, no network. See [local setup](../../docs/LOCAL_CREDENTIALS.md). Attempt 04 reached the live model but exhausted output on reasoning. Attempt 05 returned JSON with reasoning off but failed citations and semantic review. The v4 prompt correction and user-approved four-request lifetime cap are activated; both prior attempts remain counted and the $0.25 spending cap is unchanged. Follow [STATUS](../../docs/execution/STATUS.md). Older commands/status below are historical.

Narrow, reproducible spike for packet **W01-feasibility revision 1** plus **repair 01**. It proves that
one real manufacturer erratum can be retrieved, parsed into inspectable anchored evidence, and (when
credentials are supplied) sent to the intended NVIDIA model on Nebius with reservation-first budget
control. It also provides the synthetic missing-information case required by the repair.

This is **not** the application: no API, UI, database, queue, deployment, or evaluator is scaffolded
here. Outputs are drafts for Codex review.

## What exists

| Path | Purpose |
|---|---|
| `run.py` | CLI with the packet's six subcommands plus `verify-baseline` |
| `erratascope_w01/ledger.py` | Crash-safe reservation ledger, pricing validation, token bound (R1) |
| `erratascope_w01/evidence.py` | Shared artifact-content evidence validator used by CLI and report (R2) |
| `erratascope_w01/provider.py` | Reservation-first dispatch, hash-recorded artifacts, case execution (R1/R2/R4) |
| `erratascope_w01/cases.py` | `real_source` and `synthetic_missing_revision` case builders; omission expectation (R3/R4) |
| `erratascope_w01/context.py` | Citable identity / revision-header / legend / footnote anchors (R3) |
| `erratascope_w01/report.py` | Evidence-derived gate computation (R2) |
| `erratascope_w01/validate.py` | Schema, anchor, identity, and silicon-vs-document revision checks |
| `prompts/` | `draft-v2` prompts; `draft-v1` is retained as superseded attempt-01 material |
| `fixtures/` | Self-test fixtures and the **SYNTHETIC** old/new/missing-revision pair |
| `requirements.txt` / `requirements.lock` | Direct dependencies and the tested environment |

Generated artifacts:

- `.local/w01/sources/` â€” downloaded originals (private; never public evidence)
- `.local/w01/pages/` â€” page renders, plain and with anchor rectangles
- `.local/w01/results/` â€” anchors, coverage, revision matrix, inventory, self-test, baseline record, command log
- `.local/w01/results/provider/ledger.json` â€” reservations, outcomes, blocked-history events
- `.local/w01/results/provider/cases/<case>/` â€” request/response/validation artifacts per attempt
- `fixtures/manifests/w01/sources.json` â€” public-safe source and synthetic provenance
- `docs/evidence/W01/` â€” `ENVIRONMENT.json` and `FEASIBILITY_REPORT.md`

## Environment setup (measured, Windows)

```powershell
# from the project root
python -m venv .local/w01/venv      # fails here: ensurepip needs the blocked platform temp dir
uv venv --seed --python 3.11 .local/w01/venv
uv pip install --python .local/w01/venv/Scripts/python.exe -r spikes/w01/requirements.txt
```

The `.local/w01/venv` used here was created with `uv 0.11.25`, CPython 3.11.15, `pip 26.2.2`.
Exact versions are in `requirements.lock`.

Environment quirks found on this machine (also in `docs/evidence/W01/ENVIRONMENT.json`):

1. The platform temp root is not writable from the sandbox, so `python -m venv` fails at
   `ensurepip`. Point `TEMP`/`TMP` at a project directory or use `uv venv --seed`.
2. Directories created with POSIX mode `0700` (the `tempfile.mkdtemp` default) cannot be reopened
   under this sandbox. `run.py` sets `HF_HUB_DISABLE_XET=1`; do not remove it.
3. `run.py` sets `HF_HOME` under `.local/w01/hf` so Docling models stay inside the project.

## Subcommands

| Command | Network | Credentials | Meaning |
|---|---|---|---|
| `verify-baseline` | no | no | Runs the protected verifier and writes `.local/w01/results/baseline_check.json` |
| `inspect-env` | no | no | Writes `docs/evidence/W01/ENVIRONMENT.json`; variable **names** only |
| `fetch-source` | yes | no | Retrieves approved sources, hashes bytes, writes the public manifest |
| `parse-source` | no (after fetch) | no | Docling prose anchors + pdfplumber table/context anchors, coverage, renders |
| `probe-provider --case real-source` | yes | `NEBIUS_API_KEY` | Real-source interpretation case |
| `probe-provider --case synthetic-missing-revision` | yes | `NEBIUS_API_KEY` | Omission case; draft must leave identity/revision unresolved |
| `self-test` | no | no | 40 offline regression checks |
| `report` | no | no | Computes gates from this attempt's records; writes the report |

`probe-provider` also accepts `--pricing-file PATH` (default: the protected Codex pricing evidence at
`docs/execution/reviews/W01-pricing-evidence.json`). One case per invocation; it never runs both and
never retries beyond the ledger caps.

Exit codes: `0` success, `1` failed mandatory operation, `2` blocked preflight (missing credentials,
invalid pricing, or budget guard).

## Paid-call safety (R1/R4)

- An attempt is **reserved and written atomically before any HTTP request**, including case, model,
  prompt version, token bound, max output, and conservative cost. Attempt numbers are never reused.
- Request/response/validation artifacts are written as metadata wrappers and their SHA-256 hashes are
  recorded in the ledger at creation; the evidence gate rejects replacement, truncation, or
  contradictory contents.
- Timeouts, transport errors, malformed bodies, schema failures, truncation, and interrupted
  completions keep their reservation and are finalized as non-success; unknown usage stays unknown.
- Caps: **4 attempts total across cases and restarts (approved amendment)**, 16,000 input tokens (documented UTF-8 byte
  upper bound plus message overhead, not a chars/4 guess), 8,192 output tokens, **US$0.25**
  conservative spend. The ledger is a single file; a different process cannot silently start a new budget.
- Pricing is validated from the protected Codex evidence file: provider/model/base URL must match
  configuration, currency USD, rates finite and non-negative, source URL and verification date present,
  and text-only scope recorded. Invalid pricing is rejected visibly with exit 2.
- A later blocked preflight only appends a history event; it never rewrites prior attempts.

## Evidence gate (R2)

A live gate is decided by one module, `evidence.py`, which both `probe-provider` and `report` call:

- the ledger case and attempt must match the expected case, and the attempt must be finalized in the
  intended ledger;
- the request, response, and validation JSON artifacts are read and bound to the same case, attempt,
  model, endpoint, and prompt version;
- each artifact's SHA-256 is recorded in the ledger at creation, so replacement or corruption fails;
- HTTP 200, the configured returned model, nonempty content, and `finish_reason=stop` are required in
  execution, CLI, and report;
- the saved draft must equal the response content, and schema/citation/identity validation is
  recomputed against the pinned document hash, anchor fingerprint, and identity;
- the synthetic case must independently reproduce its missing-information expectation;
- missing/unrun cases are NOT_RUN, incomplete or contradictory executed evidence is FAIL, missing
  credentials are a recorded BLOCKED preflight, and a structural PASS stays provisional for Codex.

Artifact paths are confined to `.local/w01/results/provider/**`; absolute paths, traversal,
directories, empty `{}` objects, and malformed JSON are not evidence.

## Exact reproduction sequence

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

Only the two `probe-provider` commands can spend money. `self-test` and `report` never call the provider.

## Required variables

| Variable | Required for | Notes |
|---|---|---|
| `NEBIUS_API_KEY` | live `probe-provider` | Deliberately supplied to the worker process only. Never printed, logged, or stored. If absent, both cases are recorded BLOCKED. |
| `HF_HOME`, `HF_HUB_DISABLE_XET`, `TEMP`, `TMP` | Docling runtime | Set by `run.py`; see quirks above. |

No credentials are read from files, other projects, browsers, or account stores.

## Coordinate convention

Anchors store a normalized bbox `[left, top, right, bottom]` in `[0, 1]` with a **top-left origin,
x right, y down**, plus the unmodified parser coordinates in `bbox_original` and page size in points.
Docling emits bottom-left/y-up points and is converted; pdfplumber is already top-left/y-down points.
Printed page labels are captured separately from the physical zero-based `page_index`.

Context anchors (repair R3) are located text-layer spans with `context_kind`:
`source_identity` (document ID/revision/date line), `revision_header` (`Rev. Z/B/X` cells),
`status_legend` (`A/N/P/-` definitions), and `footnote` (device-variant/revision-identification notes).
The derived revision matrix is not authority; the prompt and validator require its row/header/legend anchors.

## Known limits (do not read past these)

- Selected-entry coverage only: sections 2.2.18 and 2.2.5. The full ES0620 document was inventoried for
  headings but not interpreted; the heading inventory is text-layer based and declared incomplete.
- No authentic old/new manufacturer document pair was obtained (NXP PCN returned HTTP 404).
  `fixtures/synthetic/` is an original pair, labeled **SYNTHETIC** on every object; it proves
  fixture availability only.
- **No live model call has been made in any attempt, including attempt 03**: `NEBIUS_API_KEY` was not
  present. G4 is NOT_RUN and the live half of G5 is unresolved. Published pricing is recorded, but
  account/model access is
  unverified; HTTP 401 alone proves neither the specific model nor full endpoint behavior.
- Anchor IDs are page-scoped ordinals and are not guaranteed stable across parser upgrades; the
  document hash + parser version + extraction configuration is the durable identity.
- Identity validation is structural (document ID/revision/hash and citation roles); it is not
  semantic proof of the claimed conditions.

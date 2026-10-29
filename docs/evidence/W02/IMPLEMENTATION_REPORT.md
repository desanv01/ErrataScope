# W02 implementation report — deterministic domain v1

Status: **worker implementation for Codex review** (not acceptance); updated for repair 01 / attempt 02
Packet: W02-domain-core revision 2, worker attempts W02-attempt-01 and W02-attempt-02 (repair 01)
Baseline: attempt 01 `W02-baseline.json` PASS (155 hashes, 248 links); repair 01 `W02-repair-01-baseline.json` PASS (163 hashes, 267 links) before/after repair
Runtime: Python **3.11.15**, Pydantic **2.14.1** (pre-existing `.local/w01/venv`; nothing installed)
Network/credentials: **none used**; the domain package never imports the W01 spike, provider adapter, or `.env.local`

## Scope implemented

| Gate | Implementation |
|---|---|
| W02-G1 strict contracts | Frozen Pydantic models (`extra="forbid"`), strict str/bool/int typing, deliberate UUID parsing, discriminated typed values, exact selector registry with units, approved AST with depth/node preflight, cross-reference/project/scope/coverage/identity/activation validation, sealed snapshot/fact-set content hashes, JSON schema export |
| W02-G2 evaluator | Accepted-fact resolution in the exact five-field scope only; explicit-null observations; identical-value dedupe; same-scope contradictions (never latest-wins); reviewed empty exceptions; three-valued `all`/`any`/`not`; applicability = target AND trigger AND NOT(any exception); all branches evaluated; warnings retained on false outcomes |
| W02-G3 dependencies/traces | Every target/trigger/exception leaf contributes a `(scope, selector)` dependency and deterministic trace path with operator, result, selector/operands, resolved value, fact IDs, anchor IDs, missing/conflict flags, warning codes; missing selectors and contradictions surfaced |
| W02-G4 hashes/replay | Canonical JSON (UTF-8, sorted keys, no whitespace, `allow_nan=False`), normalized unordered collections, sealed `input_hash`/`result_hash`, atomic offline replay CLI with exit codes 0/2/1, deterministic output bytes across fresh processes |
| Evidence | Four complete sealed synthetic fixtures with explicit expected outcomes, seven test modules (**89 tests** after repair 01), exported JSON schemas + selector registry, W01→W02 mapping boundary note |

## Package layout

`backend/erratascope_domain/`: `models.py`, `selectors.py`, `rules.py`, `canonical.py`, `evaluate.py`, `replay.py`, `errors.py`, `export_schemas.py`, `__init__.py`.
`backend/tests/`: `test_domain_contracts.py` (23), `test_truth_tables.py` (5), `test_resolution.py` (14), `test_dependencies.py` (7), `test_replay.py` (9), `test_repair_regressions.py` (23, repair 01), `test_selectors.py` (8, repair 01), `helpers.py`, `__init__.py` — **89 tests**.
`backend/fixtures/w02/`: `applicable.json`, `unknown_revision.json`, `conflicting.json`, `out_of_scope.json`, `README.md`, `synthetic_sources/synthetic-errata.txt`.
`docs/evidence/W02/schemas/`: 21 exported JSON schema files (20 models + `selector_registry.json`).
`docs/evidence/W02/W01-TO-DOMAIN-MAPPING.md`: reviewed conversion boundary for W04; no live adapter.

## Commands actually run (PowerShell, project root)

`$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')` and `$env:PYTHONDONTWRITEBYTECODE='1'` were set for every Python command.

| Command | Exit | Observed result |
|---|---|---|
| `.local\w01\venv\Scripts\python.exe -m unittest discover -s backend/tests -v` | 0 | attempt 01: **58 tests OK**; repair 01: **89 tests OK** (5.37–5.49 s) |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/repair-01-replay-a.json` | 0 | `result_hash=94e83eb0…ceec`, applicable=1 |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/repair-01-replay-b.json` | 0 | identical hash in fresh process; bytes SHA-256 `3d54124d…3a87` |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/unknown_revision.json --output .local/w02/repair-01-unknown.json` | 0 | `result_hash=4f642781…b748`, unknown=1, missing `component.silicon_revision` |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-repair-01-baseline.json` | 0 | PASS, 163 hashes, 267 links |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/replay-a.json` | 0 | `result_hash=94e83eb0fe02b1d01ce35ce4ec4de8c5708241ce18a34ef6135c226b2024ceec rules=1 applicable=1 unknown=0 not_applicable=0` |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/replay-b.json` | 0 | identical output/hash in a fresh process |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/unknown_revision.json --output .local/w02/replay-unknown.json` | 0 | `result_hash=4f642781da2185a8c174a3cf2b054fc205eeae5bf2c1fa1560f45bf99e83b748`, unknown=1, missing `component.silicon_revision` |
| byte/hash comparison script over replay-a/replay-b | 0 | `byte_identical=True`; SHA-256 `3d54124d1c6ea27d84b48764e7ef55f136a98d95a28d9120c5e537cc2d853a87` for both; result hashes equal |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-baseline.json` | 0 | PASS, 155 hashes, 248 links |
| `.local\w01\venv\Scripts\python.exe -m erratascope_domain.export_schemas --out docs/evidence/W02/schemas` | 0 | wrote 21 files |
| `uvx ruff check backend` (advisory lint, workspace-local tool cache) | 0/1 | only style notes remain (TRY004/SIM102); all functional lint findings fixed |

Replay artifacts: `.local/w02/replay-a.json`, `replay-b.json`, `replay-unknown.json`.

## Test coverage (89 tests, explicit oracles)

- **Contracts (23):** frozen/extra-forbid, UUID parsing, strict bool/int/text/quantity typing, quantity normalization/bounds/units/signs, blank identity, geometry ordering/rotation/synthetic-document rules, snapshot/fact-set hash tampering, duplicate IDs, unresolved refs, project/scope isolation, identity mismatch, unreviewed rules and missing consequence/anchors/exceptions, unsupported selector/operator/unit, coverage consistency/selection, baseline pin mismatch, bundle/AST limits, immutable pins, diagnostic paths, schema export, no-network parse/evaluate.
- **Truth tables (5):** all 9 pairwise `all` combinations, all 9 `any`, all 3 `not`; end-to-end AST for true/false/unknown; false target + unknown trigger retains `MISSING_SELECTOR`.
- **Resolution (14):** applicable; missing silicon revision; matching/unknown/empty exceptions; same-scope contradiction (not newest-wins); identical-fact dedupe with all supporting IDs; other component and other build/profile facts ignored; draft/rejected facts ignored; explicit null with known value; fixture journeys.
- **Dependencies (7):** all branches retained under a false target; `any(true, missing)` still records the missing dependency; dedupe; fact/anchor IDs in traces; deterministic paths; contradictory selector dependency; all three branch types traversed.
- **Replay (9):** connected fixture journey; two fresh CLI processes byte-identical; semantic change alters both hashes; invalid input preserves existing output (exit 2); malformed JSON exit 2; missing input exit 1; atomic normalized output; unknown exits 0; repeatable in-process evaluation.
- **Repair regressions (23):** explicit-null identity fields and required-key rejection; required-but-nullable `FactVersion.value`; `evaluate` strict revalidation of `model_copy`/`model_construct` bundles (schema version, UUID type, empty logical group, nested typed value) and non-mutation; foreign-project component and all evidence-reference resolution (identity display refs, nonidentity/null/draft facts); legal empty refs; aggregate 512/513/602 node boundaries, exception-split budgets and independent per-rule budgets.
- **Selectors/decimal (8):** explicit operator/type/unit table for all 12 selectors, exported-registry agreement, allowed/disallowed operator pairs, full-string decimal grammar (valid boundaries, normalization, newline/whitespace/exponent/Unicode-digit rejection) and sign constraints.

No expected truth value is generated by the evaluator under test; tables and fixture outcomes are literal oracles. Tests use original SYNTHETIC data only.

## Fixtures (all SYNTHETIC)

| Fixture | Expected (literal oracle) |
|---|---|
| `applicable.json` | applicable; target true, trigger true, exception false; `OUT_OF_SCOPE_FACT_IGNORED` for the other component's pulse fact |
| `unknown_revision.json` | unknown; target unknown; missing `component.silicon_revision`; out-of-scope other-component fact ignored |
| `conflicting.json` | unknown; target true, trigger unknown, exception false; contradiction on `operating.clock_hz` (1 MHz vs 2 MHz) |
| `out_of_scope.json` | unknown; all branches unknown; out-of-scope facts ignored; incomplete inventory, unsupported entry 1.9, failed entry 1.8 |

Synthetic source bytes: `backend/fixtures/w02/synthetic_sources/synthetic-errata.txt`, SHA-256 `2d59cf247fd836406f6e7ed09ee2674759bcc9cd9b1e9ccb4c049d94a6453068`. Fixtures are sealed with `seal_snapshot`/`seal_fact_set`; `parse_bundle` verifies those hashes.

## Determinism evidence

- Two fresh replay processes produced **byte-identical** output (`3d54124d…`), identical result hash `94e83eb0…`.
- Unknown-result replay persisted with hash `4f642781…` and exit 0.
- `input_hash` changes when a pinned semantic fact changes (pulse 10 ns → 30 ns test); result hash changes too.
- Invalid input leaves a pre-existing valid output byte-identical (tested).
- Unordered entity collections are sorted before hashing; AST child order is preserved; no generated timestamps exist in the result.

## Limitations and boundaries

- Synthetic fixtures only; this does **not** validate a real errata conversion, electrical behavior, simulator correctness, model accuracy, or whole-device coverage.
- W01 drafts are not converted; W04 must perform human-reviewed conversion preserving source scope, unknown facts and qualifications (see mapping note).
- No persistence/API/jobs (W03), UI, deployment, queue, model SDK, provider call, or credential access.
- Windows sandbox quirk: `tempfile.mkdtemp`-style 0700 directories are inaccessible here, so tests create workspace-local scratch dirs under `.local/w02` with default permissions; test-only, no product behavior affected.
- Frozen Pydantic objects are immutable for normal use; Python can still bypass with `object.__setattr__`, which is outside the JSON input threat model.

## Changed files

Created: all files under `backend/` listed above; `docs/evidence/W02/schemas/*` (21 files); `docs/evidence/W02/W01-TO-DOMAIN-MAPPING.md`; this report; `docs/execution/handoffs/W02-attempt-01.md`. Generated replay outputs under `.local/w02/`. No protected file, W01 artifact, baseline, contract, review, or prior handoff was modified; no Git/UI/deploy/W03 action was performed.

## Repair 01 (attempt 02) — R1–R4 evidence

Repair assignment: `docs/execution/reviews/W02-repair-01.md`; review: `W02-review-01.md`. Starting inventory verified **47/47** SHA-256 matches before edits; verified backup at `.local/w02/history/attempt-01-before-02/` (47 files + manifest, all copied hashes match).

| Repair | Before | After / evidence |
|---|---|---|
| **R1** explicit nulls + public validation | Four identity fields non-null; omitted `silicon_revision`/`FactVersion.value` silently null; `evaluate` accepted `model_copy(schema_version=99)` | All five identity fields are **required text-or-null** (missing key → `SCHEMA_INVALID`, explicit null accepted, blank known value rejected); `FactVersion.value` required but nullable; `evaluate` re-serializes and re-runs `parse_bundle` (strict schema, limits, hashes, references) so `model_copy`/`model_construct` bypasses, invalid nested typed values, schema-version tampering and empty logical groups raise structured `DomainValidationError`; caller input is not mutated. Tests: `ExplicitNullContractTests` (9). |
| **R2** project/evidence references | Foreign-project non-selected component accepted; missing identity/nonidentity evidence refs accepted | Every `ComponentInstance.project_id` is checked against the bundle project (selected or not); **every** `ComponentIdentity.evidence_refs` and `FactVersion.evidence_refs` anchor resolves regardless of selector/review state/null value, reusing anchor/document/hash checks; empty refs remain legal; accepted known identity still requires ≥1 anchor. Tests: `ReferenceProjectTests` (7), all resealing snapshot/fact-set so the reference check is the failing one. |
| **R3** aggregate rule budget | 602 nodes split target/trigger and 513 across exception roots parsed | Raw preflight sums target+trigger+all exceptions per `RuleVersion` and rejects >512 with `AST_NODE_LIMIT_EXCEEDED` at `rules/<index>` before recursive Pydantic parsing; depth ≤32 per expression and all other caps retained; typed `evaluate` path benefits because it re-parses via `parse_bundle`. Tests: `AggregateNodeBudgetTests` (7) covering 512 accepted, 513 rejected, 602 split rejected, exception-root split 512/513, and independent per-rule budgets. |
| **R4** registry/decimal consistency | Boolean/quantity advertised `in`; integer lacked ordering; `1\n` accepted | Registry operators now exactly match the bound AST (text eq/in; boolean eq; integer eq/in/ordering; quantity eq/ordering) with names/types/units unchanged; quantity grammar is full-string ASCII `^-?[0-9]{1,18}(?:\.[0-9]{1,9})?\Z` with `fullmatch`, rejecting newline/whitespace/exponents/specials/Unicode digits/excess digits while preserving trailing-zero and negative-zero normalization and negative temperatures. Registry/schemas regenerated. Tests: `test_selectors.py` (8) with an explicit independent operator table. |

Repair validation commands (all exit 0):

| Command | Result |
|---|---|
| `python -m unittest discover -s backend/tests -v` | **89 tests OK** (5.485 s) |
| `python -m erratascope_domain.export_schemas --out docs/evidence/W02/schemas` | 21 files written; registry verified (`boolean → ['eq']`, `quantity → eq+ordering`, `integer → eq/in+ordering`) |
| `python -m erratascope_domain.replay …applicable.json → .local/w02/repair-01-replay-a.json` | hash `94e83eb0…ceec` |
| same → `repair-01-replay-b.json` | byte-identical; SHA-256 `3d54124d…3a87` |
| `…unknown_revision.json → .local/w02/repair-01-unknown.json` | hash `4f642781…b748`, applicability unknown, missing `component.silicon_revision` |
| `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-repair-01-baseline.json` | PASS, 163 hashes, 267 links |

**Result hashes for valid fixtures are unchanged** from attempt 01 (`94e83eb0…`, `4f642781…`) because the repair changes representation requirements and invalid-input rejection, not the normalized semantics of valid inputs; replay bytes remain identical. No hash was hard-coded or bypassed.

Files changed in repair 01: `backend/erratascope_domain/models.py`, `selectors.py`, `evaluate.py`; `backend/tests/helpers.py`, `test_repair_regressions.py` (new), `test_selectors.py` (new); regenerated `docs/evidence/W02/schemas/*`; this report; `docs/execution/handoffs/W02-attempt-02.md`. No adapter, provider, dependency, baseline, contract, review or W01 artifact was changed.

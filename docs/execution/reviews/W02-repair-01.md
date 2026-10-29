# W02 repair 01 — close domain validation gaps

Codex assignment, 30 October 2026. **READY_TO_DISPATCH**, W02 revision 2, worker attempt **02**. This assignment supersedes attempt 01's start/ownership instructions for this repair only. The existing domain-v1 contract remains binding. Do not restart the project, implement W03, or change architecture.

## Read and preflight

Read [review 01](W02-review-01.md), [W02 packet](../packets/W02-domain-core.md), [domain-v1 binding](../bindings/W02-domain-v1.md), [worker rules](../WORKER_RULES.md) and this entire assignment. The [independent checker](W02-review-01-checks.py) and [observations](W02-review-01-observations.json) are read-only reproductions; incorporate meaningful equivalent regression cases into the worker-owned tests without editing these review files.

1. Work in `C:\Users\Dv\Desktop\ErrataScope`. Require no active worker and no existing W02-attempt-02 handoff.
2. Run `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-repair-01-baseline.json`; require PASS.
3. Verify every file SHA-256 in `docs/execution/reviews/W02-attempt-01-inventory.json` against actual bytes. This inventory pins the reviewed starting backend and W02 evidence; it is verified **before changes only**, not after authorized repairs. Stop on any mismatch or missing file.
4. Claim `.local/coordination/ACTIVE_WORKER.json` exclusively with W02/revision 2/attempt 02, start UTC, harness and writable paths. Back up the inventoried files under `.local/w02/history/attempt-01-before-02/`, preserving relative paths; create a manifest and verify copied hashes before modifying them. Do not overwrite prior history.

The original W02-baseline.json remains immutable historical evidence. Codex changed dispatch/status files after independently verifying it; do not use it as the active repair baseline or try to restore current status files to make it pass.

## Ownership and prohibitions

Writable: `backend/**` for the scoped domain repair/tests/fixtures/docs; `docs/evidence/W02/**` for regenerated schemas and truthful implementation report; `.local/w02/**` for backups/test/replay outputs; new `docs/execution/handoffs/W02-attempt-02.md`; your own worker lock only.

All other paths are read-only, especially W01 source/evidence/ledger, protected baselines, contracts/bindings, reviews/checkers/inventories, old handoffs, current status/prompts, `.local/reviews/**`, credentials and visuals. Do not open `.env.local`, inspect credentials, install dependencies, use uvx to obtain tools, access the network, make provider calls, mutate Git, implement UI, deploy, or begin W03. Python 3.11.15 and Pydantic 2.14.1 already installed in `.local/w01/venv` are sufficient. Do not run the Codex checker as-is because it writes in `.local/reviews`; reproduce its cases in owned tests.

## R1 — required unknown fields and validated public entry points

- ComponentIdentity's manufacturer, exact_part, family, package and silicon_revision must each be **required text-or-null** fields. Preserve exact known identity text and reject invalid/blank known identity values. Unknown is represented by an explicitly supplied null, not by omitting a key.
- Make FactVersion.value required while permitting explicit null. Do not add non-null requirements to unknown observations. Keep null warnings/IDs and accepted-known identity evidence requirements intact.
- `evaluate` must enforce the full bound schema and cross-reference/limit invariants even for Pydantic instances created/copied without validation. Merely calling model_validate on an instance with default instance-revalidation behavior is insufficient. Audit the actual nested-model path, preserving strict typing and preventing coercion through serialization.
- Retain preflight protection before recursively traversing unchecked ASTs. Return structured domain diagnostics rather than accepting invalid instances or leaking incidental attribute/recursion failures. No mutation of callers' sealed inputs.
- Regressions: all five explicit-null identity fields accepted when otherwise coherent; each of the five missing keys rejected; missing FactVersion.value rejected but explicit-null fact accepted; schema_version=99 model_copy rejected; representative nested invalid typed values and model_construct/model_copy bypasses rejected. Existing valid models remain evaluable and deterministic.

## R2 — complete reference/project checks

- Validate every ComponentInstance.project_id against the bundle/snapshot project, including components not selected by the assessment.
- Resolve **every supplied** ComponentIdentity.evidence_refs and FactVersion.evidence_refs anchor, regardless of selector, review state or whether its value is null. Empty refs remain allowed where the binding allows them; do not invent a universal nonempty evidence requirement. Known accepted identity facts still require at least one anchor.
- Reuse the existing anchor/document/project/hash constraints so resolving an ID does not bypass its source relationship. Preserve legitimate out-of-scope facts in the same snapshot and reject unresolvable/foreign scope references as already bound.
- Regressions must reseal the relevant snapshot/fact set so failure is actually the reference or project check, not a stale content hash. Test absent refs on display identity, nonidentity known/null facts and draft/rejected facts; include positive resolved refs and legal empty refs, plus nonselected foreign-project component rejection.

## R3 — aggregate AST node budget

- Enforce at most **512 total AST nodes per RuleVersion**, counting target + trigger + every exception subtree, including all composite and constant nodes. This is per rule, not per root or per bundle. Preserve depth <=32 for each expression.
- Preflight the aggregate before recursive Pydantic parsing/evaluation. Many individually small exceptions must not bypass the budget. Apply equivalent protection to the public typed evaluate entry.
- Regressions: exactly 512 aggregate nodes accepted; 513 rejected; 602 split between target/trigger rejected; excess split across exception roots rejected; multiple independent legal rules not incorrectly combined into one 512-node budget; existing depth/100-rule/fact/anchor caps retained. Use stable diagnostic codes/paths.

## R4 — consistent selector registry and full decimal grammar

- Registry operators must exactly match the bound AST: text eq/in; boolean eq; integer eq/in/lt/lte/gt/gte; quantity eq/lt/lte/gt/gte. Keep selector names, canonical units and types unchanged. Regenerate the exported registry and JSON schemas after all repairs.
- Require the entire quantity string to match the decimal grammar; reject trailing newline/other whitespace, exponents, specials, non-string values, and excessive digits. Preserve trailing-zero/negative-zero normalization, exact units, and negative temperature behavior.
- Table-driven tests must compare every selector's exported operators with explicit independent expectations, exercise allowed/disallowed type/operator pairs, and cover newline/whitespace rejection alongside valid decimal boundaries. Do not derive the expected registry from the implementation being tested.

## Required validation and evidence

Use the pinned interpreter, no new dependencies. In PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
$env:PYTHONDONTWRITEBYTECODE = '1'
.local\w01\venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.local\w01\venv\Scripts\python.exe -m erratascope_domain.export_schemas --out docs/evidence/W02/schemas
.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/repair-01-replay-a.json
.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/repair-01-replay-b.json
.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/unknown_revision.json --output .local/w02/repair-01-unknown.json
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-repair-01-baseline.json
```

Run sequentially and inspect exits. Compare fresh-process replay bytes/hashes. Tests must retain invalid-CLI exit 2/output preservation, scope/contradiction resolution, full dependencies and original truth-table oracles. New invalid schema/reference/limit cases must reject through the appropriate public API; exercise representative cases through the CLI too. No check skipping, oracle weakening or contract edits to turn red checks green. Update the implementation report with exact counts, commands/exits and R1–R4 evidence. If result hashes change, explain the normalized semantic/schema reason rather than hard-coding historical hashes as a bypass.

Record the earlier advisory `uvx ruff` command accurately in the new handoff if its cache/download behavior is known; do not infer or assert that it downloaded dependencies, and do not use it in this repair. No lint expansion is required.

## Handoff and stop

Recheck the repair protected baseline, record any failed/skipped check and actual R1–R4 outcomes, write `docs/execution/handoffs/W02-attempt-02.md`, stop owned jobs, release only your own lock and stop editing. The starting inventory is not expected to match repaired files; include changed-file hashes/results in the new handoff. Acceptance and Git/GitHub remain Codex's responsibility.

Return this exact prompt:

> Review ErrataScope W02 revision 2 repair 01, worker attempt 02. The worker has stopped editing. Read docs/execution/handoffs/W02-attempt-02.md, docs/execution/reviews/W02-review-01.md and docs/execution/reviews/W02-repair-01.md. Verify the repair protected baseline and independently check R1–R4 against actual contracts, code, exported schemas and artifacts, including explicit nulls, direct-model validation, project/evidence references, aggregate rule limits and registry/decimal consistency. Preserve W01's accepted live evidence; W02 requires no provider calls or credentials. If all W02 gates pass, record acceptance, perform its Git/GitHub checkpoint, bind eligible W03 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt. Preserve the UI/imagegen approval gate.

# ErrataScope deterministic domain package (W02 / domain v1)

Offline implementation of the bound W02 domain contract: strict immutable
entities, scoped three-valued rule evaluation, complete dependency traces, and
deterministic canonical hashing/replay. **No network, credentials, database,
frontend, or W01 spike import is used.**

## Runtime pins (already installed; nothing was installed for W02)

- Python **3.11.15** (`.local/w01/venv/Scripts/python.exe`)
- Pydantic **2.14.1**

See `requirements-domain.txt`. Only the standard library plus Pydantic is used.

## Commands

From the repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
$env:PYTHONDONTWRITEBYTECODE = '1'
.local\w01\venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/replay-a.json
.local\w01\venv\Scripts\python.exe -m erratascope_domain.export_schemas --out docs/evidence/W02/schemas
```

Replay exit codes: `0` valid evaluation (including `unknown`), `2` invalid input,
`1` IO/runtime failure. Output is written atomically only after a successful
validation+evaluation; a failure never replaces an existing output file.

## Public API

```python
from erratascope_domain import parse_bundle, evaluate

bundle = parse_bundle(raw_dict)   # raises DomainValidationError with code/path diagnostics
result = evaluate(bundle)         # revalidates, then returns canonical-hashed AssessmentResult
```

- `parse_bundle` enforces limits and AST depth on the raw JSON **before** Pydantic
  conversion, then validates cross-references, project/scope isolation, accepted
  rule/fact activation, coverage consistency, identity consistency, and supplied
  snapshot/fact-set content hashes.
- `evaluate` revalidates the typed bundle, so constructing models directly cannot
  bypass invariants. It performs no I/O and collects no credentials.
- Helpers: `seal_snapshot`, `seal_fact_set`, `truth_and`, `truth_or`, `truth_not`,
  `resolve_selector`, `validate_bundle`.

## Model boundary

Entities are frozen Pydantic models with `extra="forbid"`, UUID entity IDs and
lowercase SHA-256 content hashes. Text/boolean/integer values are strict (booleans
are not integers; JSON floats are rejected for integer/quantity values).
Quantities are canonical decimal strings with an exact registry unit; v1 performs
no unit conversion. `located` source geometry requires validated bbox/dimensions;
`synthetic_not_located` geometry requires a synthetic document.

## Selectors (registry v1)

| Selector | Type | Unit |
|---|---|---|
| `component.manufacturer` | text | — |
| `component.exact_part` | text | — |
| `component.family` | text | — |
| `component.package` | text | — |
| `component.silicon_revision` | text | — |
| `operating.external_reset_used` | boolean | — |
| `operating.reset_pulse_ns` | quantity | ns |
| `operating.clock_hz` | quantity | Hz |
| `operating.supply_voltage_v` | quantity | V |
| `operating.temperature_c` | quantity | degC |
| `firmware.initial_software_reset` | boolean | — |
| `firmware.revision_id_value` | integer | — |

The full machine-readable registry is exported to
`docs/evidence/W02/schemas/selector_registry.json`.

## Rule AST

Discriminated nodes: `eq`, `in` (text/integer), `lt/lte/gt/gte` (quantity/integer),
`all`, `any`, `not`, and reviewed `constant`. Leaf predicates require at least one
anchor belonging to the rule's document version. Limits: depth ≤ 32, nodes ≤ 512
per expression, ≤ 100 rules, ≤ 5,000 facts, ≤ 10,000 anchors per bundle.

Applicability = `target AND trigger AND NOT(any exception)`. Three-valued truth
tables follow the shared rule-language contract; every branch is evaluated and
all target/trigger/exception selectors are dependencies even when missing or when
another branch determines the result.

## Determinism

Canonical JSON: UTF-8, sorted keys, no whitespace, `ensure_ascii=False`,
`allow_nan=False`, defaults/nulls materialized. UUIDs are lowercase; quantities
are normalized decimal strings. Unordered collections are sorted by stable keys
before hashing; AST child order is preserved. `input_hash` covers the normalized
sealed bundle; `result_hash` covers the result payload excluding itself. No
generated timestamps exist in the result.

## Fixtures and tests

Self-contained SYNTHETIC fixtures live in `backend/fixtures/w02/` (see its
README for expected outcomes). Tests are table-driven where required and never
derive expected truth values from the evaluator under test. They cover strict
typing, geometry, limits, hash tampering, scope isolation, contradictions,
exceptions, dependency completeness, and cross-process replay determinism.

## Explicit non-goals / limits

- Not a verifier, simulator, firmware runner, or patch generator; no electrical
  behavior is inferred.
- No W01 spike import, no provider/model call, no automatic conversion of W01
  draft claims into executable rules (see
  `docs/evidence/W02/W01-TO-DOMAIN-MAPPING.md`).
- Not persistence/API (W03), UI, or deployment.

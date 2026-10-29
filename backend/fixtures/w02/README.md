# W02 synthetic fixtures (SYNTHETIC — not manufacturer material)

Every object here is original, hand-authored **SYNTHETIC** fixture data for the
deterministic domain package. No real device, manufacturer document, page
geometry, erratum, or revision is reproduced. The synthetic source text is
`synthetic_sources/synthetic-errata.txt`; each document's `document_sha256` is
the SHA-256 of those UTF-8 bytes
(`2d59cf247fd836406f6e7ed09ee2674759bcc9cd9b1e9ccb4c049d94a6453068`).

Anchors use `geometry_kind: "synthetic_not_located"` with null bbox/dimensions,
which the contract permits for explicitly synthetic fixtures. Fixture JSON is a
complete sealed `AssessmentInputBundle`: snapshot and fact-set content hashes were
produced by the domain `seal_snapshot`/`seal_fact_set` helpers, and `parse_bundle`
verifies them (tamper any content and parsing fails with `HASH_MISMATCH`).

All fixtures share the same project, synthetic document, snapshot with two
component instances (`subject` revision B, other component revision A), and one
accepted synthetic rule `1.1`:

- target: `component.silicon_revision == "B"`
- trigger: `operating.external_reset_used == true` AND
  `operating.reset_pulse_ns < 20 ns`
- exceptions: `firmware.initial_software_reset == true`

Expected outcomes are explicit oracles; tests do not compute them with the
evaluator:

| Fixture | Facts | Expected | Expected diagnostics |
|---|---|---|---|
| `applicable.json` | subject revision B, external reset true, pulse 10 ns, initial SW reset false | **applicable**; target true, trigger true, exception false | `OUT_OF_SCOPE_FACT_IGNORED` (other component pulse fact is not selected) |
| `unknown_revision.json` | no subject revision fact; reset true, pulse 10 ns, initial reset false | **unknown**; target unknown, trigger true, exception false | missing `component.silicon_revision`; `OUT_OF_SCOPE_FACT_IGNORED` (other component revision fact) |
| `conflicting.json` | subject revision B; two accepted `operating.clock_hz` facts (1 MHz and 2 MHz) | **unknown**; target true, trigger unknown, exception false | contradiction on `operating.clock_hz`; missing `operating.clock_hz` |
| `out_of_scope.json` | facts exist only for the other component and for another firmware build/profile | **unknown**; all three branches unknown | `OUT_OF_SCOPE_FACT_IGNORED`, missing selectors for the exact scope, `INVENTORY_INCOMPLETE`, `UNSUPPORTED_ENTRIES`, `FAILED_ENTRIES` |

Coverage is complete (`inventory_complete: true`) for the first three fixtures.
`out_of_scope.json` deliberately declares `inventory_complete: false` with an
unsupported entry `1.9` and failed entry `1.8`, and its notes say so.

## Reproduce

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
.local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/replay-a.json
```

Fixture hashes are content hashes of the bundle payload, not of these files'
bytes, so formatting changes to the JSON do not alter `input_hash`; semantic
content changes do.

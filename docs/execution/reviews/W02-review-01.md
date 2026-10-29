# W02 review 01 — changes required

Codex independent review, 30 October 2026. Packet revision 2, worker attempt 01.
Decision: **CHANGES_REQUESTED; W02/P1 not accepted.** Continue with [one consolidated repair](W02-repair-01.md) and [its exact prompt](../prompts/W02-REPAIR-01.md). W03 remains unbound and not dispatchable.

## Evidence inspected and independently exercised

- Read the worker handoff, packet, domain-v1 binding, implementation, exported contracts and synthetic fixtures. The worker lock was absent.
- Original W02 protected baseline independently passed before coordination changes: **155 hashes**, no mismatches, including the frozen W01 public evidence. The original baseline is preserved; it is historical after Codex updates dispatch documents below.
- Re-ran the existing suite using the pinned interpreter: **58 tests passed**, no failures/errors/skips.
- Ran [the independent checker](W02-review-01-checks.py), without worker test helpers: **30/46 assertions passed; 16 failed**, grouped into the four repair areas below. Results are preserved in [the review observations](W02-review-01-observations.json). These are boundary cases, not a statistical accuracy benchmark.
- All four fixture outcomes matched their documented oracles, including **unknown** for out_of_scope.json. All 18 connected AND/OR truth-table combinations passed. A false target retained an unknown exception's missing selector and dependency.
- Two fresh CLI processes produced byte-identical valid outputs. A null-exceptions input returned exit 2 and preserved the prior output. These passing checks do not establish that every invalid input is rejected.
- No product code was edited by Codex. No provider request, package installation, Git write, UI or infrastructure work occurred during this review. In-process review checks disabled sockets; inspected domain code and offline CLI paths require no network or credentials.

The review checker initially assigned an incorrect expected outcome to the out-of-scope fixture; it was corrected against the fixture's explicit oracle before recording these results. A Unicode-digit observation was excluded from blocking checks because the existing decimal contract does not explicitly specify ASCII. Neither is a worker defect in this decision.

## Required findings

### R1 — required unknown fields and public evaluation validation

`models.py` ComponentIdentity requires non-null manufacturer/exact_part/family/package, contrary to the binding's five required text-or-null keys. All four explicit-null cases reject. Conversely, omitted silicon_revision and omitted FactVersion.value are silently materialized as null, losing the required distinction between missing input and explicit unknown.

`evaluate.py` calls cross-reference validation without revalidating the full schema. A parsed bundle copied with `model_copy(update={'schema_version': 99})` is evaluated successfully. The binding explicitly requires direct construction not to bypass invariants. This uses the public Pydantic API, not an object.__setattr__ attack.

### R2 — unresolved evidence and cross-project component accepted

A sealed snapshot containing a ComponentInstance from another project is accepted. A snapshot identity referencing an absent evidence anchor is accepted. A nonidentity fact referencing an absent evidence anchor is accepted. The reference contract applies to all supplied references, not just accepted known identity facts. Hashes were recomputed in these cases; this is not a tamper-check false positive.

### R3 — node cap enforced per expression instead of per rule

A rule with 602 total nodes spread across target/trigger parses. A rule with 513 total nodes spread across target/trigger/exceptions also parses. The binding limits the whole rule to 512 nodes. The positive 512-node boundary passes and must remain valid. Per-expression checks leave arbitrarily many exception roots outside the aggregate cap.

### R4 — exported selector contract and decimal lexical acceptance disagree

The registry advertises `in` for boolean and quantity selectors even though the AST correctly forbids it. The integer selector omits ordering operators that the bound AST permits. This would mislead the next packet's consumers. Additionally, the decimal matcher accepts a trailing newline (`"1\n"`); the full value is not the prescribed decimal-string grammar.

## Gate decision

| Gate | Independent finding |
|---|---|
| W02-G1 contracts | **FAIL**: R1–R4 violate the bound contract |
| W02-G2 semantics | Tested truth tables, scope isolation, missing/conflicting facts and exception paths pass; retain regression coverage during repair |
| W02-G3 dependencies | Tested full-branch dependency and warning behavior passes; retain during repair |
| W02-G4 replay | Determinism and atomic preservation pass on tested cases; **PARTIAL** overall because invalid-input/schema acceptance remains defective |

These are targeted repairs to the existing package, not a request to restart or expand W02. No new provider evidence is needed. W01 remains accepted and its four lifetime reservations remain consumed.

## Checkpoint and next step

No W02 completion commit/push was made because W02 is not accepted. The existing W01 checkpoint remains the latest accepted checkpoint. After a passing repair review, Codex will checkpoint accepted W02, bind W03 and supply its exact worker prompt. The UI/imagegen approval gate remains PENDING.

The [repair baseline](../baselines/W02-repair-01-baseline.json) protects current coordination/review/contract files. The [attempt-01 inventory](W02-attempt-01-inventory.json) separately binds the editable starting implementation and evidence. It is a preflight comparison only; those files may change within repair ownership.

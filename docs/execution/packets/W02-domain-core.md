# W02 — Domain contracts and deterministic evaluator

Acceptance notice (30 October 2026): W02/P1 accepted under [review 02](../reviews/W02-review-02.md), including repair 01 and recorded Codex boundary corrections. Instructions below are historical; current dispatch is [W03](W03-persistence-jobs.md). Domain-v1 requirements remain unchanged.

Packet revision: **2**
Dispatch state: **ACCEPTED**
Phase: [P1](../phases/P1-domain-core.md)
Starting baseline: [W02-baseline.json](../baselines/W02-baseline.json), freshly bound after [W01 acceptance](../reviews/W01-review-06.md). The earlier deferred draft is preserved separately; it is not a dispatch baseline.
Worker: DeepSeek, attempt **W02-attempt-01**. Codex accepts.

## Authorization and reading

W01/P0 is accepted, including actual live G4/G5 and semantic review. Read [the acceptance](../reviews/W01-review-06.md) and [observed contracts](../bindings/W01-observed-contracts.md). This packet is authorized as offline domain/evaluator implementation with the fresh baseline; no provider call or credential is needed.

Read [START_HERE](../START_HERE.md), [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [domain invariants](../contracts/domain-invariants.md), [data/version contract](../contracts/data-and-versions.md), [rule language](../contracts/rule-language.md), [testing contract](../contracts/testing-and-acceptance.md), and the complete [W02 domain-v1 binding](../bindings/W02-domain-v1.md). That binding provides exact models, public API, selectors, AST, scope, numeric/hash rules, limits and behavioral tests. Spike schemas are experimental, not automatic production contracts. The [UI approval gate](../UI_APPROVAL_GATE.md) stays pending; this packet has no UI.

## Preflight and ownership

Work only in C:\Users\Dv\Desktop\ErrataScope. Run:

    python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-baseline.json

Require PASS before writes. Require no active worker lock and no W02-attempt-01 handoff. Claim .local/coordination/ACTIVE_WORKER.json exclusively with packet/revision/attempt/start UTC/harness/writable paths.

Writable paths only:
- backend/**: domain package, requirements pin, README, tests and synthetic fixtures; no unrelated scaffold.
- docs/evidence/W02/**: exported JSON schemas and implementation/test report.
- .local/w02/**: test/replay outputs and logs.
- docs/execution/handoffs/W02-attempt-01.md: new handoff only.
- .local/coordination/ACTIVE_WORKER.json: own lock only.

All other paths are read-only, including spike code, W01 artifacts/ledger, source manifest, protected baselines, plans/contracts, reviews, old handoffs, .local/reviews, credentials and visuals. Do not open .env.local or dump environment values. No package install, network, Git mutation, provider call, deployment, frontend or W03 work. Existing Python 3.11.15/Pydantic 2.14.1 is sufficient.

## Implementation sequence

1. **Contracts/G1:** implement strict models, selector registry, AST, input/reference/identity/scope/review/coverage constraints, immutable content sealing and public parse_bundle interface exactly as bound. Export JSON schemas. Check depth/size before recursive parsing. Unsupported data rejects with field/path diagnostics.
2. **Evaluator/G2:** implement accepted-fact resolution and complete three-valued semantics, explicit exceptions, contradictions and coverage warnings. No latest-wins, scope leakage, hidden identity facts or inferred electrical behavior.
3. **Dependencies/G3:** traverse every branch and retain trace nodes, relevant fact/anchor IDs, missing/conflicting inputs and all selector dependencies, even when a false branch determines the final result.
4. **Replay/G4:** implement canonical JSON/hash rules, evaluate API and offline replay CLI. Atomic output only after validation; invalid input cannot replace valid output. Preserve pinned inputs and exclude only the specified incidental fields.
5. **Evidence:** create complete sealed fixtures applicable.json, unknown_revision.json, conflicting.json and out_of_scope.json under backend/fixtures/w02, with original synthetic sources/anchors, labels and readable expected outcomes. Implement every semantic case in the binding. Include a W01-to-domain mapping note for later reviewed conversion, without building a live adapter.

## Commands and acceptance evidence

Run sequentially, inspecting each exit. In PowerShell:

    $env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
    $env:PYTHONDONTWRITEBYTECODE = '1'
    .local\w01\venv\Scripts\python.exe -m unittest discover -s backend/tests -v
    .local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/replay-a.json
    .local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/applicable.json --output .local/w02/replay-b.json
    .local\w01\venv\Scripts\python.exe -m erratascope_domain.replay --input backend/fixtures/w02/unknown_revision.json --output .local/w02/replay-unknown.json
    python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-baseline.json

Compare both replay files' bytes and result hashes. Tests must also check altered input and invalid replay, not only success examples. No tests whose expected answer is generated from the evaluator under test. Write docs/evidence/W02/IMPLEMENTATION_REPORT.md with actual commands/exits, test counts, gate evidence, changed files, pins, limitations and synthetic/no-network labeling.

| Gate | Required evidence |
|---|---|
| W02-G1 | Strict typed/review/reference/scope/coverage contracts; unsupported input rejected |
| W02-G2 | Explicit truth tables, missing/conflicting facts, scope isolation and exception cases |
| W02-G3 | All branch dependencies and missing selectors, trace facts/anchors and explanations |
| W02-G4 | Connected replay stable across fresh processes; semantic changes alter hash; invalid input preserves output |

Fix owned implementation defects before handoff; do not repeatedly rerun without changes/unresolved failure. Protected mismatch or preexisting lock means stop. A genuine contract conflict requires one concise blocker/proposal, not changes to protected contracts. After W01 acceptance and a fresh dispatch, W02 itself needs no provider calls or credentials.

## Handoff and next action

Follow [the handoff template](../templates/HANDOFF.md). Record start/end, baseline, implementation/API/schema paths, commands, failed/skipped checks, gates and provenance. Recheck baseline, stop owned processes, release only your lock and stop editing.

Return:

> Review ErrataScope W02 revision 2, worker attempt 01. The worker has stopped editing. Read docs/execution/handoffs/W02-attempt-01.md, docs/execution/packets/W02-domain-core.md, and docs/execution/bindings/W02-domain-v1.md. Verify the W02 protected baseline and independently test strict schemas, scope/contradiction resolution, three-valued semantics, complete dependencies, and deterministic replay against actual files. W01/P0 is accepted, including live G4/G5; preserve its frozen evidence. W02 is offline and needs no Nebius calls or credentials. If W02 passes, record acceptance, perform its Git/GitHub checkpoint, bind the eligible W03 scope, and give me the exact DeepSeek prompt. Otherwise give one consolidated repair assignment and prompt. Preserve the UI/imagegen approval gate.

Bound fields: baseline W02-baseline.json; exact ownership above; domain-v1/schema 1/evaluator domain-v1; existing pinned Python/Pydantic; no UI; zero provider requests/spend; no deployment. Next candidate W03 only after Codex acceptance and exact persistence/API binding. No future packet is authorized by this assignment.


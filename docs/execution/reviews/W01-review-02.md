# Codex review — W01 repair 01, worker attempt 02

Date: 29 October 2026, Malaysia.
Decision: **CHANGES_REQUESTED for the remaining R2 evidence-gate defect; live G4/G5 remain BLOCKED. W01/P0 are not complete; W02 stays unbound.**

Reviewed [worker attempt 02](../handoffs/W01-attempt-02.md) against [repair 01](W01-repair-01.md). Current next assignment: [focused repair 02](W01-repair-02.md).

## Checks actually performed

- Before any Codex status edits, the repair-01 protected baseline passed: **56 hashes, 163 local links, zero errors**, exit 0.
- Worker lock absent. Human/worker report the worker stopped; no claim of an exhaustive process audit.
- Inspected ledger/reservation code, provider execution, report gates, case builders, source identity validation, fixtures, and local artifacts.
- Ran `.local/w01/venv/Scripts/python.exe docs/execution/reviews/W01-review-02-checks.py`: exit 1 because it reproduced the remaining gate defect. It used no network or paid requests, preserved the actual provider ledger, and wrote only isolated review artifacts.
- Worker suite rerun independently with isolated outputs: **41 checks; 40 PASS, 0 FAIL, 1 SKIP** (no secret value supplied).
- Separate timeout/restart test inspected the on-disk reservation from inside a mocked transport: reservations 1, 2, 3 existed before each dispatch, spend was reserved, all three became uncertain, and a fourth call was refused after reconstructing the ledger on each iteration.
- Separate identity checks: correct sealed source accepted structurally; unrelated ID and incorrect revision rejected. Source bytes still match the manifest and anchor hash. The bundle has 78 anchors including 10 context anchors.
- Inspected the new first-page identity/footnote overlay; the located spans align with the rendered source. No new whole-document parsing or application UI work was performed.
- Actual provider ledger still contains **zero attempts**. No real response, usage, or live negative-case result exists. The review did not invoke paid inference or inspect secret values.

Evidence: `.local/reviews/W01-review-02/run-c5d8b2f4a3e2/observations.json`, its isolated suite results, and the preserved attempt-02 input snapshot.

## R1–R4 disposition

| Repair | Disposition | Scope |
|---|---|---|
| R1 reservation and failure accounting | Accepted for bounded single-worker W01 use | Independent timeout/restart proof and offline malformed-response/pricing/history regressions pass; no claim of multi-process concurrency qualification |
| R2 truthful gate derivation | **Not accepted; focused repair required** | Earlier HTTP-status/model checks improved, but artifact contents/case binding and CLI/report consistency remain insufficient |
| R3 source identity/context | Accepted for selected W01 corpus | Manifest-derived identity, citable context, positive/negative identity checks pass; this is structural grounding, not human acceptance of model semantics |
| R4 case/pricing plumbing | Accepted offline; live execution blocked | Explicit cases and validated pricing are implemented; no authenticated request has occurred |

## Remaining R2 finding — high priority

`report.py:97` trusts ledger summary flags and checks artifact existence via `_exists` at line 68; it does not parse artifacts to establish that their actual contents belong to the same case/attempt and support the claimed result.

Independent reproductions:

1. Three artifact files containing only `{}` → **G4 PASS**.
2. Response artifact says attempt 99, synthetic case, HTTP 401, while summary claims attempt 1/real source/HTTP 200 → **G4 PASS**.
3. Record itself is for the synthetic case but is submitted for real-source G4 → **PASS**.
4. `provider.passes_live_gate` accepts `finish_reason=tool_calls`, while `report.derive_case_gate` requires `stop`. The CLI can disagree with the report.

The worker's positive test `selftest.py:453` explicitly creates `{}` files and expects PASS. That test encodes the defect and must be replaced by a genuine internally consistent positive artifact bundle. Merely adding more negative status-flag tests is insufficient.

This does not mean the worker claimed a real call in this attempt. Its handoff correctly says PARTIAL. The defect matters because future stale, swapped, corrupted, or incomplete artifacts could produce false live acceptance.

## Gate outcomes

| Gate | Outcome |
|---|---|
| G1 | Supported for the submitted repair-01 baseline and local environment |
| G2 | Supported within selected source coverage |
| G3 | Supported within inspected anchors/context; not general parser accuracy |
| G4 | BLOCKED / NOT_RUN: no live real-source call; R2 additionally prevents acceptance |
| G5 | PARTIAL: local checks pass, independent R2 negatives fail, no live omission call |
| G6 | Supported as explicitly synthetic fallback, unchanged |
| G7 | Partial overall: useful current evidence exists, report gate must be repaired |

## Next action and continuity

Dispatch only [repair 02](W01-repair-02.md), using [the exact prompt](../prompts/W01-REPAIR-02.md). Preserve accepted R1/R3 work and original source/parser artifacts. Once corrected, run the two bounded live cases only if NEBIUS_API_KEY is deliberately configured in the worker process. Otherwise return partial results and the missing variable name, never a fabricated live pass.

The original and repair-01 manifests remain historical. Codex's current review/status changes are captured in [the repair-02 protected baseline](../baselines/W01-repair-02-baseline.json); do not regenerate old baselines. UI/imagegen human approval remains pending. No W02 baseline or dispatch is issued.

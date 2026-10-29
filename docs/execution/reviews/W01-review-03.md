# W01 review 03 — offline repair accepted; live evidence blocked

Date: 29 October 2026. Reviewer: Codex. Reviewed worker: attempt 03, repair 02, underlying packet revision 1.

**Decision: PARTIAL / BLOCKED_INPUT.** The offline repair is accepted after the small Codex corrections documented below. W01 and P0 are not complete. No W02 baseline, contract freeze, or future-packet dispatch is issued. The UI/imagegen approval gate remains pending.

## Protected baseline and ownership

Read [attempt 03](../handoffs/W01-attempt-03.md), [repair 02](W01-repair-02.md), and inspected the implementation and local artifacts. No worker lock was present. Before changing protected status documents, independently ran:

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-02-baseline.json
```

PASS: **62 protected hashes, 170 local links, zero errors**. Saved output: `.local/reviews/W01-review-03/repair-02-pre-review-baseline.json`. The repair-02 manifest remains unchanged historical evidence. Subsequent Codex status changes intentionally supersede its working-tree hashes; they are not worker violations.

The [review-03 snapshot](../baselines/W01-review-03-baseline.json) protects the resulting planning documents, regression checker, spike code, fixtures, and manifest. It records the offline reviewed state, not W01 completion or accepted W02 contracts. Use it explicitly for subsequent read-only verification; the original worker CLI default still names its historical repair-02 baseline.

## Independent findings and Codex corrections

The worker's common validator substantially fixes R2: artifacts are read, hash checked, confined to the provider artifact directory, bound to case/attempt/model/endpoint, and checked against pinned inputs. CLI and report share this validator.

However, the first independent run reproduced three remaining defects:

| Mutation with updated artifact hash | Before correction | Required behavior |
|---|---|---|
| Actual response content is JSON `null` | Evidence and report PASS | FAIL: no object draft to validate |
| Saved validation draft is `[]` while response draft is valid | Evidence and report PASS | FAIL: saved draft has unsupported shape |
| Response `choices` is an object instead of an array | `KeyError` | Explicit FAIL with a reason |

Initial observations: `.local/reviews/W01-review-03/run-e2c87a314842/observations.json` (**12/15 passed**). These are synthetic diagnostic fixtures, not real provider responses.

Following the agreed tiny-correction policy in [DISPATCH](../prompts/DISPATCH.md), Codex changed these files after the worker stopped:

- `spikes/w01/erratascope_w01/evidence.py`: require object drafts; validate choices/message and stored validation/input/identity shapes before accessing fields; reject unsupported shapes explicitly.
- `spikes/w01/erratascope_w01/selftest.py`: remove an early return that made the `tool_calls` branch of the non-stop-completion test unreachable.
- `spikes/w01/erratascope_w01/report.py`: replace three stale attempt-02/repair-01 headings with configured attempt metadata. The worker's actual records were attempt 03, but generated headings were misleading.

Pre-correction copies are in `.local/reviews/W01-review-03/before-codex/`. The original handoff and worker-generated public report are retained as historical evidence; the corrected generator was exercised separately against copied inputs.

## Independent verification

```powershell
.local\w01\venv\Scripts\python.exe docs/execution/reviews/W01-review-03-checks.py
```

Final result: **exit 0; 20/20 independent cases pass; worker suite 50 PASS, 0 FAIL, 1 SKIP out of 51**. The skip is the key-value leakage scan because no real key was configured. The checker deliberately clears process credentials and uses a dummy value only behind a mocked provider dispatch.

Evidence: `.local/reviews/W01-review-03/run-f02d9cd759c3/observations.json`. The persistent [checker](W01-review-03-checks.py) reruns the worker suite in an isolated directory, constructs complete positive bundles, mutates their contents, and exercises the actual CLI command function with mocked dispatch, shared evidence evaluator, and report gate. CLI exit 0 is observed only for structurally valid positive fixtures. Mock execution yields CLI exit 1 / report NOT_RUN. Invalid cases yield CLI exit 1 / report FAIL.

Coverage includes empty artifacts, wrong case/attempt, HTTP 401, replacement, non-stop completion, response/draft disagreement, null/list/scalar drafts, malformed completion shapes, invalid saved metadata shapes, real-source-shaped positive evidence, and a separate synthetic omission case. Existing worker tests cover missing/malformed/directory artifacts, model mismatch, reservation/restart accounting, identity, and omission expectations. Positive fixture branches prove local validation behavior only.

All five available manifest artifacts independently match their recorded hashes, including the real ES0620 PDF and three synthetic fixtures. ES0620 remains pinned to `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`. No new parsing or visual PDF qualification is claimed; prior selected-section G2/G3 findings are retained.

Report rendering with copied actual inputs reproduces G1/G2/G3/G6/G7 PASS, G4 NOT_RUN, G5 PARTIAL and correct attempt-03 headings. Output: `.local/reviews/W01-review-03/report-with-inputs/report.md`. A preliminary isolated render deliberately had no copied result files and produced nonpassing missing-input states; it is not the actual project gate result.

## Acceptance by gate

| Gate | Review disposition | Limit |
|---|---|---|
| G1 protected framework | PASS at worker-review boundary | New review snapshot supersedes changed Codex status files |
| G2 source and coverage | PASS, selected-section scope retained | Inventory is not complete interpretation |
| G3 evidence anchors/rendering | PASS, earlier bounded qualification retained | No general parser accuracy claim |
| G4 real-source live model draft | **NOT_RUN / BLOCKED** | No actual request/response evidence |
| G5 checks and missing-information handling | **PARTIAL** | Offline checks accepted; separate live omission case still unrun |
| G6 change fixture provenance | PASS, labeled synthetic fallback | No authentic historical manufacturer pair |
| G7 report/environment/uncertainties | PASS within spike scope | Does not prove hosted deployment or account/model access |

R1 and R3 remain accepted within their previous bounded scope. R2 is accepted offline **with the disclosed Codex corrections**, not as unchanged worker output. R4 remains accepted offline with live access unresolved.

## Remaining blocker and next action

The real `.local/w01/results/provider/ledger.json` contains **zero attempts, zero reserved requests, and US$0 reserved spend**; only blocked-preflight history exists. The provider directory contains no real request/response/validation bundle. Its hash is unchanged by independent testing. `NEBIUS_API_KEY` is absent in the current Codex process; no secret values were read or printed. No network or paid requests were made in this review.

**No further code-repair assignment is needed for the tested offline scope.** Deliberately configure `NEBIUS_API_KEY` in the process that will perform the live check. Then resume the bounded W01 real-source and synthetic-missing-revision probes, preserving the existing ledger and pricing/model configuration. Limits remain three total attempts, bounded input <=16,000 tokens, output <=8,192 tokens per request, aggregate estimated US$0.25, and no automatic retries. Missing credentials are not permission to search for another account/key.

Actual account/model access and semantic quality may still fail when tested. Codex must inspect the real artifacts and source-grounded interpretation before accepting G4/live G5. Structural PASS alone is not semantic approval. If a live probe fails, retain its reservation and artifacts and diagnose before spending another attempt.

On resume, explicitly verify the review-03 baseline. A new worker attempt, if used, requires Codex-issued attempt metadata and a scoped continuation instruction; do not restart historical repair prompts. Until real gates pass, **W02 remains PLANNED_NOT_DISPATCHABLE and unbound**. No application UI, Git publication, infrastructure, or future-packet work was started. [UI/imagegen approval](../UI_APPROVAL_GATE.md) remains pending human approval.

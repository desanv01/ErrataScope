# W01-R02 — Bind live gate outcomes to actual evidence

Date: 29 October 2026. State: **READY_TO_DISPATCH**.
This is a focused continuation of W01 revision 1 and repair 01. Do not restart W01 or redo accepted R1/R3 work.

## Preflight and ownership

Read worker rules, W01, [review 02](W01-review-02.md), and this complete assignment.

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-02-baseline.json
```

Only after PASS and no active worker lock, claim the lock. Original worker paths remain writable. Primary changes should be provider/report/shared gate helper and relevant schemas/fixtures/tests, plus minimal CLI/config/report/README updates. You may add a worker-owned shared evidence-validation module. Do not change Codex review files/checkers, `.local/reviews/**`, plans/contracts/status/baselines, previous handoffs, Git, UI, infrastructure, or W02.

Set your worker attempt metadata and baseline configuration to attempt 03/repair-02, keeping previous records intact. Do not use hard-coded previous timestamps to claim current verification. Reuse source bytes and parsing results unless a relevant defect requires recomputation.

## One required repair: a common evidence-validation path

Make CLI and report use the same verification semantics. Both must reject incomplete or inconsistent evidence, with explicit reasons. Completion requires all of the following:

1. Expected gate case equals the ledger record case; attempt is a reserved/finalized attempt from the intended ledger. Mock/cache/uncertain/failed records cannot pass a live gate.
2. Read the actual request, response, and validation JSON artifacts. An existing path, empty object, directory, malformed JSON, or unsupported shape is not evidence. Paths must be confined to intended project artifacts; do not read arbitrary account or system files.
3. Bind artifacts to the same case and attempt. Add explicit metadata where absent. Match requested model/provider, response endpoint and returned model, and recorded completion status. Record artifact hashes at creation or otherwise reliably detect replacement; do not trust only a summary flag.
4. Inspect response HTTP status and nonempty completed content. Require `finish_reason=stop` consistently in execution, CLI, and report; other reasons remain nonpassing unless Codex explicitly approves a documented provider equivalence.
5. Parse the response content and check its relationship to the saved draft/validation evidence. Recompute or verify schema/citation/identity validation against the pinned case inputs. A stored `accepted` string cannot overrule contradictory response content. A precise input/artifact manifest is sufficient; no signature service or external system is needed.
6. For the synthetic case, independently retain/evaluate its missing-information expectation. A real-source result cannot substitute for it.
7. Preserve truthful states: missing/unrun case NOT_RUN; incomplete/contradictory executed evidence FAIL; missing credentials BLOCKED; successful structural evidence is still provisional pending Codex semantic review.

Keep the scope narrow. The requirement is internally consistent, reproducible artifacts, not cryptographic proof that a malicious actor could never fabricate a network trace.

## Required regressions

Replace the current `{}`-artifact positive test with a complete internally consistent bundle. Include:

- Empty `{}` artifacts rejected.
- Malformed JSON, directories, missing artifacts rejected.
- Wrong case or attempt in either ledger or artifact rejected.
- HTTP 401 or wrong model in actual response rejected despite optimistic ledger flags.
- Response/draft/validation disagreement or post-recording artifact replacement rejected.
- Missing/empty/truncated/non-stop completion rejected by both CLI and report semantics.
- Valid complete real-source-shaped bundle passes structural checks; explicitly mock transport stays mock and cannot pass the live gate.
- Valid complete synthetic-shaped bundle requires its own passing omission expectation.
- Existing R1 timeout/restart and R3 identity regression coverage remains green.

Synthetic fixtures must remain explicitly labeled. A unit fixture may exercise a structural-positive branch, but must never be inserted into the real provider ledger or reported as a real request.

## Live evidence and budget

After the offline fix passes, if the user has deliberately configured NEBIUS_API_KEY in this worker process, run the existing real-source and synthetic-missing-revision cases. Preserve all existing reservations; at review time the actual ledger had zero attempts. Limits remain three attempts total, 16,000 bounded input tokens, 8,192 output tokens per attempt, aggregate estimated US$0.25, no automatic retries. Use the existing protected pricing evidence; do not change the model/provider silently.

If the key is absent, finish local repair and report G4/live G5 BLOCKED. Do not search for credentials, print keys, spend on another service, or infer access from the public catalog. Do not manufacture a pass to move to W02.

## Handoff

Run the focused new regressions and existing suite; record commands/exits. Recheck the repair-02 protected baseline. Write `docs/execution/handoffs/W01-attempt-03.md` with R2 before/after evidence, each W01 gate, exact live/mock status, and remaining input names. Preserve older evidence. Stop owned processes, release the worker lock, and stop editing.

Return:

> Review ErrataScope W01 repair 02, worker attempt 03. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-03.md and docs/execution/reviews/W01-repair-02.md. Verify the repair-02 protected baseline and independently test artifact-content/case binding and consistent CLI/report gates. Require actual live evidence for G4 and live G5. Record acceptance or remaining blockers; W02 stays unbound until all W01 gates pass. Preserve the UI/imagegen approval gate.

# W01 live completion â€” worker attempt 04

**Historical/superseded:** [credits are now restored](../decisions/2026-10-29-credits-restored.md). Current dispatch is [W01 live v2](../prompts/W01-LIVE-COMPLETION-V2.md), before W02. Preserve the text below as history; do not execute its old dispatch.

**SUPERSEDED FOR DISPATCH, 29 October 2026:** do not run this historical sequence. Start [W02](../prompts/W02-START.md) under [the sequencing decision](../decisions/2026-10-29-defer-live-provider.md). Codex will rebind live checks once usable access exists. Project-root .env.local is now supported; earlier environment-only instructions below are historical.

**SUPERSEDED FOR DISPATCH, 29 October 2026:** do not run this historical sequence. Start [W02](../prompts/W02-START.md) under [the sequencing decision](../decisions/2026-10-29-defer-live-provider.md). Codex will issue a fresh live continuation when usable credit/access exists. Project-root .env.local is now supported by the CLI; earlier environment-only instructions below are historical.

State: **READY_TO_DISPATCH AFTER CREDENTIAL INPUT**. This continues W01 revision 1; it is not W02 or another offline repair cycle.

## Goal and prerequisites

Produce actual provider evidence for the two remaining W01 gates: real-source interpretation (G4) and synthetic missing-revision handling (live G5). The reviewed implementation is already available. Read [review 03](../reviews/W01-review-03.md), [worker rules](../WORKER_RULES.md), and the [original W01 constraints](../packets/W01-feasibility.md). This continuation narrows write access and supersedes historical attempt numbers, baselines, and command sequences.

Required human input: `NEBIUS_API_KEY` deliberately configured in the environment inherited by DeepSeek's executing shell. Do not paste the key into a prompt, handoff, source file, or report. Do not search for it. Check only presence. If absent, stop before claiming the lock or running the sequence, and tell the human to configure that variable for the worker process and rerun this same prompt. Do not redo the offline repair or pretend W02 is ready.

## Preflight and ownership

Work in `C:\Users\Dv\Desktop\ErrataScope`. Verify:

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-live-completion-baseline.json
```

Require PASS. Confirm `docs/execution/handoffs/W01-attempt-04.md` does not already exist and no `.local/coordination/ACTIVE_WORKER.json` exists. Claim the lock exclusively as required by the worker rules, with attempt W01-attempt-04 and actual start UTC. Do not overwrite another lock. Codex has already set the three attempt/baseline metadata values in `config.py`; its evidence-window timestamp is the actual dispatch preparation time, not an invented prior execution time. Record the worker's actual start separately in its lock and handoff.

Allowed writes only:

- `.local/coordination/ACTIVE_WORKER.json`, owned by this attempt.
- `.local/w01/results/**`: command/check outputs, persistent provider ledger and actual new provider artifacts. Preserve existing attempt reservations and blocked-event history; never reset counters or reuse attempt filenames.
- `.local/w01/tmp/selftest/**`: existing suite temporary outputs, as used by the implementation.
- `.local/w01/history/attempt-03-before-04/**`: copies of prior mutable reports/results before refresh.
- `docs/evidence/W01/ENVIRONMENT.json` and `docs/evidence/W01/FEASIBILITY_REPORT.md`: measured, redacted refreshes.
- `docs/execution/handoffs/W01-attempt-04.md`: new handoff.

All spike code, fixtures, manifest, plans, contracts, review checkers, baselines, existing handoffs, `.local/reviews/**`, and other paths are protected. No code repair, dependency install, source download/reparse, Git operation, UI, deployment, or W02 work. If a code defect prevents completion, preserve its evidence and return for Codex diagnosis; do not edit protected code to force success.

## Execution sequence

Before refresh, copy existing top-level result JSON files and the two public evidence files into the allowed history folder. Do not copy credentials or environment variables. Record commands and actual exit codes in the handoff.

Use the existing interpreter:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-completion-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
```

Run sequentially, inspecting each exit. A failed required offline check blocks paid dispatch. Do not run the Codex review checker; it writes to Codex-owned review paths. Reuse accepted source bytes, anchors, and coverage. Inspect only the existing provider ledger and protected pricing evidence to confirm remaining budget and no prior successful completion of these cases. At issuance the real ledger has zero reservations; do not assume that is still true if rerunning.

Then run exactly one real-source case:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source
```

If it fails, is uncertain, or does not pass the structural evidence check, stop further paid requests and report the actual cause. Do not retry or change model/provider/settings. If it succeeds structurally and budget remains, run the separate negative case once:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
```

Limits remain **three total reserved attempts across W01, <=16,000 bounded input tokens and <=8,192 output tokens per request, estimated aggregate <=US$0.25**, preserving the configured model/endpoint/pricing. This continuation authorizes at most these two new requests; any third request requires Codex diagnosis and a continuation decision. No automatic retries. Timeouts consume reservations. No other inference service or promotional-code redemption.

After live success or failure, preserve artifacts, run `self-test` once more to exercise the configured-key leakage scan against the newly generated evidence, recheck the baseline with the explicit command above, then run:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
```

Inspect the redacted report and handoff for secrets before finishing. Do not print matching secret values. If exposure is detected, stop external publication and report the affected paths privately without reproducing the value. Missing usage stays unknown, not zero. A successful synthetic model call is live provider evidence using synthetic source material, not a real manufacturer observation.

## Handoff and return

Write attempt 04 with actual start/end, paths, command exits, request IDs where available, case/attempt bindings, model/finish status, token usage or unknown, reserved/estimated cost, each gate result, and failed or skipped checks. Point to raw private artifacts without copying full payloads to public docs. Include a short source-versus-draft checklist and possible interpretation issues for Codex; do not claim semantic acceptance yourself.

Verify protected baseline again. Stop owned processes, release only your lock, and stop editing. Return this exact prompt:

> Review ErrataScope W01 live completion, worker attempt 04. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-04.md and docs/execution/continuations/W01-live-completion.md. Verify its protected baseline, actual provider ledger and both case-bound artifact bundles; independently check source-grounded semantics, omission behavior, CLI/report gates, budget accounting, and secret handling. Do not infer live success from mocks. If every W01 gate passes, accept W01/P0, perform the appropriate Git/GitHub checkpoint under docs/execution/COMPLETION_PROTOCOL.md, bind W02 to accepted contracts and code, and give me its exact DeepSeek prompt. Otherwise record one concrete next action and its prompt. Preserve the UI/imagegen approval gate.

# W01 live completion v4 — worker attempt 06

State: **READY_TO_DISPATCH — approved count amendment activated.** The previous v3 prompt is spent/superseded. Never reuse it.

## Activation prerequisite — Codex only

The user approved four lifetime requests with the $0.25 cap unchanged. Codex activated [the amendment](../decisions/2026-10-29-w01-four-request-cap.md) and [audit record](../decisions/W01-v4-activation.json). Both failed attempts remain counted; the 16,000 input/8,192 output limits remain unchanged. Use [the live-v4 baseline](../baselines/W01-live-v4-baseline.json). Worker metadata is attempt 06. No worker may change the caps or redo activation. Starting ledger SHA-256: `740f98edc8583075c6c58c5dd5c774a2c9047ff32e52762f93102d136cfe8617`.

## Worker scope after activation

Single worker in `C:\Users\Dv\Desktop\ErrataScope`. Read current STATUS, review 05, this assignment and WORKER_RULES. No existing active lock, attempt-06 handoff or `attempt-05-before-06` history directory may be present. Stop if any exists. Require key CONFIGURED and active baseline PASS, then claim your exclusive lock with actual UTC and owned paths.

Only writable paths: own `.local/coordination/ACTIVE_WORKER.json`; CLI-generated `.local/w01/results/**` with append-only provider history; `.local/w01/tmp/selftest/**`; `.local/config-tests/**`; new `.local/w01/history/attempt-05-before-06/**`; the two public W01 evidence files ENVIRONMENT.json and FEASIBILITY_REPORT.md; new `docs/execution/handoffs/W01-attempt-06.md`.

All code, prompt files, fixtures, source bytes/manifests/anchors/coverage/matrix/renders, baselines, plans/contracts/reviews, prior handoffs and credential files are read-only. No source downloads/reparse, installs, Git mutation, UI, infrastructure, W02, model switching or code repair.

Back up top-level results JSON, both public evidence files, provider ledger and all five existing request/response/validation artifacts before refreshing anything. Write a manifest of relative paths, byte sizes and hashes; verify the copies. Never overwrite history. Preserve provider attempts 1 and 2 and all old blocked events. Starting ledger must match Codex's activation record, contain exactly two reservations with outcomes empty and schema_invalid, spend $0.0200484, and no synthetic attempts. Any difference means stop for review, not a fresh reservation.

## Offline preflight

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.local\w01\venv\Scripts\python.exe spikes/w01/run.py check-key
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-live-v4-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-v4-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe -m unittest discover -s spikes/w01/tests -v
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
```

Inspect all exit codes. Require all 11 unit tests and assigned local self-tests to pass, including configured-key scanning. The CLI loads only the designated .env.local key with process-environment precedence. Never display the value or open/print the credential file. Do not run review checkers writing `.local/reviews`.

## Paid execution after passing preflight

Use the already corrected `draft-v4-grounded-no-thinking` request, same `nvidia/Nemotron-3.5-Super-VL` endpoint/model/pricing, text-only anchors and unchanged strict schema. Reasoning remains explicitly disabled. Do not reuse/relabel a cached answer as a new live response.

1. Run exactly one corrected real-source call, global reservation 3:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source
```

2. If nonpassing, timeout, uncertain, empty, truncated or invalid, stop paid execution immediately. Preserve reservation 4 unused. No retries.
3. If structurally passing, inspect the final draft privately against the anchor text. Stop paid execution if the obvious review-05 errors recur: workaround labeled exception, example address made mandatory, empty/unrelated citations or invented identity/revision. Record this semantic failure even if the CLI structurally passed; do not edit the draft, ledger, validator or reported structural evidence.
4. Only after the real-source result is structurally passing with no identified semantic blocker, run exactly one synthetic omission call, global reservation 4:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
```

Stop after this call regardless of outcome. At most two new calls, four total lifetime reservations after approval, $0.25 aggregate bound. Unknown usage is unknown, not zero. No exploratory calls, fifth request, cap changes, provider/model fallback or automatic retry. All used/uncertain reservations remain counted.

## Final checks and return

After success or failure:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-v4-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
```

Keep structural gate results distinct from provisional semantic findings. Verify all old artifact hashes and old ledger attempt records/events unchanged. Handoff must record actual commands/exits/times, provider attempt IDs, request mode, finish/reasoning/final-content metadata, input/output usage and cost estimates, reservations remaining, G1–G7, any structural-pass/semantic-fail distinction, and cited-source checklist. Missing information may be listed only in unresolved_fields; this is valid and does not require invented citations. Synthetic source identity/revision must remain null and unresolved. No acceptance declaration.

Write the new handoff, verify baseline again, stop owned processes, release only your lock, stop editing and return:

> Review ErrataScope W01 live completion v4, worker attempt 06. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-06.md, docs/execution/reviews/W01-review-05.md and docs/execution/continuations/W01-live-completion-v4.md. Verify the activated live-v4 baseline and approved count-cap amendment without resetting lifetime reservations. Independently check all new actual provider artifacts and preserved attempts 1–2, source-grounded semantics (especially unknown fields, workaround versus exception and optional/example versus mandatory details), live omission behavior, CLI/report gates, budget and secrets. Mocks and edited cached outputs are not live success. If all required gates pass, accept W01/P0, freeze observed contracts, perform the Git/GitHub checkpoint, rebind W02 revision 2 and give its exact DeepSeek prompt. Otherwise issue one consolidated repair/continuation with a concrete next action. Preserve the UI/imagegen approval gate.

# W01 live completion v2 — attempt 04

State: **READY_TO_DISPATCH AFTER KEY CONFIGURATION**. Credits restored; this is the current assignment. The earlier W01 live prompt and temporary W02 dispatch are superseded. Read [the latest decision](../decisions/2026-10-29-credits-restored.md), [review 03](../reviews/W01-review-03.md), [worker rules](../WORKER_RULES.md), and the original W01 constraints. No worker has used attempt 04 yet.

## Preflight

Work in `C:\Users\Dv\Desktop\ErrataScope`. The human may deliberately configure root `.env.local` with NEBIUS_API_KEY; the reviewed CLI loads it explicitly. Never open/cat that file or dump environment values. Run only the presence check:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py check-key
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-live-v2-baseline.json
```

Require CONFIGURED and baseline PASS. Missing key means report the exact missing input and stop without network or repeating repair work. Check that no worker lock or attempt-04 handoff exists. Claim the lock exclusively, recording actual start UTC and owned paths. Do not delete another lock. Codex has set metadata to W01-attempt-04 and the current baseline; the configured evidence-window timestamp is dispatch preparation time, not a claim of completed execution.

## Ownership

Only write `.local/coordination/ACTIVE_WORKER.json` (own lock), `.local/w01/results/**`, `.local/w01/tmp/selftest/**`, `.local/w01/history/attempt-03-before-04/**`, `docs/evidence/W01/ENVIRONMENT.json`, `docs/evidence/W01/FEASIBILITY_REPORT.md`, and new `docs/execution/handoffs/W01-attempt-04.md`. Set PYTHONDONTWRITEBYTECODE=1 to avoid incidental protected-code writes.

All code, fixtures, source manifest, documents/anchors, baselines, plans/contracts, Codex review paths/checkers, existing handoffs, and credential files are read-only. No source re-download/reparse, package install, Git, UI, hosting, W02 or code repair. If execution exposes a code or model-compatibility issue, preserve evidence and return it; do not weaken the gate or edit code.

## Execute

Copy current top-level results JSON and the two public evidence files into the allowed history folder before refreshing them, preserving previous reports. Never overwrite existing history; if the folder already exists, stop for Codex to determine whether this attempt already started. The real provider ledger is persistent: do not reset attempts, reservations, blocked events or pricing history.

Run sequentially and inspect every exit:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-v2-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
```

Only after required local checks pass, inspect ledger counters and protected pricing evidence, then run one real-source call:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source
```

If failed/uncertain/nonpassing, stop paid execution and preserve the cause. If structurally passing and budget remains, run one separate live synthetic case:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
```

Keep model `nvidia/Nemotron-3.5-Super-VL`, the configured endpoint and protected text pricing. Maximum two new calls in this continuation. W01 lifetime limits: three reserved attempts total, <=16,000 bounded input and <=8,192 output tokens per request, <=US$0.25 estimated aggregate. No automatic retries, image calls, alternate models/services or account operations. Timeouts count. A third request needs a Codex diagnosis/continuation; do not spend it reflexively.

After success or failure, rerun self-test to scan new artifacts with the configured key, then verify baseline and generate report. Manually inspect only public reports for accidental exposure; never print a suspected secret. Do not run Codex review checkers that write `.local/reviews`.

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-v2-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
```

Run the public-evidence secret check again after report generation (self-test) so the newly rendered report is covered. Record that final result in the handoff; no further report rewrite is needed unless it found a problem. Report missing usage as unknown, not zero. Synthetic source plus actual API response is a live synthetic-input test; no manufacturer observation is claimed from it.

## Finish and return

Write attempt 04 with actual times, paths, commands/exits, G1-G7 results, each provider case/attempt/model/finish/validation outcome, request IDs if available, token usage/estimated cost/remaining reservations, and a concise source-versus-draft review checklist. Point to private raw artifacts; do not copy full payloads or secrets to public evidence. Structural success is provisional pending Codex semantic review.

Verify baseline once more, stop owned processes, release only your lock, stop editing and return:

> Review ErrataScope W01 live completion v2, worker attempt 04. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-04.md and docs/execution/continuations/W01-live-completion-v2.md. Verify the live-v2 protected baseline, actual provider ledger and both case-bound artifact bundles. Independently check source-grounded semantics, omission behavior, CLI/report gates, budget accounting and secret handling; mocks are not live success. If all W01 gates pass, accept W01/P0, perform the Git/GitHub checkpoint under docs/execution/COMPLETION_PROTOCOL.md, rebind the already prepared W02 revision 2 to the accepted state, and give me its exact DeepSeek prompt. Otherwise provide one consolidated repair/continuation prompt with the concrete next action. Preserve the UI/imagegen approval gate.

# W01 live completion v3 — worker attempt 05

State: **READY_TO_DISPATCH**. This supersedes live completion v2/attempt 04. Read [review 04](../reviews/W01-review-04.md), [worker rules](../WORKER_RULES.md), and [W01 constraints](../packets/W01-feasibility.md). This assignment is execution only; Codex already corrected request mode and stale report prose.

## Preflight and exclusive ownership

Work in `C:\Users\Dv\Desktop\ErrataScope`. Require no active worker lock, no attempt-05 handoff, and no `.local/w01/history/attempt-04-before-05` directory. If any exists, stop and report possible prior execution; never clear it or restart calls automatically. Set PYTHONDONTWRITEBYTECODE=1. Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.local\w01\venv\Scripts\python.exe spikes/w01/run.py check-key
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-live-v3-baseline.json
```

Require CONFIGURED and PASS. The CLI explicitly loads the root `.env.local` key, with process environment precedence. Never print/open the credential file, dump variables or expose the value. No need to reconfigure a working key. Claim `.local/coordination/ACTIVE_WORKER.json` exclusively with actual UTC, worker attempt and writable paths.

Only writable paths:

- Your own lock.
- `.local/w01/results/**` for CLI-produced records and new artifacts; existing provider attempt records/artifacts are append-only history, never altered or deleted. Ledger changes may only append reservations/events or finalize the newly reserved attempts through the reviewed CLI.
- `.local/w01/tmp/selftest/**` and `.local/config-tests/**` for isolated tests.
- New `.local/w01/history/attempt-04-before-05/**` backup.
- `docs/evidence/W01/ENVIRONMENT.json`, `docs/evidence/W01/FEASIBILITY_REPORT.md`.
- New `docs/execution/handoffs/W01-attempt-05.md`.

All code, test files, prompts, schemas, source manifest, anchors, coverage, revision matrix, renders, existing handoffs/reviews, baselines, contracts, plans and credential files are read-only. No downloads, reparsing, dependency installs, Git mutation, UI, infrastructure or W02. A failure means preserve evidence and return; do not edit code to make the gate pass.

## Preserve previous evidence

Before refreshing outputs, copy current top-level results JSON and both public evidence files into the new history directory, with original relative locations, byte counts and SHA-256 manifest. Include a separate backup of the current provider ledger and attempt-01 request/response artifacts. Never overwrite an existing history directory. Verify copied bytes match originals. Historical worker-04 report must remain available even though its stale missing-key explanation is corrected by the next report.

Before any network call require the actual ledger to have exactly one reservation, attempt 1, case real_source, outcome empty, reserved total $0.0100242, and no synthetic attempts. Its starting SHA-256 must be `dededd2eed47dedb187f51b172ebdddb820e6661fa255a57d898be533e6231ca`. If counters/history differ, stop rather than spending an uncertain remaining attempt. Verify request/response against their recorded hashes; do not print payloads.

## Offline preflight

Run sequentially, inspecting each exit code:

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-v3-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py inspect-env
.local\w01\venv\Scripts\python.exe -m unittest discover -s spikes/w01/tests -v
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
```

Require all nine unit tests and all required local self-tests to pass, including configured-key scan. Mock tests prove local request wiring only. Do not run Codex checkers that write `.local/reviews`.

The request builder now sends `chat_template_kwargs: {enable_thinking: false}` with mode `draft-v3-no-thinking` in local metadata. That field is top-level HTTP JSON, not a nested `extra_body` wrapper. The prompt content remains in the draft-v2 files. No need to add an SDK or change prompts. Hosted behavior remains to be measured.

## Two bounded live cases, sequentially

Keep exact model `nvidia/Nemotron-3.5-Super-VL`, existing Nebius endpoint, protected text prices and text-only inputs. Lifetime W01 limits remain three reservations total, <=16,000 bounded input and <=8,192 output tokens per call, <=$0.25 aggregate reserved estimate. Only two reservations remain; this assignment authorizes at most those two, not two plus retries. No automatic retries, exploratory model-list/chat calls, route switches, fallback providers, output cap increases, resets or ledger edits.

First run one real-source request (expected global provider attempt 2):

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case real-source
```

If it fails, times out, is uncertain, truncated, empty, structurally invalid or unsupported: stop paid execution immediately, keep attempt 3 unused, finish the report and handoff. Do not reinterpret reasoning_content as final JSON. Do not retry even if the HTTP status is 400 or the account shows plenty of credit.

Only if the CLI returns success with actual case-bound response and validation artifacts, complete non-truncated final content and correct model binding, run the separate synthetic omission case (expected global provider attempt 3):

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py probe-provider --case synthetic-missing-revision
```

Stop paid execution after this call regardless of outcome. Inspect response metadata privately for finish_reason, final-content presence, reasoning-token count if supplied, usage and request ID. Record unavailable metrics as unknown, never zero. A response succeeding with final content demonstrates this request's usable output; do not claim the hosted reasoning toggle worked unless evidence supports it.

## Finish after success or failure

```powershell
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
.local\w01\venv\Scripts\python.exe spikes/w01/run.py verify-baseline --baseline docs/execution/baselines/W01-live-v3-baseline.json
.local\w01\venv\Scripts\python.exe spikes/w01/run.py report
.local\w01\venv\Scripts\python.exe spikes/w01/run.py self-test
```

Preserve failures and actual exit codes. The final self-test scans the newly generated report. Require unchanged attempt-01 artifact hashes and ledger record, all prior blocked events retained, and no baseline drift. For each generated draft, provide a concise provisional checklist of source identity versus silicon revision, cited section/row/header/legend anchors, affected-revision mapping, and unknowns. Synthetic identity/revision must remain unresolved. Worker inspection does not declare acceptance; Codex independently judges semantics.

Write the new handoff with times, commands/exits, gate results, global provider attempt numbers, request mode, finish/model/validation outcomes, source-versus-draft checklist, usage/cost estimates, reservation totals and exact remaining blockers. Link local raw artifacts; do not copy raw payloads or credentials into public evidence. No worker Git actions or acceptance claims.

Verify the framework baseline once more, stop owned processes, release only your lock, stop editing and return this exact prompt:

> Review ErrataScope W01 live completion v3, worker attempt 05. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-05.md, docs/execution/reviews/W01-review-04.md and docs/execution/continuations/W01-live-completion-v3.md. Verify the live-v3 protected baseline, preserved provider attempt 1 and all new case-bound artifacts. Independently check actual request-mode behavior, source-grounded semantics, omission behavior, CLI/report gates, budget accounting and secret handling; mocks are not live success. If all W01 gates pass, accept W01/P0, perform the Git/GitHub checkpoint under docs/execution/COMPLETION_PROTOCOL.md, freeze observed contracts, rebind the prepared W02 revision 2 and give me its exact DeepSeek prompt. Otherwise provide one consolidated repair/continuation with the concrete next action; never reset the lifetime budget. Preserve the UI/imagegen approval gate.

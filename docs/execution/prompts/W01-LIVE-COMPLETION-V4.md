# Exact DeepSeek prompt — W01 attempt 06

**READY_TO_DISPATCH.** The user approved four lifetime requests and Codex activated [the amendment](../decisions/2026-10-29-w01-four-request-cap.md). Use only this prompt; v3 is superseded.

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W01 live-completion worker, attempt 06.

Read and follow:
docs/execution/STATUS.md
docs/execution/reviews/W01-review-05.md
docs/execution/continuations/W01-live-completion-v4.md
docs/execution/WORKER_RULES.md
docs/execution/decisions/2026-10-29-w01-four-request-cap.md
docs/execution/decisions/W01-v4-activation.json

First require Codex's recorded count-cap approval/activation and the frozen live-v4 baseline. If these are absent or still pending, stop without a provider request. Never activate the amendment yourself.

Codex has already corrected the prompt. Missing fields go in unresolved_fields without unsupported claims; every emitted claim still needs relevant citations. Keep workaround and exception distinct, and preserve optional/example versus mandatory details. Do not change code, schema, prompts or source inputs.

Check key presence only; the CLI loads project-root .env.local. Never print the key or credential file. Verify the protected baseline, absence of an active worker/attempt-06 handoff/history folder, and exact starting ledger against the activation record. Claim the worker lock, back up current evidence and run the prescribed offline preflight.

Execute one corrected real-source call as global attempt 3. If it fails structurally, is uncertain, or clearly repeats the semantic defects identified in review 05, stop paid execution and preserve the remaining reservation. Only after a passing real-source result without an identified semantic blocker, execute the separate synthetic omission call as global attempt 4.

At most TWO new requests under the approved FOUR lifetime reservation cap; keep the $0.25 aggregate spending cap and both historical attempts counted. No automatic retries, exploratory calls, model fallback, cap changes or budget reset. Preserve all old artifacts and ledger history.

After success or failure, complete the assignment's final checks, report and secret scan. Write docs/execution/handoffs/W01-attempt-06.md with actual outcomes and remaining blockers. Distinguish structural gate results from semantic findings. No acceptance claim, Git mutation, UI, infrastructure or W02 work. Preserve the human UI/imagegen approval gate.

Recheck the baseline, stop owned processes, release only your lock, stop editing and return the exact Codex review prompt in the continuation assignment.
```

# Exact DeepSeek prompt â€” finish W01 live evidence

**Historical/superseded:** [credits are now restored](../decisions/2026-10-29-credits-restored.md). Current dispatch is [W01 live v2](../prompts/W01-LIVE-COMPLETION-V2.md), before W02. Preserve the text below as history; do not execute its old dispatch.

**SUPERSEDED FOR DISPATCH, 29 October 2026:** do not run this historical sequence. Start [W02](../prompts/W02-START.md) under [the sequencing decision](../decisions/2026-10-29-defer-live-provider.md). Codex will rebind live checks once usable access exists. Project-root .env.local is now supported; earlier environment-only instructions below are historical.

**SUPERSEDED FOR DISPATCH, 29 October 2026:** do not run this historical sequence. Start [W02](../prompts/W02-START.md) under [the sequencing decision](../decisions/2026-10-29-defer-live-provider.md). Codex will issue a fresh live continuation when usable credit/access exists. Project-root .env.local is now supported by the CLI; earlier environment-only instructions below are historical.

Paste the following into DeepSeek after configuring `NEBIUS_API_KEY` in the environment its executing shell inherits. It does not automatically load a `.env` file. Never paste the key into this prompt.

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W01 live-completion worker, attempt 04.

Read docs/execution/START_HERE.md, docs/execution/WORKER_RULES.md, docs/execution/STATUS.md, docs/execution/reviews/W01-review-03.md, and the complete docs/execution/continuations/W01-live-completion.md. Follow that continuation exactly; it supersedes historical dispatch instructions.

First check only whether NEBIUS_API_KEY is present in your executing process. Never print its value or search for credentials. If absent, stop and tell me to configure it for your process; do not redo repairs or start W02.

Verify docs/execution/baselines/W01-live-completion-baseline.json with scripts/verify_execution_framework.py. After PASS, confirm no worker lock or attempt-04 handoff exists, then claim the exclusive worker lock.

This is execution only: preserve the accepted code, source/anchor artifacts, fixtures, and all ledger history. Run the specified offline preflight, then one real-source probe and, only if it succeeds, one synthetic-missing-revision probe. Preserve the three-total-attempt/$0.25 cap; no retries or substitutions. If any required check fails, preserve evidence and return the blocker; do not edit code.

Refresh the permitted redacted evidence, rerun the specified secret/local checks and protected baseline verification, write docs/execution/handoffs/W01-attempt-04.md, stop owned processes, release your lock, and stop editing. No Git, UI, infrastructure, or future-packet work.

Return the exact Codex review prompt at the end of the continuation assignment. Do not claim acceptance yourself.
```

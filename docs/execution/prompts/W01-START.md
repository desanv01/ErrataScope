# Exact prompt — start W01 in DeepSeek

Paste the block below into one DeepSeek worker chat whose project folder is `C:\Users\Dv\Desktop\ErrataScope`.

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single implementation worker for ErrataScope packet W01 revision 1.

Read docs/execution/START_HERE.md, docs/execution/WORKER_RULES.md, docs/execution/STATUS.md, and the complete docs/execution/packets/W01-feasibility.md. Read the contracts and P0 document that W01 lists.

Verify the protected baseline with:
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json

If verification fails or another worker lock exists, stop and report the exact issue without changing protected files. Otherwise claim the packet's exclusive advisory lock and execute W01 completely within its allowed paths.

Build the narrow source/parser/provider feasibility spike, not the full application. Follow the packet's source provenance, anchor-coordinate, isolated-environment, model-call budget, and local-test requirements. Use only deliberately supplied project credentials; never search other folders or accounts for keys and never print secret values. If NEBIUS_API_KEY is absent, finish all independent local/source/parser work and report the live-provider gate as blocked; do not substitute mock output for a real call.

Do not modify plans/contracts/status/baselines, perform Git mutations, provision infrastructure, start UI implementation, or proceed to W02. UI/UX requires the human's approval of Codex-generated imagegen mockups first. Source-page renders for parsing evidence are permitted.

Run the specified checks, fix in-scope failures, and record actual commands, exit codes, artifacts, live/mock distinctions, and unresolved gates. Write the next unused docs/execution/handoffs/W01-attempt-NN.md using the handoff template. Recheck the protected baseline, stop owned background processes, release your own worker lock, and stop editing.

Your final response must state READY_FOR_REVIEW, PARTIAL, or BLOCKED; give the handoff path; summarize required missing input by variable/file name only; and provide the exact Codex review prompt from W01 with the actual attempt path. Do not claim Codex acceptance or start another packet.
```

## Credential note

The live-provider gate needs NEBIUS_API_KEY deliberately configured in the DeepSeek process/environment. Do not paste its value into the prompt or chat. Missing credentials do not prevent the assigned independent work; the worker must report the remaining live gate honestly.


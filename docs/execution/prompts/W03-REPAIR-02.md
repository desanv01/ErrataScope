# DeepSeek prompt — W03 repair 02, attempt 03

Paste the following into the single DeepSeek worker:

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W03 revision-2 repair-02 worker, attempt 03. The preceding worker has stopped; W03 is not accepted.

Read and execute:
docs/execution/reviews/W03-review-02.md
docs/execution/reviews/W03-repair-02.md
docs/execution/packets/W03-persistence-jobs.md
docs/execution/bindings/W03-foundation-v1.md
docs/execution/WORKER_RULES.md

Before edits, verify docs/execution/baselines/W03-repair-02-baseline.json with scripts/verify_execution_framework.py and all hashes in docs/execution/reviews/W03-attempt-02-inventory.json. Claim your lock exclusively and create the verified attempt-02-before-03 backup specified in the assignment.

Do not run the old default test/reconciler setup: its shared artifact volume can delete application files. Implement R1 storage isolation/ownership first, then R2 staging/GC/finalization fencing and R3 exact path/no-symlink safety. Retain the passing authorization, API, idempotency and acknowledgement-loss fixes. Use real local PostgreSQL/Valkey/API/storage and preserve accepted W01/W02 code/evidence, existing volumes, historical results and applied migrations 0001/0002. Record existing missing artifacts honestly; never manufacture replacement evidence.

Follow the complete assignment's regressions, sentinel check and attempt-03 recovery evidence requirements. No provider calls, credentials/.env.local access, package changes, hosted provisioning, Git actions, UI or W04 work. UI/imagegen approval remains pending. Do not delegate or change protected contracts/reviews/status.

Recheck the protected baseline. Write docs/execution/handoffs/W03-attempt-03.md with actual commands/results and any remaining blockers. Stop owned resources, release your lock and stop editing. Return the exact Codex review prompt from the repair assignment. Do not declare acceptance.
```

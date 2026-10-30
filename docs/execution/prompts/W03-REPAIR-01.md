# DeepSeek dispatch — W03 repair 01, attempt 02

~~~text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W03 revision 2 repair-01 worker, attempt 02.

Read and follow:
docs/execution/reviews/W03-repair-01.md
docs/execution/reviews/W03-review-01.md
docs/execution/packets/W03-persistence-jobs.md
docs/execution/bindings/W03-foundation-v1.md
docs/execution/WORKER_RULES.md

The repair assignment supersedes attempt 01's dispatch instructions. Verify docs/execution/baselines/W03-repair-01-baseline.json and every starting hash in docs/execution/reviews/W03-attempt-01-inventory.json before edits. Stop on mismatch or an active worker lock. Claim your lock exclusively and create the required verified history backup.

Repair R1–R4 together:
R1: Current authorization before every idempotent replay and correct privilege boundaries.
R2: Bound membership/project routes, nested errors, server request IDs and bounded pagination.
R3: Streaming staging, short transactions and safe orphan reconciliation.
R4: Preserve committed receipt bytes on ambiguous commit acknowledgement; complete heartbeat, attempt/cancellation and outbox fencing with real recovery tests.

Keep the pinned dependencies and isolated erratascope-w03 stack. Preserve existing volumes and examples. Add a new migration if needed; do not rewrite already-applied 0001 or reset volumes. Keep accepted domain code/tests, W01/W02 evidence and protected documents unchanged.

Run the required actual PostgreSQL/Valkey/API/storage tests, 92 accepted domain tests, connected flow and recovery matrix. No mocked-persistence or skipped-service acceptance. Update evidence and OpenAPI truthfully.

No Nebius calls, .env.local access, hosted provisioning/deployment, Git, UI or W04 implementation. Hosted P2 and UI/imagegen approval remain pending.

Recheck the repair baseline. Write docs/execution/handoffs/W03-attempt-02.md with actual R1–R4 results, commands/exits and remaining limitations. Stop owned services/jobs while preserving volumes, release your lock and stop editing.

Return the exact Codex review prompt from the repair assignment. Do not declare acceptance or start another packet.
~~~

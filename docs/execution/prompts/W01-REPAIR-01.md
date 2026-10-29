# Exact DeepSeek repair prompt

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single worker for W01 repair 01.

Read docs/execution/START_HERE.md, docs/execution/WORKER_RULES.md, docs/execution/STATUS.md, docs/execution/packets/W01-feasibility.md, docs/execution/reviews/W01-review-01.md, and the complete docs/execution/reviews/W01-repair-01.md. Follow the repair instructions where they explicitly update the original packet.

Verify the new repair baseline, not the historical initial baseline:
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-01-baseline.json

If valid and no worker lock exists, claim the lock and repair R1–R4 within the original writable paths. Preserve the source/parser work. Fix request reservations and uncertain outcomes, evidence-derived gates, source identity/citation consistency, and explicit real-source/negative-case execution. Use the Codex pricing evidence through a validated configuration path. Run offline regression checks before any paid probe; retain the original three-request/$0.25 limits across attempts.

Use only NEBIUS_API_KEY deliberately supplied to your process; never print it or search for credentials. If it is absent, finish all independent repairs and report live gates blocked. Never substitute mocks for live success.

Do not edit Codex reviews/checkers, plans/contracts/status/baselines, or attempt-01 handoff. Do not perform Git actions, UI work, infrastructure provisioning, or W02 work.

Write docs/execution/handoffs/W01-attempt-02.md with actual checks, gate evidence, and remaining blockers. Recheck the repair baseline, stop owned processes, release your lock, stop editing, and return the exact Codex review prompt from the repair assignment.
```

# Exact DeepSeek prompt — W01 repair 02

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W01 repair-02 worker.

Read docs/execution/START_HERE.md, docs/execution/WORKER_RULES.md, docs/execution/STATUS.md, docs/execution/reviews/W01-review-02.md, and the complete docs/execution/reviews/W01-repair-02.md. Follow the original W01 constraints except where this repair explicitly updates them.

Preflight:
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-02-baseline.json

After PASS and confirming no active worker lock, claim the lock. Preserve accepted R1/R3 and source/parser work. Repair the remaining R2 defect: CLI/report must inspect and bind actual request/response/validation contents to the same case, attempt, model, and completed response. Empty or contradictory artifacts must fail. Replace the empty-artifact positive test with a genuine consistent fixture and run all specified regressions.

Do not modify Codex reviews/checkers, plans/contracts/status/baselines, old handoffs, or .local/reviews. No Git, UI, infrastructure, or W02 work.

Run paid cases only after offline checks pass and only if NEBIUS_API_KEY was deliberately supplied to your process. Preserve the three-request/$0.25 limits and all reservations. Never print or search for keys. If absent, finish the repair and report live gates blocked.

Write docs/execution/handoffs/W01-attempt-03.md with actual evidence and gate results. Recheck the repair-02 baseline, stop owned processes, release your lock, stop editing, and return the exact Codex review prompt from the repair assignment.
```

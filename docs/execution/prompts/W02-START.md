> Historical W02 assignment; W02 is accepted. Current dispatch: [W03](W03-START.md).

> Historical attempt-01 prompt. Current dispatch is [W02 repair 01, attempt 02](W02-REPAIR-01.md); do not rerun this initial assignment.

# Exact DeepSeek prompt — W02 revision 2

**READY_TO_DISPATCH:** W01/P0 accepted, including actual live G4/G5 and semantic review. Use the freshly bound W02 baseline.


```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single implementation worker for W02 revision 2, attempt W02-attempt-01.

Read docs/execution/START_HERE.md, docs/execution/WORKER_RULES.md, docs/execution/STATUS.md, docs/execution/reviews/W01-review-06.md, docs/execution/bindings/W01-observed-contracts.md, the complete docs/execution/packets/W02-domain-core.md, and docs/execution/bindings/W02-domain-v1.md plus the shared contracts named there.

Codex has accepted W01 including live G4/G5 and issued the fresh W02 baseline. No Nebius key, credit, network, or model call is needed. Do not run the historical W01 live-completion prompt or inspect .env.local.

Run:
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W02-baseline.json

After PASS, confirm no active worker lock or W02-attempt-01 handoff exists, then claim the exclusive worker lock. Implement the complete bound domain package, strict contracts, scope resolution, three-valued evaluator, full traces/dependencies, canonical hashes, offline replay CLI, and meaningful synthetic fixtures/tests in the specified writable paths.

Use the existing Python/Pydantic runtime and exact check commands in the packet. Do not edit protected files, weaken semantic requirements, install packages, perform Git actions, build application UI, deploy, or start W03. Fix in-scope implementation failures before handing back.

Write docs/evidence/W02/IMPLEMENTATION_REPORT.md and docs/execution/handoffs/W02-attempt-01.md with actual checks/results. Reverify the protected baseline, stop owned processes, release your lock, stop editing, and return the packet's exact Codex review prompt.
```

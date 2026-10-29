> Historical W02 assignment; W02 is accepted. Current dispatch: [W03](W03-START.md).

# DeepSeek dispatch — W02 repair 01, attempt 02

Paste the following into the single DeepSeek worker:

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W02 revision 2 repair-01 worker, attempt 02.

Read and follow:
docs/execution/reviews/W02-repair-01.md
docs/execution/reviews/W02-review-01.md
docs/execution/packets/W02-domain-core.md
docs/execution/bindings/W02-domain-v1.md
docs/execution/WORKER_RULES.md

The repair assignment supersedes attempt 01's start instructions. Verify docs/execution/baselines/W02-repair-01-baseline.json and every starting file hash in docs/execution/reviews/W02-attempt-01-inventory.json before any edits. Stop on mismatch or an active worker lock. Claim your lock exclusively and create the required verified backup.

Repair R1–R4 together: required explicit-null contracts and full validation at evaluate; complete component-project and evidence-reference checks; the 512-node aggregate per-rule cap before recursive parsing; and selector-registry/decimal grammar consistency. Preserve the passing evaluator, dependencies, replay behavior and all W01 evidence. Add meaningful regression tests and regenerate exported schemas/registry. Do not weaken the protected binding or review expectations.

Use only the assignment's writable paths and existing pinned Python/Pydantic environment. No credentials, provider calls, network, package installation, Git, UI, deployment or W03 work. Do not modify or run the Codex review checker that writes under .local/reviews; reproduce its relevant cases in your owned tests.

Run the required offline checks, update docs/evidence/W02/IMPLEMENTATION_REPORT.md truthfully, and recheck the repair protected baseline. Write docs/execution/handoffs/W02-attempt-02.md with actual R1–R4 evidence and any remaining failures. Stop owned jobs, release your lock and stop editing.

Return the exact Codex review prompt at the end of the repair assignment. Do not declare acceptance or start another packet.
```

# P0 â€” Feasibility, corpus, and boundary freeze

Phase specification revision 1. **Implementation status: PARTIAL â€” LIVE EVIDENCE BLOCKED.** Codex owns phase acceptance.

Implementation packet(s): [W01](../packets/W01-feasibility.md).

## Scope, deliverables, and exit conditions

**Inputs:** this plan, prior proposal, eligible provider access, proposed source URLs.

**Tasks:** record the product boundary; fetch and hash a narrow corpus; verify exact affected revisions and source authority; obtain authentic old/new documents or label the synthetic fallback; define coverage; inspect available runtimes; test parser + PDF coordinates; make a bounded real NVIDIA/Nebius request; check hosted account/region/cost feasibility; audit initial licensing constraints.

**Deliverables:** architecture decision record, source manifest, provider spike record with usage, parser inspection samples, draft evaluation cases, deployment choice, supported predicate vocabulary.

**Exit gate:** at least one real source section produces an inspectable, cited draft via the intended runtime model; source rendering is trustworthy enough for review; the final change demo has an honest provenance plan; the hosting route is feasible.

**If blocked:** reduce the source subset, repair the parser adapter, or select another eligible NVIDIA model actually available through Nebius. Do not silently substitute a noneligible runtime or begin a large UI before resolving the core path.

## Execution ownership

Read the [dispatch status](../STATUS.md) and assigned packet. This phase document is not a worker dispatch. Each packet pins its baseline, writable paths, detailed steps, and checks. A phase can span packets and is complete only when all its exit conditions are evidenced.

## Required evidence

- Attempt-numbered worker handoff listing actual changed files and checks.
- Source/model/fixture provenance where used; explicit failed or skipped checks.
- Codex independent review with each exit condition marked supported, failed, or unresolved.
- Accepted baseline and any contract decision record before dependent work starts.

## Failure handling

Preserve partial outputs and diagnostic evidence. Do not broaden scope or weaken the phase gate to clear a blocker. Codex consolidates repair instructions and records the resulting phase state. Workers cannot mark this phase complete.

## Completion record

Attempt 03 offline repairs are accepted after small Codex corrections. [Codex review 03](../reviews/W01-review-03.md) records 20/20 independent checks, 50 worker-suite passes and one skip, and zero actual provider attempts. Real-source G4 and live missing-information G5 remain required. P0 is not complete. [The latest credits-restored decision](../decisions/2026-10-29-credits-restored.md) schedules live W01 completion before the prepared W02 packet.


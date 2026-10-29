# P7 — Complete workflow and review packets

Phase specification revision 1. **Implementation status: NOT_STARTED.** Codex owns phase acceptance.

Implementation packet(s): [W08](../packets/W08-ui-export.md).

## Scope, deliverables, and exit conditions

**Inputs:** P5 and P6 capabilities.

**Tasks:** finish the five views, empty/error/loading states, navigation, accessibility, JSON and Markdown export, artifact manifest, and deterministic replay entry point. Add an optional printable view only after the core packet works.

**Deliverables:** complete product journey and an export bundle containing sources/anchors, accepted rule/fact versions, coverage, traces, decisions, open requests, evaluator version, and hashes. Include original documents only where access and redistribution rights permit.

**Exit gate:** a fresh local environment can replay the assessment from an authorized packet without a model call and match the canonical result hash; missing restricted source bytes are declared; links and permissions work; export does not omit uncertainty.

**If blocked:** retain JSON + readable Markdown rather than spending the critical path on elaborate PDF layout. Reproducibility and source traceability take priority over presentation extras.

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

No accepted implementation evidence yet. Codex will add review references after execution.


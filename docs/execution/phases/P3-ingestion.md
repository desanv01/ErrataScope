# P3 — Source ingestion, live interpretation, and review

Phase specification revision 1. **Implementation status: W04 BACKEND BOUND / NOT_STARTED. UI approval pending.** Codex owns phase acceptance.

Implementation packet(s): [W04](../packets/W04-ingestion-review.md).

## Scope, deliverables, and exit conditions

**Inputs:** P0 corpus/provider findings; P2 durable infrastructure.

**Tasks:** implement ingestion, document inventory, anchors, parser provenance, Nemotron adapter, bounded retries, citation checks, extraction-run records, and a minimal interpretation-review screen. Include a live/cached indicator and full source context.

**Deliverables:** real source → persisted draft rule → accepted rule workflow; coverage manifest; source viewer with verified coordinates; model-call audit record.

**Exit gate:** the reviewer can inspect every predicate's source, reject a bad interpretation, accept a correct version, and see unsupported entries. Invalid JSON, missing citations, truncated output, provider timeout, and prompt injection fixtures cannot activate a rule.

**If blocked:** narrow to the proven digital-text subset or supported page images. Keep failed extraction visible. Do not replace all model work with hand-authored rules and describe the result as live extraction.

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

[W04 backend revision 2](../packets/W04-ingestion-review.md) is ready against accepted W03. No P3 implementation acceptance yet. UI/imagegen and real-source semantic approval remain explicit gates.


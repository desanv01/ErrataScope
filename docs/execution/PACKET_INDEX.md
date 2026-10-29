# Packet index and dependency map

Revision 6. W01/P0 accepted. W02 revision 2 is READY_TO_DISPATCH against the fresh accepted baseline. [Acceptance](reviews/W01-review-06.md), [status](STATUS.md).

| Packet | Deliverable | Prerequisite acceptance | Phase coverage |
|---|---|---|---|
| [W01](packets/W01-feasibility.md) | Real source/parser/provider feasibility | Documentation baseline | P0 |
| [W02](packets/W02-domain-core.md) | Domain contracts and deterministic evaluator | W01 full acceptance + refreshed domain-v1 baseline | P1 |
| [W03](packets/W03-persistence-jobs.md) | Persistence, authorization, artifacts, durable jobs | W02 | P2 |
| [W04](packets/W04-ingestion-review.md) | Live document interpretation and rule review | W03 | P3 |
| [W05](packets/W05-product-assessment.md) | Scoped product assessment workflow | W04 | P4 |
| [W06](packets/W06-evidence-requirements.md) | Evidence requests and restricted requirement consistency | W05 | P5 |
| [W07](packets/W07-change-impact.md) | Changed baseline and newly added errata impact | W05; W06 accepted before shared-folder dispatch | P6 |
| [W08](packets/W08-ui-export.md) | Complete five-view workflow and reproducible exports | W06 + W07 | P7 |
| [W09](packets/W09-evaluation-production.md) | Frozen evaluation and production acceptance | W08 | P8 + P9; P2 hosted acceptance |
| [W10](packets/W10-release.md) | Accurate release/submission package | W09 | P10 |

W06 and W07 have partially independent logic after W05, but the current operating policy is sequential single-writer execution. Do not launch parallel workers without a new explicit ownership plan.

## Dispatch binding checklist — Codex

Before each future packet: record accepted baseline; resolve exact schemas/routes/dependency versions; provide approved design artifact for UI work; verify writable-file ownership; specify concrete commands for the existing codebase; include any deployment or cost authorization limits; set packet READY_TO_DISPATCH and issue its prompt. Existing acceptance gates stay binding.

Delivery units from the agreed workflow: A=W01 and W02 contract freeze; B=W02/W03; C=W04/W05; D=W06/W07; E=W08; F=W09/W10. This mapping batches work without discarding P0–P10 requirements.


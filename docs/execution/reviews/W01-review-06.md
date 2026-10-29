# W01 attempt 06 — ACCEPTED; P0 complete

Codex independent acceptance, 29 October 2026. **W01 revision 1 and P0 are ACCEPTED for the bounded feasibility scope.** All seven required gates pass, including real provider evidence and manual source-grounded semantic review. This does not accept a production application or general model accuracy.

## Independent evidence

- Live-v4 baseline: PASS before any Codex status edits, 142 hashes / 233 links. Saved at `.local/reviews/W01-review-06/baseline-before.json`.
- [Independent audit](W01-review-06-checks.py): all new request/response/validation wrappers and hashes match; requests equal the pinned case payloads; exact model/endpoint, HTTP 200, finish=stop, reasoning tokens=0. Both actual drafts pass recomputed schema/citation/identity checks. Synthetic omission expectation passes with null identity/revision.
- Offline replay of the CLI result handling against those saved actual artifacts returns 0 for both cases, consistent with the report and shared validator. Dispatch was stubbed for that replay; no additional live request occurred or is claimed. The underlying responses are the worker's actual paid attempts 3 and 4.
- Recomputed G1–G7 agree with the report: all PASS. All 19 pre-attempt backup files match their manifest. Prior attempts 1–2, their five artifacts, and eight blocked events match the activation record/history. All four reservations remain counted.
- Actual source PDF bytes match `dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd`; all 78 anchors bind to it. All six plain/overlay render pairs exist. Page-index 9 overlay was visually inspected: paragraph/code boxes follow the source, including the any-address wording and example code.
- Configured-key scan found no leak in the 117 scanned document/evidence files. This is a bounded scan, not a universal security audit. Worker lock absent.
- Runtime checked: Python 3.11.15 and Pydantic 2.14.1, matching the W02 binding. Worker 11-unit/51-self-test reports remain supported by the unchanged reviewed implementation; focused independent review tested actual artifacts rather than spending more inference.

## Semantic disposition

Real-source attempt 3: the identity matches the cited identity anchor; both errata's Z/B/X status mappings match row/header/legend context. Consequences preserve may/might qualifiers. Workaround steps and revision-B register instruction are grounded, with no remedy mislabeled as an exception. The example address is explicitly distinguished from the allowed address range. Missing device scope/trigger/exception information remains unresolved rather than invented.

Claim 4's `workaround_restriction` category contains a clarification of what is and is not constrained. Its statement faithfully identifies the AXISRAM1 scope and explicitly says the example address is not required. **Accepted as a nonblocking taxonomy limitation of the draft schema**, not converted into an executable requirement. Later human-reviewed conversion must preserve that nuance.

Synthetic attempt 4: the fixture identifier is explicitly fixture metadata, while source_document_id and source_revision remain null. Fictional device and brownout consequence match the fixture; the cited uncertainty about an undocumented workaround is grounded in its text. No silicon revision or document identity is invented. The source is labeled synthetic, not a manufacturer observation.

The draft conservatively leaves trigger_condition unresolved even where NRST-use context exists. This is an extraction-completeness limitation rather than fabricated certainty and does not defeat W01's cited-draft feasibility gate. It must not silently become a constant-true rule later.

## Budget and scope limits

Four of four lifetime reservations consumed; zero remaining. Aggregate reserved estimate $0.0404655, usage-based estimate $0.0128994, both below $0.25. These are model-rate estimates, not billing receipts. Final ledger SHA-256: `028084e43708460cc0e6a35cc03000bbbf2c756c6c87f235bf52d333a84e55a6`. No paid review request, reset or fifth call.

Only ES0620 Rev 5 sections 2.2.18 and 2.2.5 were interpreted; this is not whole-document/device coverage. No authentic historical manufacturer revision pair is claimed; change fixtures remain synthetic. No hosted end-to-end product, arbitrary-document generalization, safety verdict, VerifForge capability or production reliability is established. PDF redistribution permission remains unknown; vendor bytes and raw provider responses remain private.

## Freeze and next action

[Observed W01 contracts](../bindings/W01-observed-contracts.md) and [acceptance evidence](../../evidence/W01/ACCEPTANCE.json) freeze the accepted inputs, interfaces, request mode and actual successful artifact hashes. Model drafts remain provisional source interpretations, never automatically accepted RuleVersion ASTs.

Codex prepares the private Git/GitHub checkpoint under [the completion protocol](../COMPLETION_PROTOCOL.md), then dispatches [W02 revision 2](../packets/W02-domain-core.md) against its fresh accepted baseline. W02 is offline domain/evaluator work only. The [UI/imagegen approval gate](../UI_APPROVAL_GATE.md) remains pending. No UI or W03 work is dispatched by this acceptance.

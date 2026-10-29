# W01 attempt 05 — independent review

Date: 29 October 2026. **PARTIAL, NOT ACCEPTED. G4 FAIL; G5 PARTIAL.** W02 remains unbound/not dispatchable. UI/imagegen approval remains pending.

## Verified execution and evidence

The live-v3 protected baseline passed independently before Codex edits: 130 hashes, 215 links. Worker lock absent. [Read-only audit](W01-review-05-checks.py) verified both attempts' artifact hashes/wrappers, model/endpoint binding, input bounds, costs, 16 backup files, unchanged attempt-1 ledger record and prior blocked events, and no configured credential in the 103 scanned document/evidence files. Evidence is saved under `.local/reviews/W01-review-05/`. Pricing values stayed unchanged; only its normal validation timestamp refreshed.

Provider attempt 2 is real live evidence: HTTP 200, exact configured model, top-level disable-thinking request, final JSON, finish_reason stop, zero reported reasoning tokens. Recorded usage: 2,481 input / 1,495 output / 3,976 total. It establishes usable final output for this request mode, not general reliability or semantic correctness.

Independent validation reproduces exactly two empty-citation schema errors, claims 1 and 9 (zero-based). Shared CLI/report evidence remains FAIL. No synthetic live attempt or artifact bundle exists. G1/G2/G3/G6/G7 retain their bounded prior findings with unchanged protected source artifacts; the current local checks do not replace live G5.

Two of three lifetime reservations are consumed. Reserved estimate: $0.0200484. Usage-based aggregate estimate: $0.0102069, not an invoice. Starting ledger hash after worker 05: `86ad7b589e4ab8df5c3dbf9a6a699ae00b054c6f514643be4f49bfc34506a9f2`. No paid requests were made during this review. No ledger reset or cap increase has been applied as part of this review record.

## Semantic review of the actual final draft

| Draft content | Finding |
|---|---|
| ES0620 / Rev 5 / August 2026 | Matches identity anchor. The added manufacturer name is not stated in that cited identity anchor; avoid unsupported identity embellishment. |
| 2.2.18 Z=A, B=A, X=not applicable | Matches cited table row, governing headers and legends. |
| 2.2.5 Z=no workaround, B=A, X=A | Matches cited table row, governing headers and legends. |
| Two uncited unknown-device claims | Schema-invalid. Leaving device scope unresolved is appropriate for this bounded input, but it need not be emitted as a claim. |
| Revision-B Boot ROM register workaround classified as exception | Incorrect category. Anchor `st-es0620:p06:029` documents a remedial instruction, not a condition under which the defect does not apply. |
| Workaround restriction requires address 0x34001004 | Unsupported strengthening. Anchor `st-es0620:p09:020` explicitly permits any address in AXISRAM1; the following code gives an example. Preserve the memory-region requirement and example status. |
| Trigger for 2.2.5 described as reading the register | The cited `p06:026` states the register value remains the same. It does not establish that operational trigger as a documented precondition. Omit or mark unresolved unless suitable source text supports it. |
| Reset may fail and may require power cycle | Faithful to the cited consequence text; preserve the uncertainty qualifiers. |

A diagnostic copy with only the two uncited claims removed passes structural validation but still contains the category/address errors. That copy was held in memory only; it is not a new model response and does not pass G4. This demonstrates why merely relaxing citations or editing cached output would be insufficient.

## Codex correction already applied offline

Keep the existing schema and citation minimum. Add [draft-v4 instructions](../../../spikes/w01/prompts/draft_v4_system.md) and [output guidance](../../../spikes/w01/prompts/draft_v4_schema.md). Both case builders use mode `draft-v4-grounded-no-thinking`, retain reasoning off and retain the same source text, anchors, model, endpoint, token caps and pricing.

Missing fields belong in `unresolved_fields`; unsupported claim entries should be omitted, not filled with empty or unrelated citations. Explicitly separate workaround/exception, preserve any/example/required qualifiers, scope statements per section, and avoid unsupported trigger/identity claims. Old prompt files and actual provider responses remain immutable.

Validation: 9 unit tests PASS; 20 independent artifact/CLI/report checks PASS. The isolated worker suite returned 50 PASS / 1 SKIP (deliberately absent credential). New input bounds are 11,334 real-source and 7,571 synthetic, both below 16,000; output cap remains 8,192. Prompt quality still requires actual live and human semantic review. No local test is claimed to prove the model will comply.

## Consolidated continuation and count-cap decision

[Live completion v4 / worker attempt 06](../continuations/W01-live-completion-v4.md) is prepared. One corrected real-source call and one separate synthetic omission call are needed; neither can be replaced by old failed evidence or a mock. Only one request remains under [W01 Task 5](../packets/W01-feasibility.md).

Proposed explicit amendment: increase total lifetime request count **3 to 4**, preserve both used reservations and all artifacts, keep the **$0.25 aggregate spending cap**, 16,000 input and 8,192 output caps. At most two new requests, stop at the first failure. New conservative reservation estimates are $0.010773 and $0.0096441; projected lifetime reserved total $0.0404655. No recursive retries or fifth request.

The user was asked specifically to approve this count-cap change. Until that answer and Codex activation, v4 is not dispatchable; do not spend the last reservation through an old prompt. Keep the ledger unchanged. Activation must record the approval, update configuration and ledger cap metadata without changing used attempts/spend/history, test the limit, then freeze a fresh baseline and issue the exact prompt. This is an explicit amendment, never a budget reset. The current offline preparation is protected by [the hold checkpoint](../baselines/W01-review-05-hold-baseline.json); it is not a live-execution baseline.

Git/GitHub acceptance checkpoint is deferred because no packet has been accepted. After all W01 gates and semantics pass, Codex freezes observed contracts, performs the checkpoint, rebinds W02 revision 2 and supplies its prompt. UI approval remains a separate human gate.

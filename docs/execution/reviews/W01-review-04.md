# W01 worker attempt 04 — independent review and continuation

Reviewed 29 October 2026. **PARTIAL; W01/P0 NOT ACCEPTED.** Worker stopped; no active lock. W02 remains unbound/not dispatchable. UI/imagegen approval remains pending.

## Verified evidence

- Original live-v2 baseline independently passed before Codex edits: 123 hashes, 208 links. Saved at `.local/reviews/W01-review-04/baseline-before.json`. All 13 files in the worker's attempt-03 backup match its manifest.
- [Independent read-only checker](W01-review-04-checks.py) matched request/response hashes and wrappers, endpoint, model, case, attempt, budget arithmetic, absence of a synthetic bundle, and configured-key absence from 95 evidence/document files. Saved safe observations: `.local/reviews/W01-review-04/observations.json`. This is a bounded leak check, not a claim that every possible credential was scanned.
- One actual recorded request: HTTP 200, exact `nvidia/Nemotron-3.5-Super-VL`, request ID `f421941fc2042e05ed147949084bce44`. Response: finish_reason=length, content=null, 8,192 completion/reasoning tokens; 2,481 prompt tokens, 10,673 total. No JSON draft or validation artifact exists. Reasoning text is not accepted final output.
- Ledger has one finalized live `real_source` reservation with outcome `empty`. Reserved estimate $0.0100242; usage-based estimate $0.0081171 using protected pricing. This is an estimate, not an account invoice. Two of three lifetime attempts remain; aggregate cap remains $0.25. Failed attempts are never refunded to this counter.
- Shared artifact validator and report both reject the actual attempt. No synthetic live request occurred. Authentication and route worked for this request; final-answer quality and omission behavior are unproven.
- G1/G2/G3/G6/G7 retain their bounded prior findings with intact baseline/source artifacts. G4 FAIL; G5 PARTIAL (local checks pass, live omission case NOT_RUN). No source-grounded final-draft semantic review is possible without a final draft. The omission fixture's local result does not substitute for a live result.

## Diagnosis and bounded correction

This request exhausted its output cap entirely on reasoning. That does not establish a general model limitation. Keep the same model, endpoint, source scope, schema, token caps, pricing and lifetime budget; explicitly request `chat_template_kwargs: {enable_thinking: false}`.

[NVIDIA's official model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16) documents this toggle and the shared reasoning/final-answer output allowance. Its example is for a self-hosted OpenAI-compatible server. The accessible Nebius material did not establish support for this toggle on this hosted route. Therefore this is a justified, bounded compatibility test, not a claim of verified Nebius support. No extra discovery or paid handshake is authorized. A rejection, ignored control producing another empty answer, truncation or validation failure stops paid execution immediately.

Codex applied small corrections before freezing the next baseline:

1. `cases.py`: request mode `draft-v3-no-thinking`, explicit disable-thinking field on both cases. Existing draft-v2 prompt files remain the content source.
2. `provider.py`: allow that field into the actual HTTP JSON body; client metadata remains filtered out. No retries added.
3. `report.py`: only current, case-specific blocked events can explain an unrun case. Remove static prose that incorrectly said no paid dispatch occurred. Preserve all historical ledger events and the worker-04 report.
4. `config.py`: next worker metadata/baseline only. All prices, caps, model, schema and pinned inputs unchanged.

Before-code copies are under `.local/reviews/W01-review-04/before/`. After the functional corrections, nine unittest tests passed, including both cases' outbound JSON and no retry after a mocked HTTP 400. The isolated independent checker passed 20/20 artifact/CLI/report cases; its worker suite had 50 PASS / 1 SKIP because it deliberately clears credentials. This is not live acceptance. Real ledger remained unchanged; no paid review requests were made.

## Single next assignment

Dispatch [live completion v3, attempt 05](../continuations/W01-live-completion-v3.md), using [the exact prompt](../prompts/W01-LIVE-COMPLETION-V3.md) and [new baseline](../baselines/W01-live-v3-baseline.json). The worker executes the already corrected code; it does not repair or redesign it. At most two remaining calls: real source first; only after a passing result, synthetic omission. Preserve attempt 1 and all history.

No Git/GitHub acceptance checkpoint is due because W01 is not accepted. After successful independent review, Codex performs that checkpoint, freezes observed contracts and rebinds the prepared W02 revision 2, then provides its prompt. The UI/imagegen gate is unchanged.

# Consolidated repair assignment — W01-R01

Issued: 29 October 2026. State: **READY_TO_DISPATCH**.
Underlying packet: W01 revision 1. Attempt-01 decision: CHANGES_REQUESTED / partial useful evidence.
Read [Codex review 01](W01-review-01.md), the original W01 packet, worker rules, and the source/provider/testing contracts.

## Baseline and ownership

Use `docs/execution/baselines/W01-repair-01-baseline.json` for this repair's preflight/final protected checks:

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-repair-01-baseline.json
```

The old W01 baseline is preserved historical evidence and will differ because Codex updated status/review documents. Do not regenerate either manifest.

Original W01 writable paths remain allowed: `spikes/w01/**`, `fixtures/manifests/w01/**`, `docs/evidence/W01/**`, `.local/w01/**`, your new `W01-attempt-02.md` handoff, and your own coordination lock. Preserve attempt 01, all Codex review files/checkers, `.local/reviews/**`, plans/contracts/status, and baseline files. No Git mutations, UI, infrastructure, W02, or stack rewrite.

Claim the exclusive worker lock. Preserve useful source bytes/parser outputs; do not repeat downloads or full conversion unless a repair actually requires it. Public-safe reports may be regenerated, but exact prior evidence and attempt history must remain available. Codex preserved attempt-01 inputs privately.

## R1 — Reserve before dispatch; preserve uncertain attempts

1. Add a validated ledger schema and crash-safe atomic writes. Reserve attempt number, case ID, input/prompt/model identity, maximum/estimated usage, and conservative cost before calling HTTP.
2. Timeout, HTTP error, malformed JSON, validation failure, or interrupted completion must not erase the reservation or permit reuse. Finalize known outcomes; retain conservative reservations for uncertain outcomes.
3. Persist no more than three inference attempts across cases, retries, and process restarts. Keep output/input/$0.25 caps. Do not reset the ledger to get more calls. A different path or process must not silently begin a new budget.
4. Validate finite nonnegative prices, counts, and totals; tie pricing to source/date/model. Reject invalid/missing configuration visibly.
5. Replace the misleading conservative chars/4 claim with an actual documented bounded strategy (tokenizer where available, or sufficiently conservative text/UTF-8 estimate plus message overhead). If the bound exceeds the cap, reduce input or block rather than underestimate it.
6. A later blocked preflight must not overwrite history with `live_requests_made=false` after prior dispatches.

Required offline tests: four simulated timeouts stop dispatch at three; restart reads reservations; malformed response consumes its attempt; existing history survives later missing-key block; invalid/NaN/negative pricing rejected. No network in these tests.

## R2 — Evidence-derived gate results

1. Record explicit case types `real_source` and `synthetic_missing_revision` and their request/response/validation artifacts.
2. A live structural gate requires intended provider/model binding, HTTP success, nonempty usable nontruncated completion, successful JSON/schema/citation validation, and evidence tied to that case. Model aliases require explicit documented mapping, not arbitrary acceptance.
3. Failed requests, invalid drafts, mocks, cache-only outputs, missing evidence, and unexecuted cases cannot become PASS. Overall human acceptance remains a Codex decision.
4. Derive G4 from the real-source case; derive live G5 from the separate omission case plus actual local results. Preserve partial states.
5. Remove hard-coded baseline and local-test success claims from report generation. Read actual current-run records and distinguish historical evidence from current verification. A missing record is unknown/not-run, not pass.

Required offline tests: HTTP 401/500, wrong model, truncated/empty completion, malformed/invalid JSON, missing artifacts, no negative-case run, and failing local test all produce nonpassing appropriate gates. A valid mock is still mock-only.

## R3 — Source identity and context

1. Build payload identity from the actual sealed manifest/source, not literals for Rev 5/date/document ID.
2. Provide source identity anchors or a separately validated provenance reference so the correct source revision is usable without fabrication or omission.
3. Validate draft document ID/revision against expected source identity and hash. Reject mismatches. Maintain source-document revision vs silicon revision as separate concepts.
4. Include anchor IDs for governing revision-column headers, applicable status legend entries, and material caveats/footnotes used in interpretation. Do not let a derived matrix become uncited authority.
5. Keep technical claims provisional. Source-identity consistency is not semantic proof of all claimed conditions.

Required offline tests: correct real identity accepted structurally with its evidence, unrelated document ID rejected, wrong revision rejected, missing expected revision remains unresolved where appropriate, and unknown silicon revision is not filled in from document revision. Preserve inspected anchor coordinate correctness.

## R4 — Runnable cases and live evidence when inputs exist

1. Add documented case selection, for example `probe-provider --case real-source` and `probe-provider --case synthetic-missing-revision`. No command may silently run both or retry beyond caps.
2. Add a documented validated pricing input using [Codex pricing evidence](W01-pricing-evidence.json), with exact model/source/date fields. Do not ask the human to edit internal ledger counters. The public reference does not prove account-specific availability.
3. Run offline repair checks before enabling paid calls. If the intentionally supplied `NEBIUS_API_KEY` is absent, complete all local repair work, then report the live cases BLOCKED. Never search accounts/folders or ask for the key in chat.
4. If credentials are deliberately available and compatibility/budget gates pass, run the real-source case and the missing-information case, preserving actual artifacts/usage/finish reason/validation/reviewer notes. An uncertain timeout counts as a request. Stop at the existing W01 limits.
5. Correct the report/README: published pricing evidence is now available; account/model access is still unverified until a real call. HTTP 401 alone does not prove the specific model or full endpoint behavior.

## Validation and finishing

- Rerun the worker suite with added regressions; record exact commands/exits and output paths.
- The protected Codex attempt-01 checker is diagnostic evidence with its old call signatures. Do not modify it to suit the repair. Add regression tests to the worker-owned suite. If a corrected public signature prevents rerunning that old diagnostic, document the change and provide equivalent regression evidence for Codex review.
- Run only the parser/anchor checks needed for changed identity/context anchors; retain existing source hashes and bounded coverage.
- Recheck the repair baseline. Write `docs/execution/handoffs/W01-attempt-02.md` with R1–R4 dispositions, original gate dispositions, live/mock distinctions, remaining input names, and exact reproduction commands.
- Stop owned processes, release your own lock, and stop editing.

Return this prompt:

> Review ErrataScope W01 repair 01, worker attempt 02. The worker has stopped editing. Read docs/execution/handoffs/W01-attempt-02.md and docs/execution/reviews/W01-repair-01.md. Verify the repair protected baseline and independently check R1–R4 against actual files and artifacts. Require real provider evidence for G4 and the live part of G5. Record acceptance or remaining repairs; W02 stays unbound until all required W01 gates pass. Preserve the UI/imagegen approval gate.

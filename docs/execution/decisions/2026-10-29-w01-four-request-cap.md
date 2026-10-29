# Approved W01 lifetime request-count amendment

User approval received 29 October 2026: **"Approve 4 lifetime requests; keep $0.25 cap"** in response to the explicit proposal to increase W01 from three to four lifetime requests with both used attempts counted.

This amendment changes only the lifetime request-count ceiling from 3 to 4. The aggregate reserved spending cap remains $0.25; the per-call input bound remains 16,000 and output cap 8,192. Existing attempts 1 and 2, their artifacts, failures, reservations, pricing and blocked-event history are retained. No attempt number, counter or spending total is reset. At most two new calls are authorized: corrected real-source attempt 3, then synthetic omission attempt 4 only after the first passes the assignment's structural and provisional semantic checks. Stop at first failure; no fifth call or automatic retry.

Codex activation updates `config.py`, the current worker metadata, the ledger's cap metadata and its update timestamp. The audit record [W01-v4-activation.json](W01-v4-activation.json) binds before/after ledger hashes, old and new caps, preserved history and artifacts. The original ledger and changed-code snapshots are retained under `.local/reviews/W01-v4-activation/`. New checkpoint: [live-v4 baseline](../baselines/W01-live-v4-baseline.json).

Offline verification passed: 11 unit tests (including retained used slots, refusal of a fifth reservation across restart, and independent spending guard); 20 independent artifact/CLI/report cases; isolated worker self-tests 50 PASS / 1 SKIP because that checker clears credentials. Timeout and restart tests now exercise the configured count cap; the timeout test ID is `timeouts_stop_at_request_cap`. These are offline checks, not live acceptance.

The [v4 continuation](../continuations/W01-live-completion-v4.md) and [exact DeepSeek prompt](../prompts/W01-LIVE-COMPLETION-V4.md) are activated only with the passing frozen baseline. Prompt correction was independently prepared in [review 05](../reviews/W01-review-05.md); its original pending-approval statements remain historical. No provider call is made by activation.

W01/P0 remain PARTIAL. W02 remains unbound. After a passing independent W01 review, Codex performs the Git/GitHub checkpoint, freezes observed contracts, rebinds W02 revision 2 and provides its prompt. UI/imagegen approval is unchanged and pending.

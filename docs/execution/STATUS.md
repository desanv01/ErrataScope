# Canonical execution dispatch status

Updated: 30 October 2026. Codex-owned.

**W01/P0, W02/P1 and W03 local foundation ACCEPTED. W04 revision 2 BACKEND portion READY_TO_DISPATCH, attempt 01.**

- [W03 review 05](reviews/W03-review-05.md): 110 real integration tests, 92 domain tests; independent lifetime 16/16, failure-handle 3/3, HTTP 22/22, ack-loss 8/8, connected 11/11, real crash/restart and fresh sentinel pass. [Accepted freeze](bindings/W03-observed-contracts.md).
- Public GitHub checkpoint pushed/verified: commit `99090c6aed74c0378eeae02860f33027b9cbca2d`, tag `w03-local-accepted`. [Git record](decisions/W03-git-checkpoint.json), [standing public authorization](decisions/2026-10-30-public-repository.md).
- Start [W04 prompt](prompts/W04-START.md), [packet](packets/W04-ingestion-review.md), [complete binding](bindings/W04-ingestion-v1.md), [protected baseline](baselines/W04-backend-v1-baseline.json), [starting inventory](reviews/W04-starting-inventory.json).
- Scope: immutable sources/anchors/coverage, bounded ingestion jobs, actual Nebius drafts and explicit conversion/review backend. W01 four-call history remains exhausted; new W04-backend-v1 budget is at most two paid reservations and $0.25 reserved estimate, no automatic paid retries.
- Preserve accepted evidence/domain/foundation behavior, existing volumes and the explicit 41 legacy missing artifacts. Hosted P2 NOT_RUN, UI/imagegen PENDING. Full W04/P3 is not accepted by a backend-only result. W05–W10 remain unbound.
- No worker running at dispatch preparation. Review services stopped; pgdata/artifacts/test_artifacts retained. No W04 code was implemented by Codex.

Follow [completion protocol](COMPLETION_PROTOCOL.md): review actual evidence, checkpoint accepted scope, and provide the exact next eligible prompt.

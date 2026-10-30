# W04 backend start — revision 2, attempt 01

Paste this into the single DeepSeek worker. All referenced files already exist locally; publication does not gate local dispatch.

```text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W04 revision 2 backend worker, attempt 01.

Read and follow:
docs/execution/STATUS.md
docs/execution/WORKER_RULES.md
docs/execution/packets/W04-ingestion-review.md
docs/execution/bindings/W04-ingestion-v1.md
docs/execution/bindings/W01-observed-contracts.md
docs/execution/bindings/W02-observed-contracts.md
docs/execution/bindings/W03-observed-contracts.md
and the shared contracts required by the packet.

W03 local foundation is accepted at commit 99090c6aed74c0378eeae02860f33027b9cbca2d, tag w03-local-accepted. Do not restart W03 repairs. Hosted P2 remains NOT_RUN; UI/imagegen approval remains PENDING.

Before editing, run:
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W04-backend-v1-baseline.json

Require PASS. Verify every starting hash in docs/execution/reviews/W04-starting-inventory.json. Require no active worker lock and no W04-attempt-01 handoff; claim your lock exclusively and create the verified backup specified in the binding. Do not refresh the baseline to conceal a mismatch.

Implement only the bound backend: immutable source ingestion, bounded real-PDF extraction and coverage, exact source anchors, durable extraction jobs, strict cited Nemotron drafts, private evidence/accounting, explicit conversion proposals and authorized append-only rule reviews. Preserve the accepted domain, storage/auth/recovery behaviors, existing data/volumes and regression tests. Follow the exact writable-file list and the single migration-head-test exception. Do not edit plans, protected evidence, prior migrations or W01 code/ledger.

Complete offline and real local integration checks first. Then use only the separately authorized W04-backend-v1 live budget: maximum 2 lifetime paid reservations, $0.25 total reserved-estimate cap, 16000 input and 8192 output tokens per call. Exact model nvidia/Nemotron-3.5-Super-VL; top-level chat_template_kwargs.enable_thinking=false. W01 remains exhausted at 4/4; never reset either ledger. Run one real-source case, then the synthetic missing-revision case only if the first passes the binding's checks. No automatic paid retries or model switching. Load only the designated project key without displaying it. If live work is blocked, finish independent in-scope work and report PARTIAL with the exact blocker.

No UI/frontend, hosted provisioning, Git mutations, delegation, W05 or other future packet. A test actor exercising a review endpoint is not actual human semantic approval. Never claim full W04/P3 acceptance while UI remains pending.

Write docs/evidence/W04/IMPLEMENTATION_REPORT.md and docs/execution/handoffs/W04-attempt-01.md with actual commands, exit codes, gate evidence, reservation history, source/semantic limitations and preserved sentinel/legacy-loss results. Recheck the protected baseline. Stop owned services/jobs while retaining volumes, release your lock, stop editing, and return the exact Codex review prompt below.
```

## Exact return prompt

```text
Review ErrataScope W04 revision 2 backend-v1, worker attempt 01. The worker has stopped editing. Read docs/execution/handoffs/W04-attempt-01.md, docs/execution/packets/W04-ingestion-review.md and docs/execution/bindings/W04-ingestion-v1.md. Verify the protected baseline and starting backup. Independently check real source/anchor/coverage fidelity, strict provider and case-bound evidence, durable reservation accounting without resetting W01 or W04 history, reviewed conversion and project/current-role authorization, immutable persistence and restart/replay/cancellation behavior. Require actual provider evidence for live gates; mock/cached/edited outputs are not new live success. Distinguish synthetic review-mechanism tests from genuine semantic acceptance. Preserve accepted W01/W02 evidence, W03 foundation behavior, the known 41 legacy missing artifacts, hosted P2 NOT_RUN and UI/imagegen PENDING. Record backend acceptance or one consolidated repair; full W04/P3 remains incomplete until its UI and semantic gates pass. Perform the appropriate Git/GitHub checkpoint for accepted scope under the standing public-repository authorization and give the exact next eligible prompt or concrete UI-approval step. Do not start an unbound future packet.
```

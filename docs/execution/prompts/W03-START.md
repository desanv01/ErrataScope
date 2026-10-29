# DeepSeek dispatch — W03 revision 2, attempt 01

~~~text
Work in C:\Users\Dv\Desktop\ErrataScope as the single W03 revision 2 implementation worker, attempt 01.

Read and follow:
docs/execution/START_HERE.md
docs/execution/WORKER_RULES.md
docs/execution/packets/W03-persistence-jobs.md
docs/execution/bindings/W03-foundation-v1.md
docs/execution/bindings/W02-observed-contracts.md
and the shared contracts required by the packet.

W01/P0 and W02/P1 are accepted. Verify docs/execution/baselines/W03-baseline.json before editing. Require no active worker lock and no existing W03-attempt-01 handoff; claim your lock exclusively.

Implement the bound local foundation: PostgreSQL migrations and immutable version persistence; JWT/project authorization; private local artifacts; typed FastAPI routes; idempotency and review concurrency; durable PostgreSQL jobs/attempts/outbox/events with Valkey/RQ delivery and recovery; a real connected synthetic artifact-digest flow.

Use the exact pinned Linux images/dependency lock and isolated erratascope-w03 Compose project. Docker is available; handle any harness permission requirement without changing unrelated resources. Follow the packet's allowed paths and commands. Keep accepted domain code/tests, W01/W02 evidence and protected documents unchanged.

Only the assigned local containers/dependency downloads are authorized. No Nebius requests, .env.local access, hosted provisioning/deployment, Git, frontend/UI or W04 work. Hosted P2 acceptance and the UI/imagegen gate remain open.

Run the accepted domain suite and actual PostgreSQL/Valkey integration, authorization, concurrency and restart/recovery checks. Do not claim integration success from mocks or skipped services. Export OpenAPI and truthful evidence to docs/evidence/W03/.

Recheck the protected baseline. Write docs/execution/handoffs/W03-attempt-01.md with actual gates, commands/exits, changed files and limitations. Stop your owned jobs/services while preserving volumes, release your lock and stop editing.

Return the exact Codex review prompt from the packet. Do not declare acceptance or begin another packet.
~~~

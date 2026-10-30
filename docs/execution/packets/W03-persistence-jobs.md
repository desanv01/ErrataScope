# W03 — Persistence, authorization, artifacts, and durable jobs

Acceptance notice (30 October 2026): **W03 local foundation accepted**, worker attempt 05, [review 05](../reviews/W03-review-05.md). [Observed freeze](../bindings/W03-observed-contracts.md). Earlier dispatch instructions below are historical; hosted P2 and UI remain open.

Packet revision: **2**
Dispatch state: **ACCEPTED**
Phase: [P2](../phases/P2-foundation.md), non-UI local foundation only.
Worker: DeepSeek, attempt **W03-attempt-01**. Codex owns acceptance and Git.
Starting baseline: [W03-baseline.json](../baselines/W03-baseline.json), bound after [W02/P1 acceptance](../reviews/W02-review-02.md).

## Required reading

Read [worker rules](../WORKER_RULES.md), [status](../STATUS.md), [W02 freeze](../bindings/W02-observed-contracts.md), the entire [foundation-v1 binding](../bindings/W03-foundation-v1.md), [data/version](../contracts/data-and-versions.md), [API/jobs](../contracts/api-and-jobs.md), [security](../contracts/security-and-operations.md) and [testing](../contracts/testing-and-acceptance.md) contracts. The binding supplies exact runtime pins, routes, records, auth/storage/job semantics, tests and exclusions.

## Preflight and ownership

Work only in C:\Users\Dv\Desktop\ErrataScope. Run:

~~~powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-baseline.json
docker version
docker compose version
~~~

Require baseline PASS, no active lock and no existing W03-attempt-01 handoff. Claim .local/coordination/ACTIVE_WORKER.json exclusively with packet/revision/attempt, start UTC and ownership. Docker permission errors may require the harness's permission mechanism; do not alter Docker configuration or unrelated projects.

Writable paths only:

- backend/erratascope_service/** — new service package/helpers.
- backend/migrations/** and backend/alembic.ini — Alembic history/config.
- backend/requirements-service.lock — exact protected Linux lock copy.
- backend/tests_w03/** — new foundation tests/fixtures.
- backend/README-W03.md and backend/.dockerignore — instructions/build exclusions.
- infra/w03/** — Dockerfile, compose.yaml, local templates/scripts and hosted prerequisites.
- docs/evidence/W03/** — sanitized reports, logs, OpenAPI, dependency/image inventories.
- .local/w03/** — synthetic keys/tokens, test data/logs and scratch; never publish secrets.
- docs/execution/handoffs/W03-attempt-01.md and your own worker lock.

Everything else is read-only, including accepted domain code, backend/tests/**, W02 fixtures/requirements/README, W01/W02 evidence, protected documentation, .local/reviews/**, .local/w01/**, .env.local and Git metadata. No provider calls, credentials search, UI, W04, account provisioning or hosted deployment. Only the assigned local containers/dependencies are authorized infrastructure work. No volume deletion or global Docker prune.

## Sequence

1. Runtime/config: service package, frozen lock, backend-only Docker build, isolated Compose, local JWT bootstrap, hosted-disabled configuration.
2. Persistence/auth: Alembic schema, constrained ownership/versions, actor/project checks, immutable validated bundle persistence.
3. Artifacts/API: private streaming artifacts, typed routes, errors, idempotency/review concurrency, OpenAPI.
4. Jobs/recovery: durable DB state, JSON-serialized RQ delivery, attempt-token guarded commits, outbox/reconciliation and artifact_digest.
5. Real-service integration/race/restart evidence; retain domain tests; hosted validation stays unrun.

## Commands and evidence

Implement these exact interfaces, then run sequentially and inspect exits. They are target interfaces to create, not claims that implementation exists. The test service uses /app as cwd/PYTHONPATH and mounts only .local/w03 as /local for outputs/dev keys. API receives only public JWKS. Domain tests write scratch data inside the container; do not modify protected host files for path convenience.

~~~powershell
docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet
docker compose -p erratascope-w03 -f infra/w03/compose.yaml build
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm --no-deps test python -m erratascope_service.cli bootstrap-local --out /local/dev-auth
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait db broker
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait api worker dispatcher
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests -v
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w03 -v
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m erratascope_service.cli verify-foundation --output /local/verification.json
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W03-baseline.json
~~~

verify-foundation must drive the actual API and DB/broker-backed worker with synthetic tokens, verify receipt/content/events and foreign-user denial, and write actual observations without secrets. Integration tests use a dedicated DB/schema namespace and resource prefix inside this project's database, preserving running example data. Missing services fail tests, not skip or mock them.

Implement a PowerShell recovery script under infra/w03/ that narrowly restarts this project's worker/dispatcher, records deterministic stage barriers and confirms recovery. Gate failpoints to explicit local test mode; no production HTTP failpoint endpoints. Restart API/worker with existing volumes and verify retrieval. At completion stop only services started/owned by this attempt, preserve volumes/evidence and record stopped/remaining resources; no hidden jobs.

Export docs/evidence/W03/openapi.json, IMPLEMENTATION_REPORT.md and sanitized recovery evidence. G1=migrations/flow; G2=auth/artifacts; G3=idempotency/review races; G4=actual recovery; G5=hosted prerequisites documented. Hosted execution is NOT_RUN and P2 overall hosted/UI deliverables remain pending.

## Handoff

Recheck baseline, write handoff, stop owned jobs/services, release your lock and stop editing. Do not start W04 or edit acceptance status. If blocked, report the precise prerequisite and complete independent in-scope work; never change stack/pins or weaken gates.

Return:

> Review ErrataScope W03 revision 2, worker attempt 01. The worker has stopped editing. Read docs/execution/handoffs/W03-attempt-01.md, docs/execution/packets/W03-persistence-jobs.md and docs/execution/bindings/W03-foundation-v1.md. Verify the W03 protected baseline, preserving accepted W01/W02 evidence and domain code. Independently check actual PostgreSQL migrations/version integrity, JWT/project/artifact authorization, idempotency and review races, RQ/outbox/attempt-token recovery and the connected local API flow. Mocks or skipped services do not establish integration pass. Hosted P2 acceptance remains open unless separately authorized and evidenced; no UI approval is implied. If W03 passes, record acceptance, perform the Git/GitHub checkpoint, bind eligible W04 scope and give its exact DeepSeek prompt. Otherwise issue one consolidated repair and prompt. Preserve the UI/imagegen approval gate.

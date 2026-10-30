# W04 backend — ingestion and interpretation review

This directory extends the accepted W03 local service. It adds immutable source versions, bounded real-PDF extraction with located anchors/coverage, strict cited model drafts, a reservation-first Nebius adapter with an independently capped W04 budget, explicit conversion proposals and append-only authorized reviews. It is **backend only**; hosted P2 is NOT_RUN and UI/imagegen remains PENDING. Full W04/P3 is not accepted by this work.

## Isolation

- W03 service lock is unchanged. The additive parser lock is `backend/requirements-ingestion.lock`, installed with `--require-hashes --only-binary=:all:` into the same image.
- Compose project remains `erratascope-w03`. Main volumes `pgdata`, `artifacts` remain; tests use the dedicated `erratascope_test` database and `test_artifacts` volume. Never point tests at main data.
- Live provider configuration is a separate override: `infra/w04/compose.live.yaml`. It enables live mode for API/worker and mounts the designated `.env.local` read-only only into the worker; API/dispatcher/test/parser never receive it.

## Start, migrate, test

```powershell
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W04-backend-v1-baseline.json
docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet
docker compose -p erratascope-w03 -f infra/w03/compose.yaml build
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait db broker
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml up -d --wait api worker dispatcher

# W04 backend tests (real PostgreSQL/storage; isolated test DB)
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w04

# Existing regressions
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w03
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests
```

## Offline connected verification (no provider call)

```powershell
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m erratascope_service.ingestion.cli verify-ingestion --mode offline --case real_source --output /w04/verify-offline-real.json
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m erratascope_service.ingestion.cli verify-ingestion --mode offline --case synthetic_missing_revision --output /w04/verify-offline-synthetic.json
```

## Live budget (separately authorized; not a W01 reset)

Only after the offline suite and connected mock/offline checks pass:

```powershell
docker compose -p erratascope-w03 -f infra/w03/compose.yaml -f infra/w04/compose.live.yaml up -d --wait api worker dispatcher
docker compose -p erratascope-w03 -f infra/w03/compose.yaml -f infra/w04/compose.live.yaml exec -T worker python -m erratascope_service.ingestion.cli check-key
docker compose -p erratascope-w03 -f infra/w03/compose.yaml -f infra/w04/compose.live.yaml run --rm test python -m erratascope_service.ingestion.cli verify-ingestion --mode live --case real_source --output /w04/verify-live-real.json
# Only if the real-source case passes:
docker compose -p erratascope-w03 -f infra/w03/compose.yaml -f infra/w04/compose.live.yaml run --rm test python -m erratascope_service.ingestion.cli verify-ingestion --mode live --case synthetic_missing_revision --output /w04/verify-live-synthetic.json
```

- Budget `W04-backend-v1`: maximum **2** paid reservations lifetime, **$0.25** total reserved estimate, **16,000** input / **8,192** output tokens per call. No refunds/reset on retry or test DB reset. W01 remains exhausted at 4/4.
- `check-key` prints only `CONFIGURED`/`MISSING`; it never prints the key.
- No automatic paid retry or model switch. A failed/uncertain live call consumes its reservation and is retained.

## Recovery / finish

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File infra/w03/recover.ps1
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W04-backend-v1-baseline.json
docker compose -p erratascope-w03 -f infra/w03/compose.yaml stop
```

Stop services while retaining `pgdata`, `artifacts`, and `test_artifacts`. Do not delete volumes; the 41 known legacy missing artifacts remain explicit and unreplaced.

## API/CLI surfaces

- `POST/GET /api/v1/projects/{project_id}/sources`, `POST /sources/{id}/extractions`
- `GET /api/v1/extractions/{id}`, `/anchors`, `/coverage`, `/drafts`; `GET /drafts/{id}`
- `POST /drafts/{id}/proposals`, `GET /proposals/{id}`, `POST/GET /proposals/{id}/reviews`, `GET /rules/{id}`
- CLI: `python -m erratascope_service.ingestion.cli {check-key,verify-ingestion,verify-evidence,export-openapi}`

Model output is untrusted data, never an active rule. A test actor exercising review endpoints is mechanism testing, not human semantic approval.

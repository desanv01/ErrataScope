# Judge/test-build setup

Use a source checkout and Docker Desktop (Linux containers, current Compose; tested 5.5.1). Host Python/Node and provider credits are not required for the free demonstration.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/submission/start-clean.ps1
# If the official PDF download is unavailable, supply the exact source:
powershell -ExecutionPolicy Bypass -File scripts/submission/start-clean.ps1 -PdfPath "C:\path\to\es0620.pdf"
```

Open http://127.0.0.1:18081/. Select the recorded live case, inspect citations/unknowns, enter a review note, review or reject, and export. Switch to the synthetic/offline example to inspect missing identity and unlocated excerpts. Local auth is automatic; tokens expire after two hours and can be refreshed by rerunning with -NoBuild. Data remains intact. Stop via scripts/submission/stop-clean.ps1.

The source-only new-volume installation was independently tested with -PdfPath. Automatic ST download timed out here; do not mistake that unverified external dependency for a proven unattended download. Use the official URL and pinned hash in README. The snapshot is visibly recorded, not new inference.

## Developer verification history

The following commands describe the developer workspace, including private source/evidence fixtures. Historical baseline checks are not standalone judge setup commands and require the developer's preserved local evidence.

﻿
## Automated checks actually run

```powershell
python scripts/verify_submission_baseline.py
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend run build
docker compose -p erratascope-w03 -f infra/w03/compose.yaml config --quiet
docker compose -p erratascope-w03 -f infra/w03/compose.yaml build
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm migrate
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_submission
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w04
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests_w03
docker compose -p erratascope-w03 -f infra/w03/compose.yaml run --rm test python -m unittest discover -s tests
```

The retained test/build checkpoint results are recorded in the attempt handoff. The local browser journey is under `.local/submission/browser/journey.mjs` (private tooling) and its sanitized result is `docs/submission/evidence/S01/browser-results.json`.

## Browser journey

- Real API at `http://127.0.0.1:18080/`, not mocked components.
- Desktop 1586×992 and narrow 390×844.
- Recorded live result visible with actual source/citations; synthetic/offline case visibly distinct.
- Citation selection highlights the actual located excerpt.
- Review note + Review draft succeeds; external revision change produces the stale 409 message.
- Markdown export downloads real current content with no authorization material.
- No unexpected console errors (the expected stale-conflict 409 is the only network error).

## Clean-install status

Verified with `powershell -ExecutionPolicy Bypass -File scripts/submission/start-clean.ps1 -NoBuild` against isolated project `erratascope-s01-demo`, fresh PostgreSQL/artifact/test volumes and port `18081`. The recorded-demo snapshot was imported through the bounded local importer (`backend/erratascope_service/submission/demo_import.py`), not by copying the main database; zero provider calls are made. A separate browser run passed citation, review, export and narrow-layout checks. Codex completed the clean setup with both recorded-live and original synthetic/offline examples, fixed atomic review/idempotency and citation navigation, and independently ran eight focused tests and sixteen HTTP checks plus actual browser interactions. See ../S01-review-01.md. Automatic source download timed out in the review environment; supplying the exact pinned PDF via -PdfPath is the verified path.


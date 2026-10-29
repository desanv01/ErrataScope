# W01 revision 1 — independent Codex review, attempt 01

Date: 29 October 2026 (Malaysia).
Decision: **CHANGES_REQUESTED; useful source/parser findings accepted as partial evidence. W01 and P0 are not complete. W02 remains unbound.**

Worker handoff: [attempt 01](../handoffs/W01-attempt-01.md).
Reviewed packet: [W01 revision 1](../packets/W01-feasibility.md).
Consolidated next assignment: [W01 repair 01](W01-repair-01.md).

## Independent checks actually performed

- Initial protected-baseline command: exit 0, 49 hashes and 146 links checked, no mismatch. This occurred before Codex updated status/review documents.
- Worker coordination lock absent. Human and handoff state the worker stopped; no claim of a machine-wide process audit.
- Inspected implementation, manifest, provider ledger, source/anchor/coverage artifacts, prompts, fixtures, and report generation.
- Ran `.local/w01/venv/Scripts/python.exe docs/execution/reviews/W01-review-01-checks.py`: exit 1 because independent negative checks reproduced defects. It made zero network/provider calls and isolated generated evidence under `.local/reviews/W01-review-01/`.
- Inside that check, independently reran the worker suite with isolated output paths and no credentials: 18 checks, 17 PASS, 0 FAIL, 1 SKIP.
- Recomputed source SHA-256 and checked it against the source manifest and anchor bundle: matches. Opened actual PDF: 38 pages, document revision visible on its first page. Parsed 68 saved anchors through their Pydantic contract.
- Visually inspected the selected reset passage and summary-table overlay. The rectangles align with the inspected text, and the displayed revision columns support the recorded selected rows. This is a bounded visual check, not full-document extraction acceptance.
- Reopened the official Nebius announcement and located published model ID, endpoint example, and text pricing. See [pricing evidence](W01-pricing-evidence.json). Account availability remains unverified.

Evidence: `.local/reviews/W01-review-01/observations.json`; isolated self-test results; worker input hash manifest and snapshot. The independent script is a reproduction of attempt-01 defects, not the production evaluator or a comprehensive application test.

No fresh full Docling conversion, authenticated model request, deployment, or application UI work was performed in this review. The worker's original source and result artifacts were preserved.

## Findings requiring repair

### R1 — High: uncertain requests do not consume the request/spend reservation

`provider.py:241` sends the request before `provider.py:296` increments/persists the counter. A timeout, response JSON decode failure, process interruption, or validation exception before the final ledger write can leave the request uncounted. The independent test simulated four timeouts: **four dispatches, zero recorded requests**, despite the three-request cap.

Reserve the attempt and conservative budget atomically before dispatch; retain uncertain usage/cost on failures. A restart must not reuse that attempt number. Validate finite nonnegative pricing and budget input. Character-count/4 is a heuristic, not a conservative token upper bound; do not describe it as guaranteed conservative. Preserve previous attempts when reporting a later preflight block.

### R2 — High: gate reporting can falsely claim live success

`report.py:69,81` marks G4/G5 PASS whenever `live_requests_made` is true. A synthetic review state containing only an HTTP 401/rejected attempt produced **G4 PASS and G5 PASS**. `provider.py:317` also accepts a record with the wrong returned model and a truncated completion if `live`, HTTP 200, and validator status are set. The report's baseline evidence is hard-coded true at `report.py:139`.

Derive gates from verified per-case artifacts/results, actual baseline/check records, and explicit failure states. Successful real-source inference does not establish a successful missing-information case. Check response/model identity, completion status, nonempty usable content, and structural/citation validation. Human semantic acceptance remains separate.

### R3 — Medium: source identity is inconsistent between prompt and validator

`provider.py:98` hard-codes document ID/revision/date instead of using the fetched source record. The actual prompt supplies Rev 5 but none of the 68 current anchors contains that document revision. `validate.py:94-105` requires the revision in cited anchor text, so the expected revision is rejected unless the model improperly omits it. Conversely, a draft with an unrelated source document ID was accepted by the validator in the independent fixture test.

Bind ID/revision/hash to the actual source record and provide citable identity evidence, or explicitly validate identity against a sealed provenance record while keeping technical claims anchored. Do not fix this by deleting revision/identity validation. Include relevant header/legend/footnote context with evidence IDs instead of relying only on an uncited derived matrix.

### R4 — Medium: the live negative scenario and reproducible pricing setup are unfinished

`run.py:122` exposes only the real-source probe. The synthetic missing-information fixture exists, but there is no runnable live case selection/check for it. Pricing setup also requires unexplained manual ledger editing. Credentials alone will not complete the requested evidence.

Add explicit real-source and synthetic-omission cases, a documented validated pricing input, per-case evidence, and truthful statuses. Use the Codex-verified public pricing record subject to model/account compatibility. No paid call until R1/R2 are repaired and offline checks pass.

## Gate disposition

| Gate | Codex disposition | Reason |
|---|---|---|
| G1 | Supported for attempt-01 baseline/environment evidence | Original protected hashes match; isolated environment and commands are present; no worker lock remains |
| G2 | Supported for the selected corpus only | Actual bytes/hash/page count and explicit incomplete coverage checked |
| G3 | Supported for inspected anchors; identity handoff needs R3 | Selected overlays are credible; this does not establish general parser accuracy |
| G4 | NOT_RUN / BLOCKED; adapter also requires repair | No authenticated live response; missing key reported; R1/R2/R3 apply |
| G5 | PARTIAL | Existing local suite passes; independent checks expose defects; live omission case not run/implemented |
| G6 | Supported as synthetic fallback only | Original labeled fixtures exist; no authentic manufacturer old/new pair or change engine claimed |
| G7 | PARTIAL | Useful environment gaps recorded; published pricing now found; report-generation logic must be corrected |

## Decisions and limits

- Preserve the proven source/parser work; do not restart W01 or replace the selected stack.
- Python 3.11.15 and the observed pinned parser environment are feasibility findings, not a blanket production-version freeze.
- Document hash plus parser version alone does not uniquely identify an anchor span. W02 must bind extraction run/configuration and anchor identity; contracts remain unbound until W01 passes.
- Published pricing is no longer an unresolved research item. Authenticated account/model access remains unresolved.
- The UI research/imagegen/human-approval gate is unchanged and pending.
- No W02 prompt or acceptance baseline is issued.

## Baseline continuity

The original W01 baseline remains the historical issued baseline. Codex's status/review changes necessarily change some protected documentation. Do not overwrite the original manifest or interpret those documented Codex changes as worker tampering. Repair 01 uses a new [repair protected baseline](../baselines/W01-repair-01-baseline.json). The independent checker and review records are protected from worker edits.

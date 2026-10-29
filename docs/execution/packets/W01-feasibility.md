# W01 — Real-source, parser, and Nebius feasibility

Packet revision: **1**
Dispatch state: **ACCEPTED**

Current scheduling: **W01/P0 accepted** under [review 06](../reviews/W01-review-06.md). All four inference reservations are consumed. Earlier continuation commands are historical and must not be rerun. Next assignment is W02.
Phase: [P0](../phases/P0-feasibility.md)
Starting baseline: [W01-baseline.json](../baselines/W01-baseline.json)
Owner: one DeepSeek implementation worker; Codex accepts.

## Objective

Produce a reproducible local feasibility bundle proving that one real manufacturer erratum can be retrieved, parsed into inspectable anchored evidence, and interpreted through the intended NVIDIA model on Nebius. Establish what is actually available before building the application.

This is a spike, not the production application. Implement small reusable adapters where useful, but do not scaffold the full API, UI, database, queue, or deployment. Outputs are drafts for Codex review, not accepted engineering conclusions.

## Required reading

1. [START_HERE](../START_HERE.md), [WORKER_RULES](../WORKER_RULES.md), [STATUS](../STATUS.md).
2. [Domain invariants](../contracts/domain-invariants.md).
3. [Provider/source contract](../contracts/provider-and-sources.md).
4. [Data/version contract](../contracts/data-and-versions.md) and [rule semantics](../contracts/rule-language.md).
5. [Testing contract](../contracts/testing-and-acceptance.md) and [P0](../phases/P0-feasibility.md).
6. This complete packet and its handoff template. Other research is optional when a specific ambiguity requires it.

## Starting assumptions to verify, not silently trust

- Workspace currently contains planning and illustrative assets, not an application.
- No Git repository is required or authorized to be created by the worker.
- Candidate source is ST ES0620; planning observed Rev 5 and 38 pages.
- Candidate model ID is nvidia/Nemotron-3.5-Super-VL at the documented Nebius endpoint.
- No credentials are embedded in this packet. NEBIUS_API_KEY must be intentionally available to the worker process.
- Python/runtime/package, Docker/WSL, provider access, and hosting feasibility have not been established by Codex.

## Allowed writes

- `spikes/w01/**`: spike source, schema, prompts, small synthetic fixtures, README, isolated dependency declaration/lock.
- `fixtures/manifests/w01/**`: public-safe source metadata and hashes; no full vendor PDFs.
- `docs/evidence/W01/**`: redacted feasibility reports and reproduction notes.
- `docs/execution/handoffs/W01-attempt-NN.md`: your new attempt only.
- `.local/w01/**`: virtual environment, downloaded originals, page renders, exact redacted request/response artifacts, logs, cache.
- `.local/coordination/ACTIVE_WORKER.json`: exclusive advisory lock for this attempt.

Everything else is protected, including the root .gitignore, all plan/contract/status files, existing visuals/references, and the baseline verifier. No Git mutation. Do not change system packages, other project folders, account settings, or global configuration.

## Task 1 — Establish baseline and isolated environment

1. Confirm project root. Run `python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json`.
2. If hashes differ, stop before writing and report the mismatch. Otherwise claim the exclusive worker lock. Existing lock means report BLOCKED; do not remove it.
3. Record Python executable/version, platform, package tool availability, and Docker/WSL availability with short read-only commands. Do not start services or install Docker.
4. Create a virtual environment under `.local/w01/venv` using a compatible available Python. Use its explicit interpreter for installations and spike runs. Candidate Python 3.12 is not mandatory if another available runtime works.
5. Try the approved dependencies: Docling, pdfplumber, Pydantic, the OpenAI-compatible SDK or httpx/requests transport, and a minimal PDF rendering helper if needed. Prefer Python standard library for hashing/reporting. Pin exact successful versions in the spike dependency files; record installation failures.
6. If Docling installation or execution fails, use the allowed pdfplumber path and record the limitation. Do not repeatedly reinstall or substitute an unrelated OCR service. A compatible local renderer is sufficient; no paid external OCR.

## Task 2 — Build the narrow command-line spike

Provide `spikes/w01/run.py` with subcommands:

- `inspect-env`: reports versions/configured variable names only; never secret values.
- `fetch-source`: fetches approved source(s), hashes bytes, records source metadata.
- `parse-source`: extracts the selected sections and produces page/anchor artifacts.
- `probe-provider`: performs bounded real requests only when deliberately invoked and key is present.
- `self-test`: validates schemas, anchor integrity, local failure paths, synthetic labeling; no network or model calls.
- `report`: summarizes artifacts, results, unresolved gates, and reproduction commands without modifying canonical status.

Equivalent internal implementation is allowed; preserve these command names so Codex has predictable entry points. No catch-all command should unexpectedly incur provider charges. Exit nonzero for failed mandatory operations. Missing credentials must produce a clear configured-variable message without values and cannot be reported as a live success.

Write all generated data under allowed paths. Source paths/configuration are explicit; do not search the filesystem for documents or credentials.

## Task 3 — Establish an honest corpus manifest

1. Retrieve the ST source using the contract URL. Record response status, final source URL without credentials, retrieval UTC, SHA-256, size, actual page count, document ID/revision/date if extractable.
2. Store original bytes only under `.local/w01/sources/`. Record public metadata in `fixtures/manifests/w01/sources.json` with schema version 1.
3. Locate reset-related entry and revision-identification entry from actual contents. Candidate section labels 2.2.18 and 2.2.5 must be checked. Preserve table headers, revision columns, and footnotes that govern meaning.
4. Inventory entry identifiers/headings for the selected document where practical. State whether inventory is complete. Explicitly select a small supported subset; never claim the full source was interpreted.
5. Retrieve the NXP notice metadata and identify linked current/historical errata candidates. Make at most three targeted attempts to locate authentic older/newer documents; do not spend the packet on open-ended research or bypass unavailable access.
6. If authentic versions cannot be obtained, prepare a tiny original synthetic old/new pair under `spikes/w01/fixtures/` with an added erratum and a changed condition. Label every object SYNTHETIC and distinguish it from NXP source material. This proves fixture availability, not the change engine.
7. Record redistribution status as known/unknown with a source reference. Unknown rights means no public full-document bundle.

## Task 4 — Produce inspectable source anchors

1. Parse only the relevant pages with Docling where supported. Record parser/version and fallback use per output; whole-document text inventory may be lightweight, but avoid unnecessary model/OCR processing.
2. Persist normalized anchors with document hash, zero-based page index, printed page label if available, section, text, normalized bbox in [0,1], original page dimensions/rotation, parser provenance, and anchor ID.
3. Normalize to a documented coordinate convention: top-left origin, x right, y down, bbox [left, top, right, bottom]. Preserve original parser coordinates separately when needed to debug conversion.
4. Render at least one selected page and a copy with anchor rectangles using an approved local renderer. Inspect that the source condition and its governing headers/footnotes are represented. A bounding box may cover multiple related anchors; do not guess a box for text that was not located.
5. Put page renders and extended extracted text under `.local/w01/`; public-safe report references them by relative path. If a required condition cannot be anchored, report that limitation and do not manufacture a citation.
6. Create a coverage summary listing selected entries, successfully anchored entries, missing/ambiguous entries, and unsupported extraction. This is not a product applicability result.

## Task 5 — Verify the real provider path within a small budget

Only this task invokes inference. The human-approved workflow authorizes a bounded feasibility probe using intentionally supplied project credentials. Do not obtain credentials from other accounts/projects or redeem promotional codes.

Limits for this packet: maximum four inference requests total (user-approved amendment of 29 October 2026; used attempts remain counted), including retries/repair; maximum 16,000 input tokens estimated per request; maximum 8,192 output tokens per request; maximum estimated aggregate inference spend US$0.25 using verified current pricing. Text-first; no image requests until documented input/billing behavior is clear. If cost cannot reasonably be bounded, report BLOCKED for the paid probe. Disable SDK automatic retries or account for them explicitly so the request cap is real.

1. Read the current official quickstart/structured-output guidance. Record accessed URLs and date. Use the exact documented endpoint/parameters; do not guess vision payloads or reasoning flags.
2. Check presence of NEBIUS_API_KEY without printing it. If absent, complete Tasks 1–4 and 6, implement/test the adapter with clearly marked local fixtures, and return PARTIAL/BLOCKED for live access. Do not pause the entire useful assignment to hunt for a key.
3. If the provider documents a model-list endpoint, a bounded read-only query may confirm the candidate. Do not dump account-wide data. An unavailable model is a blocker to report, not permission to substitute another provider.
4. Send one relevant real source excerpt plus anchor IDs and necessary table context. Ask for a structured DRAFT containing source identity, affected device/revision statements, trigger conditions, exceptions, workaround restrictions, unresolved interpretation fields, and supporting anchor IDs for each claim. No product safety verdict and no invented missing revision.
5. Validate with Pydantic. Verify all referenced anchors exist and refer to the expected immutable source. A schema-valid result is not semantically accepted. Preserve a short reviewer checklist comparing actual source vs interpretation.
6. If budget permits, use a second request with an explicitly synthetic excerpt that omits revision/condition information. Confirm output leaves it unresolved rather than supplying an invented value. A local assertion reports pass/fail honestly; do not change the expected outcome to accommodate hallucination.
7. The approved v4 continuation allocates remaining global attempt 3 to the corrected real-source case and attempt 4 to the synthetic case only after passing real-source checks. No fifth request is authorized. Provider timeout with uncertain usage counts as an attempt. No recursive retry loop.
8. Record model actually returned, endpoint, status, request ID where available, latency, usage, finish reason, and estimated spend. Store redacted exact payload artifacts privately. Missing usage remains unknown, not zero. If output is empty/truncated, expose that failure.
9. Cached/mock output never passes the live-request gate. Lack of strict JSON mode may use server-side parsing/validation with a recorded limitation; it may not bypass citation or review checks.

## Task 6 — Local checks and feasibility report

Implement a small meaningful self-test suite for: valid fixture accepted by schema; malformed JSON/schema rejected; nonexistent anchor rejected; bbox/page validity; missing revision remains unresolved in the fixture; synthetic artifacts labeled; source hash mismatch detected. These tests must run without network or credentials. Do not write production evaluator tests or pretend this spike passes P1.

Produce:

- `spikes/w01/README.md`: environment setup, subcommands, exact reproduction sequence, required variable names, known limits.
- `docs/evidence/W01/FEASIBILITY_REPORT.md`: observed source/parser/provider results, gate table, versions, cost/latency when available, unresolved decisions.
- `docs/evidence/W01/ENVIRONMENT.json`: redacted runtime/capability metadata.
- `fixtures/manifests/w01/sources.json`: source and synthetic-fixture metadata/provenance.
- `.local/w01/results/`: raw local artifacts and check output, with references from the report.

Hosting feasibility is read-only: identify local container support and required hosted account/configuration names. Do not enumerate account projects, provision infrastructure, choose a paid plan, or assert account access without evidence. Record a proposed compatible route for Codex to freeze.

## Required commands and evidence

After environment creation, use its explicit Python interpreter, e.g.:

```powershell
.local\\w01\\venv\\Scripts\\python.exe spikes/w01/run.py inspect-env
.local\\w01\\venv\\Scripts\\python.exe spikes/w01/run.py fetch-source
.local\\w01\\venv\\Scripts\\python.exe spikes/w01/run.py parse-source
.local\\w01\\venv\\Scripts\\python.exe spikes/w01/run.py self-test
.local\\w01\\venv\\Scripts\\python.exe spikes/w01/run.py probe-provider
.local\\w01\\venv\\Scripts\\python.exe spikes/w01/run.py report
python scripts/verify_execution_framework.py --baseline docs/execution/baselines/W01-baseline.json
```

Run probe-provider only under Task 5's conditions. Record actual executable paths if different. A command list in README is not evidence it ran; capture actual exit codes and result paths.

## Acceptance gates — Codex decides

| ID | Required evidence |
|---|---|
| W01-G1 | Protected baseline unchanged; outputs inside owned paths; isolated environment reproducible |
| W01-G2 | Real source bytes/hash/revision provenance and explicit selected coverage |
| W01-G3 | At least one real condition with inspectable page/anchor/context and recorded parser provenance |
| W01-G4 | Real intended NVIDIA-on-Nebius response, usage/limits recorded, draft schema/citation checks; no secret exposure |
| W01-G5 | Missing-information negative case and local invalid-input checks with honest outcomes |
| W01-G6 | Authentic change-source pair or explicitly synthetic fallback; no invented manufacturer revision |
| W01-G7 | Feasibility report identifies actual environment/provider/hosting uncertainties and next contract decisions |

Absent credentials may leave G4/G5 live portions unresolved while useful artifacts are retained. Codex may accept specific findings, but P0 is not automatically complete. Model interpretation errors are evidence to review, not a reason to hide results.

## Stop conditions and handoff

Stop dependent work for protected-hash mismatch, preexisting worker lock, unauthorized path need, unavailable required model, exhausted budget, or contract conflict. Complete independent assigned tasks when safe and useful. No production scaffolding as filler work.

Write `docs/execution/handoffs/W01-attempt-01.md` if absent; otherwise use the next unused attempt number. Follow the template, list all paths/checks, recheck baseline, stop owned processes, release your own lock, and stop editing.

Return this exact prompt with the actual attempt path:

> Review ErrataScope packet W01 revision 1. The DeepSeek worker has stopped editing. Read docs/execution/handoffs/W01-attempt-01.md and inspect the actual spike, source manifest, and local artifacts against docs/execution/packets/W01-feasibility.md and its protected baseline. Run focused independent checks; do not infer a live-provider pass from mocks or a handoff claim. Record acceptance, partial findings, or one consolidated repair assignment. If all required gates pass, freeze the observed contracts and prepare W02 with its accepted baseline. Do not start an unbound future packet.


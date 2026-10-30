# S01 independent review — local implementation accepted

30 October 2026. **ACCEPTED: the reduced local cited-interpretation/review application. Public release remains incomplete.** This is not acceptance of full W04/P3, hosted P2, real applicability, or the failed W04 live omission case.

## Evidence inspected and reproduced

- Worker protected baseline453/453 PASS before coordination updates; all 14 starting backup files match. Worker gate-report file bindings 12/12 verified. Existing W01/W04 ledgers remain byte-identical at 4/4 and 2/2; no new provider requests or key access.
- Retained actual database/artifacts:157 rows, 116 readable, 41 missing; the missing IDs exactly match the historical set. Actual source bytes,39 anchors, 53 coverage entries and 9 claims remain bound. Saved public demo draft exactly matches retained live draft content. The tested image matches 49 workspace Python sources.
- Independent focused real-PostgreSQL suite:8/8 PASS, including two added transaction failure/concurrency regressions. Worker 110 foundation, 92 domain and 11 W04 checks are retained evidence; those unchanged suites were not repeatedly rerun for UI-only corrections. Two post-suite psycopg ResourceWarnings were observed; assertions passed.
- Independent real HTTP checks 16/16 PASS: authorized source/draft summaries, unrelated/anonymous denial, preserved request identity, truthful cached import, two cases, unknown source/revision, unlocated synthetic citations, JSON 404 and real Markdown exports without credential markers.
- Actual browser: cross-entry citations, opening identity context, review then rejection, revision 2 survives API recreation, real Markdown download, synthetic selection, desktop 1586×992 and narrow 390×844 without horizontal overflow. Screenshots and sanitized results are in `evidence/S01-review-01/`.
- Source-only checkout with no private `.local`, host venv or dev keys: image built, new isolated volumes initialized, authentication generated, migration applied, recorded snapshot imported, original offline example prepared. Restart reuses source/import/history. Setup with the pinned PDF explicitly supplied passed. **Automatic ST download timed out in this environment**; `-PdfPath` is the verified fallback and remains a documented external-source prerequisite.
- The actual worker partial release manifest returns exit 2 with integrity_pass=true and gate_pass=false. Historical reports were preserved, not rewritten as successful release evidence.

## Direct release-critical corrections

1. Review row and idempotency receipt now commit atomically. Draft-row locking precedes receipt lookup; identical concurrent requests replay one row, and injected receipt failure leaves no orphan review.
2. Citation selection changes to the cited entry and opens collapsed identity/legend context. Previously a page 7 citation could leave the pane on section 2.2.18 with no highlight.
3. Review history follows pagination; switching cases clears an unsaved note. Synthetic anchors are labeled unlocated, with no invented physical PDF page in UI or exports.
4. Clean launcher builds before bootstrap, uses PowerShell readiness checks instead of a private venv, fails on Docker errors, isolates the port/auth files and refreshes short-lived local tokens. Import is resumed even if setup stopped after writing its state file.
5. Recorded importer verifies actual source bytes, is local-only and marks new imported drafts `cached`; original live rows/ledgers are unchanged. Clean demo now includes the original synthetic/offline case as well.
6. Removed an accidental untracked root npm-init manifest (private backup retained), which claimed ISC and an unusable test script. The real frontend package remains pinned and original code license is MIT. Added ignores for local browser traces/downloads.

No provider recovery redesign, registry expansion or new inference budget was introduced. No hosted service or publication has been fabricated.

## Release decision and next step

Freeze this local application scope. Git checkpoint the implementation and corrections under standing public authorization; do not create a W04-accepted tag. Use `RELEASE_NEXT.md` for remaining actions. Public YouTube video and actual Devpost submission/confirmation are still required. The official track matching this application is **Best Apps and Agents**.

The user requested a silent video under 3 minutes with their name and brief introduction followed by real demo footage. Before producing it, inspect the MajuPilot Desktop project and its HyperFrames workflow, as recorded in `release/VIDEO_PREFERENCES.md`. No video has yet been produced or uploaded by this review.

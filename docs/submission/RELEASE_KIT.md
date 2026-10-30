# Release kit — prepare now, finalize from actual build

State: **DRAFT / NOT_READY / NOT_SUBMITTED**. Templates below are not claims that features or hosting already exist. Finish against the chosen S01 release scope. Official requirements: [hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules), checked 30 October 2026.

## Distribution decision

Use a simple stable hosted demonstration only if its real authentication, private storage and free judge access can be verified quickly. Do not disable hosted fail-closed checks to expose the local development stack publicly. No temporary unauthenticated tunnel to the full local API, hard-coded public JWT/key, unlimited anonymous inference or exposure of the Docker socket/database.

Otherwise publish a working test-build/release URL with source, pinned setup, local prerequisites, launch commands and a curated case. Verify it from a fresh checkout/environment without hidden `.local` artifacts or developer session. Include an allowed download/import mechanism for the genuine manufacturer document with checksum verification; a public repository alone is not a working test-build demonstration. Do not put full vendor PDFs or private payloads into the release.

Judge access must be free and usable through the end of judging. A build that silently requires the judge to purchase inference credits or obtain inaccessible private files is not yet verified. Decide and test how the recorded example and intended runtime path are available without exposing the owner's key. If credentials are needed for a private hosted demo, provide scoped testing access through submission instructions, not public owner credentials. Keep this as an explicit unresolved release gate until exercised.

## Release checklist

- [ ] Chosen actual release scope and supported entries recorded; no unimplemented claims.
- [ ] Main and unknown/error browser journeys pass against real API.
- [ ] W04 actual provider evidence verified; live/cache/synthetic states clear.
- [ ] Source identity/anchors/coverage and reviewed-rule semantics checked.
- [ ] Fresh setup/test build or actual hosted demo works without the developer's session.
- [ ] Free judge access confirmed; availability retained through judging.
- [ ] Public repo URL and release commit/tag correct.
- [ ] Open-source license file exists and applies to project code; third-party/source rights listed separately.
- [ ] README quickstart, environment variable names, model/provider role, supported scope, known limits and test commands match actual build.
- [ ] Secrets scan/staged-path review; no .env/private keys/vendor PDFs/raw model payloads.
- [ ] Public YouTube video <3 minutes shows the actual working app.
- [ ] Description, track, testing instructions and provider/tool feedback complete.
- [ ] Links tested signed out; final submission confirmation observed before deadline.

## Video shot list — target 2:35

| Time | Shot and narration purpose |
|---|---|
| 0:00–0:15 | Problem: manufacturer errata contain revision-specific qualifications that are easy to miss. Show the actual selected document |
| 0:15–0:40 | Run/inspect the genuine Nebius/Nemotron interpretation. Identify actual live versus previously recorded/cached status |
| 0:40–1:10 | Click citations; show source context, revision and unknown fields; disclose selected coverage |
| 1:10–1:35 | Demonstrate explicit review/reject and why model draft alone is not an accepted rule |
| 1:35–2:10 | Preferred: facts → applicability → change missing fact → new result. Fallback: unresolved case, correction/rejection and review summary. Use only working features |
| 2:10–2:25 | Export or reproducible record; briefly show the result's source/version provenance |
| 2:25–2:35 | Supported scope, repo/test-build URL, and one clear limitation |

Record actual screen behavior; no mockup passed off as software. Do not show credentials/terminal environment. Avoid copyrighted music. A slow provider call may be shortened in editing only if that edit is disclosed rather than presented as a measured latency. Do not promise sub-second inference or general engineering certification.

## Submission text draft — edit to match accepted release

**Working title:** ErrataScope.

**One-line pitch:** Turn selected manufacturer errata into cited, reviewable interpretations, with uncertainty kept visible.

**Problem:** Engineers must connect device revisions and operating conditions to dense manufacturer notices. Missing a qualification or treating missing information as a negative answer can lead to the wrong decision.

**What it does:** Describe the actual selected-source workflow and approved UI. Include deterministic applicability and changed-fact reassessment only if delivered and semantically verified; otherwise describe interpretation/review only. Name ES0620 Rev 5 and the selected scope, not universal document support.

**How AI is used:** NVIDIA Nemotron interprets bounded manufacturer passages through Nebius Token Factory. Structured outputs are validated and linked to exact source anchors. Review remains explicit. Accepted deterministic evaluation, if included, uses separately reviewed rules and scoped facts rather than asking the model to declare hardware safe.

**Recommended track:** Best Apps and Agents, subject to the final form and actual delivered behavior. Do not select Physical AI merely because the source documents concern chips.

**Provider feedback from actual W01 evidence:** Initial reasoning consumed the output budget without final JSON. Explicitly disabling thinking produced a final response. Missing-information claims then exposed a citation-schema mismatch; the accepted prompt separated unresolved fields from cited claims. Preserve exact model/settings and mention W04 results only after verification.

**New work/reuse:** Record the genuinely new ErrataScope implementation; list used open-source libraries and standard infrastructure. VerifForge is a separate project; do not claim its implementation/features as ErrataScope work.

**Testing instructions:** Fill actual demo/test-build URL, supported platform, prerequisites, exact setup/start steps, sample source acquisition, any safe testing access, normal/unknown-case steps, expected behavior and limitations. No placeholders may remain at submission.

## Publication and submission actions

Codex owns reviewed Git/GitHub checkpoints under standing public authorization. While W04 owns the workspace, do not stage/commit/push its unreviewed partial files. Preserve the separate planning artifacts and checkpoint them with the next safe reviewed handoff. Actual Devpost submission must use the final reviewable entry and authorized account, with user confirmation of any entrant declarations; never report submitted without platform confirmation.

The current official judging end is 23 December 2026 noon Pacific / 24 December 04:00 MYT; older project notes are stale. Final release must use the current rule dates and actual accessible links.

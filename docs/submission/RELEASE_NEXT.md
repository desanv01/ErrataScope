# Release completed — submission confirmed

**Current status: SUBMITTED.** The user completed final submission, and Codex observed Devpost's **“Project submitted!”** banner at https://devpost.com/software/erratascope. The public video is https://youtu.be/oD1uhOq6UHk. The source test build is available at https://github.com/desanv01/ErrataScope/releases/tag/hackathon-2026-local-demo.

Read [the final submission receipt](release/SUBMISSION_RECEIPT.md) for verified links, artifact hashes and scope. Chrome computer use was stopped at the user's request. **Do not repeat upload/submission or start another worker packet.** Keep public judging links available.

## Archived pre-submission instructions

The remaining text records the earlier release checklist and its then-pending state; it is retained as history, not as current work to execute.

The local S01 workflow is accepted; its public submission is not complete. Do not dispatch W05–W10 or another general implementation worker.

## 1. Application preview

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/submission/start-clean.ps1 -NoBuild
```

Use `-NoBuild` only after building this version; omit it on a new checkout. Open http://127.0.0.1:18081/. Both recorded-live and synthetic/offline cases are included. If downloading the manufacturer source fails, supply the exact PDF with `-PdfPath "C:\path\to\es0620.pdf"`. The provided-PDF path is independently tested; an automatic download timed out during review. Make this prerequisite clear in judging instructions. Stop using `scripts/submission/stop-clean.ps1`; retain volumes.

## 2. Silent video — next Codex work

Read `release/VIDEO_PREFERENCES.md` and inspect the actual MajuPilot Desktop project before authoring. Reuse its applicable HyperFrames workflow and installed skills. Produce an under-three-minute silent video with the user's name, brief project introduction and actual application footage. Use restrained captions and accurate recorded-live/synthetic labels. Never show secrets or pretend a stored result is a fresh provider call.

Suggested duration: 10 seconds intro;20 seconds problem/workspace;35 seconds recorded provenance and cross-entry citations;20 seconds unknowns/coverage;30 seconds review/reject/history;20 seconds export;20 seconds original synthetic case;5 seconds closing. Approximately 2m40s. Remove or shorten optional steps if footage exceeds the limit. Do not spend the remaining window rebuilding the product.

Exact next Codex prompt:

> Prepare ErrataScope's silent demonstration video under three minutes. Read docs/submission/S01-review-01.md, docs/submission/release/VIDEO_PREFERENCES.md and docs/submission/release/DEMO_SCRIPT.md. First locate and inspect my MajuPilot project folder on the Desktop, understand its actual HyperFrames/video workflow and relevant installed skills, then use the appropriate same techniques for ErrataScope. Include my name and a brief project intro, followed by actual application footage with minimal captions; no voiceover needed. Preserve recorded-live versus synthetic/offline labels, source/coverage uncertainty and human-review semantics. Produce and verify a local final video; do not change the accepted application or publish/upload without the release instruction. Then give the exact YouTube and Devpost steps and remaining fields.

## 3. Public release fields

- Code URL: https://github.com/desanv01/ErrataScope
- Test-build instructions: https://github.com/desanv01/ErrataScope/blob/main/docs/submission/release/TESTING.md
- Track: **Best Apps and Agents Track**.
- Description/tool feedback: `release/SUBMISSION_COPY.md`.
- Video: upload the verified final file to **public YouTube**, then add its actual URL. No video URL exists yet.
- Test access: free local recorded-demo workflow, Windows/Docker instructions and pinned-source requirement. No provider key is needed for this demonstration. Do not claim hosted production availability.
- Keep code and testing access available through judging. State clearly that the project makes actual NVIDIA/Nebius runtime calls through its backend and that the free demonstration replays the recorded output; it does not make a fresh inference call on page load.

## 4. Submission timing and confirmation

Official deadline: **31 October 2026, 01:00 MYT** (30 October, 10:00 am PDT). Target submission 00:15 MYT, leaving upload/form contingency. The official rules require a public source repository/license, working demo/hosted app/test-build URL, project text, track, tool feedback and public YouTube demonstration under 3 minutes. Source: https://nebiusglobalaihackathon.devpost.com/rules (checked 30 October 2026).

Complete the actual Devpost form and verify its submission confirmation. A local video, saved draft, Git push or plan is not a submitted entry. No video upload or Devpost submission has occurred in S01 review.

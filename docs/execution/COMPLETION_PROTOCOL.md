# Codex completion and next-step protocol

Standing user instruction, 29 October 2026: after each phase or W-packet completion, Codex performs the appropriate Git/GitHub actions and supplies the next exact DeepSeek prompt. A review must not end with an unexplained status and no next action.

## After every worker review

1. State the acceptance result, evidence, and remaining blockers. Worker completion is not packet acceptance.
2. If incomplete, issue one scoped repair or continuation assignment with its protected baseline and exact prompt. State any input the human must provide first and how the worker returns for review. Do not dispatch a dependent packet through an unmet gate.
3. If accepted, update canonical packet/phase status and record the accepted implementation/contracts.
4. Perform the applicable Git/GitHub checkpoint below. Record actual commit/PR URLs or an explicit concrete blocker; do not claim it happened if it did not.
5. Bind the next eligible packet to actual accepted files/contracts, validate its baseline and links, and provide the exact pasteable worker prompt plus its saved path. Where no packet is eligible, identify the specific human input or external event needed instead.

## Git/GitHub checkpoint after acceptance

Codex owns Git and GitHub; DeepSeek never mutates Git. The user's standing instruction authorizes routine repository setup, scoped branches, accepted-work commits, pushes, and review PRs for this project. Follow an existing repository's workflow when present. For ErrataScope, the user intentionally chose public visibility and explicitly authorized reviewed public checkpoints on 30 October 2026; see [standing authorization](decisions/2026-10-30-public-repository.md). Do not request this same visibility confirmation again. For a different/new repository with no visibility decision, prefer private initial publication. Verify the authenticated owner and intended repository before creating or pushing. Use the current project name unless the user selects a replacement; do not let an optional naming discussion block a private checkpoint.

Inspect the actual diff and staged paths. Exclude keys, `.env`, `.local`, raw provider payloads, vendor PDFs, environments, and unapproved third-party material. Inspect public-safe reports and preserved research for sensitive content before staging. Preserve unrelated work. Use descriptive commits stating the accepted outcome and actual validation. Push only the intended branch. If a PR is created, attach it to this Codex task. Report CI status when relevant; do not silently merge merely because a PR exists. Avoid duplicate commits for packet and phase completion when one checkpoint covers both.

If authentication, repository identity, network policy, or another real prerequisite blocks publication, finish the safe preparation, record the precise blocker and next action, and continue any independently eligible planning. Never substitute a vague promise for the checkpoint result.

## Current application

W01/P0, W02/P1 and [W03 local foundation](reviews/W03-review-05.md) are accepted. W03 commit `99090c6aed74c0378eeae02860f33027b9cbca2d` and tag `w03-local-accepted` are pushed and remotely verified. W04 is now partially reviewed; [S01](../submission/S01_BINDING.md) is the only next dispatch. UI direction is approved; browser acceptance and full hosted P2 remain open. Follow [STATUS](STATUS.md), not historical repair prompts.

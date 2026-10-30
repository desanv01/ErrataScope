# Active-worker transition and Codex handoff

## Right now

Leave the existing W04 worker running. Do not paste a new implementation assignment into it, launch another implementation worker, edit its protected files, change its caps, delete its lock, or stage its partial code. Codex is preparing only new, disjoint planning/mockup files. This is the human-approved exception for planning alongside the single product-code writer, not authorization for parallel implementation.

The new release plan governs the deadline target. It does not retroactively change W04's protected assignment. Canonical status/baseline changes happen after a clean handoff. Partial W04 work may support the reduced release only after independent review of the actual subset; do not mark full W04 accepted because only a subset is shipped.

## If still running at 19:00 MYT — progress prompt

```text
Please give a concise W04 progress checkpoint at the next safe task boundary. Keep following your current bound assignment; this message does not authorize scope changes or a new packet.

Report: what is actually implemented; checks already completed; provider reservations actually consumed and results; remaining tasks/blockers; and the next concrete milestone. Do not print credentials. Do not create extra live calls for this update. Continue the current assignment unless I explicitly request a clean stop.
```

Send the response to Codex. Do not stop a nearly completed useful operation solely because the clock reached the checkpoint.

## If Codex/human decides to stop and narrow — controlled-stop prompt

```text
Stop W04 at the next safe checkpoint so Codex can review and narrow the deadline release. Do not start new features or paid calls. Let any already dispatched paid request settle and preserve its reservation/evidence; do not kill it and assume it was free.

Preserve all work, files, data volumes and history. Write docs/execution/handoffs/W04-attempt-01.md as PARTIAL, listing implemented paths, commands/tests actually run, failures, remaining work, current migration state, jobs/services and every provider reservation. Do not claim unrun checks passed or full acceptance. Stop only your owned work safely, retain volumes, release only your lock once ownership is settled, then stop editing. Do not reset/revert Git, erase outputs, switch models or dispatch another packet. Return the handoff path for Codex review.
```

If that handoff already exists, never overwrite it: report the existing handoff and use a clearly named append-only addendum after coordinating with Codex.

## Exact next Codex prompt — normal or partial handoff

```text
Review the stopped W04 worker against its original protected baseline, then apply the user-approved deadline plan in docs/submission/START_HERE.md and docs/submission/DEADLINE_PLAN.md. Read the actual W04 attempt handoff and artifacts. Preserve W01/W02/W03 evidence, all live reservation history, existing data and the UI/imagegen gate.

Prioritize the actual shipped journey. Independently verify the required source/provider/review/authorization path; distinguish local/mock/cached/live evidence. Record accepted, partial, blocked and deferred scope honestly. Fix small isolated defects directly and run focused affected checks; consolidate larger release-critical repairs. Do not require completion of all original W05–W10 ambitions before a narrowed submission is prepared.

Read docs/submission/S01_SUBMISSION_SLICE.md. If enough backend scope is safe and the visual design is explicitly approved, bind S01 to actual observed files/routes/contracts, exact writable paths, commands and a fresh baseline; issue its exact DeepSeek start prompt. If design is still pending, complete its approval step; independent backend fixes may be separately bound without UI. If applicability cannot be expressed faithfully or connected by the feature-freeze cutoff, select the cited-interpretation/review fallback and state that limit. Do not dispatch an unbound template.

Perform the appropriate scoped Git/GitHub checkpoint for accepted work under the user's standing public-repository authorization. Always finish with a concrete next action and exact prompt. Reserve time for the working test build/demo, public video, release materials and actual submission before 31 October 2026 01:00 MYT.
```

## Activation checklist — Codex only after handoff

1. Verify no worker still owns mutations, transactions or dispatched provider calls; inspect lock/handoff rather than guessing a stale lock.
2. Record actual W04 scope, inventory/hash preservation, safe migration head, source/provider evidence and unresolved defects. No acceptance from worker claims alone.
3. Read the current clock; choose preferred/fallback release scope and record what is deferred.
4. Record explicit imagegen approval if received; do not equate approval of the deadline plan with visual approval.
5. Bind the smallest remaining integration work against observed OpenAPI and files, with no assumptions that W04 delivered every proposed route. Populate S01 dispatch manifest before handing it to a worker.
6. Update canonical execution status/completion protocol then, preserving historical manifests; create new baseline, don't rewrite an old baseline to conceal changes.
7. Checkpoint reviewed scope, provide start prompt, and follow the timeboxes. Do not restart the whole foundation review.

# UI proposal — one evidence-review workspace

Status: **VISUAL DIRECTION APPROVED; S01 IMPLEMENTATION BOUND**. The user explicitly approved the displayed mockup on 30 October 2026. The canonical UI gate is now updated following W04 handoff. Codex notified the user before this research/mockup work. No application UI has been implemented.

## Shortlist actually inspected

1. **VoiceStudio** — discovered on the [Trendshift weekly list](https://trendshift.io/weekly), then inspected its official [voice-cloning screenshot](https://raw.githubusercontent.com/debpalash/VoiceStudio/main/docs/media/electron/voice-cloning.png). [Repository](https://github.com/debpalash/VoiceStudio). Visible strengths: compact navigation, selected-item list, large task area, adjacent detail inspector, restrained dark surfaces and a clear primary action. Adapt its organized work area; omit the many tool categories and decorative outer frame.
2. **RAGFlow** — inspected a frame of its official [chunking/source demonstration](https://raw.githubusercontent.com/infiniflow/ragflow-docs/refs/heads/image/image/chunking.gif). [Repository](https://github.com/infiniflow/ragflow). Visible strengths: answer/source coexistence and a readable original-document pane. Adapt direct citation inspection; avoid a generic chat-first product and avoid the oversized document overlay obscuring the task.

Reference images were viewed locally and remain private under `.local/submission-planning/references/`; they are not copied into the public product or treated as assets licensed for reuse. No claim that both projects rank on the current weekly list: only VoiceStudio's listing was observed. Flowise/Khoj repositories were also consulted, but their actual UI was not inspected in this pass and they are not visual evidence for the chosen direction.

## Proposed direction

One compact desktop workspace: dark charcoal navigation and review controls, a warm-white source document pane, subtle blue/teal action color, amber for unresolved/review-required states. No ornamental charts, gradient hero, giant chat box, or broad dashboard. Semantic state uses words/icons as well as color.

Navigation is limited to sources/selected entries. Source context and cited draft sit together. The primary action is explicit review, with reject/request-change nearby. Optional facts/assessment appears as a panel/tab only if the backend journey is delivered. Show source revision, selected coverage, draft/review state and provider provenance separately. Unknown is not a safety verdict.

The proposed image uses illustrative layout content, not engineering evidence or a completed app screenshot. Implemented text, conditions, citations and status must come from actual reviewed backend data; never copy invented mockup technical values into fixtures or code.

## Proposed states to implement after approval

- Source selected / no extraction yet.
- Extraction running and bounded failure.
- Cited draft awaiting review, source context visible.
- Rejected/unresolved draft with a clear explanation.
- Reviewed rule + fact form + unknown/applicable result only if the preferred scope passes.
- Explicit partial coverage and export state.

## Approval record

- Generated mockup: [approved-workspace-v1.png](ui/approved-workspace-v1.png).
- Prompt: [ui/MOCKUP_PROMPT.md](ui/MOCKUP_PROMPT.md).
- Generation method: built-in imagegen, as explicitly requested by the user. The 12ui and imagegen skill guidance was read; no HTML/code conversion or application implementation has started.
- User visual decision: **Approve this direction**. See [approval record](ui/approval.json).
- Final design brief: [approved brief](ui/APPROVED_DESIGN_BRIEF.md); image hash recorded in approval.json. Bind worker ownership at W04 handoff.

The visual decision is complete. Do not ask for the same approval again; use the exact approved image/brief for S01. Do not rewrite the active W04 protected UI gate mid-run; preserve the decision here and bind it after handoff.

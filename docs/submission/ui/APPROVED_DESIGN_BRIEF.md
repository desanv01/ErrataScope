# Approved workspace v1 — implementation brief

User decision on 30 October 2026: **“Approve this direction”** in response to the displayed imagegen mockup. Scope: the dark workspace, light source pane and adjacent interpretation/review panel for the deadline build. This is explicit visual approval, not application acceptance or authorization to edit during W04's active run.

Authoritative image: [approved-workspace-v1.png](approved-workspace-v1.png). Machine-readable decision/hash: [approval.json](approval.json). Original generation prompt: [MOCKUP_PROMPT.md](MOCKUP_PROMPT.md). Built-in imagegen was used; no external reference image was copied into the mockup.

## Preserve

- Compact dark header with ErrataScope, current project/source context and secondary export action.
- Narrow selected-source/entry navigator. No generic marketing page or expansive admin menu.
- Main source pane beside the interpretation/review pane, so citations can be inspected without losing the draft.
- Readable light source paper/excerpt against the dark workspace; restrained blue/teal action accent and amber uncertainty/review-required treatment.
- Source identity, selected coverage, draft/review status, unresolved information, citation controls and explicit review/reject actions.
- Practical type sizes, clear contrast, keyboard focus, sensible loading/empty/error/permission states. Status must use text, not color alone.

## Correct illustrative content during integration

The image is a layout target, not source evidence. The pictured **12 / 48** counter and page-12 citation are illustrative and must not be copied as factual metadata. The accepted ES0620 file has **38 physical pages**, and each actual citation must use its true located page/printed label. Likewise all prose in the white panel is illustrative: render actual authorized source text and exact citations. No hard-coded invented erratum statement, revision applicability, false live status or fabricated outcome.

"Review draft" opens or submits the explicitly supported review action; it must not automatically activate an executable rule. An interpretation review and an accepted AST rule are different states. Bind labels/actions to actual W04 semantics. Source-panel highlights require real geometry; otherwise show an honest extracted excerpt with citation metadata rather than fake rectangles.

Facts tab and assessment actions are included only if the preferred submission scope is actually implemented. In the fallback, hide unfinished actions or explain unavailability plainly; do not add dead controls merely to match the image. Export becomes enabled only when an actual authorized summary is available.

## Responsive behavior and implementation

At desktop widths, maintain source navigation plus two content panels. At narrower widths, collapse the navigator and allow source/review tabs or stacked panes; preserve access to citations and actions without horizontal overflow. Keep the main review action discoverable.

Use the agreed React/Vite/TypeScript frontend and the existing API, with exact paths/dependency pins supplied by S01 binding after W04 review. Apply the applicable design skill's image-to-implementation workflow when binding; do not generate a replacement visual style. Never expose a provider key or bypass current backend auth to make the screenshot work.

Compare the implemented screenshot with this approved source at one desktop and one narrow viewport; check actual actions/data in a browser. One focused discrepancy pass is sufficient unless a functional/accessibility problem remains. No new four-candidate design exploration is required: the user has approved this direction.

## Coordination

The original protected `docs/execution/UI_APPROVAL_GATE.md` remains byte-unchanged while W04 runs. This separate decision is the pending activation evidence. At W04 handoff, Codex copies the explicit approval reference into canonical status, issues a new baseline and binds UI ownership. Do not refresh the old W04 baseline or allow a concurrent implementation worker.

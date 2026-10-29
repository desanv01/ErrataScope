# UI/UX research, imagegen, and human approval gate

Status: **PENDING — no UI direction approved.**
Authority: explicit human instruction on 29 October 2026.

## Required sequence, owned by Codex

1. Notify the human before starting UI/UX work.
2. Research https://trendshift.io/weekly and GitHub projects. Inspiration may come from any relevant interface category, not only engineering/errata products.
3. Present a manageable shortlist with actual UI screenshots/examples where accessible, repository/live-demo links, specific useful design elements, and tradeoffs for ErrataScope. Clearly distinguish inspected UI from inferred or unavailable examples. Popularity is not evidence of suitability.
4. Use imagegen to create ErrataScope mockups based on the research and the product's evidence-review workflow. Apply the required Codex design skills as appropriate. Label mockups as proposed design, not implemented screenshots.
5. Present the mockups and obtain explicit human approval, including revisions if requested.
6. Record approved artifact paths, user decision, design constraints, and the packet allowed to implement them. Freeze a worker-facing design brief.
7. Only then dispatch UI implementation. Workers reproduce the approved direction; they do not substitute their own design.

## Scope and enforcement

No application UI shell, page layout, styled components, or visual implementation may start before approval. Backend, API/schema, evaluator, persistence, corpus/provider, and source-coordinate inspection work may proceed independently. A PDF page render used to check extraction is technical evidence and is not an application UI design.

If a packet mixes backend and UI work, dispatch only an explicitly scoped backend portion while this gate is pending. Its UI acceptance remains incomplete. Do not mark the whole packet/phase accepted by omitting its UI deliverables.

## Approval record

- Inspiration shortlist: not prepared yet.
- Imagegen mockups: not generated yet.
- Human visual approval: not received.
- Approved implementation brief: not issued.
- UI worker dispatch: prohibited until the above sequence is complete.

# UI and design contract — revision 1

Five views: product snapshot, assessment list, evidence workspace, change review, review packet. Primary flow is identify → review interpretation → assess → resolve evidence → review changes → export.

Codex owns design research and mockup preparation; the human owns visual direction approval. **Explicit human requirement, 29 October 2026: notify the user before UI/UX work; research inspiration from https://trendshift.io/weekly and GitHub, including unrelated product categories; present a shortlist with visible UI examples and source links; generate imagegen mockups; wait for the user's review and approval before UI implementation.** Do not treat elapsed time, a preselected option, backend acceptance, or approval of the architecture as visual approval.

Before substantial UI creation, Codex must also perform the required design-first workflow available in its environment. DeepSeek implements the user-approved artifact; it does not assume Codex-only plugins are available in its harness. W01 contains no application UI work. Technical source-page/anchor renders in W01 are parsing evidence, not UI mockups, and remain authorized.

See [UI approval gate](../UI_APPROVAL_GATE.md). No worker may create an application UI shell, component layout, or visual design before that gate is explicitly approved. Backend/API/contracts and other independent non-UI work may proceed.

Evidence workspace coordinates source passage, interpreted condition, and product facts. Keep snapshot/baseline and coverage visible. Clicking a condition opens its exact anchor including needed table headers/footnotes. Unknowns expose causes and evidence requests.

Required states: loading, empty, unauthorized, parser/provider failure, unsupported interpretation, draft/reviewed, contradictory facts, changed baseline, ambiguous correspondence, export failure, review concurrency conflict.

Use text/icons alongside colors; keyboard-operable review; no misleading confidence percentages or safe/unsafe badges. Desktop can use panes; smaller screens use contextual tabs. No full PDF editing or generic chatbot needed.

Default stack: React/Vite/TypeScript, React Router, TanStack Query/Table, one component system, PDF.js. Do not substitute framework or invent design independently to bypass a missing design prerequisite. Non-UI backend work can continue while that prerequisite is pending.


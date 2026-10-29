# W01 draft → W02 domain mapping boundary

W01/P0 is accepted as a bounded feasibility spike. Its model output is a **draft
source interpretation**, not an active rule. W02 deliberately does not import the
spike, call a provider, or convert free-text claims into executable predicates.
This note records the reviewed conversion boundary reserved for W04.

## What transfers as provenance, not as executable semantics

| W01 observed item | W02 counterpart | Conversion rule |
|---|---|---|
| ES0620 Rev 5 bytes, SHA-256 `dcabef6a…d3fd`, 38 pages | `DocumentVersion` (`authority` manufacturer, `synthetic: false`) | Use exact sealed bytes/hash where the W04 conversion is human-reviewed; do not re-download here. |
| 78 anchors with page index, text, bbox, parser provenance | `SourceAnchor` | Re-create anchors with immutable IDs bound to the document hash. W01 anchor IDs are page-scoped parser ordinals and are not stable across reparses. |
| Selected sections 2.2.18 / 2.2.5 only | `CoverageManifest` selected entries | Selected-entry coverage is not whole-device coverage; keep `inventory_complete: false` unless W04 performs a complete inventory. |
| Document revision `Rev 5` | `DocumentVersion.revision` | Distinct from silicon revision; never copy the document revision into `component.silicon_revision`. |
| Silicon revisions Z/B/X rows and legends | Rule `affected` context / facts | `FactVersion` values require reviewed evidence; the derived matrix is navigation, not authority. |
| Draft claim fields and citations | Candidate `RuleVersion` AST input | Manual W04 authoring only; no mechanical free-text → AST conversion, no auto-activation. |
| `unresolved_fields` (device scope, trigger, exception) | Missing facts/selectors, unknown conditions | Missing information stays unknown. It must never become `constant: true`, empty exceptions, or an inferred predicate. |
| Workaround wording with any-address/example nuance | `workaround_documentation` / `workaround_restrictions` display text | Preserve qualifications (AXISRAM1 region requirement, example address); do not turn a clarification into an executable restriction. |
| Model categories that mislabel a remedy as an exception | AST structure | Human review must place workaround text under workaround fields, not `exceptions`. |

## Facts and scope

- W01 claims are not facts. W04 must author `FactVersion` rows from reviewed
  source text with `origin` (`declared`/`extracted`/`measured`/`external`) and
  evidence anchors.
- Accepted identity facts must reference existing anchors. Snapshot identity is a
  consistency constraint only; it is never a hidden second fact channel.
- Scopes are exact five-field values. Other component/build/profile facts are
  out of scope for an assessment and are never selected or treated as
  contradictions.

## Explicitly out of scope for W02

- No live adapter, provider call, credential use, or AI-generated rules.
- No persistence/API/jobs (W03), no UI, no deployment.
- No assertion that W01's draft is semantically complete: W01 accepted a bounded
  cited draft for two entries, not general accuracy or a whole-device assessment.

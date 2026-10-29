# W02 binding — deterministic domain v1

Codex-owned implementation contract, 29 October 2026. Binding for W02 revision 2, rebound after [W01/P0 acceptance](../reviews/W01-review-06.md). Read [the observed-contract freeze](W01-observed-contracts.md). This freezes the domain boundary; it does **not** claim the W01 model-output shape is production-qualified. Follow the shared domain/rule/data contracts as well as these concrete choices.

## Runtime and package

Use the existing Python 3.11.15 interpreter at `.local/w01/venv/Scripts/python.exe` and installed Pydantic 2.14.1. No dependency installation is needed. Use standard-library `unittest`, `decimal`, `hashlib`, `json`, `uuid`, `argparse`, and typing. New package path is `backend/erratascope_domain/`; use PYTHONPATH=backend for execution. No FastAPI, database, frontend, queue, Docker, or model SDK is needed in this packet. Record these two runtime/dependency pins in `backend/requirements-domain.txt`; do not copy the heavyweight parser requirements into the domain package.

Files: `__init__.py`, `models.py`, `selectors.py`, `rules.py`, `canonical.py`, `evaluate.py`, `replay.py`, plus local helpers only within this package. `backend/README.md` documents commands and domain API. Importing the package must not read credentials, initialize a provider, touch the network, or import the W01 spike/Docling.

## Public entry points and schemas

Export `parse_bundle(raw: dict) -> AssessmentInputBundle` and `evaluate(bundle: AssessmentInputBundle) -> AssessmentResult` from the package. `parse_bundle` validates all cross-references, domain limits, approved rule AST and accepted-input rules; it returns a sealed typed value or raises a structured validation error. `evaluate` also validates, so constructing a model directly cannot bypass invariants. Do not evaluate arbitrary Python or expressions.

Use `schema_version: Literal[1]`, extra fields forbidden, frozen models, immutable tuples/frozen child objects, strict bool/integer/text typing, and explicit nulls where specified. Valid JSON UUID strings become UUIDs through deliberate field parsing; do not enable general coercion to accomplish that. Document field descriptions and export JSON schemas under `docs/evidence/W02/schemas/`. All entity/version IDs are UUID strings, except selector/anchor IDs and human-readable entry identifiers. Content hashes are lowercase 64-character SHA-256 hex.

Minimum model definitions:

| Model | Required contents |
|---|---|
| ComponentIdentity | manufacturer, exact_part, family, package, silicon_revision as text-or-null, evidence_refs; all five keys required even when null |
| ComponentInstance | id, project_id, identity |
| ProductSnapshot | id, project_id, product_name, board_revision text-or-null, firmware_build_id, operating_profile_id, component_instances, predecessor_id nullable, content_hash |
| EvaluationScope | project_id, snapshot_id, subject_id (component instance), firmware_build_id, operating_profile_id; all nonempty, exact and mandatory |
| DocumentVersion | id, project_id, document_id/revision/manufacturer nullable, source_url nullable, document_sha256, authority manufacturer/forum/synthetic, synthetic bool, predecessor_id nullable |
| SourceAnchor | anchor_id, document_version_id, document_sha256, page_index >=0, printed_page_label nullable, section nullable, text, bbox nullable, page_width_pt/page_height_pt nullable, page_rotation, parser_name/version, geometry_kind located/synthetic_not_located |
| FactVersion | id, scope, selector, typed value-or-null, origin declared/extracted/measured/external, evidence_refs, review_state draft/accepted/rejected, predecessor_id nullable |
| FactSet | id, project_id, fact_versions (exact immutable versions), content_hash |
| RuleVersion | id, project_id, document_version_id, entry_id, review_state, reviewer_id nullable, target, trigger, exceptions, consequence, workaround_documentation, workaround_restrictions, anchors, predecessor_id nullable |
| CoverageManifest | id, project_id, document_version_ids, inventory_complete bool, discovered/supported/reviewed/assessed/failed/unsupported entry-key sets, selected entry keys, notes |
| SourceBaseline | id, project_id, document_version_ids, rule_version_ids, coverage_manifest_id |
| AssessmentInputBundle | schema_version, project_id, scope, snapshot, fact_set, source_baseline, documents, anchors, rules, coverage, evaluator_version='domain-v1' |
| AssessmentResult | schema/evaluator versions, project/scope/pinned IDs, input_hash, result_hash, per-rule results and full traces, sorted selector_dependencies, missing_selectors, contradictions, warnings, coverage summary |

Entry key is `(document_version_id, entry_id)`, not just entry text. Every reference must resolve within this bundle and same project; v1 has no implicit shared-corpus exemption. IDs must be unique; duplicate anchor IDs, duplicate fact version IDs, or unresolved source/rule references are invalid. Source/anchor hashes must agree. Located geometry requires finite coordinates ordered inside [0,1], positive finite page dimensions and rotation in {0,90,180,270}; synthetic geometry may have null bbox/dimensions but must be marked synthetic, never invented page geometry. Physical page index and printed label remain distinct.

W01's claims are a **draft interpretation**, not RuleVersion AST. Do not make a live adapter, auto-activate a draft, or mechanically convert free-text claims to executable predicates. For W02 use original labeled synthetic sources/anchors and manually specified fixtures. Write a mapping note documenting the later reviewed conversion boundary (W04), including document revision versus silicon revision and immutable source/anchor IDs. No public full manufacturer documents or new source downloads.

## Selector registry and typed values

All selectors address the current component subject in the exact EvaluationScope. No wildcards, implicit scope inheritance, latest-wins resolution, fuzzy matching, or derived engineering values.

| Selector | Type | Canonical unit |
|---|---|---|
| component.manufacturer | text | none |
| component.exact_part | text | none |
| component.family | text | none |
| component.package | text | none |
| component.silicon_revision | text | none |
| operating.external_reset_used | boolean | none |
| operating.reset_pulse_ns | quantity | ns |
| operating.clock_hz | quantity | Hz |
| operating.supply_voltage_v | quantity | V |
| operating.temperature_c | quantity | degC |
| firmware.initial_software_reset | boolean | none |
| firmware.revision_id_value | integer | none |

Each selector registry record declares type, allowed operators, unit, and a description. Values are discriminated objects: `{kind:'text', value:'...'}`, `{kind:'boolean', value:true}`, `{kind:'integer', value:123}`, `{kind:'quantity', value:'3.3', unit:'V'}`. Text comparisons are case-sensitive exact comparisons; no trimming or normalization that changes identity. Reject blank identity facts. Integer excludes booleans; reject floats/strings for integer, strings/numbers for boolean, or non-strings for text.

Quantity input must be a decimal string (no exponent, NaN, Infinity, or JSON float), optional minus, at most 18 integral and 9 fractional digits; normalize trailing zeros and negative zero for comparison/hash. Registry unit must match exactly; `mV` does not silently become `V`. No unit conversion in v1. Allow negative temperature, reject negative pulse/clock/voltage. Unsupported selectors/units/types reject the bundle before evaluation. Null FactVersion value represents an explicitly unknown observation, never false.

Identity selectors resolve from accepted FactVersions only. Non-null snapshot identity values constrain consistency: a matching-scope accepted identity fact that disagrees with its snapshot identity is a validation error, not silently preferred. Missing accepted identity evidence remains unknown even if a display-only snapshot field is populated. Require evidence references for accepted known identity facts, and resolve each referenced anchor in the bundle. Snapshot identities are for scope/reference validation and display, not a hidden second fact channel.

## Rule AST, activation, and limits

Discriminated nodes:

- `eq`: selector, value, anchor_ids.
- `in`: selector, nonempty tuple of homogeneous typed values, anchor_ids; text/integer only.
- `lt`, `lte`, `gt`, `gte`: selector, value, anchor_ids; quantity/integer only and registry-compatible.
- `all`, `any`: nonempty tuple `children`.
- `not`: one `child`.
- `constant`: explicit boolean `value` plus nonempty anchor_ids and nonempty review_rationale. This represents an intentionally reviewed unconditional condition, not a missing extraction field.

Every technical leaf has at least one existing anchor from that rule's document version. Composite nodes derive provenance from children. `target`, `trigger`, and `exceptions` are required keys. Empty exceptions explicitly means reviewed no exceptions; missing/null exceptions reject activation. Accepted rules require nonempty reviewer_id, consequence and source anchors; target/trigger cannot be null. Workaround documentation/restrictions may be null, preserving unknown rather than inferring availability. Draft/rejected rules are rejected by this accepted-assessment entry point; do not add provisional execution in W02.

Enforce <=32 expression depth, <=512 nodes per rule, <=100 rules, <=5,000 facts and <=10,000 anchors per bundle. Reject unknown operators, empty logical groups, bad types and excessive nesting before evaluation with stable diagnostic codes/paths. Do not use Python recursion on unchecked deeply nested untrusted data; preflight depth before recursive Pydantic conversion.

## Resolution and three-valued evaluation

Truth values serialize as `'true'`, `'false'`, `'unknown'`. Implement the shared rule-language truth tables exactly. Applicability = target AND trigger AND NOT(any exception). Empty reviewed exception list gives exception=false. Evaluate every branch (no performance short-circuit needed at these limits), retaining warnings even when a false target determines the final outcome.

Resolve selector facts only in the exact five-field scope, considering accepted facts. Draft/rejected facts never supply values. Other-component/build/profile facts are ignored for this assessment and never create false contradictions. A fact with wrong project or unresolved subject/snapshot reference is structurally invalid; legitimate other components in the same snapshot are allowed. For facts from other snapshots, bundle references are insufficient in v1: reject rather than silently accepting an unresolvable scope. Other builds/profiles of the same snapshot may be retained as out-of-scope facts for tests; record that they are not selected.

- No accepted known value: unknown, list selector as missing (explicit-null fact IDs retained in trace).
- Several identical accepted known values: one resolved value with all supporting fact IDs.
- Multiple different accepted known values in the same scope: unknown with contradiction, never choose the newest.
- Known value plus null observation: known value determines comparison; retain the null observation warning and IDs. This is not a contradiction between two known values.

For each rule return target/trigger/exception/overall truth, applicability `applicable/not_applicable/unknown`, and a complete tree trace. Each node has a deterministic path (e.g. `rules/<id>/target/children/0`), operator, result, child traces or selector/operands, relevant fact IDs, anchor IDs, missing/conflict reason, and warning codes. Explicitly return unresolved warnings even for not_applicable final results. Never output safe/certified/defect_free fields.

Collect dependencies by traversing **all target/trigger/exception leaves**, whether known, missing, conflicting, or irrelevant to the final truth. Dependency identity includes exact scope + selector; deduplicate and sort for serialization. A missing selector is still a dependency so arrival of a fact can reopen assessment later. No subscriptions/queue implementation in W02.

Coverage sets must be internally consistent: supported <= discovered, reviewed <= supported, assessed <= reviewed; failed and unsupported <= discovered and disjoint from supported. Selected entries <= discovered. Every evaluated rule entry must be selected/reviewed/assessed; no fabricated assessment of unreviewed entries. Incomplete inventory or other unsupported entries produce explicit coverage warnings, not not_applicable for absent rules. Result is only for its selected rules and includes that scope. Do not claim whole-device completeness merely because all selected rules are false.

## Canonical hashes and replay

Canonical serialization: UTF-8, sorted object keys, no whitespace separators, ensure_ascii=False, allow_nan=False; model defaults/null fields materialized. Normalize UUID strings to lowercase standard form and quantity decimal strings as above. Require finite geometry numbers and normalize those to JSON floats at parse time (so integer versus float geometry input does not arbitrarily change the normalized result). For other numeric fields enforce strict integers; do not coerce them to floats. Preserve Unicode strings as supplied; no hidden Unicode normalization. Semantic sequences such as AST children retain order. Sets (coverage, dependencies, unordered entity collections) sort by stable keys before hashing.

Content-hash fields omit only their own digest slot when sealing/validating the relevant object. `input_hash` hashes the full normalized sealed assessment bundle. It must change when a pinned semantic input changes. `result_hash` hashes the result payload excluding only result_hash and any explicitly declared top-level operational timestamp (prefer no generated timestamp in the domain result). Do not recursively discard timestamps/provenance. All supplied content hashes must be verified; provide `seal_snapshot` and `seal_fact_set` helpers rather than accepting fake digests. IDs/times are supplied, never randomly generated during evaluation. Repeated replay of identical inputs returns byte-identical normalized results/hashes across two fresh processes on the pinned runtime. Different syntactic AST child order need not hash identically.

CLI: `python -m erratascope_domain.replay --input PATH --output PATH`. Read one JSON bundle, validate/evaluate, and write the result only after success (atomic sibling temp replace). stdout prints result hash and scoped result counts, not credentials or full input. Exit 0 for valid evaluation including unknown; exit 2 for invalid input; exit 1 for IO/runtime failure. A validation failure must not replace a prior valid output file. No HTTP, credentials, model calls, or file references read from inside the untrusted input bundle. Paths are explicit CLI inputs/outputs only.

## Required implementation evidence

Use `backend/tests/test_domain_contracts.py`, `test_truth_tables.py`, `test_resolution.py`, `test_dependencies.py`, `test_replay.py` (helpers allowed). Fixtures under `backend/fixtures/w02/` must be small, original and labeled SYNTHETIC with a README and readable expected outcomes. Include two components so cross-component leakage is actually tested. Table-driven test oracles must be explicitly specified, not generated by calling the evaluator under test.

Required cases: all 9 pairwise three-valued all/any combinations and 3 not cases; applicable; false target with unknown trigger (false plus warning); missing silicon revision; matching and unknown exceptions; same-scope contradictory facts; identical facts deduplicated; other component/build/profile facts ignored; draft facts ignored; snapshot/fact identity mismatch rejected; bool-as-int and numeric string type errors rejected; wrong/unsupported units; explicit nulls; unsupported selector/operator; unresolved/cross-project anchors; unreviewed rule and absent exceptions rejected; incomplete inventory correctly labeled; dependencies from every branch including missing exception selectors; bounds/depth rejected; tampered content hash rejected; replay twice in fresh processes; changed semantic input changes hash; invalid replay does not overwrite output. Test at least one connected JSON fixture → parsing → resolution → AST → trace → hash → CLI result journey with networking disabled or forbidden by tests.

This packet proves deterministic document-condition evaluation, not electrical behavior, simulator correctness, NVIDIA model accuracy, or general verification. Later packets must preserve that boundary.

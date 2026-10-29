# Data and version contract — revision 1

Binding semantics; exact Pydantic fields and SQL migrations are frozen in W02/W03.

## Identity and scope

ProductSnapshot includes product identity, board revision, firmware/build reference, operating profile, component instances, predecessor, and content hash. Component identity distinguishes manufacturer, exact part, family, package, silicon revision, and evidence. Unknown values remain explicit; fuzzy suggestions require review.

FactVersion contains subject, selector, typed value, optional supported unit, scope, origin (declared/extracted/measured/external), evidence references, review state, and predecessor. A sealed FactSet references exact accepted versions. Different profiles/builds do not automatically conflict.

## Immutable content and history

Seal document bytes, source versions, rule versions, fact sets, snapshots, and assessment inputs. Updates create new versions. Append review and invalidation events. Mutable current-state projections may be rebuilt from history.

Assessment pins project, snapshot, fact set, source baseline, coverage manifest, rule versions, schema/evaluator versions, and canonical result hash. Exclude incidental timestamps from deterministic result hashing.

Use UTC timestamps, UUIDs, explicit schema versions, and SHA-256 for bytes. Canonical JSON hashing must specify encoding, stable key order, numeric handling, and omitted/null semantics in W02. Never hash credentials into public manifests.

## Source and anchor

DocumentVersion records source URL, manufacturer/document ID, revision, publication/retrieval dates, SHA-256, authority type, artifact location, and predecessor. Anchor records physical page index (zero-based), printed page label if known, section, extracted text, normalized bbox, page dimensions/rotation, parser/version, and coordinate provenance. Do not conflate printed and physical page numbers.

CoverageManifest distinguishes inventory complete/incomplete, discovered entries, supported entries, reviewed entries, assessed entries, failed/unsupported entries, and selected scope.

## Storage and authorization

Relational columns for identity/ownership/relationships; JSONB for validated AST and trace. Exact model response bytes live in private artifacts, not just JSONB. Every cross-entity reference must belong to the appropriate project or explicitly authorized shared corpus.

No cross-project artifact deduplication information leakage. Foreign keys, unique idempotency scope, and optimistic concurrency protect accepted data.


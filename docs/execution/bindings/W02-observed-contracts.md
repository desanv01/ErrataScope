# W02 accepted domain-v1 boundary

Accepted 30 October 2026 under [review 02](../reviews/W02-review-02.md). Final byte hashes: [acceptance manifest](../../evidence/W02/ACCEPTANCE.json). The [domain-v1 binding](W02-domain-v1.md) remains the authoritative semantic contract.

- Python 3.11.15, Pydantic 2.14.1; `backend/erratascope_domain/` is a pure package with no provider, credentials, network, ORM or API imports.
- Public `parse_bundle` accepts a JSON-object-shaped input with JSON arrays for rules/exceptions; it verifies strict fields, immutable seals, all source/evidence/project/scope references and rule bounds. Required identity and fact unknowns use explicit nulls. `evaluate` revalidates caller-supplied instances and rejects serializer type coercions.
- Exact accepted FactVersion scope supplies values. Display identity is not a hidden evidence channel. Contradictions produce unknown; null observations remain visible. Facts outside the selected legitimate scope do not leak into resolution.
- Reviewed AST vocabulary, 32-depth and aggregate 512-node-per-rule limits are fixed. Known, missing and conflicting leaves all remain dependencies. No arbitrary code or external artifact reads inside the domain evaluator.
- Input/result/snapshot/fact-set hashes and deterministic output bytes are frozen by the implementation. API and persistence adapters must use these helpers; do not recreate a subtly different hash algorithm in SQL or an API serializer.
- Schemas are necessary structural descriptions, not replacements for Python cross-reference/semantic validation. Persisted data must cross the accepted parser/evaluator boundary before assessment.
- W01 model drafts are still not executable rules. W04 needs explicit reviewed conversion. W03 may persist and round-trip original synthetic accepted bundles for adapter tests, but cannot auto-activate extraction output.

W03 may import this package and add external adapters/tests. It may not edit the accepted domain package, domain requirements, fixtures, exported schemas or existing domain tests without a new Codex-issued repair scope. UI approval remains pending.

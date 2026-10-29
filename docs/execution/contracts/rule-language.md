# Rule language — revision 1

This is the semantic contract for W02. W01 only drafts a compatible interpretation; it does not implement the production evaluator.

## Predicates

Support typed eq, in, numeric bound comparisons with a limited explicit unit vocabulary, all, any, and not. Values must match the declared selector type. No implicit truthiness, string-to-number guessing, arbitrary expressions, dynamic imports, SQL, or eval.

Rule contains target, trigger, exceptions, documented consequence, workaround documentation/restrictions, anchors, interpretation status, schema version, and source identity. Every technical predicate requires supporting anchors.

Missing extraction fields are not equivalent to unconditional conditions or empty exceptions. Unsupported semantics block activation. An intentionally unconditional trigger must be explicit and reviewed.

## Evaluation

Use true/false/unknown:
- all: false if any false; true if all true; otherwise unknown.
- any: true if any true; false if all false; otherwise unknown.
- not: flips true/false; preserves unknown.

Overall applicability = target AND trigger AND NOT(any matching exception).
Reviewed empty exceptions mean no exception matches. Missing/contradictory relevant facts yield unknown at the leaf. Retain warnings even when a different false condition determines the conjunction.

Register every declared selector, including short-circuited and missing ones. Return intermediate results, fact versions, source anchors, missing selectors, contradictions, and unsupported/coverage markers.

## Checks

Exhaustive three-valued combinations; type mismatch; supported/unsupported units; missing revision; scope mismatch; contradictory facts; known-false target plus unknown trigger; exceptions; deterministic replay; dependency completeness.

A draft/provisional run is labeled. Accepted evaluation uses exact reviewed inputs. No output field called safe, certified, or defect-free.


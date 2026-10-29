"""W02 repair-01 regressions: R1 explicit nulls/direct-model validation, R2
reference/project completeness, R3 aggregate rule node budget.

Expected outcomes are explicit literals; no oracle is derived from the evaluator.
"""

from __future__ import annotations

import unittest
import uuid

from erratascope_domain import evaluate
from erratascope_domain.errors import DomainValidationError
from erratascope_domain.models import EntryKey

from tests import helpers as H

IDENTITY_KEYS = ("manufacturer", "exact_part", "family", "package", "silicon_revision")


def codes(raw: dict) -> set[str]:
    with unittest.TestCase().assertRaises(DomainValidationError) as context:
        H.parse_bundle(raw)
    return set(context.exception.codes)


def evaluate_codes(bundle) -> set[str]:
    with unittest.TestCase().assertRaises(DomainValidationError) as context:
        evaluate(bundle)
    return set(context.exception.codes)


class ExplicitNullContractTests(unittest.TestCase):
    def test_all_five_identity_nulls_accepted(self) -> None:
        null_identity = H.identity(
            manufacturer=None,
            exact_part=None,
            family=None,
            package=None,
            silicon_revision=None,
        )
        snap = H.snapshot((H.instance(H.SUBJECT, null_identity),))
        bundle = H.parse_bundle(H.build_raw(snapshot_model=snap))
        self.assertIsNone(bundle.snapshot.component_instances[0].identity.manufacturer)
        self.assertIsNone(bundle.snapshot.component_instances[0].identity.silicon_revision)
        result = evaluate(bundle)
        self.assertEqual(result.rules[0].applicability, "applicable")

    def test_each_identity_key_is_required(self) -> None:
        for key in IDENTITY_KEYS:
            with self.subTest(key=key):
                raw = H.build_raw()
                del raw["snapshot"]["component_instances"][0]["identity"][key]
                self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_fact_value_required_but_explicit_null_accepted(self) -> None:
        raw = H.build_raw()
        del raw["fact_set"]["fact_versions"][0]["value"]
        self.assertIn("SCHEMA_INVALID", codes(raw))
        null_raw = H.build_raw(facts=(H.fact("component.silicon_revision", None),))
        bundle = H.parse_bundle(null_raw)
        self.assertIsNone(bundle.fact_set.fact_versions[0].value)

    def test_evaluate_rejects_model_copy_schema_version(self) -> None:
        bundle = H.parse_bundle(H.build_raw())
        tampered = bundle.model_copy(update={"schema_version": 99})
        self.assertIn("SCHEMA_INVALID", evaluate_codes(tampered))

    def test_evaluate_rejects_model_copy_wrong_uuid_type(self) -> None:
        bundle = H.parse_bundle(H.build_raw())
        tampered = bundle.model_copy(update={"project_id": "not-a-uuid"})
        self.assertIn("SCHEMA_INVALID", evaluate_codes(tampered))

    def test_evaluate_rejects_constructed_empty_logical_group(self) -> None:
        bundle = H.parse_bundle(H.build_raw())
        bad_rule = bundle.rules[0].model_copy(update={"target": {"op": "all", "children": []}})
        tampered = bundle.model_copy(update={"rules": (bad_rule,)})
        self.assertTrue({"INVALID_AST", "SCHEMA_INVALID"} & evaluate_codes(tampered))

    def test_evaluate_rejects_constructed_nested_typed_value(self) -> None:
        bundle = H.parse_bundle(H.build_raw())
        bad_fact = bundle.fact_set.fact_versions[0].model_copy(
            update={"value": {"kind": "text", "value": 5}}
        )
        bad_fact_set = bundle.fact_set.model_copy(update={"fact_versions": (bad_fact,)})
        tampered = bundle.model_copy(update={"fact_set": bad_fact_set})
        self.assertIn("SCHEMA_INVALID", evaluate_codes(tampered))

    def test_evaluate_does_not_mutate_caller_input(self) -> None:
        bundle = H.parse_bundle(H.build_raw())
        before = bundle.model_dump_json()
        evaluate(bundle)
        self.assertEqual(bundle.model_dump_json(), before)

    def test_valid_bundle_remains_evaluable_and_deterministic(self) -> None:
        bundle = H.parse_bundle(H.build_raw())
        first = evaluate(bundle)
        second = evaluate(bundle)
        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.rules[0].applicability, "applicable")


class ReferenceProjectTests(unittest.TestCase):
    def test_foreign_project_component_rejected(self) -> None:
        foreign = H.instance(H.OTHER_COMPONENT, project_id=uuid.uuid4())
        snap = H.snapshot((H.instance(), foreign))
        self.assertIn("PROJECT_MISMATCH", codes(H.build_raw(snapshot_model=snap)))

    def test_missing_identity_evidence_reference_rejected(self) -> None:
        identity = H.identity(evidence_refs=("missing-anchor",))
        snap = H.snapshot((H.instance(H.SUBJECT, identity),))
        self.assertIn("UNRESOLVED_ANCHOR", codes(H.build_raw(snapshot_model=snap)))

    def test_missing_nonidentity_fact_evidence_rejected(self) -> None:
        bad = H.fact(
            "operating.clock_hz",
            H.quantity("1", "Hz"),
            evidence_refs=("missing-anchor",),
        )
        self.assertIn("UNRESOLVED_ANCHOR", codes(H.build_raw(facts=(bad,))))

    def test_missing_null_fact_evidence_rejected(self) -> None:
        bad = H.fact(
            "component.silicon_revision",
            None,
            evidence_refs=("missing-anchor",),
        )
        self.assertIn("UNRESOLVED_ANCHOR", codes(H.build_raw(facts=(bad,))))

    def test_missing_draft_fact_evidence_rejected(self) -> None:
        bad = H.fact(
            "operating.clock_hz",
            H.quantity("1", "Hz"),
            review_state="draft",
            evidence_refs=("missing-anchor",),
        )
        self.assertIn("UNRESOLVED_ANCHOR", codes(H.build_raw(facts=(bad,))))

    def test_legal_empty_evidence_references_accepted(self) -> None:
        identity = H.identity(evidence_refs=())
        snap = H.snapshot(
            (H.instance(H.SUBJECT, identity), H.instance(H.OTHER_COMPONENT))
        )
        facts = (
            H.fact("component.silicon_revision", H.text("B")),
            H.fact("operating.clock_hz", H.quantity("1", "Hz"), evidence_refs=()),
            H.fact(
                "operating.clock_hz",
                H.quantity("2", "Hz"),
                review_state="draft",
                evidence_refs=(),
            ),
        )
        bundle = H.parse_bundle(H.build_raw(facts=facts, snapshot_model=snap))
        self.assertEqual(len(bundle.fact_set.fact_versions), 3)

    def test_resolved_evidence_references_accepted(self) -> None:
        identity = H.identity(evidence_refs=(H.ANCHOR, H.ANCHOR_2))
        snap = H.snapshot((H.instance(H.SUBJECT, identity),))
        H.parse_bundle(H.build_raw(snapshot_model=snap))


class AggregateNodeBudgetTests(unittest.TestCase):
    @staticmethod
    def _constants(count: int):
        return tuple(H.constant(True) for _ in range(count))

    def test_exactly_512_aggregate_nodes_accepted(self) -> None:
        rule = H.rule(
            target=H.all_(*self._constants(510)),  # 511 nodes
            trigger=H.constant(True),  # 1 node -> 512 total
            exceptions=(),
        )
        bundle = H.parse_bundle(H.build_raw(rules=(rule,)))
        self.assertEqual(evaluate(bundle).rules[0].applicability, "applicable")

    def test_513_aggregate_nodes_rejected(self) -> None:
        rule = H.rule(
            target=H.all_(*self._constants(511)),  # 512 nodes
            trigger=H.constant(True),  # 1 node -> 513 total
            exceptions=(),
        )
        with self.assertRaises(DomainValidationError) as context:
            H.parse_bundle(H.build_raw(rules=(rule,)))
        self.assertIn("AST_NODE_LIMIT_EXCEEDED", context.exception.codes)
        self.assertIn("rules/0", [item.path for item in context.exception.diagnostics])

    def test_602_nodes_split_target_trigger_rejected(self) -> None:
        rule = H.rule(
            target=H.all_(*self._constants(300)),  # 301
            trigger=H.all_(*self._constants(300)),  # 301 -> 602
            exceptions=(),
        )
        self.assertIn("AST_NODE_LIMIT_EXCEEDED", codes(H.build_raw(rules=(rule,))))

    def test_excess_split_across_exception_roots_rejected(self) -> None:
        rule = H.rule(
            target=H.constant(True),  # 1
            trigger=H.constant(True),  # 1
            exceptions=(
                H.all_(*self._constants(255)),  # 256
                H.all_(*self._constants(254)),  # 255 -> 513
            ),
        )
        self.assertIn("AST_NODE_LIMIT_EXCEEDED", codes(H.build_raw(rules=(rule,))))

    def test_512_split_across_exception_roots_accepted(self) -> None:
        rule = H.rule(
            target=H.constant(True),
            trigger=H.constant(True),
            exceptions=(
                H.all_(*self._constants(254)),  # 255
                H.all_(*self._constants(254)),  # 255 -> 512
            ),
        )
        bundle = H.parse_bundle(H.build_raw(rules=(rule,)))
        self.assertEqual(evaluate(bundle).rules[0].overall, "false")

    def test_multiple_rules_do_not_share_one_budget(self) -> None:
        first = H.rule(
            rule_id=H.uuid_for(71),
            entry_id="2.1",
            target=H.all_(*self._constants(398)),  # 399
            trigger=H.constant(True),  # 400 total
            exceptions=(),
        )
        second = H.rule(
            rule_id=H.uuid_for(72),
            entry_id="2.2",
            target=H.all_(*self._constants(398)),
            trigger=H.constant(True),
            exceptions=(),
        )
        entries = (
            EntryKey(document_version_id=H.DOCUMENT, entry_id="2.1"),
            EntryKey(document_version_id=H.DOCUMENT, entry_id="2.2"),
        )
        coverage = H.coverage(entries=entries)
        baseline = H.baseline(rule_ids=(first.id, second.id))
        raw = H.build_raw(
            rules=(first, second),
            coverage_manifest=coverage,
            baseline_model=baseline,
        )
        bundle = H.parse_bundle(raw)
        result = evaluate(bundle)
        self.assertEqual(len(result.rules), 2)
        self.assertEqual([rule.applicability for rule in result.rules], ["applicable", "applicable"])

    def test_depth_limit_remains_per_expression(self) -> None:
        nested = H.constant(True)
        for _ in range(40):
            nested = H.not_(nested)
        self.assertIn("AST_DEPTH_EXCEEDED", codes(H.build_raw(rules=(H.rule(trigger=nested, exceptions=()),))))


if __name__ == "__main__":
    unittest.main()

"""W02-G1: strict contracts, references, scope, coverage, limits and hashes."""

from __future__ import annotations

import copy
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from erratascope_domain import parse_bundle
from erratascope_domain.errors import DomainValidationError
from erratascope_domain.models import (
    AssessmentInputBundle,
    CoverageManifest,
    EntryKey,
)
from pydantic import ValidationError

from tests import helpers as H


def codes(raw: dict) -> set[str]:
    with unittest.TestCase().assertRaises(DomainValidationError) as context:
        parse_bundle(raw)
    return set(context.exception.codes)


class StrictContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = H.build_raw()

    def test_valid_bundle_parses_and_is_frozen(self) -> None:
        bundle = parse_bundle(self.raw)
        self.assertIsInstance(bundle, AssessmentInputBundle)
        self.assertIsInstance(bundle.snapshot.id, uuid.UUID)
        self.assertIsInstance(bundle.rules[0].target, object)
        with self.assertRaises(ValidationError):
            bundle.snapshot = bundle.snapshot  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["rules"][0]["unexpected_field"] = True
        self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_invalid_uuid_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["snapshot"]["id"] = "not-a-uuid"
        self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_strict_typed_value_rejections(self) -> None:
        cases = {
            "bool_as_integer": H.integer(True),
            "float_as_integer": H.integer(1.0),
            "string_as_integer": {"kind": "integer", "value": "1"},
            "string_as_boolean": {"kind": "boolean", "value": "true"},
            "number_as_boolean": {"kind": "boolean", "value": 1},
            "float_as_quantity": {"kind": "quantity", "value": 3.3, "unit": "V"},
            "number_as_text": {"kind": "text", "value": 7},
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                raw = H.build_raw(facts=(H.fact("firmware.revision_id_value", H.integer(1)),))
                raw["fact_set"]["fact_versions"][0]["value"] = value
                self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_quantity_bounds_and_normalization(self) -> None:
        normalized = parse_bundle(
            H.build_raw(facts=(H.fact("operating.supply_voltage_v", H.quantity("0010.500", "V")),))
        ).fact_set.fact_versions[0].value
        self.assertEqual(normalized.value, "10.5")
        negative_zero = parse_bundle(
            H.build_raw(facts=(H.fact("operating.temperature_c", H.quantity("-0.0", "degC")),))
        ).fact_set.fact_versions[0].value
        self.assertEqual(negative_zero.value, "0")
        for bad in ("1e3", "NaN", "Infinity", "1234567890123456789", "1.1234567891"):
            with self.subTest(value=bad):
                raw = H.build_raw(facts=(H.fact("operating.clock_hz", H.quantity("1", "Hz")),))
                raw["fact_set"]["fact_versions"][0]["value"] = {
                    "kind": "quantity",
                    "value": bad,
                    "unit": "Hz",
                }
                self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_unit_and_sign_constraints(self) -> None:
        raw = H.build_raw(facts=(H.fact("operating.reset_pulse_ns", H.quantity("1", "us")),))
        self.assertIn("UNIT_MISMATCH", codes(raw))
        raw = H.build_raw(facts=(H.fact("operating.reset_pulse_ns", H.quantity("-1", "ns")),))
        self.assertIn("NEGATIVE_QUANTITY", codes(raw))
        raw = H.build_raw(
            facts=(H.fact("component.manufacturer", H.text("   ")),)
        )
        self.assertIn("BLANK_IDENTITY", codes(raw))

    def test_geometry_contract(self) -> None:
        with self.assertRaises(ValidationError):
            H.anchor(geometry_kind="located")
        with self.assertRaises(ValidationError):
            H.anchor(
                geometry_kind="located",
                bbox=(0.5, 0.1, 0.1, 0.4),
                dimensions=(595, 842),
            )
        with self.assertRaises(ValidationError):
            H.anchor(
                geometry_kind="located",
                bbox=(0.1, 0.1, 0.9, 0.9),
                dimensions=(595, 842),
                rotation=45,
            )
        located = H.anchor(
            geometry_kind="located",
            bbox=(0.1, 0.1, 0.9, 0.9),
            dimensions=(595, 842),
        )
        self.assertEqual(located.page_rotation, 0)
        self.assertEqual(located.bbox, (0.1, 0.1, 0.9, 0.9))

    def test_synthetic_geometry_requires_synthetic_document(self) -> None:
        raw = H.build_raw(
            documents=(H.document(synthetic=False, authority="manufacturer"),),
        )
        self.assertIn("INVALID_GEOMETRY", codes(raw))

    def test_content_hash_tamper_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["snapshot"]["content_hash"] = "0" * 64
        self.assertIn("HASH_MISMATCH", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["fact_set"]["fact_versions"][0]["value"]["value"] = "A"
        self.assertIn("HASH_MISMATCH", codes(raw))

    def test_duplicate_ids_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["anchors"].append(copy.deepcopy(raw["anchors"][0]))
        self.assertIn("DUPLICATE_ID", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["rules"].append(copy.deepcopy(raw["rules"][0]))
        self.assertIn("DUPLICATE_ID", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["fact_set"]["fact_versions"].append(copy.deepcopy(raw["fact_set"]["fact_versions"][0]))
        self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_unresolved_references_rejected(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["rules"][0]["document_version_id"] = str(uuid.uuid4())
        self.assertIn("UNRESOLVED_REF", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["rules"][0]["anchors"] = ["missing-anchor"]
        self.assertIn("UNRESOLVED_ANCHOR", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["fact_set"]["fact_versions"][0]["evidence_refs"] = ["missing-anchor"]
        self.assertIn("UNRESOLVED_ANCHOR", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["coverage"]["document_version_ids"].append(str(uuid.uuid4()))
        self.assertIn("UNRESOLVED_REF", codes(raw))

    def test_project_and_snapshot_scope_isolated(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["fact_set"]["fact_versions"][0]["scope"]["project_id"] = str(uuid.uuid4())
        self.assertIn("PROJECT_MISMATCH", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["fact_set"]["fact_versions"][0]["scope"]["snapshot_id"] = str(uuid.uuid4())
        self.assertIn("UNRESOLVED_REF", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["scope"]["subject_id"] = str(uuid.uuid4())
        self.assertIn("SCOPE_MISMATCH", codes(raw))

    def test_identity_mismatch_rejected(self) -> None:
        facts = (
            H.fact("component.silicon_revision", H.text("A")),
        )
        raw = H.build_raw(facts=facts)
        self.assertIn("IDENTITY_MISMATCH", codes(raw))

    def test_rule_activation_requirements(self) -> None:
        raw = H.build_raw(rules=(H.rule(review_state="draft"),))
        self.assertIn("UNREVIEWED_RULE", codes(raw))
        raw = H.build_raw(rules=(H.rule(reviewer_id="  "),))
        self.assertIn("UNREVIEWED_RULE", codes(raw))
        raw = H.build_raw(rules=(H.rule(consequence=""),))
        self.assertIn("MISSING_CONSEQUENCE", codes(raw))
        raw = H.build_raw(rules=(H.rule(anchors=()),))
        self.assertIn("MISSING_ANCHORS", codes(raw))
        raw = copy.deepcopy(self.raw)
        del raw["rules"][0]["exceptions"]
        self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_unsupported_selector_operator_and_unit(self) -> None:
        raw = H.build_raw(facts=(H.fact("operating.unknown_selector", H.text("x")),))
        self.assertIn("UNSUPPORTED_SELECTOR", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["rules"][0]["target"] = {
            "op": "regex",
            "selector": "component.silicon_revision",
            "value": H.text("B"),
            "anchor_ids": [H.ANCHOR],
        }
        self.assertIn("UNSUPPORTED_OPERATOR", codes(raw))
        raw = H.build_raw(
            rules=(
                H.rule(
                    trigger=H.in_("operating.clock_hz", [H.quantity("1", "Hz")]),
                    exceptions=(),
                ),
            )
        )
        self.assertIn("UNSUPPORTED_OPERATOR", codes(raw))
        raw = H.build_raw(
            rules=(H.rule(trigger=H.lt("component.silicon_revision", H.text("B")), exceptions=()),)
        )
        self.assertIn("UNSUPPORTED_OPERATOR", codes(raw))

    def test_coverage_consistency_and_selection(self) -> None:
        entry = EntryKey(document_version_id=H.DOCUMENT, entry_id="1.1")
        other = EntryKey(document_version_id=H.DOCUMENT, entry_id="9.9")
        coverage = CoverageManifest(
            id=H.COVERAGE,
            project_id=H.PROJECT,
            document_version_ids=(H.DOCUMENT,),
            inventory_complete=True,
            discovered=(entry, other),
            supported=(entry,),
            reviewed=(other,),
            assessed=(other,),
            failed=(),
            unsupported=(),
            selected=(entry,),
        )
        raw = H.build_raw(coverage_manifest=coverage)
        found = codes(raw)
        self.assertIn("COVERAGE_INCONSISTENT", found)
        self.assertIn("UNSELECTED_ENTRY", found)

    def test_baseline_pin_mismatch_rejected(self) -> None:
        raw = H.build_raw(baseline_model=H.baseline(rule_ids=(uuid.uuid4(),)))
        self.assertIn("UNRESOLVED_REF", codes(raw))

    def test_bundle_limits(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["rules"] = [copy.deepcopy(raw["rules"][0]) for _ in range(101)]
        self.assertIn("RULE_LIMIT_EXCEEDED", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["fact_set"]["fact_versions"] = [
            copy.deepcopy(raw["fact_set"]["fact_versions"][0]) for _ in range(5001)
        ]
        self.assertIn("FACT_LIMIT_EXCEEDED", codes(raw))
        raw = copy.deepcopy(self.raw)
        raw["anchors"] = [copy.deepcopy(raw["anchors"][0]) for _ in range(10001)]
        self.assertIn("ANCHOR_LIMIT_EXCEEDED", codes(raw))

    def test_ast_depth_and_node_limits(self) -> None:
        nested = H.constant(True)
        for _ in range(40):
            nested = H.not_(nested)
        raw = H.build_raw(rules=(H.rule(trigger=nested, exceptions=()),))
        self.assertIn("AST_DEPTH_EXCEEDED", codes(raw))
        huge = H.any_(*[H.constant(True) for _ in range(513)])
        raw = H.build_raw(rules=(H.rule(trigger=huge, exceptions=()),))
        self.assertIn("AST_NODE_LIMIT_EXCEEDED", codes(raw))

    def test_pinned_inputs_are_immutable(self) -> None:
        snapshot = H.snapshot()
        with self.assertRaises(ValidationError):
            snapshot.product_name = "changed"  # type: ignore[misc]
        fact_set = H.fact_set((H.fact("component.silicon_revision", H.text("B")),))
        with self.assertRaises(ValidationError):
            fact_set.content_hash = "1" * 64  # type: ignore[misc]

    def test_error_diagnostics_have_paths(self) -> None:
        raw = copy.deepcopy(self.raw)
        raw["rules"][0]["target"]["selector"] = "component.nope"
        with self.assertRaises(DomainValidationError) as context:
            parse_bundle(raw)
        paths = [item.path for item in context.exception.diagnostics]
        self.assertTrue(any("rules/0/target" in path for path in paths), paths)

    def test_schema_export_contract(self) -> None:
        from erratascope_domain.export_schemas import export

        with H.temp_dir("w02-test") as temp:
            written = export(Path(temp))
            self.assertIn("assessment_input_bundle.schema.json", written)
            self.assertIn("selector_registry.json", written)
            for name in written:
                json.loads((Path(temp) / name).read_text(encoding="utf-8"))
            registry = json.loads(
                (Path(temp) / "selector_registry.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(registry), 12)

    def test_parse_and_evaluate_do_not_touch_network(self) -> None:
        import socket

        raw = H.load_fixture("applicable.json")
        with patch.object(socket, "socket", side_effect=AssertionError("network attempted")):
            bundle = parse_bundle(raw)
            from erratascope_domain import evaluate

            result = evaluate(bundle)
        self.assertEqual(result.rules[0].applicability, "applicable")


if __name__ == "__main__":
    unittest.main()


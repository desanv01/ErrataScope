"""W02 repair R4: selector registry/operator and decimal-grammar tables.

The expected operator table is an explicit independent oracle, not derived from
the registry implementation. Decimal cases exercise full-string matching.
"""

from __future__ import annotations

import json
import unittest

from erratascope_domain.errors import DomainValidationError
from erratascope_domain.export_schemas import export
from erratascope_domain.selectors import SELECTORS, get_selector

from tests import helpers as H

# Independent literal oracle for the bound AST/registry contract.
EXPECTED_OPERATORS = {
    "component.manufacturer": ("eq", "in"),
    "component.exact_part": ("eq", "in"),
    "component.family": ("eq", "in"),
    "component.package": ("eq", "in"),
    "component.silicon_revision": ("eq", "in"),
    "operating.external_reset_used": ("eq",),
    "operating.reset_pulse_ns": ("eq", "lt", "lte", "gt", "gte"),
    "operating.clock_hz": ("eq", "lt", "lte", "gt", "gte"),
    "operating.supply_voltage_v": ("eq", "lt", "lte", "gt", "gte"),
    "operating.temperature_c": ("eq", "lt", "lte", "gt", "gte"),
    "firmware.initial_software_reset": ("eq",),
    "firmware.revision_id_value": ("eq", "in", "lt", "lte", "gt", "gte"),
}

EXPECTED_TYPES = {
    "component.manufacturer": ("text", None),
    "component.exact_part": ("text", None),
    "component.family": ("text", None),
    "component.package": ("text", None),
    "component.silicon_revision": ("text", None),
    "operating.external_reset_used": ("boolean", None),
    "operating.reset_pulse_ns": ("quantity", "ns"),
    "operating.clock_hz": ("quantity", "Hz"),
    "operating.supply_voltage_v": ("quantity", "V"),
    "operating.temperature_c": ("quantity", "degC"),
    "firmware.initial_software_reset": ("boolean", None),
    "firmware.revision_id_value": ("integer", None),
}


def codes(raw: dict) -> set[str]:
    with unittest.TestCase().assertRaises(DomainValidationError) as context:
        H.parse_bundle(raw)
    return set(context.exception.codes)


class SelectorRegistryTests(unittest.TestCase):
    def test_registry_operators_match_bound_ast(self) -> None:
        self.assertEqual(set(SELECTORS), set(EXPECTED_OPERATORS))
        for name, expected in EXPECTED_OPERATORS.items():
            with self.subTest(selector=name):
                self.assertEqual(get_selector(name).operators, expected)

    def test_registry_types_and_units_unchanged(self) -> None:
        for name, (kind, unit) in EXPECTED_TYPES.items():
            with self.subTest(selector=name):
                spec = get_selector(name)
                self.assertEqual((spec.kind, spec.unit), (kind, unit))

    def test_exported_registry_matches_explicit_oracle(self) -> None:
        with H.temp_dir("registry") as directory:
            export(directory)
            registry = json.loads((directory / "selector_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(set(registry), set(EXPECTED_OPERATORS))
        for name, expected in EXPECTED_OPERATORS.items():
            with self.subTest(selector=name):
                self.assertEqual(tuple(registry[name]["operators"]), expected)
                self.assertEqual(registry[name]["kind"], EXPECTED_TYPES[name][0])
                self.assertEqual(registry[name]["unit"], EXPECTED_TYPES[name][1])

    def test_disallowed_type_operator_pairs_rejected(self) -> None:
        cases = {
            "boolean_in": H.in_("operating.external_reset_used", [H.boolean(True)]),
            "quantity_in": H.in_("operating.clock_hz", [H.quantity("1", "Hz")]),
            "text_ordering": H.lt("component.silicon_revision", H.text("B")),
            "boolean_ordering": H.lt("operating.external_reset_used", H.boolean(True)),
        }
        for name, trigger in cases.items():
            with self.subTest(name=name):
                raw = H.build_raw(rules=(H.rule(trigger=trigger, exceptions=()),))
                self.assertIn("UNSUPPORTED_OPERATOR", codes(raw))

    def test_allowed_type_operator_pairs_accepted(self) -> None:
        integer_fact = H.fact("firmware.revision_id_value", H.integer(3))
        cases = {
            "integer_in": H.in_("firmware.revision_id_value", [H.integer(3)]),
            "integer_ordering": H.gt("firmware.revision_id_value", H.integer(2)),
            "quantity_ordering": H.lt("operating.clock_hz", H.quantity("2", "Hz")),
            "quantity_eq": H.eq("operating.clock_hz", H.quantity("1", "Hz")),
            "text_in": H.in_("component.silicon_revision", [H.text("B")]),
        }
        for name, trigger in cases.items():
            with self.subTest(name=name):
                facts = (integer_fact, H.fact("operating.clock_hz", H.quantity("1", "Hz")))
                raw = H.build_raw(facts=facts, rules=(H.rule(trigger=trigger, exceptions=()),))
                H.parse_bundle(raw)


class DecimalGrammarTests(unittest.TestCase):
    VALID = {
        "0": "0",
        "-0.0": "0",
        "-273.15": "-273.15",
        "123456789012345678": "123456789012345678",
        "1.123456789": "1.123456789",
        "-0.000000001": "-0.000000001",
        "0010.500": "10.5",
    }
    INVALID = (
        "1\n",
        " 1",
        "1 ",
        "\t1",
        "+1",
        "1.",
        ".5",
        "1e3",
        "1E3",
        "NaN",
        "Infinity",
        "-Infinity",
        "",
        "1234567890123456789",
        "1.1234567891",
        "Ù¡Ù¢Ù£",
        "1,000",
    )

    def test_valid_decimal_boundaries_and_normalization(self) -> None:
        for raw_text, normalized in self.VALID.items():
            with self.subTest(value=raw_text):
                raw = H.build_raw(
                    facts=(H.fact("operating.temperature_c", H.quantity(raw_text, "degC")),)
                )
                bundle = H.parse_bundle(raw)
                self.assertEqual(bundle.fact_set.fact_versions[0].value.value, normalized)

    def test_invalid_decimal_lexemes_rejected(self) -> None:
        for bad in self.INVALID:
            with self.subTest(value=repr(bad)):
                raw = H.build_raw(
                    facts=(H.fact("operating.clock_hz", H.quantity("1", "Hz")),)
                )
                raw["fact_set"]["fact_versions"][0]["value"] = {
                    "kind": "quantity",
                    "value": bad,
                    "unit": "Hz",
                }
                self.assertIn("SCHEMA_INVALID", codes(raw))

    def test_negative_temperature_allowed_negative_clock_rejected(self) -> None:
        H.parse_bundle(
            H.build_raw(facts=(H.fact("operating.temperature_c", H.quantity("-40", "degC")),))
        )
        raw = H.build_raw(
            facts=(H.fact("operating.clock_hz", H.quantity("-1", "Hz")),)
        )
        self.assertIn("NEGATIVE_QUANTITY", codes(raw))


if __name__ == "__main__":
    unittest.main()


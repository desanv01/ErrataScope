"""W02-G2: fact resolution, scope isolation, contradictions and exceptions."""

from __future__ import annotations

import unittest

from erratascope_domain import evaluate
from erratascope_domain.evaluate import resolve_selector

from tests import helpers as H


def evaluated(facts=None, rules=None):
    return evaluate(H.parse_bundle(H.build_raw(facts=facts, rules=rules)))


BASE_FACTS = (
    H.fact("component.silicon_revision", H.text("B")),
    H.fact("operating.external_reset_used", H.boolean(True)),
    H.fact("operating.reset_pulse_ns", H.quantity("10", "ns")),
    H.fact("firmware.initial_software_reset", H.boolean(False)),
)


class ResolutionTests(unittest.TestCase):
    def test_applicable_basic(self) -> None:
        result = evaluated(BASE_FACTS)
        rule = result.rules[0]
        self.assertEqual((rule.target, rule.trigger, rule.exception), ("true", "true", "false"))
        self.assertEqual(rule.overall, "true")
        self.assertEqual(rule.applicability, "applicable")
        self.assertEqual(result.missing_selectors, ())

    def test_missing_silicon_revision_is_unknown(self) -> None:
        facts = tuple(f for f in BASE_FACTS if f.selector != "component.silicon_revision")
        result = evaluated(facts)
        rule = result.rules[0]
        self.assertEqual(rule.target, "unknown")
        self.assertEqual(rule.overall, "unknown")
        self.assertIn("component.silicon_revision", result.missing_selectors)
        self.assertTrue(rule.target_trace.missing)

    def test_matching_exception_makes_not_applicable(self) -> None:
        facts = tuple(
            H.fact("firmware.initial_software_reset", H.boolean(True))
            if item.selector == "firmware.initial_software_reset"
            else item
            for item in BASE_FACTS
        )
        rule = evaluated(facts).rules[0]
        self.assertEqual(rule.exception, "true")
        self.assertEqual(rule.overall, "false")
        self.assertEqual(rule.applicability, "not_applicable")

    def test_unknown_exception_makes_overall_unknown(self) -> None:
        facts = tuple(f for f in BASE_FACTS if f.selector != "firmware.initial_software_reset")
        result = evaluated(facts)
        rule = result.rules[0]
        self.assertEqual((rule.target, rule.trigger, rule.exception), ("true", "true", "unknown"))
        self.assertEqual(rule.overall, "unknown")
        self.assertIn("firmware.initial_software_reset", result.missing_selectors)

    def test_empty_reviewed_exceptions_mean_no_exception(self) -> None:
        rule = H.rule(exceptions=())
        result = evaluated(BASE_FACTS, (rule,))
        self.assertEqual(result.rules[0].exception, "false")
        self.assertEqual(result.rules[0].applicability, "applicable")

    def test_same_scope_contradiction_never_chooses_newest(self) -> None:
        facts = (
            H.fact("component.silicon_revision", H.text("B")),
            H.fact("operating.clock_hz", H.quantity("1000000", "Hz")),
            H.fact("operating.clock_hz", H.quantity("2000000", "Hz")),
        )
        rule = H.rule(
            trigger=H.lt("operating.clock_hz", H.quantity("1500000", "Hz")),
            exceptions=(),
        )
        result = evaluated(facts, (rule,))
        evaluated_rule = result.rules[0]
        self.assertEqual(evaluated_rule.trigger, "unknown")
        self.assertEqual(evaluated_rule.overall, "unknown")
        self.assertEqual([item.selector for item in result.contradictions], ["operating.clock_hz"])
        self.assertIn("operating.clock_hz", result.missing_selectors)
        self.assertTrue(evaluated_rule.trigger_trace.conflict)
        self.assertEqual(len(evaluated_rule.trigger_trace.fact_ids), 2)

    def test_identical_facts_are_deduplicated_with_all_supporting_ids(self) -> None:
        first = H.fact("component.silicon_revision", H.text("B"), fact_id=H.uuid_for(41))
        second = H.fact("component.silicon_revision", H.text("B"), fact_id=H.uuid_for(42))
        facts = (first, second,) + tuple(
            f for f in BASE_FACTS if f.selector != "component.silicon_revision"
        )
        rule = evaluated(facts).rules[0]
        self.assertEqual(rule.target, "true")
        self.assertEqual(set(rule.target_trace.fact_ids), {first.id, second.id})
        self.assertEqual(rule.target_trace.resolved_value.value, "B")

    def test_other_component_facts_are_ignored(self) -> None:
        other_scope = H.scope(subject=H.OTHER_COMPONENT)
        facts = (
            H.fact("component.silicon_revision", H.text("B"), fact_scope=other_scope),
            H.fact("operating.external_reset_used", H.boolean(True), fact_scope=other_scope),
            H.fact("operating.reset_pulse_ns", H.quantity("10", "ns"), fact_scope=other_scope),
        )
        result = evaluated(facts)
        self.assertEqual(result.rules[0].overall, "unknown")
        self.assertIn("OUT_OF_SCOPE_FACT_IGNORED", {warning.code for warning in result.warnings})

    def test_other_build_and_profile_facts_are_ignored(self) -> None:
        other_build = H.scope(firmware_build=H.OTHER_BUILD, operating_profile=H.OTHER_PROFILE)
        other_profile = H.scope(operating_profile=H.OTHER_PROFILE)
        facts = (
            H.fact("component.silicon_revision", H.text("B"), fact_scope=other_build),
            H.fact("operating.external_reset_used", H.boolean(True), fact_scope=other_profile),
            H.fact("operating.reset_pulse_ns", H.quantity("10", "ns"), fact_scope=other_build),
        )
        result = evaluated(facts)
        self.assertEqual(result.rules[0].overall, "unknown")
        self.assertNotIn("contradiction", [item.selector for item in result.contradictions])

    def test_draft_and_rejected_facts_never_supply_values(self) -> None:
        facts = (
            H.fact("component.silicon_revision", H.text("B"), review_state="draft"),
            H.fact("operating.external_reset_used", H.boolean(True), review_state="rejected"),
        )
        result = evaluated(facts)
        rule = result.rules[0]
        self.assertEqual(rule.target, "unknown")
        self.assertIn("component.silicon_revision", result.missing_selectors)
        self.assertIn("operating.external_reset_used", result.missing_selectors)

    def test_explicit_null_with_known_value_retains_warning(self) -> None:
        known = H.fact("component.silicon_revision", H.text("B"), fact_id=H.uuid_for(51))
        null = H.fact("component.silicon_revision", None, fact_id=H.uuid_for(52))
        facts = (known, null) + tuple(
            f for f in BASE_FACTS if f.selector != "component.silicon_revision"
        )
        result = evaluated(facts)
        rule = result.rules[0]
        self.assertEqual(rule.target, "true")
        self.assertIn("NULL_OBSERVATION_RETAINED", {warning.code for warning in result.warnings})
        self.assertEqual(set(rule.target_trace.fact_ids), {known.id, null.id})

    def test_resolve_selector_reports_conflict_status(self) -> None:
        raw = H.build_raw(
            facts=(
                H.fact("component.silicon_revision", H.text("B")),
                H.fact("operating.clock_hz", H.quantity("1000000", "Hz")),
                H.fact("operating.clock_hz", H.quantity("2000000", "Hz")),
            )
        )
        bundle = H.parse_bundle(raw)
        resolution = resolve_selector(bundle, "operating.clock_hz")
        self.assertEqual(resolution.status, "conflict")
        self.assertEqual(len(resolution.groups), 2)

    def test_out_of_scope_fixture_is_unknown_with_coverage_warning(self) -> None:
        result = evaluate(H.parse_bundle(H.load_fixture("out_of_scope.json")))
        self.assertEqual(result.rules[0].overall, "unknown")
        warning_codes = {warning.code for warning in result.warnings}
        self.assertIn("OUT_OF_SCOPE_FACT_IGNORED", warning_codes)
        self.assertIn("INVENTORY_INCOMPLETE", warning_codes)
        self.assertIn("UNSUPPORTED_ENTRIES", warning_codes)
        self.assertFalse(result.coverage_summary.inventory_complete)

    def test_unknown_revision_fixture(self) -> None:
        result = evaluate(H.parse_bundle(H.load_fixture("unknown_revision.json")))
        self.assertEqual(result.rules[0].overall, "unknown")
        self.assertIn("component.silicon_revision", result.missing_selectors)


if __name__ == "__main__":
    unittest.main()

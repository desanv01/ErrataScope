"""W02-G3: complete branch dependencies, missing selectors and trace evidence."""

from __future__ import annotations

import unittest

from erratascope_domain import evaluate

from tests import helpers as H


def evaluate_raw(raw):
    return evaluate(H.parse_bundle(raw))


class DependencyTests(unittest.TestCase):
    def test_every_branch_dependency_retained_under_false_target(self) -> None:
        rule = H.rule(
            target=H.constant(False),
            trigger=H.all_(
                H.eq("component.silicon_revision", H.text("B")),
                H.eq("operating.clock_hz", H.quantity("1", "Hz")),
            ),
            exceptions=(
                H.eq("firmware.initial_software_reset", H.boolean(True)),
                H.eq("operating.external_reset_used", H.boolean(True)),
            ),
        )
        facts = (
            H.fact("component.silicon_revision", H.text("B")),
            H.fact("operating.external_reset_used", H.boolean(True)),
        )
        result = evaluate_raw(H.build_raw(facts=facts, rules=(rule,)))
        evaluated = result.rules[0]
        self.assertEqual(evaluated.target, "false")
        self.assertEqual(evaluated.overall, "false")
        dependencies = [item.selector for item in result.selector_dependencies]
        self.assertEqual(
            dependencies,
            [
                "component.silicon_revision",
                "firmware.initial_software_reset",
                "operating.clock_hz",
                "operating.external_reset_used",
            ],
        )
        self.assertEqual(
            list(result.missing_selectors),
            ["firmware.initial_software_reset", "operating.clock_hz"],
        )
        missing_codes = [
            warning for warning in result.warnings if warning.code == "MISSING_SELECTOR"
        ]
        self.assertEqual(len(missing_codes), 2)

    def test_any_with_true_branch_still_records_missing_dependency(self) -> None:
        rule = H.rule(
            target=H.any_(
                H.constant(True),
                H.eq("operating.clock_hz", H.quantity("1", "Hz")),
            ),
            exceptions=(),
        )
        result = evaluate_raw(H.build_raw(rules=(rule,)))
        self.assertEqual(result.rules[0].target, "true")
        self.assertIn(
            "operating.clock_hz", [item.selector for item in result.selector_dependencies]
        )
        self.assertIn("operating.clock_hz", result.missing_selectors)

    def test_dependency_identity_deduplicates_same_scope_selector(self) -> None:
        rule = H.rule(
            target=H.eq("component.silicon_revision", H.text("B")),
            trigger=H.eq("component.silicon_revision", H.text("B")),
            exceptions=(),
        )
        result = evaluate_raw(H.build_raw(rules=(rule,)))
        selectors = [item.selector for item in result.selector_dependencies]
        self.assertEqual(selectors.count("component.silicon_revision"), 1)
        self.assertEqual(len(result.selector_dependencies), 1)

    def test_trace_contains_fact_ids_and_anchor_ids(self) -> None:
        result = evaluate_raw(H.build_raw())
        trace = result.rules[0].target_trace
        self.assertEqual(trace.selector, "component.silicon_revision")
        self.assertEqual(len(trace.fact_ids), 1)
        self.assertEqual(trace.anchor_ids, (H.ANCHOR,))
        self.assertEqual(trace.resolved_value.value, "B")
        self.assertEqual(trace.result, "true")

    def test_trace_paths_are_deterministic(self) -> None:
        result = evaluate_raw(H.build_raw())
        rule = H.parse_bundle(H.build_raw()).rules[0]
        rule_id = str(rule.id)
        target = result.rules[0].target_trace
        trigger = result.rules[0].trigger_trace
        self.assertEqual(target.path, f"rules/{rule_id}/target")
        self.assertEqual(trigger.path, f"rules/{rule_id}/trigger")
        self.assertEqual(trigger.children[0].path, f"rules/{rule_id}/trigger/children/0")

    def test_contradictory_selector_remains_a_dependency(self) -> None:
        facts = (
            H.fact("component.silicon_revision", H.text("B")),
            H.fact("operating.clock_hz", H.quantity("1000000", "Hz")),
            H.fact("operating.clock_hz", H.quantity("2000000", "Hz")),
        )
        rule = H.rule(
            trigger=H.lt("operating.clock_hz", H.quantity("1500000", "Hz")),
            exceptions=(),
        )
        result = evaluate_raw(H.build_raw(facts=facts, rules=(rule,)))
        self.assertIn("operating.clock_hz", [item.selector for item in result.selector_dependencies])
        self.assertIn("operating.clock_hz", result.missing_selectors)
        self.assertTrue(result.rules[0].trigger_trace.conflict)

    def test_all_three_branch_types_are_traversed(self) -> None:
        rule = H.rule(
            target=H.eq("component.silicon_revision", H.text("B")),
            trigger=H.eq("operating.external_reset_used", H.boolean(True)),
            exceptions=(H.eq("firmware.initial_software_reset", H.boolean(True)),),
        )
        result = evaluate_raw(H.build_raw(rules=(rule,)))
        selectors = {item.selector for item in result.selector_dependencies}
        self.assertEqual(
            selectors,
            {
                "component.silicon_revision",
                "operating.external_reset_used",
                "firmware.initial_software_reset",
            },
        )
        self.assertEqual(len(result.rules[0].exception_traces), 1)
        self.assertEqual(
            result.rules[0].exception_traces[0].path,
            f"rules/{H.RULE}/exceptions/0",
        )


if __name__ == "__main__":
    unittest.main()

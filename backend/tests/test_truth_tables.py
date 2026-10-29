"""W02-G2: explicit three-valued truth tables (all/any/not)."""

from __future__ import annotations

import unittest

from erratascope_domain import evaluate
from erratascope_domain.evaluate import truth_and, truth_not, truth_or

from tests import helpers as H

T, F, U = "true", "false", "unknown"

AND_TABLE = {
    (T, T): T,
    (T, F): F,
    (T, U): U,
    (F, T): F,
    (F, F): F,
    (F, U): F,
    (U, T): U,
    (U, F): F,
    (U, U): U,
}
OR_TABLE = {
    (T, T): T,
    (T, F): T,
    (T, U): T,
    (F, T): T,
    (F, F): F,
    (F, U): U,
    (U, T): T,
    (U, F): U,
    (U, U): U,
}
NOT_TABLE = {T: F, F: T, U: U}


class TruthTableTests(unittest.TestCase):
    def test_pairwise_all_table(self) -> None:
        for (left, right), expected in AND_TABLE.items():
            with self.subTest(left=left, right=right):
                self.assertEqual(truth_and([left, right]), expected)

    def test_pairwise_any_table(self) -> None:
        for (left, right), expected in OR_TABLE.items():
            with self.subTest(left=left, right=right):
                self.assertEqual(truth_or([left, right]), expected)

    def test_not_table(self) -> None:
        for value, expected in NOT_TABLE.items():
            with self.subTest(value=value):
                self.assertEqual(truth_not(value), expected)

    def _evaluate_target(self, target_ast: dict):
        rule = H.rule(target=target_ast, exceptions=())
        raw = H.build_raw(rules=(rule,))
        return evaluate(H.parse_bundle(raw)).rules[0]

    def test_end_to_end_all_any_not_with_unknown_leaf(self) -> None:
        unknown_leaf = H.eq("operating.clock_hz", H.quantity("1", "Hz"))
        true_leaf = H.constant(True)
        false_leaf = H.constant(False)
        cases = {
            "all_true_unknown": (H.all_(true_leaf, unknown_leaf), U),
            "all_false_unknown": (H.all_(false_leaf, unknown_leaf), F),
            "any_true_unknown": (H.any_(true_leaf, unknown_leaf), T),
            "any_false_unknown": (H.any_(false_leaf, unknown_leaf), U),
            "not_unknown": (H.not_(unknown_leaf), U),
            "not_true": (H.not_(true_leaf), F),
            "not_false": (H.not_(false_leaf), T),
        }
        for name, (target, expected) in cases.items():
            with self.subTest(name=name):
                rule = self._evaluate_target(target)
                self.assertEqual(rule.target, expected)
                self.assertEqual(rule.overall, expected)

    def test_false_target_with_unknown_trigger_retains_warning(self) -> None:
        rule = H.rule(
            target=H.constant(False),
            trigger=H.eq("operating.clock_hz", H.quantity("1", "Hz")),
            exceptions=(),
        )
        result = evaluate(H.parse_bundle(H.build_raw(rules=(rule,))))
        evaluated = result.rules[0]
        self.assertEqual(evaluated.target, F)
        self.assertEqual(evaluated.trigger, U)
        self.assertEqual(evaluated.overall, F)
        self.assertEqual(evaluated.applicability, "not_applicable")
        self.assertIn("operating.clock_hz", result.missing_selectors)
        self.assertIn("MISSING_SELECTOR", {warning.code for warning in result.warnings})


if __name__ == "__main__":
    unittest.main()

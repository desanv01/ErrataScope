"""Codex review-02 regressions for serialization and raw-container bypasses."""
import copy
import json
from pathlib import Path
import unittest

from erratascope_domain import evaluate, parse_bundle
from erratascope_domain.errors import DomainValidationError
from erratascope_domain.selectors import TextValue


class PublicBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((Path(__file__).parents[1] / 'fixtures/w02/applicable.json').read_text())

    def test_constructed_bytes_operand_not_coerced_to_text(self):
        bundle = parse_bundle(self.raw)
        operand = TextValue.model_construct(kind='text', value=b'B')
        target = bundle.rules[0].target.model_copy(update={'value': operand})
        rule = bundle.rules[0].model_copy(update={'target': target})
        invalid = bundle.model_copy(update={'rules': (rule,)})
        with self.assertRaises(DomainValidationError) as caught:
            evaluate(invalid)
        self.assertIn('SCHEMA_INVALID', caught.exception.codes)
        self.assertIsInstance(invalid.rules[0].target.value.value, bytes)

    def test_rules_tuple_cannot_bypass_aggregate_cap(self):
        raw = copy.deepcopy(self.raw)
        node = {'op': 'constant', 'value': True,
                'anchor_ids': [raw['anchors'][0]['anchor_id']],
                'review_rationale': 'Original synthetic boundary case'}
        raw['rules'][0].update(target={'op': 'all', 'children': [node] * 300},
                               trigger={'op': 'all', 'children': [node] * 300}, exceptions=[])
        raw['rules'] = tuple(raw['rules'])
        with self.assertRaises(DomainValidationError) as caught:
            parse_bundle(raw)
        self.assertIn('SCHEMA_INVALID', caught.exception.codes)

    def test_exceptions_tuple_cannot_bypass_aggregate_cap(self):
        raw = copy.deepcopy(self.raw)
        node = {'op': 'constant', 'value': False,
                'anchor_ids': [raw['anchors'][0]['anchor_id']],
                'review_rationale': 'Original synthetic boundary case'}
        raw['rules'][0]['exceptions'] = tuple(copy.deepcopy(node) for _ in range(511))
        with self.assertRaises(DomainValidationError) as caught:
            parse_bundle(raw)
        self.assertIn('SCHEMA_INVALID', caught.exception.codes)

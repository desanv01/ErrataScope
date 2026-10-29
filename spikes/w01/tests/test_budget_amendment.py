"""Offline count-cap tests using a copy of existing history; no provider calls."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'spikes/w01'))
from erratascope_w01 import config
from erratascope_w01.ledger import Ledger, BudgetExhausted, load_pricing


class BudgetAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.real_path = config.PROVIDER_DIR/'ledger.json'
        self.before_hash = hashlib.sha256(self.real_path.read_bytes()).hexdigest()
        source = json.loads(self.real_path.read_text(encoding='utf-8'))
        # Keep the first two actual failed reservations even after later calls exist.
        source['attempts'] = source['attempts'][:2]
        self.assertEqual(len(source['attempts']), 2)
        source['requests_reserved'] = 2
        source['spend_reserved_usd'] = sum(a['estimated_cost_usd'] for a in source['attempts'])
        source['caps'] = dict(config.BUDGET)
        directory = ROOT/'.local/config-tests'/uuid.uuid4().hex
        directory.mkdir(parents=True)
        self.path = directory/'ledger.json'
        self.path.write_text(json.dumps(source), encoding='utf-8')
        self.addCleanup(directory.rmdir)
        self.addCleanup(self.path.unlink, missing_ok=True)
        self.original = source
        self.payload = {'model':config.PROVIDER['model_id'], 'messages':[{'role':'user','content':'offline'}], 'max_tokens':16}

    def tearDown(self):
        self.assertEqual(hashlib.sha256(self.real_path.read_bytes()).hexdigest(), self.before_hash)

    def reserve(self, ledger):
        return ledger.reserve(case='real_source', payload=self.payload, pricing=load_pricing(), prompt_version='offline-budget-test', execution_mode='mock')

    def test_two_used_slots_are_retained_and_fifth_is_blocked_after_restart(self):
        self.assertEqual(config.BUDGET['max_requests'], 4)
        self.assertEqual(config.BUDGET['max_estimated_spend_usd'], .25)
        ledger = Ledger(self.path)
        self.assertEqual(self.reserve(ledger).attempt, 3)
        restarted = Ledger(self.path)
        self.assertEqual(self.reserve(restarted).attempt, 4)
        restarted = Ledger(self.path)
        before = self.path.read_bytes()
        with self.assertRaises(BudgetExhausted):
            self.reserve(restarted)
        self.assertEqual(self.path.read_bytes(), before)
        state = restarted.state.model_dump(mode='json')
        self.assertEqual(state['attempts'][:2], self.original['attempts'])
        self.assertEqual(state['blocked_events'], self.original['blocked_events'])
        self.assertEqual(state['requests_reserved'], 4)
        self.assertGreater(state['spend_reserved_usd'], self.original['spend_reserved_usd'])

    def test_spending_guard_still_blocks_before_request_cap(self):
        # Simulate an already nearly exhausted monetary envelope without paid calls.
        ledger = Ledger(self.path)
        with patch.dict(config.BUDGET, {'max_estimated_spend_usd': self.original['spend_reserved_usd']}):
            before = self.path.read_bytes()
            with self.assertRaises(BudgetExhausted):
                self.reserve(ledger)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(ledger.state.requests_reserved, 2)


if __name__ == '__main__':
    unittest.main()

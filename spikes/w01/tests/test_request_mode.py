"""Offline wire-format and report freshness regressions; no provider requests."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erratascope_w01 import config, provider, report


class RequestModeTests(unittest.TestCase):
    def test_both_cases_send_reasoning_control_without_metadata(self):
        spec = importlib.util.spec_from_file_location('mode_cli', Path(__file__).resolve().parents[1]/'run.py')
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        for factory in [cli._load_real_source_case, cli._load_synthetic_case]:
            with self.subTest(case=factory.__name__):
                payload = factory()['payload']
                calls = []
                def handler(request):
                    calls.append(request)
                    body = json.loads(request.content)
                    self.assertEqual(body['chat_template_kwargs'], {'enable_thinking': False})
                    self.assertEqual(body['max_tokens'], 8192)
                    self.assertEqual(body['model'], config.PROVIDER['model_id'])
                    self.assertEqual(str(request.url), 'https://api.tokenfactory.nebius.com/v1/chat/completions')
                    self.assertFalse({'case', 'prompt_metadata', 'extra_body'} & set(body))
                    return httpx.Response(400, json={'error':'offline compatibility failure'})
                with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                    response = provider.send_request(payload, 'OFFLINE-TEST-ONLY', client=client)
                self.assertEqual(response['status_code'], 400)
                self.assertEqual(len(calls), 1)  # no retry even on rejection
                self.assertEqual(payload['prompt_metadata']['prompt_version'], 'draft-v4-grounded-no-thinking')

    def test_old_and_other_case_blockers_are_not_current(self):
        ledger = {'blocked_events':[
            {'utc':'2026-01-01T00:00:00Z','case':'synthetic_missing_revision','reason':'old missing key'},
            {'utc':'2026-10-29T22:00:01Z','case':'real_source','reason':'current real failure'},
        ]}
        with patch.object(config, 'WORKER_ATTEMPT_START_UTC', '2026-10-29T22:00:00Z'):
            self.assertIsNone(report._blocked_reason(ledger, 'synthetic_missing_revision'))
            self.assertEqual(report._blocked_reason(ledger, 'real_source'), 'current real failure')
            ledger['blocked_events'].append({'utc':'2026-10-29T22:00:02Z','case':'synthetic_missing_revision','reason':'current synthetic failure'})
            self.assertEqual(report._blocked_reason(ledger, 'synthetic_missing_revision'), 'current synthetic failure')

if __name__ == '__main__':
    unittest.main()

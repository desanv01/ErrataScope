"""Read-only inspection of worker 04 evidence; no network or ledger writes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'spikes/w01'))
sys.dont_write_bytecode = True
from erratascope_w01 import config, evidence, report
from erratascope_w01.localenv import load_nebius_key
from erratascope_w01.ledger import estimate_cost_usd, bound_input_tokens

out = ROOT / '.local/reviews/W01-review-04'
out.mkdir(parents=True, exist_ok=True)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
ledger_path = config.PROVIDER_DIR / 'ledger.json'
before = digest(ledger_path)
ledger = json.loads(ledger_path.read_text())
assert len(ledger['attempts']) == ledger['requests_reserved'] == 1
r = ledger['attempts'][0]
assert r['attempt'] == 1 and r['case'] == 'real_source' and r['execution_mode'] == 'live'
artifacts = {}
for kind in ['request', 'response']:
    p = ROOT / r[kind + '_artifact']
    assert digest(p) == r[kind + '_sha256']
    a = json.loads(p.read_text())
    assert a['case'] == r['case'] and a['attempt'] == 1 and a['artifact_kind'] == kind
    assert a['endpoint'] == evidence.expected_endpoint()
    assert a['model_requested'] == config.PROVIDER['model_id']
    artifacts[kind] = a
assert not r.get('validation_artifact')
response = artifacts['response']
body = response['body']; choice = body['choices'][0]; usage = body['usage']
assert response['http_status'] == 200 and body['model'] == config.PROVIDER['model_id']
assert choice['finish_reason'] == 'length' and choice['message']['content'] is None
assert usage['completion_tokens'] == usage['completion_tokens_details']['reasoning_tokens'] == 8192
assert usage['prompt_tokens'] == 2481 and usage['total_tokens'] == 10673
reserved = estimate_cost_usd(r['input_token_bound'], r['max_output_tokens'], r['pricing'])
assert abs(reserved - r['estimated_cost_usd']) < 1e-12
assert abs(ledger['spend_reserved_usd'] - reserved) < 1e-12
assert bound_input_tokens(artifacts['request']['request'])['tokens'] == r['input_token_bound']
actual_estimate = estimate_cost_usd(usage['prompt_tokens'], usage['completion_tokens'], r['pricing'])
spec = importlib.util.spec_from_file_location('review_cli', ROOT/'spikes/w01/run.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
real = cli._load_real_source_case()
inputs = dict(ledger=ledger, anchors=real['anchors'], expected_document_sha256=real['document_sha256'], expected_identity=real['expected_identity'])
result = evidence.evaluate_case(record=r, case='real_source', **inputs)
gate = report.derive_case_gate(r, gate_id='G4', case='real_source', blocked_reason=None, case_inputs=inputs)
assert result.status == gate['status'] == 'FAIL'
assert not any(a['case'] == 'synthetic_missing_revision' for a in ledger['attempts'])
assert not list((config.PROVIDER_DIR/'cases/synthetic_missing_revision').glob('*.json'))
load_nebius_key(); key = os.environ.get('NEBIUS_API_KEY', '')
assert key.strip()
paths = list((ROOT/'docs').rglob('*.md')) + list((ROOT/'docs').rglob('*.json')) + list(config.RESULT_DIR.rglob('*.json'))
leaks = [p for p in paths if key.encode() in p.read_bytes()]
assert not leaks, 'Configured credential detected in evidence; paths/values suppressed'
assert not (ROOT/'.local/coordination/ACTIVE_WORKER.json').exists()
assert digest(ledger_path) == before
summary = dict(status='PASS', meaning='Review checks pass; W01 live acceptance still FAIL', paid_calls=0,
    ledger_sha256=before, actual_attempts=1, remaining_attempts=2, reserved_usd=reserved,
    usage_estimate_usd=actual_estimate, usage=usage, g4=gate, synthetic_live='NOT_RUN',
    configured_key_leaks=0, scanned_files=len(paths), reasoning_chars=len(choice['message'].get('reasoning_content') or ''),
    request_sha256=r['request_sha256'], response_sha256=r['response_sha256'])
(out/'observations.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))

"""Independent worker-05 evidence audit. No provider calls or ledger mutations."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'spikes/w01'))
sys.dont_write_bytecode = True
from erratascope_w01 import config, evidence, report
from erratascope_w01.ledger import estimate_cost_usd, bound_input_tokens
from erratascope_w01.localenv import load_nebius_key
from erratascope_w01.validate import validate_draft

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT/'.local/reviews/W01-review-05'; out.mkdir(parents=True, exist_ok=True)
lp = config.PROVIDER_DIR/'ledger.json'; before = sha(lp); ledger = read(lp)
assert ledger['requests_reserved'] == len(ledger['attempts']) == 2
history = ROOT/'.local/w01/history/attempt-04-before-05'
manifest = read(history/'BACKUP_MANIFEST.json')
assert all(sha(history/f['path']) == f['sha256'] for f in manifest['files'])
old_candidates = [history/f['path'] for f in manifest['files'] if f['path'].endswith('ledger.json')]
assert len(old_candidates) == 1
old = read(old_candidates[0])
assert ledger['attempts'][0] == old['attempts'][0]
assert ledger['blocked_events'] == old['blocked_events']
assert {k:v for k,v in ledger['pricing'].items() if k != 'validated_utc'} == {k:v for k,v in old['pricing'].items() if k != 'validated_utc'}
assert ledger['caps'] == old['caps']
bundles = []
for i, rec in enumerate(ledger['attempts'], 1):
    assert rec['attempt'] == i and rec['execution_mode'] == 'live' and rec['case'] == 'real_source'
    bundle = {}
    for kind in ['request', 'response', 'validation']:
        if not rec.get(kind+'_artifact'):
            assert i == 1 and kind == 'validation'; continue
        p = ROOT/rec[kind+'_artifact']; assert sha(p) == rec[kind+'_sha256']
        a = read(p); assert a['attempt'] == i and a['case'] == rec['case'] and a['artifact_kind'] == kind
        if kind != 'validation':
            assert a['endpoint'] == evidence.expected_endpoint()
            assert a['model_requested'] == config.PROVIDER['model_id']
        bundle[kind] = a
    assert bound_input_tokens(bundle['request']['request'])['tokens'] == rec['input_token_bound']
    assert abs(estimate_cost_usd(rec['input_token_bound'], rec['max_output_tokens'], rec['pricing']) - rec['estimated_cost_usd']) < 1e-12
    bundles.append(bundle)
r = ledger['attempts'][1]; b = bundles[1]; body = b['response']['body']; choice = body['choices'][0]
assert b['request']['request']['chat_template_kwargs'] == {'enable_thinking': False}
assert b['request']['prompt_version'] == 'draft-v3-no-thinking'
assert b['response']['http_status'] == 200 and body['model'] == config.PROVIDER['model_id']
assert choice['finish_reason'] == 'stop' and body['usage']['completion_tokens_details']['reasoning_tokens'] == 0
draft = json.loads(choice['message']['content'])
spec = importlib.util.spec_from_file_location('audit_cli', ROOT/'spikes/w01/run.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
real = cli._load_real_source_case()
args = dict(anchors=real['anchors'], expected_document_sha256=real['document_sha256'], expected_identity=real['expected_identity'])
validation = validate_draft(draft, **args)
assert validation.status == 'rejected'
assert len(validation.errors) == 2 and all('anchor_ids' in e for e in validation.errors)
result = evidence.evaluate_case(record=r, case='real_source', ledger=ledger, **args)
gate = report.derive_case_gate(r, gate_id='G4', case='real_source', blocked_reason=None, case_inputs={**args,'ledger':ledger})
assert result.status == gate['status'] == 'FAIL'
# Counterfactual diagnostic ONLY: deleting empty-citation claims can pass structural
# validation but leaves semantic defects. Never write this as a provider artifact.
structural_only = copy.deepcopy(draft)
structural_only['claims'] = [c for c in draft['claims'] if c['anchor_ids']]
counterfactual = validate_draft(structural_only, **args)
assert counterfactual.status == 'accepted'
anchor_index = {a.anchor_id:a.text for a in real['anchors']}
assert draft['claims'][5]['field'] == 'exception'
assert 'use the new register definition' in anchor_index['st-es0620:p06:029']
assert 'requires' in draft['claims'][8]['statement'] and '0x34001004' in draft['claims'][8]['statement']
assert 'any address in AXISRAM1' in anchor_index['st-es0620:p09:020']
assert not any(a['case'] == 'synthetic_missing_revision' for a in ledger['attempts'])
assert not list((config.PROVIDER_DIR/'cases/synthetic_missing_revision').glob('*.json'))
reserved = sum(a['estimated_cost_usd'] for a in ledger['attempts'])
assert abs(reserved - ledger['spend_reserved_usd']) < 1e-12
usage_estimate = sum(estimate_cost_usd(b['response']['body']['usage']['prompt_tokens'], b['response']['body']['usage']['completion_tokens'], rec['pricing']) for b, rec in zip(bundles, ledger['attempts']))
load_nebius_key(); key = os.environ.get('NEBIUS_API_KEY',''); assert key.strip()
scan = list((ROOT/'docs').rglob('*.md'))+list((ROOT/'docs').rglob('*.json'))+list(config.RESULT_DIR.rglob('*.json'))
assert not any(key.encode() in p.read_bytes() for p in scan), 'Credential detected; values suppressed'
assert not (ROOT/'.local/coordination/ACTIVE_WORKER.json').exists()
assert sha(lp) == before
summary = dict(review_checks='PASS', acceptance='FAIL', paid_review_calls=0, ledger_sha256=before,
    history_files_verified=len(manifest['files']), prior_ledger_history_unchanged=True,
    reservations=2, remaining=1, reserved_usd=reserved, usage_estimate_total_usd=usage_estimate,
    usage=body['usage'], validation=validation.as_dict(), g4=gate, live_g5='NOT_RUN',
    counterfactual_structural_result=counterfactual.status,
    counterfactual_semantic_result='REJECTED: workaround mislabeled as exception; example address made mandatory',
    configured_key_leaks=0, scan_files=len(scan))
(out/'observations.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))

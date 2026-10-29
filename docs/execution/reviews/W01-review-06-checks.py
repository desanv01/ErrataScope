"""Read-only audit of accepted live artifacts, with offline CLI replay. No inference."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import sys
from argparse import Namespace
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'spikes/w01')); sys.dont_write_bytecode = True
from erratascope_w01 import config, evidence, report
from erratascope_w01.ledger import bound_input_tokens, estimate_cost_usd, load_pricing
from erratascope_w01.localenv import load_nebius_key
from erratascope_w01.validate import validate_draft
from erratascope_w01.cases import evaluate_missing_information
from erratascope_w01.schemas import DraftInterpretation

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT/'.local/reviews/W01-review-06'; out.mkdir(parents=True,exist_ok=True)
lp=config.PROVIDER_DIR/'ledger.json'; before=sha(lp); ledger=read(lp)
activation=read(ROOT/'docs/execution/decisions/W01-v4-activation.json')
assert ledger['caps']==config.BUDGET==activation['caps_after']
assert ledger['requests_reserved']==len(ledger['attempts'])==4
history=ROOT/'.local/w01/history/attempt-05-before-06'; backup=read(history/'BACKUP_MANIFEST.json')
assert all(sha(history/f['path'])==f['sha256'] for f in backup['files'])
prior_path=next(history/f['path'] for f in backup['files'] if f['path'].endswith('ledger.json'))
assert sha(prior_path)==activation['ledger_sha256_after']
prior=read(prior_path)
assert ledger['attempts'][:2]==prior['attempts'] and ledger['blocked_events']==prior['blocked_events']
assert all(sha(ROOT/a['path'])==a['sha256'] for a in activation['unchanged_artifacts'])
spec=importlib.util.spec_from_file_location('audit_cli',ROOT/'spikes/w01/run.py')
cli=importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
case_inputs={}; observations=[]; usage_cost=0
for rec in ledger['attempts']:
    artifacts={}
    for kind in ['request','response','validation']:
        if not rec.get(kind+'_artifact'):
            assert rec['attempt']==1 and kind=='validation'; continue
        p=ROOT/rec[kind+'_artifact']; assert sha(p)==rec[kind+'_sha256']; a=read(p)
        assert a['attempt']==rec['attempt'] and a['case']==rec['case'] and a['artifact_kind']==kind
        artifacts[kind]=a
    req=artifacts['request']; response=artifacts['response']; body=response['body']
    assert req['endpoint']==response['endpoint']==evidence.expected_endpoint()
    assert req['model_requested']==response['model_requested']==body['model']==config.PROVIDER['model_id']
    assert bound_input_tokens(req['request'])['tokens']==rec['input_token_bound']
    assert abs(estimate_cost_usd(rec['input_token_bound'],rec['max_output_tokens'],rec['pricing'])-rec['estimated_cost_usd'])<1e-12
    usage=body['usage']; usage_cost+=estimate_cost_usd(usage['prompt_tokens'],usage['completion_tokens'],rec['pricing'])
    if rec['attempt']<3: continue
    choice=body['choices'][0]
    assert response['http_status']==200 and choice['finish_reason']=='stop'
    assert req['request']['chat_template_kwargs']=={'enable_thinking':False}
    assert req['prompt_version']=='draft-v4-grounded-no-thinking'
    assert usage['completion_tokens_details']['reasoning_tokens']==0
    draft=json.loads(choice['message']['content'])
    case=cli._load_real_source_case() if rec['case']=='real_source' else cli._load_synthetic_case()
    args=dict(anchors=case['anchors'],expected_document_sha256=case['document_sha256'],expected_identity=case['expected_identity'])
    case_inputs[rec['case']]=args
    assert req['request']==case['payload']
    validation=validate_draft(draft,**args); assert validation.status=='accepted'
    verdict=evidence.evaluate_case(record=rec,case=rec['case'],ledger=ledger,**args)
    gate=report.derive_case_gate(rec,gate_id=rec['case'],case=rec['case'],blocked_reason=None,case_inputs={**args,'ledger':ledger})
    assert verdict.status==gate['status']=='PASS'
    if rec['case']=='synthetic_missing_revision':
        assert draft['source_document_id'] is None and draft['source_revision'] is None
        assert evaluate_missing_information(DraftInterpretation(**draft))['status']=='pass'
    # Exercise actual CLI result handling with preserved live artifacts. Dispatch is
    # stubbed to return the existing record; this is NOT another live provider test.
    fake_ledger=MagicMock(); pricing=load_pricing(); fake_ledger.state.pricing=pricing
    fake_ledger.state.model_dump.return_value=ledger
    with patch('erratascope_w01.ledger.Ledger',return_value=fake_ledger), patch('erratascope_w01.provider.run_case',return_value=rec) as dispatch, patch.dict(os.environ,{'NEBIUS_API_KEY':'OFFLINE-AUDIT-ONLY'}), redirect_stdout(io.StringIO()):
        code=cli.cmd_probe_provider(Namespace(case=rec['case'].replace('_','-'),pricing_file=None))
        assert code==0 and dispatch.call_count==1
    observations.append({'attempt':rec['attempt'],'case':rec['case'],'artifact_status':verdict.status,'cli_replay_exit':code,'report_gate':gate['status'],'usage':usage,'request_sha256':rec['request_sha256'],'response_sha256':rec['response_sha256'],'validation_sha256':rec['validation_sha256']})
state={'manifest':read(config.MANIFEST_PATH),'anchors':read(config.RESULT_DIR/'anchors.json'),'coverage':read(config.RESULT_DIR/'coverage.json'),'renders':read(config.RESULT_DIR/'renders.json'),'selftest':read(config.RESULT_DIR/'selftest.json'),'baseline':read(config.RESULT_DIR/'baseline_check.json'),'environment':read(config.ENVIRONMENT_PATH),'ledger':ledger}
gates=report.compute_gates(state,case_inputs)
assert len(gates)==7 and all(g['status']=='PASS' for g in gates)
assert [(g['gate'],g['status']) for g in gates]==[(g['gate'],g['status']) for g in read(config.RESULT_DIR/'report_summary.json')['gates']]
reserved=sum(a['estimated_cost_usd'] for a in ledger['attempts']); assert abs(reserved-ledger['spend_reserved_usd'])<1e-12
assert reserved<=.25
load_nebius_key();key=os.environ.get('NEBIUS_API_KEY','');assert key.strip()
scan=list((ROOT/'docs').rglob('*.md'))+list((ROOT/'docs').rglob('*.json'))+list(config.RESULT_DIR.rglob('*.json'))
assert not any(key.encode() in p.read_bytes() for p in scan),'Credential detected; values suppressed'
assert sha(lp)==before and not (ROOT/'.local/coordination/ACTIVE_WORKER.json').exists()
summary=dict(status='PASS',paid_review_requests=0,ledger_sha256=before,previous_history_unchanged=True,backup_files_verified=len(backup['files']),cases=observations,gates=gates,reservations_used=4,reservations_remaining=0,reserved_usd=reserved,usage_estimate_usd=usage_cost,configured_key_scan_files=len(scan),configured_key_leaks=0)
(out/'observations.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))

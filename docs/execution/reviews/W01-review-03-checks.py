"""Offline independent artifact-binding checks; never calls the provider."""
from pathlib import Path
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout
from argparse import Namespace
import importlib.util
import io
import hashlib
import json
import os
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'spikes/w01'))
sys.dont_write_bytecode = True
from erratascope_w01 import config, selftest

spec = importlib.util.spec_from_file_location('w01_review_cli', ROOT/'spikes/w01/run.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def cli_exit(bundle):
    """Exercise the real command function, replacing only dispatch/ledger/input IO."""
    from erratascope_w01.ledger import load_pricing
    pricing = load_pricing()
    ledger = MagicMock()
    ledger.state.pricing = pricing
    ledger.state.model_dump.return_value = bundle['ledger']
    materials = bundle['materials']
    case = dict(case=bundle['case'], payload={}, anchors=materials['anchors'],
                expected_identity=materials['identity'], document_sha256=materials['sha'])
    with patch('erratascope_w01.ledger.Ledger', return_value=ledger), \
         patch('erratascope_w01.provider.run_case', return_value=bundle['record']) as dispatch, \
         patch.object(cli,'_load_real_source_case',return_value=case), \
         patch.object(cli,'_load_synthetic_case',return_value=case), \
         patch.dict(os.environ, {'NEBIUS_API_KEY':'OFFLINE-REVIEW-DUMMY-NOT-A-KEY'}), \
         redirect_stdout(io.StringIO()):
        result = cli.cmd_probe_provider(Namespace(case=bundle['case'].replace('_','-'),pricing_file=None))
        assert dispatch.call_count == 1
        return result


def main():
    out = ROOT / '.local/reviews/W01-review-03' / ('run-' + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    assert out.resolve().is_relative_to((ROOT / '.local/reviews/W01-review-03').resolve())
    original = config.RESULT_DIR
    real_ledger = config.PROVIDER_DIR / 'ledger.json'
    before = hashlib.sha256(real_ledger.read_bytes()).hexdigest()
    results = out / 'results'; results.mkdir()
    for name in ['anchors.json','coverage.json','revision_matrix.json']:
        shutil.copy2(original/name, results/name)
    observations = {'network_used': False, 'paid_requests': 0, 'live_attempts': len(json.loads(real_ledger.read_text())['attempts'])}
    variants = ['valid_real','empty_artifact','wrong_case','wrong_attempt','http_401','replaced','tool_calls','draft_disagreement','null_content','list_content','scalar_content','list_saved_draft','malformed_choices','valid_synthetic','mock','bad_choice','bad_message','bad_validation','bad_inputs','bad_identity']
    checks = []
    with patch.object(config,'RESULT_DIR',results), patch.object(config,'LOCAL_DIR',out/'local'), patch.object(config,'PROVIDER_DIR',out/'provider'), patch.object(selftest,'TMP_ROOT',out/'tmp'), patch.dict(os.environ,{},clear=True):
        suite = selftest.run_self_test()
        observations['worker_suite'] = {k:suite[k] for k in ['checks_total','checks_passed','checks_failed','checks_skipped']}
        for variant in variants:
            case = 'synthetic_missing_revision' if variant=='valid_synthetic' else 'real_source'
            with selftest._bundle('independent-'+variant,case) as b:
                def read(kind):
                    return json.loads(b['paths'][kind].read_text(encoding='utf-8'))
                if variant=='empty_artifact': selftest._rewrite(b,'response',{})
                if variant=='wrong_case':
                    response=read('response'); response['case']='synthetic_missing_revision'; selftest._rewrite(b,'response',response)
                if variant=='wrong_attempt':
                    response=read('response'); response['attempt']=99; selftest._rewrite(b,'response',response)
                if variant=='http_401':
                    response=read('response'); response['http_status']=401; selftest._rewrite(b,'response',response)
                if variant=='replaced': selftest._rewrite(b,'response',raw='{}',rehash=False)
                if variant=='tool_calls':
                    response=read('response'); response['body']['choices'][0]['finish_reason']='tool_calls'; selftest._rewrite(b,'response',response)
                if variant=='draft_disagreement':
                    v=read('validation'); v['draft']['source_document_id']='UNRELATED'; selftest._rewrite(b,'validation',v)
                if variant in ['null_content','list_content','scalar_content']:
                    response=read('response'); response['body']['choices'][0]['message']['content']={'null_content':'null','list_content':'[]','scalar_content':'7'}[variant]; selftest._rewrite(b,'response',response)
                if variant=='list_saved_draft':
                    v=read('validation'); v['draft']=[]; selftest._rewrite(b,'validation',v)
                if variant=='malformed_choices':
                    response=read('response'); response['body']['choices']={'bad':'shape'}; selftest._rewrite(b,'response',response)
                if variant=='bad_choice':
                    response=read('response'); response['body']['choices']=[7]; selftest._rewrite(b,'response',response)
                if variant=='bad_message':
                    response=read('response'); response['body']['choices'][0]['message']=['wrong']; selftest._rewrite(b,'response',response)
                if variant in ['bad_validation','bad_inputs','bad_identity']:
                    v=read('validation')
                    if variant=='bad_identity': v['inputs']['identity']=['wrong']
                    else: v[{'bad_validation':'validation','bad_inputs':'inputs'}[variant]]=['wrong']
                    selftest._rewrite(b,'validation',v)
                if variant=='mock': b['record']['execution_mode']='mock'
                expected='PASS' if variant.startswith('valid_') else ('MOCK_ONLY' if variant=='mock' else 'FAIL')
                try:
                    verdict=selftest._evaluate(b); report=selftest._gate(b)
                    exit_code=cli_exit(b)
                    wanted_report='NOT_RUN' if expected=='MOCK_ONLY' else expected
                    checks.append({'case':variant,'expected':expected,'evidence':verdict.status,'report':report['status'],'cli_exit':exit_code,'pass':verdict.status==expected and report['status']==wanted_report and exit_code==(0 if expected=='PASS' else 1)})
                except Exception as exc:
                    checks.append({'case':variant,'expected':expected,'exception':type(exc).__name__,'pass':False})
    observations['checks']=checks
    observations['independent_passed']=sum(c['pass'] for c in checks)
    observations['independent_total']=len(checks)
    observations['original_live_ledger_unchanged']=hashlib.sha256(real_ledger.read_bytes()).hexdigest()==before
    (out/'observations.json').write_text(json.dumps(observations,indent=2)+'\n',encoding='utf-8')
    observations['evidence_path']=(out/'observations.json').relative_to(ROOT).as_posix()
    print(json.dumps(observations,indent=2))
    return 0 if all(c['pass'] for c in checks) and suite['checks_failed']==0 else 1


if __name__=='__main__':
    sys.exit(main())

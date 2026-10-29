"""Independent offline review of W01 attempt 02. Does not modify worker evidence."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'spikes/w01'))
sys.dont_write_bytecode = True
from erratascope_w01 import cases, config, ledger, provider, report, selftest
from erratascope_w01.schemas import AnchorDocument
from erratascope_w01.validate import validate_draft
import httpx


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    out = ROOT / '.local/reviews/W01-review-02' / ('run-' + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    assert out.resolve().is_relative_to((ROOT / '.local/reviews/W01-review-02').resolve())
    result = {'network_used': False, 'paid_requests': 0, 'generated_utc': datetime.now(timezone.utc).isoformat()}
    original_results = config.RESULT_DIR
    original_ledger = config.PROVIDER_DIR / 'ledger.json'
    ledger_hash_before = hashlib.sha256(original_ledger.read_bytes()).hexdigest()
    result['original_provider_attempts'] = len(read(original_ledger)['attempts'])
    result['worker_lock_absent'] = not (ROOT / '.local/coordination/ACTIVE_WORKER.json').exists()
    isolated_results = out / 'suite-results'
    isolated_results.mkdir()
    for name in ['anchors.json', 'coverage.json', 'revision_matrix.json']:
        shutil.copy2(original_results / name, isolated_results / name)
    with patch.object(config, 'RESULT_DIR', isolated_results), patch.object(config, 'LOCAL_DIR', out / 'suite-local'), patch.object(config, 'PROVIDER_DIR', out / 'suite-provider'), patch.object(selftest, 'TMP_ROOT', out / 'suite-tmp'), patch.dict(os.environ, {}, clear=True):
        suite = selftest.run_self_test()
    result['worker_suite'] = {k: suite[k] for k in ['checks_total', 'checks_passed', 'checks_failed', 'checks_skipped']}
    result['worker_suite_failures'] = [v for v in suite['results'] if v['status'] == 'FAIL']

    pricing = ledger.load_pricing(config.PRICING_EVIDENCE_PATH)
    payload = {'model': config.PROVIDER['model_id'], 'messages': [{'role': 'user', 'content': 'SYNTHETIC OFFLINE REVIEW'}], 'max_tokens': 64, 'case': 'real_source', 'prompt_metadata': {'prompt_version': 'codex-review-02'}}
    timeout_dir = out / 'timeout'
    timeout_path = timeout_dir / 'ledger.json'
    observed = []
    def timeout(request):
        saved = ledger.Ledger(timeout_path).state
        observed.append({'reserved_before_dispatch': saved.requests_reserved, 'spend_reserved_before_dispatch': saved.spend_reserved_usd})
        raise httpx.ReadTimeout('Synthetic offline timeout', request=request)
    refused = 0
    with patch.object(config, 'PROVIDER_DIR', timeout_dir), httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        for _ in range(4):
            try:
                provider.run_case(case='real_source', payload=payload, anchors=[], expected_identity=None,
                    expected_document_sha256='0'*64, pricing=pricing, api_key='SYNTHETIC-NOT-A-CREDENTIAL',
                    ledger=ledger.Ledger(timeout_path), client=client, execution_mode='mock')
            except ledger.BudgetExhausted:
                refused += 1
    timeout_state = ledger.Ledger(timeout_path).state
    result['reservation_before_dispatch_and_restart'] = {
        'dispatches': len(observed), 'refused': refused, 'on_dispatch': observed,
        'states': [a.state for a in timeout_state.attempts],
        'pass': len(observed)==3 and refused==1 and [o['reserved_before_dispatch'] for o in observed]==[1,2,3] and all(a.state=='uncertain' for a in timeout_state.attempts)}

    # Deliberately inconsistent artifacts must not pass a live evidence gate.
    artifact_dir = out / 'gate-artifacts'
    artifact_dir.mkdir()
    record = {'attempt': 1, 'case': 'real_source', 'state': 'finalized', 'outcome': 'success', 'execution_mode': 'live',
        'http_status': 200, 'model_returned': config.PROVIDER['model_id'], 'finish_reason': 'stop',
        'validation': {'status': 'accepted'}, 'case_expectation': None,
        'reserved_utc': '2026-10-29T10:25:00Z', 'finalized_utc': '2026-10-29T10:26:00Z'}
    for kind in ['request','response','validation']:
        path = artifact_dir / (kind+'.json')
        path.write_text('{}', encoding='utf-8')
        record[kind+'_artifact'] = path.relative_to(ROOT).as_posix()
    result['empty_artifacts_gate'] = report.derive_case_gate(record, gate_id='G4', case='real_source', blocked_reason=None)['status']
    (artifact_dir/'response.json').write_text(json.dumps({'attempt': 99, 'case': 'synthetic_missing_revision', 'http_status': 401, 'body': {'error': 'SYNTHETIC rejected request'}}), encoding='utf-8')
    result['contradictory_artifacts_gate'] = report.derive_case_gate(record, gate_id='G4', case='real_source', blocked_reason=None)['status']
    wrong_case = dict(record, case='synthetic_missing_revision')
    result['wrong_case_record_gate'] = report.derive_case_gate(wrong_case, gate_id='G4', case='real_source', blocked_reason=None)['status']
    tool_finish = dict(record, finish_reason='tool_calls')
    result['cli_accepts_nonstop_finish'] = provider.passes_live_gate(tool_finish)

    manifest = read(config.MANIFEST_PATH)
    source = next(s for s in manifest['sources'] if s['source_key']=='st-es0620')
    doc = AnchorDocument(**read(original_results/'anchors.json'))
    identity = next(a for a in doc.anchors if a.context_kind=='source_identity')
    expected = cases.source_identity_from_manifest(manifest)
    draft = {'schema_version':1, 'source_document_id':source['document_id'], 'source_revision':source['revision'],
        'claims':[{'field':'source_identity','statement':'Document identity as printed.','anchor_ids':[identity.anchor_id],'status':'supported'}], 'unresolved_fields':[]}
    correct = validate_draft(draft, doc.anchors, doc.document_sha256, expected)
    wrong = copy.deepcopy(draft); wrong['source_document_id']='UNRELATED-DOCUMENT'
    wrong_result = validate_draft(wrong, doc.anchors, doc.document_sha256, expected)
    wrong_rev = copy.deepcopy(draft); wrong_rev['source_revision']='Rev 999'
    result['identity'] = {'correct':correct.status, 'wrong_document':wrong_result.status,
        'wrong_revision':validate_draft(wrong_rev,doc.anchors,doc.document_sha256,expected).status,
        'anchors':len(doc.anchors), 'context_anchors':sum(a.context_kind is not None for a in doc.anchors),
        'source_hash_matches':hashlib.sha256((ROOT/source['artifact_path']).read_bytes()).hexdigest()==source['sha256']==doc.document_sha256}
    result['original_provider_ledger_unchanged'] = hashlib.sha256(original_ledger.read_bytes()).hexdigest()==ledger_hash_before
    result['remaining_gate_defect'] = any(result[k]=='PASS' for k in ['empty_artifacts_gate','contradictory_artifacts_gate','wrong_case_record_gate']) or result['cli_accepts_nonstop_finish']
    (out/'observations.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    result['evidence_path'] = (out/'observations.json').relative_to(ROOT).as_posix()
    print(json.dumps(result,indent=2))
    return 1 if result['remaining_gate_defect'] or suite['checks_failed'] else 0


if __name__ == '__main__':
    sys.exit(main())

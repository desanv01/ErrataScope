"""Codex W01 review: offline checks, isolated artifacts, no paid/provider calls."""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'spikes/w01'))
sys.dont_write_bytecode = True
from erratascope_w01 import config, provider, report, selftest
from erratascope_w01.schemas import AnchorDocument, SourceManifest
from erratascope_w01.validate import validate_draft
import httpx
import pymupdf

OUT = ROOT / '.local/reviews/W01-review-01'
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    observations = {'network_used': False, 'paid_requests': 0}
    manifest = SourceManifest(**read(config.MANIFEST_PATH))
    source = next(s for s in manifest.sources if s.source_key == 'st-es0620')
    pdf_path = ROOT / source.artifact_path
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    document = AnchorDocument(**read(config.RESULT_DIR / 'anchors.json'))
    with pymupdf.open(pdf_path) as pdf:
        observations['source'] = {
            'hash_matches_manifest_and_anchors': digest == source.sha256 == document.document_sha256,
            'page_count_matches': len(pdf) == source.page_count == document.page_count,
            'page_count': len(pdf),
            'revision_visible_on_first_page': 'Rev 5' in pdf[0].get_text(),
            'anchor_count': len(document.anchors),
        }
    observations['worker_lock_absent'] = not (ROOT / '.local/coordination/ACTIVE_WORKER.json').exists()

    # Run worker suite without altering original evidence or accessing credentials.
    with patch.object(config, 'RESULT_DIR', OUT / 'selftest-results'), patch.object(config, 'LOCAL_DIR', OUT / 'selftest-local'), patch.dict(os.environ, {}, clear=True):
        result = selftest.run_self_test()
    observations['worker_suite_rerun'] = {k: result[k] for k in ['checks_total', 'checks_passed', 'checks_failed', 'checks_skipped']}

    fixture = selftest.load_anchor_fixture()
    payload = {'model': config.PROVIDER['model_id'], 'messages': [], 'max_tokens': 64,
               'prompt_metadata': {'estimated_input_tokens_chars_div_4': 1}}
    fake_budget = {'schema_version': 1, 'requests_used': 0, 'estimated_spend_usd': 0.0,
                   'attempts': [], 'pricing': {'verified': True, 'input_usd_per_1m': 0.3, 'output_usd_per_1m': 0.9}}
    calls = []
    def timeout(*args, **kwargs):
        calls.append('simulated-timeout-no-network')
        raise httpx.ReadTimeout('Simulated timeout after dispatch; no network used')

    attempt_dir = OUT / 'timeout-ledger'
    attempt_dir.mkdir(exist_ok=True)
    (attempt_dir / 'budget.json').write_text(json.dumps(fake_budget), encoding='utf-8')
    with patch.object(config, 'PROVIDER_DIR', attempt_dir), patch.dict(os.environ, {'NEBIUS_API_KEY': 'SYNTHETIC-NOT-A-CREDENTIAL'}, clear=True), patch.object(provider, 'build_draft_payload', return_value=payload), patch.object(provider, 'send_request', side_effect=timeout):
        for _ in range(4):
            try:
                provider.probe(fixture, {}, {}, [])
            except (httpx.ReadTimeout, provider.ProviderBlocked):
                pass
        budget = provider.load_budget()
    observations['timeout_budget'] = {'simulated_dispatches': len(calls), 'requests_recorded': budget['requests_used'], 'cap': 3,
                                     'defect_reproduced': len(calls) > 3 or budget['requests_used'] != min(len(calls), 3)}

    false_state = {'provider': {'live_requests_made': True, 'attempts': [{'live': True, 'http_status': 401, 'validation': {'status': 'rejected'}}]},
                   'coverage': {}, 'baseline_ok': False, 'source_sha': None, 'synthetic_ok': False, 'change_source_note': 'synthetic review state'}
    rows = report._gate_rows(false_state)
    observations['report_on_failed_request'] = {row[0]: row[1] for row in rows if row[0] in ['W01-G4','W01-G5']}
    observations['gate_accepts_truncated_wrong_model'] = provider.passes_live_gate({
        'live': True, 'http_status': 200, 'validation': {'status': 'accepted'},
        'model_returned': 'SYNTHETIC-WRONG-MODEL', 'finish_reason': 'length', 'empty_or_truncated': True})

    raw = read(config.FIXTURE_DIR / 'draft_valid.json')
    raw['source_document_id'] = 'COMPLETELY-DIFFERENT-DOCUMENT'
    observations['wrong_source_id_validation'] = validate_draft(raw, fixture.anchors, fixture.document_sha256).status

    matrix = read(config.RESULT_DIR / 'revision_matrix.json')
    payload = provider.build_draft_payload(document, {}, matrix['rows'], list(config.SELECTED_SECTIONS))
    candidate = next(a for a in document.anchors if a.section == '2.2.18' and a.block_role == 'body')
    raw = {'schema_version': 1, 'source_document_id': source.document_id, 'source_revision': source.revision,
           'claims': [{'field': 'trigger_condition', 'statement': 'Reset condition requires review.', 'anchor_ids': [candidate.anchor_id], 'status': 'supported'}],
           'unresolved_fields': []}
    validation = validate_draft(raw, document.anchors, document.document_sha256)
    observations['real_revision_grounding'] = {'any_anchor_contains_revision': any(source.revision.lower() in a.text.lower() for a in document.anchors),
        'candidate_result': validation.status, 'errors': validation.errors,
        'prompt_has_revision_identity': source.revision in payload['messages'][1]['content']}

    observations['defects_present'] = bool(observations['timeout_budget']['defect_reproduced'] or
        any(v == 'PASS' for v in observations['report_on_failed_request'].values()) or
        observations['gate_accepts_truncated_wrong_model'] or observations['wrong_source_id_validation'] == 'accepted')
    (OUT / 'observations.json').write_text(json.dumps(observations, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(observations, indent=2))
    return 1 if observations['defects_present'] else 0


if __name__ == '__main__':
    sys.exit(main())

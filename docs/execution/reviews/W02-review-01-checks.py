"""Independent offline W02 boundary checks; expected behavior comes from binding.

Only writes review artifacts under .local/reviews/W02-review-01. Does not import
worker test helpers, read credentials, use a provider, or edit worker files.
"""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import os
import subprocess
import sys
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'));sys.dont_write_bytecode=True
from erratascope_domain import parse_bundle,evaluate
from erratascope_domain.models import ProductSnapshot,FactSet
from erratascope_domain.canonical import snapshot_content_hash,fact_set_content_hash,dump_model,normalized_result_bytes
from erratascope_domain.selectors import QuantityValue,SELECTORS
from erratascope_domain.errors import DomainValidationError
from pydantic import ValidationError

OUT=ROOT/'.local/reviews/W02-review-01';OUT.mkdir(parents=True,exist_ok=True)
BASE=json.loads((ROOT/'backend/fixtures/w02/applicable.json').read_text(encoding='utf-8'))
results=[]
def check(name,expected,fn):
    try:
        observed=fn(); ok=observed==expected
        results.append(dict(name=name,expected=expected,observed=observed,pass_check=ok))
    except Exception as exc:
        results.append(dict(name=name,expected=expected,observed='UNEXPECTED_EXCEPTION',error=type(exc).__name__,pass_check=False))
def accepts(raw):
    try: parse_bundle(raw);return True
    except DomainValidationError:return False
def reseal(raw):
    raw['snapshot']['content_hash']=snapshot_content_hash(dump_model(ProductSnapshot.model_validate(raw['snapshot'])))
    raw['fact_set']['content_hash']=fact_set_content_hash(dump_model(FactSet.model_validate(raw['fact_set'])))
    return raw
def mutate(fn):
    r=copy.deepcopy(BASE);fn(r);return reseal(r)
def missing_key(identity=False):
    r=copy.deepcopy(BASE)
    obj=r['snapshot']['component_instances'][0]['identity'] if identity else r['fact_set']['fact_versions'][0]
    key='silicon_revision' if identity else 'value'
    obj[key]=None
    reseal(r)
    del obj[key]
    return r
def const(value):
    return {'op':'constant','value':value,'anchor_ids':[BASE['anchors'][0]['anchor_id']],'review_rationale':'Independent synthetic boundary case'}

with patch('socket.socket',side_effect=AssertionError('network forbidden in domain review')):
    check('baseline_fixture',True,lambda:accepts(BASE))
    for field in ['manufacturer','exact_part','family','package','silicon_revision']:
        def unknown(field=field):
            r=copy.deepcopy(BASE);r['snapshot']['component_instances'][0]['identity'][field]=None
            r['snapshot']['content_hash']=snapshot_content_hash(r['snapshot'])
            return accepts(r)
        check('explicit_unknown_identity_'+field,True,unknown)
    check('missing_silicon_revision_key_rejected',False,lambda:accepts(missing_key(identity=True)))
    check('missing_fact_value_key_rejected',False,lambda:accepts(missing_key()))
    check('foreign_component_project_rejected',False,lambda:accepts(mutate(lambda r:r['snapshot']['component_instances'][0].update(project_id=str(uuid.UUID(int=999))))))
    check('missing_snapshot_identity_evidence_ref_rejected',False,lambda:accepts(mutate(lambda r:r['snapshot']['component_instances'][0]['identity'].update(evidence_refs=['absent-anchor']))))
    def bad_nonidentity_ref(r):
        f=next(f for f in r['fact_set']['fact_versions'] if not f['selector'].startswith('component.'))
        f['evidence_refs']=['absent-anchor']
    check('missing_nonidentity_fact_evidence_ref_rejected',False,lambda:accepts(mutate(bad_nonidentity_ref)))
    def total_nodes(n):
        r=copy.deepcopy(BASE);rule=r['rules'][0]
        rule['target']={'op':'all','children':[const(True) for _ in range(n)]}
        rule['trigger']={'op':'all','children':[const(True) for _ in range(n)]}
        rule['exceptions']=[]
        return accepts(r)
    check('aggregate_512_rule_nodes_accepted',True,lambda:total_nodes(255))
    check('aggregate_602_rule_nodes_rejected',False,lambda:total_nodes(300))
    def many_exceptions():
        r=copy.deepcopy(BASE);r['rules'][0].update(target=const(True),trigger=const(True),exceptions=[const(False) for _ in range(511)])
        return accepts(r)
    check('aggregate_513_nodes_across_exceptions_rejected',False,many_exceptions)
    def invalid_instance():
        b=parse_bundle(BASE).model_copy(update={'schema_version':99})
        try:evaluate(b);return True
        except (DomainValidationError,ValidationError):return False
    check('evaluate_revalidates_model_copy_schema_version',False,invalid_instance)
    def invalid_leaf():
        b=parse_bundle(BASE);trigger=b.rules[0].trigger
        # An unvalidated copy with an empty conjunction is a normal Pydantic API,
        # not an object.__setattr__ attack; evaluation must still reject it.
        from erratascope_domain.rules import All
        invalid=All.model_construct(op='all',children=())
        rule=b.rules[0].model_copy(update={'trigger':invalid})
        try:evaluate(b.model_copy(update={'rules':(rule,)}));return True
        except (DomainValidationError,ValidationError):return False
    check('evaluate_rejects_constructed_empty_logical_group',False,invalid_leaf)
    def quantity_valid(value):
        try:QuantityValue(kind='quantity',value=value,unit='V');return True
        except ValidationError:return False
    check('quantity_trailing_newline_rejected',False,lambda:quantity_valid('1\n'))
    check('boolean_registry_disallows_in',False,lambda:'in' in SELECTORS['operating.external_reset_used'].operators)
    check('quantity_registry_disallows_in',False,lambda:'in' in SELECTORS['operating.supply_voltage_v'].operators)
    check('integer_registry_allows_ordering',True,lambda:'lt' in SELECTORS['firmware.revision_id_value'].operators)
    for fixture,expectation in [('applicable','applicable'),('unknown_revision','unknown'),('conflicting','unknown'),('out_of_scope','unknown')]:
        check('fixture_'+fixture,expectation,lambda fixture=fixture:evaluate(parse_bundle(json.loads((ROOT/f'backend/fixtures/w02/{fixture}.json').read_text()))).rules[0].applicability)
    # Explicit independent Kleene table, exercised through complete bundles.
    truth=['true','false','unknown']
    and_table=[['true','false','unknown'],['false','false','false'],['unknown','false','unknown']]
    or_table=[['true','true','true'],['true','false','unknown'],['true','unknown','unknown']]
    def expr(value):
        if value=='unknown':return {'op':'eq','selector':'operating.temperature_c','value':{'kind':'quantity','value':'25','unit':'degC'},'anchor_ids':[BASE['anchors'][0]['anchor_id']]}
        return const(value=='true')
    for op,table in [('all',and_table),('any',or_table)]:
        for i,j in itertools.product(range(3),repeat=2):
            def connected(op=op,i=i,j=j):
                r=copy.deepcopy(BASE);r['rules'][0].update(target={'op':op,'children':[expr(truth[i]),expr(truth[j])]},trigger=const(True),exceptions=[])
                return evaluate(parse_bundle(r)).rules[0].overall
            check(f'connected_{op}_{truth[i]}_{truth[j]}',table[i][j],connected)
    def false_target_missing_exception():
        r=copy.deepcopy(BASE);r['rules'][0].update(target=const(False),trigger=const(True),exceptions=[expr('unknown')])
        result=evaluate(parse_bundle(r))
        return result.rules[0].overall=='false' and 'operating.temperature_c' in result.missing_selectors and any(d.selector=='operating.temperature_c' for d in result.selector_dependencies)
    check('false_target_retains_unknown_exception_dependency',True,false_target_missing_exception)

# Separate processes test the CLI and output-preservation guarantee.
env={k:v for k,v in os.environ.items() if not any(t in k.upper() for t in ['TOKEN','SECRET','API_KEY'])}
env.update(PYTHONPATH=str(ROOT/'backend'),PYTHONDONTWRITEBYTECODE='1')
def replay(input_path,output_path):
    return subprocess.run([sys.executable,'-B','-m','erratascope_domain.replay','--input',str(input_path),'--output',str(output_path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
a=OUT/'replay-a.json';b=OUT/'replay-b.json'
ra=replay(ROOT/'backend/fixtures/w02/applicable.json',a);rb=replay(ROOT/'backend/fixtures/w02/applicable.json',b)
check('fresh_process_cli_success',True,lambda:ra.returncode==rb.returncode==0)
check('fresh_process_bytes_identical',True,lambda:a.read_bytes()==b.read_bytes())
bad=copy.deepcopy(BASE);bad['rules'][0]['exceptions']=None
bad_path=OUT/'invalid.json';bad_path.write_text(json.dumps(bad),encoding='utf-8');before=a.read_bytes();failed=replay(bad_path,a)
check('invalid_cli_exit_and_output_preservation',True,lambda:failed.returncode==2 and a.read_bytes()==before)
summary={'checks':results,'passed':sum(c['pass_check'] for c in results),'total':len(results),'provider_calls':0,'network_used':False}
(OUT/'observations.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
sys.exit(0 if all(c['pass_check'] for c in results) else 1)

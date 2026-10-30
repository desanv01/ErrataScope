"""Independent W03 checks. Run in the W03 test image against the main local API.

Uses only generated local dev tokens, unique synthetic projects, PostgreSQL,
Valkey and private artifact bytes. Never prints tokens or connection strings.
Does not reset any DB, edit worker source or overwrite worker evidence.
"""
import concurrent.futures
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid

import httpx
from sqlalchemy import delete, select, update, func
from erratascope_service import jobs, services
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, Job, JobAttempt, Membership, Outbox, StageResult
from erratascope_service.artifacts import ArtifactStore

settings=load_settings()
factory=get_session_factory(settings)
dev=json.loads(Path('/local/dev-auth/tokens.json').read_text())
actor=uuid.UUID(dev['users']['user-a']['sub'])
other=uuid.UUID(dev['users']['user-b']['sub'])
client=httpx.Client(base_url='http://api:8000',timeout=30,
    headers={'Authorization':'Bearer '+dev['users']['user-a']['token']})
rows=[]
def record(name, expected, actual):
    rows.append({'name':name,'expected':expected,'actual':actual,'pass':expected==actual})
def key(): return uuid.uuid4().hex
def post(path,body=None,idem=None,**kwargs):
    h=kwargs.pop('headers',{})
    h['Idempotency-Key']=idem or key()
    return client.post(path,json=body,headers=h,**kwargs) if body is not None else client.post(path,headers=h,**kwargs)
def project():
    response=post('/api/v1/projects',{'name':'codex-review-'+key()[:8]})
    assert response.status_code==201,response.status_code
    return response.json()['id']
def upload(p,data=b'Original synthetic Codex W03 review source\n',idem=None):
    response=post(f'/api/v1/projects/{p}/artifacts',idem=idem,
        content=data,headers={'Content-Type':'text/plain','X-Filename':'review.txt'})
    assert response.status_code==201,response.status_code
    return response.json()

record('ready_real_services',200,client.get('/health/ready').status_code)
p=project(); artifact=upload(p)
base=f'/api/v1/projects/{p}'
record('artifact_roundtrip',True,client.get(f"{base}/artifacts/{artifact['id']}/content").content==b'Original synthetic Codex W03 review source\n')
# API shape and owner/member boundaries use actual HTTP.
record('project_detail_route',200,client.get(base).status_code)
record('membership_put_route',200,client.put(f'{base}/members/{other}',
    json={'role':'viewer'},headers={'Idempotency-Key':key()}).status_code)
# Legacy actual route ensures a viewer exists even when the bound route is absent.
client.post(f'{base}/members',json={'actor_id':str(other),'role':'viewer'},
    headers={'Idempotency-Key':key()})
with httpx.Client(base_url='http://api:8000',timeout=30,
    headers={'Authorization':'Bearer '+dev['users']['user-b']['token']}) as viewer:
    record('viewer_members_list_denied',403,viewer.get(f'{base}/members').status_code)
record('membership_delete_route',204,client.delete(f'{base}/members/{other}',
    headers={'Idempotency-Key':key()}).status_code)

# Idempotent mutation replay must recheck current membership even for same actor/key.
rk=key(); candidate={'artifact_id':artifact['id'],'content_hash':artifact['sha256'],'annotation':'review-only synthetic candidate'}
r=post(f'{base}/review-items',candidate,rk);assert r.status_code==201
jk=key(); job_payload={'kind':'artifact_digest','artifact_id':artifact['id']}
j=post(f'{base}/jobs',job_payload,jk);assert j.status_code==202
with factory() as session:
    session.execute(delete(Membership).where(Membership.project_id==uuid.UUID(p),Membership.actor_id==actor))
    session.commit()
record('revoked_fresh_artifact_read_denied',404,client.get(f"{base}/artifacts/{artifact['id']}").status_code)
record('revoked_review_idempotency_replay_denied',404,post(f'{base}/review-items',candidate,rk).status_code)
record('revoked_job_idempotency_replay_denied',404,post(f'{base}/jobs',job_payload,jk).status_code)
record('revoked_fresh_job_create_denied',404,post(f'{base}/jobs',job_payload).status_code)

# Server-generated request identifier and error contract.
unauth=httpx.get('http://api:8000/api/v1/projects',headers={'X-Request-ID':'client-controlled'},timeout=10)
record('nested_error_envelope',True,isinstance(unauth.json().get('error'),dict))
rid=unauth.headers.get('X-Request-ID','')
try: uuid.UUID(rid); valid_uuid=True
except ValueError: valid_uuid=False
record('server_generated_request_uuid',True,valid_uuid and rid!='client-controlled')

# Real concurrent identical uploads: check both DB convergence and private bytes.
q=project(); idem=key(); barrier=threading.Barrier(6)
def concurrent_upload(_):
    barrier.wait(timeout=10)
    return upload(q,b'SYNTHETIC CONCURRENT UPLOAD\n'*4000,idem)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
    results=list(executor.map(concurrent_upload,range(6)))
record('duplicate_upload_one_resource',1,len({v['id'] for v in results}))
with factory() as session:
    linked=set(session.scalars(select(Artifact.storage_key).where(Artifact.project_id==uuid.UUID(q))).all())
folder=settings.artifact_root/uuid.UUID(q).hex
actual_files={str(v.relative_to(settings.artifact_root)) for v in folder.glob('*.bin')}
record('duplicate_upload_no_orphan_bytes',0,len(actual_files-linked))
jobs.reconcile_once(settings)
actual_files={str(v.relative_to(settings.artifact_root)) for v in folder.glob('*.bin')}
record('reconcile_cleans_unreferenced_upload_bytes',0,len(actual_files-linked))

# Actual API worker produces a durable receipt and preserves it on duplicate execution.
s=project(); a=upload(s)
job=post(f'/api/v1/projects/{s}/jobs',{'kind':'artifact_digest','artifact_id':a['id']}).json()
deadline=time.monotonic()+30
while time.monotonic()<deadline:
    state=client.get(f"/api/v1/projects/{s}/jobs/{job['id']}").json()
    if state.get('status') in ['succeeded','failed','cancelled']:break
    time.sleep(.2)
record('live_worker_succeeds','succeeded',state.get('status'))
events=client.get(f"/api/v1/projects/{s}/jobs/{job['id']}/events?limit=1").json()
count=len(events) if isinstance(events,list) else len(events.get('items',[]))
record('event_limit_one_honored',True,count<=1)
record('event_cursor_envelope',True,isinstance(events,dict) and 'next_cursor' in events)
if state.get('status')=='succeeded':
    content=client.get(f"/api/v1/projects/{s}/artifacts/{state['result_artifact_id']}/content").json()
    record('receipt_digest',a['sha256'],content['sha256'])
    jobs.execute(job['id'])
    with factory() as session:
        count=session.scalar(select(func.count()).select_from(StageResult).where(StageResult.job_id==uuid.UUID(job['id'])))
    record('duplicate_execute_one_stage',1,count)

# Token lease condition on a real parked job: an expired lease cannot be revived.
with factory() as session:
    parked=services.create_job(session,project_id=uuid.UUID(s),actor_id=actor,artifact_id=uuid.UUID(a['id']))
    parked_id=parked.id
    session.execute(update(Outbox).where(Outbox.job_id==parked_id).values(available_at=services.utcnow()+timedelta(hours=1)))
    session.commit()
with factory() as session:
    claim=jobs.claim_job(session,parked_id,settings); token=claim['token']
with factory() as session:
    session.execute(update(Job).where(Job.id==parked_id).values(lease_until=services.utcnow()-timedelta(seconds=5)))
    session.commit()
record('expired_lease_heartbeat_denied',False,jobs.heartbeat(settings,parked_id,token))
with factory() as session:
    services.cancel_job(session,uuid.UUID(s),parked_id,actor);session.commit()
with factory() as session:
    attempt=session.scalar(select(JobAttempt).where(JobAttempt.job_id==parked_id,JobAttempt.token==token))
    record('cancelled_attempt_closed',True,attempt.ended_at is not None and attempt.outcome=='cancelled')

report={'checks':rows,'passed':sum(r['pass'] for r in rows),'total':len(rows),
    'source':'actual local HTTP/PostgreSQL/Valkey and private synthetic artifacts',
    'provider_calls':0,'secret_values_recorded':False,
    'synthetic_project_ids':[p,q,s]}
Path('/reviewout/observations.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
client.close()

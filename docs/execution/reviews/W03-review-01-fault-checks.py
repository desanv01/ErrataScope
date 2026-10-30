"""Controlled failure injection against actual local PostgreSQL/artifact store.

No provider or mocked persistence. Simulates a DB rejection after byte staging
and a lost success acknowledgement after a real database commit. Leaves unique
synthetic records for inspection, writes only review output, never prints keys.
"""
import json
from pathlib import Path
from datetime import timedelta
import uuid
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from erratascope_service import services,jobs
from erratascope_service.api import create_app
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact,Job,Outbox,StageResult
from erratascope_service.artifacts import ArtifactStore,ArtifactError

s=load_settings(); f=get_session_factory(s)
dev=json.loads(Path('/local/dev-auth/tokens.json').read_text())
actor=uuid.UUID(dev['users']['user-a']['sub'])
auth={'Authorization':'Bearer '+dev['users']['user-a']['token']}
out=[]
def rec(name,expected,actual):out.append({'name':name,'expected':expected,'actual':actual,'pass':expected==actual})
def key():return uuid.uuid4().hex

with TestClient(create_app(s),raise_server_exceptions=False) as client:
    r=client.post('/api/v1/projects',headers={**auth,'Idempotency-Key':key()},json={'name':'codex-faults-'+key()[:8]})
    assert r.status_code==201
    p=uuid.UUID(r.json()['id']); folder=s.artifact_root/p.hex
    original_record=services.create_artifact_record
    def db_reject(session,**kwargs):
        # Actual PostgreSQL CHECK rejects this value after actual bytes were written.
        kwargs['media_type']='synthetic/invalid'
        return original_record(session,**kwargs)
    with patch.object(services,'create_artifact_record',side_effect=db_reject):
        r=client.post(f'/api/v1/projects/{p}/artifacts',
            headers={**auth,'Idempotency-Key':key(),'Content-Type':'text/plain'},
            content=b'Original synthetic rollback probe\n')
    rec('staged_upload_real_db_rejection',409,r.status_code)
    with f() as db:
        refs=set(db.scalars(select(Artifact.storage_key).where(Artifact.project_id==p)).all())
    staged={str(v.relative_to(s.artifact_root)) for v in folder.glob('*.bin')}
    rec('rollback_leaves_no_untracked_artifact',0,len(staged-refs))
    jobs.reconcile_once(s)
    staged={str(v.relative_to(s.artifact_root)) for v in folder.glob('*.bin')}
    rec('orphan_reconciliation_available',0,len(staged-refs))

    r=client.post(f'/api/v1/projects/{p}/artifacts',
        headers={**auth,'Idempotency-Key':key(),'Content-Type':'text/plain'},
        content=b'Original synthetic commit acknowledgement probe\n')
    assert r.status_code==201
    artifact_id=uuid.UUID(r.json()['id'])
    with f() as db:
        j=services.create_job(db,project_id=p,actor_id=actor,artifact_id=artifact_id)
        jid=j.id
        db.execute(update(Outbox).where(Outbox.job_id==jid).values(available_at=services.utcnow()+timedelta(hours=1)))
        db.commit()
    original_commit=Session.commit
    fired=[False]
    def commit_then_lose_ack(db):
        final=any(isinstance(o,Job) and o.id==jid and o.status=='succeeded' for o in db.identity_map.values())
        original_commit(db)
        if final and not fired[0]:
            fired[0]=True
            raise OSError('SYNTHETIC commit acknowledgement lost after real commit')
    with patch.object(Session,'commit',commit_then_lose_ack):
        jobs.execute(str(jid))
    rec('ack_loss_fault_injected',True,fired[0])
    with f() as db:
        j=db.get(Job,jid)
        stage=db.get(StageResult,(jid,'receipt'))
        result=db.get(Artifact,j.result_artifact_id) if j.result_artifact_id else None
        rec('success_transaction_durable','succeeded',j.status)
        rec('stage_transaction_durable',True,stage is not None)
        try:
            ArtifactStore(s.artifact_root).read_bytes(result.storage_key,result.sha256,result.byte_length)
            readable=True
        except ArtifactError:
            readable=False
        rec('committed_receipt_survives_ack_loss',True,readable)
    jobs.execute(str(jid))
    with f() as db:
        j=db.get(Job,jid);result=db.get(Artifact,j.result_artifact_id)
        rec('redelivery_restores_or_preserves_receipt',True,
            (s.artifact_root/result.storage_key).is_file())

report={'checks':out,'passed':sum(v['pass'] for v in out),'total':len(out),
    'fault_injection':'Actual PostgreSQL constraint failure; acknowledgement loss raised after actual Session.commit, no database mock',
    'synthetic_project_id':str(p),'synthetic_job_id':str(jid),'provider_calls':0}
Path('/reviewout/fault-observations.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

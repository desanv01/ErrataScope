"""Independent R3/R4 probes: real DBs, isolated temporary bytes, no credentials output.

Run only after worker/tests stop, with test service DB and /reviewout mounted.
Does not reset a database or touch the application artifact volume.
"""
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
from datetime import timedelta
from unittest.mock import patch
from sqlalchemy import select, update, create_engine, text
from sqlalchemy.orm import Session
from erratascope_service import jobs, services
from erratascope_service.artifacts import ArtifactStore, reconcile_orphans, ArtifactError
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, Job, Outbox, UploadStaging

rows=[]
def rec(name, expected, actual):
    rows.append(dict(name=name, expected=expected, actual=actual, passed=expected==actual))

temp=Path(tempfile.mkdtemp(prefix='codex-w03-review-02-'))
os.environ['W03_ARTIFACT_ROOT']=str(temp/'store')
s=load_settings(); factory=get_session_factory(s); store=ArtifactStore(s.artifact_root)
dev=json.loads(Path('/local/dev-auth/tokens.json').read_text())
actor=uuid.UUID(dev['users']['user-a']['sub'])
with factory() as db:
    p=services.create_project(db,actor_id=actor,name='SYNTHETIC codex storage lifecycle probe')
    pid=p.id;db.commit()

# Test DB and application DB cannot safely own the same storage root.
# This deliberately shares ONLY a new temporary store to prove the defect.
aid=uuid.uuid4(); key,sha,n=store.put_bytes(pid,aid,b'SYNTHETIC database-owned bytes',max_bytes=1000)
with factory() as db:
    services.create_artifact_record(db,project_id=pid,actor_id=actor,artifact_id=aid,
        storage_key=key,sha256=sha,byte_length=n,media_type='text/plain',original_name='synthetic.txt')
    db.commit()
other=dataclasses.replace(s,database_url=s.database_url.rsplit('/',1)[0]+'/erratascope')
# The service factory is process-global; use a distinct engine for the second DB.
other_engine=create_engine(other.database_url)
with Session(other_engine) as db:
    assert db.scalar(text('select current_database()'))=='erratascope'
    reconcile_orphans(db,store,grace_seconds=0);db.commit()
other_engine.dispose()
rec('other_database_gc_preserves_owned_bytes',True,(store.root/key).exists())

# Unknown paths with a .bin extension are not generated UUID artifact paths.
unknown=store.root/'notes'/'keep.bin';unknown.parent.mkdir();unknown.write_bytes(b'unknown file')
with factory() as db:
    reconcile_orphans(db,store,grace_seconds=0);db.commit()
rec('unknown_path_preserved',True,unknown.exists())

# Resolving before checking components hides an internal symlink.
actual=store.root/'internal-target';actual.mkdir()
linkpid=uuid.uuid4();link=store.staging_root/linkpid.hex;link.symlink_to(actual,target_is_directory=True)
rejected=False
try:
    up=store.begin_staging(linkpid,uuid.uuid4());up.write(b'x',10);up.abort()
except ArtifactError:
    rejected=True
rec('internal_symlink_rejected',True,rejected)
link.unlink()

# A lease-expired journal row ignores the grace period even for fresh bytes.
aid=uuid.uuid4();up=store.begin_staging(pid,aid);up.write(b'fresh staging',100);up.finish()
with factory() as db:
    db.add(UploadStaging(artifact_id=aid,project_id=pid,actor_id=actor,
        staging_key=up.key,state='active',lease_until=services.utcnow()-timedelta(seconds=1),
        created_at=services.utcnow(),updated_at=services.utcnow()));db.commit()
with factory() as db:
    reconcile_orphans(db,store,grace_seconds=3600);db.commit()
rec('fresh_expired_staging_honors_grace',True,up.path.exists())

# Model a paused receipt writer whose staging lease expires while its job
# lease is still current. Hook the real pre-commit fence, use real transactions.
src=uuid.uuid4();key,sha,n=store.put_bytes(pid,src,b'SYNTHETIC receipt input',max_bytes=1000)
with factory() as db:
    services.create_artifact_record(db,project_id=pid,actor_id=actor,artifact_id=src,
        storage_key=key,sha256=sha,byte_length=n,media_type='text/plain',original_name='source.txt')
    j=services.create_job(db,project_id=pid,actor_id=actor,artifact_id=src);jid=j.id
    db.execute(update(Outbox).where(Outbox.job_id==jid).values(available_at=services.utcnow()+timedelta(hours=1)))
    db.commit()
original=jobs._fence;injected=[]
def expire_then_collect(db,job_id,token):
    with factory() as fresh:
        staging=fresh.scalar(select(UploadStaging).where(UploadStaging.project_id==pid,UploadStaging.state=='active'))
        assert staging is not None
        staging.lease_until=services.utcnow()-timedelta(seconds=1);fresh.commit()
    with factory() as fresh:
        result=reconcile_orphans(fresh,store,grace_seconds=0);fresh.commit()
        injected.append(result)
    return original(db,job_id,token)
with patch.object(jobs,'_fence',side_effect=expire_then_collect):
    jobs.execute(str(jid))
with factory() as db:
    job=db.get(Job,jid);result=db.get(Artifact,job.result_artifact_id) if job.result_artifact_id else None
    readable=False
    if result:
        try:
            store.read_bytes(result.storage_key,result.sha256,result.byte_length);readable=True
        except ArtifactError:
            pass
    rec('receipt_gc_race_fault_executed',True,bool(injected))
    rec('succeeded_job_has_readable_receipt',True,job.status!='succeeded' or readable)
    receipt_observation=dict(job_status=job.status,receipt_row=result is not None,receipt_readable=readable)

report=dict(checks=rows,passed=sum(r['passed'] for r in rows),total=len(rows),
    receipt_observation=receipt_observation,provider_calls=0,
    storage_scope='new temporary store only; application artifact volume untouched by this checker',
    timing='controlled expired staging lease at actual pre-commit fence; real PostgreSQL and filesystem')
Path('/reviewout/storage-observations.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

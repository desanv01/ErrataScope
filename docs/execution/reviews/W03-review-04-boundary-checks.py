"""Independent repair-03 boundaries using actual PostgreSQL and temporary files.

No provider, no application-volume mutations, no database reset.
"""
import dataclasses, hashlib, json, os, tempfile, uuid
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select,update,text
from sqlalchemy.orm import Session
from erratascope_service import services,jobs
from erratascope_service.api import create_app
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import UploadStaging,Artifact,Job,Outbox
from erratascope_service.artifacts import ArtifactStore,StagingUpload,ArtifactError,reconcile_orphans
from erratascope_service.storage_identity import database_identity,StoreIdentityError

base=Path(tempfile.mkdtemp(prefix='codex-w03-review04-'));s=dataclasses.replace(load_settings(),artifact_root=base/'store')
os.environ['W03_ARTIFACT_ROOT']=str(s.artifact_root)
identity=database_identity(s.database_url);store=ArtifactStore(s.artifact_root,database_identity=identity)
f=get_session_factory(s);dev=json.loads(Path('/local/dev-auth/tokens.json').read_text())
actor=uuid.UUID(dev['users']['user-a']['sub']);auth={'Authorization':'Bearer '+dev['users']['user-a']['token']}
rows=[]
def rec(n,e,a):rows.append(dict(name=n,expected=e,actual=a,passed=e==a))
def key():return uuid.uuid4().hex

with TestClient(create_app(s),raise_server_exceptions=False) as c:
    res=c.post('/api/v1/projects',headers={**auth,'Idempotency-Key':key()},json={'name':'SYNTHETIC codex repair02 boundaries'})
    assert res.status_code==201,res.status_code
    pid=uuid.UUID(res.json()['id'])
    original_finish=StagingUpload.finish;fired=[]
    def finish_expire(up):
        result=original_finish(up)
        if up.project_hex==pid.hex and not fired:
            with f() as db:
                row=db.get(UploadStaging,uuid.UUID(up.artifact_hex));assert row is not None
                row.lease_until=services.utcnow()-timedelta(seconds=10);db.commit();fired.append(True)
        return result
    with patch.object(StagingUpload,'finish',finish_expire):
        res=c.post(f'/api/v1/projects/{pid}/artifacts',headers={**auth,'Idempotency-Key':key(),'Content-Type':'text/plain'},content=b'expired lease probe')
    rec('expired_upload_fault_executed',True,bool(fired))
    rec('expired_upload_without_gc_rejected',409,res.status_code)

# Prior unknown-path and static-symlink cases.
unknown=store.root/'notes'/'keep.bin';unknown.parent.mkdir();unknown.write_bytes(b'unknown')
with f() as db:reconcile_orphans(db,store,grace_seconds=0,database_identity=identity);db.commit()
rec('unknown_file_preserved',True,unknown.exists())
target=store.root/'internal';target.mkdir();lp=uuid.uuid4();link=store.staging_root/lp.hex;link.symlink_to(target,target_is_directory=True)
rejected=False
try:up=store.begin_staging(lp,uuid.uuid4());up.abort()
except ArtifactError:rejected=True
rec('static_internal_symlink_rejected',True,rejected);link.unlink()

# A parent can change after checking; O_NOFOLLOW on the leaf does not pin parents.
rp=uuid.uuid4();ra=uuid.uuid4();rk=store.final_key(rp,ra)
original_dir=store.root/rp.hex;original_dir.mkdir();(original_dir/f'{ra.hex}.bin').write_bytes(b'owned original')
outside=base/'outside';outside.mkdir();external=outside/f'{ra.hex}.bin';external.write_bytes(b'outside sentinel')
saved=base/'saved-original';swapped=[]
def swap_after_pin(point):
    if point=='before_delete_unlink' and not swapped:
        original_dir.rename(saved);original_dir.symlink_to(outside,target_is_directory=True);swapped.append(True)
store.fault_hook=swap_after_pin
store.delete(rk)
store.fault_hook=None
rec('parent_swap_fault_executed',True,bool(swapped))
rec('parent_swap_does_not_delete_external_file',True,external.exists())
original_dir.unlink();saved.rename(original_dir)

# Exact layouts must reject trailing LF; Python regex $ is not a full-string boundary.
bad=store.final_key(uuid.uuid4(),uuid.uuid4())+'\n';accepted=True
try:store._checked_path(bad)
except ArtifactError:accepted=False
rec('noncanonical_newline_key_rejected',False,accepted)

# Actual mismatched session, not a pretend string. Default collector call must fail closed.
aid=uuid.uuid4();sk,sha,n=store.put_bytes(pid,aid,b'SYNTHETIC ownership sentinel',max_bytes=1000)
with f() as db:
    services.create_artifact_record(db,project_id=pid,actor_id=actor,artifact_id=aid,storage_key=sk,sha256=sha,byte_length=n,media_type='text/plain',original_name='sentinel.txt');db.commit()
other=create_engine(s.database_url.rsplit('/',1)[0]+'/erratascope');denied=False
with Session(other) as db:
    assert db.scalar(text('select current_database()'))=='erratascope'
    try:reconcile_orphans(db,store,grace_seconds=0);db.commit()
    except StoreIdentityError:denied=True;db.rollback()
for hint in (identity,):
    with Session(other) as db:
        refused=False
        try:reconcile_orphans(db,store,grace_seconds=0,database_identity=hint);db.commit()
        except StoreIdentityError:refused=True;db.rollback()
        rec('forged_hint_cannot_override_actual_session',True,refused)
other.dispose()
rec('actual_mismatched_session_without_hint_denied',True,denied)
rec('mismatched_session_preserves_bytes',True,(store.root/sk).exists())

# Prior receipt GC race: now live job-owned staging should be protected.
src=uuid.uuid4();sk,sha,n=store.put_bytes(pid,src,b'SYNTHETIC receipt input',max_bytes=1000)
with f() as db:
    services.create_artifact_record(db,project_id=pid,actor_id=actor,artifact_id=src,storage_key=sk,sha256=sha,byte_length=n,media_type='text/plain',original_name='source.txt')
    job=services.create_job(db,project_id=pid,actor_id=actor,artifact_id=src);jid=job.id
    db.execute(update(Outbox).where(Outbox.job_id==jid).values(available_at=services.utcnow()+timedelta(hours=1)));db.commit()
original_fence=jobs._fence
def expire_collect(db,job_id,token):
    with f() as fresh:
        row=fresh.scalar(select(UploadStaging).where(UploadStaging.owner_job_id==job_id,UploadStaging.state=='active'));assert row is not None
        row.lease_until=services.utcnow()-timedelta(seconds=10);fresh.commit()
    with f() as fresh:reconcile_orphans(fresh,store,grace_seconds=0,database_identity=identity);fresh.commit()
    return original_fence(db,job_id,token)
with patch.object(jobs,'_fence',side_effect=expire_collect):jobs.execute(str(jid))
with f() as db:
    job=db.get(Job,jid);a=db.get(Artifact,job.result_artifact_id) if job.result_artifact_id else None
    readable=False
    if a:
        try:store.read_bytes(a.storage_key,a.sha256,a.byte_length);readable=True
        except ArtifactError:pass
    rec('prior_receipt_gc_race_preserves_result',True,job.status=='succeeded' and readable)
# The normal receipt verification path creates a pinned store each time.
# Count only descriptors whose target is this disposable store, after GC.
import gc
def root_handles():
    targets=[]
    for p in Path('/proc/self/fd').iterdir():
        try:
            if os.readlink(p)==str(store.root):targets.append(p.name)
        except OSError:pass
    return len(targets)
gc.collect();before=root_handles()
for _ in range(12):assert jobs.verify_receipt(s,jid)
gc.collect();after=root_handles()
rec('receipt_verification_releases_store_handles',0,after-before)
report=dict(checks=rows,passed=sum(x['passed'] for x in rows),total=len(rows),
    scope='real PostgreSQL with controlled timing and isolated temporary files; no application bytes touched',provider_calls=0)
Path('/reviewout/boundary-observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

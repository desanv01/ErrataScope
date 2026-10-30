"""Bounded resource probes on disposable storage; no DB or application-file edits."""
from pathlib import Path
import gc,json,os,tempfile,uuid
from erratascope_service.artifacts import ArtifactStore,ArtifactError
from erratascope_service.storage_identity import StoreIdentityError

base=Path(tempfile.mkdtemp(prefix='codex-w03-handles-'));rows=[]
def handles():
    found=[]
    for p in Path('/proc/self/fd').iterdir():
        try:
            if os.readlink(p).startswith(str(base)):found.append(os.readlink(p))
        except OSError:pass
    return len(found)
def rec(name,before):
    gc.collect();after=handles();rows.append(dict(name=name,expected_growth=0,actual_growth=after-before,passed=after==before))

store=ArtifactStore(base/'store',database_identity='local-owner')
gc.collect();before=handles()
for _ in range(8):
    try:ArtifactStore(base/'store',database_identity='wrong-owner')
    except StoreIdentityError:pass
rec('rejected_store_construction_closes_root',before)

pid=uuid.uuid4();outside=base/'outside';outside.mkdir();link=store.staging_root/pid.hex
link.symlink_to(outside,target_is_directory=True)
before=handles()
for _ in range(8):
    try:store.begin_staging(pid,uuid.uuid4())
    except ArtifactError:pass
rec('rejected_staging_parent_closes_intermediate_fd',before)
link.unlink()

pid=uuid.uuid4();aid=uuid.uuid4();up=store.begin_staging(pid,aid);up.write(b'x',10);up.finish()
before=handles()
for _ in range(8):
    try:store.begin_staging(pid,aid)
    except (ArtifactError,OSError):pass
rec('duplicate_staging_create_closes_pinned_parent',before)
up.abort();store.close()
report=dict(checks=rows,passed=sum(v['passed'] for v in rows),total=len(rows),scope='isolated temporary files; eight bounded calls per failure path; GC performed before measurement',provider_calls=0)
Path('/reviewout/handle-observations.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

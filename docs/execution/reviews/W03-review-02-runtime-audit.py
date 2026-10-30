"""Read-only runtime/source and main storage inventory; output contains no secrets."""
import hashlib
import json
from pathlib import Path
from sqlalchemy import select,text
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact
from erratascope_service.artifacts import ArtifactStore,ArtifactError

source=Path('/review-source');image=Path('/app');files=[]
for folder in ('erratascope_service','erratascope_domain','migrations','tests_w03'):
    for p in sorted((source/folder).rglob('*.py')):
        q=image/p.relative_to(source)
        files.append(dict(path=p.relative_to(source).as_posix(),
            same=q.is_file() and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(q.read_bytes()).digest()))
s=load_settings();store=ArtifactStore(s.artifact_root);f=get_session_factory(s)
bad=[];checked=0
with f() as db:
    version=db.execute(text('select version_num from erratascope.alembic_version')).scalars().all()
    for a in db.scalars(select(Artifact)):
        checked+=1
        try:store.read_bytes(a.storage_key,a.sha256,a.byte_length)
        except ArtifactError as e:bad.append(dict(id=str(a.id),project_id=str(a.project_id),code=e.code))
report=dict(image_files=len(files),image_mismatches=[r['path'] for r in files if not r['same']],
    migration=version,main_artifacts_checked=checked,main_artifact_failures=bad,
    attribution='Read-only point-in-time inventory after stopping the unsafe shared-store test run; no pre-review byte inventory exists, so time/cause of any pre-existing missing file cannot be established.')
Path('/reviewout/runtime-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='main_artifact_failures'},indent=2))
print('main_artifact_failure_count:',len(bad))

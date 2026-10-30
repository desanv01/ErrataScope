import hashlib, json, uuid
from pathlib import Path
from sqlalchemy import select, text
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact
from erratascope_service.artifacts import ArtifactStore, ArtifactError
from erratascope_service.ingestion.models import ModelDraft, SourceVersion, SourceAnchor, CoverageEntry, ProviderReservation

settings=load_settings(); factory=get_session_factory(settings)
checks={}; report={}; missing=[]
with ArtifactStore(settings.artifact_root) as store, factory() as db:
    report['migration']=db.execute(text('select version_num from erratascope.alembic_version')).scalars().all()
    def artifact(aid):
        a=db.get(Artifact,aid)
        return store.read_bytes(a.storage_key,a.sha256,a.byte_length)
    rows=list(db.scalars(select(Artifact)))
    for a in rows:
        try: artifact(a.id)
        except ArtifactError: missing.append(str(a.id))
    report['artifact_count']=len(rows); report['missing_ids']=sorted(missing)
    d=db.get(ModelDraft,uuid.UUID('075a2625-862f-4d9a-b932-83f94358cb3d'))
    src=db.get(SourceVersion,d.source_id)
    anchors=list(db.scalars(select(SourceAnchor).where(SourceAnchor.extraction_id==d.extraction_id)))
    coverage=list(db.scalars(select(CoverageEntry).where(CoverageEntry.extraction_id==d.extraction_id)))
    body=json.loads(artifact(d.response_artifact_id)); request=json.loads(artifact(d.request_artifact_id))
    checks['source_hash']=hashlib.sha256(artifact(src.artifact_id)).hexdigest()==src.sha256=='dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd'
    checks['stored_response_matches_draft']=json.loads(body['choices'][0]['message']['content'])==d.draft
    checks['no_thinking']=request['chat_template_kwargs']['enable_thinking'] is False
    checks['finish_stop']=body['choices'][0]['finish_reason']=='stop'
    checks['exact_model']=request['model']=='nvidia/Nemotron-3.5-Super-VL'
    keys={a.anchor_key for a in anchors}
    checks['all_citations_resolve']=all(c.get('citations') and set(c['citations'])<=keys for c in d.draft['claims'])
    checks['anchor_scope_hash']=all(a.document_sha256==src.sha256 and a.source_id==src.id and a.project_id==src.project_id and 0<=a.page_index<38 for a in anchors)
    checks['coverage_selected']=set(c.section for c in coverage if c.status=='supported')=={'2.2.18','2.2.5'}
    reservations=list(db.scalars(select(ProviderReservation)))
    report['reservations']=[{'id':str(r.id),'status':r.status,'response_hash':r.response_hash} for r in reservations]
    checks['ledger_response_binding']=any(r.response_hash==d.response_hash for r in reservations)
    report['response_artifact_equals_wire_hash']=hashlib.sha256(artifact(d.response_artifact_id)).hexdigest()==d.response_hash
    report['anchors']=len(anchors);report['coverage']=len(coverage);report['claims']=len(d.draft['claims'])
    report['source']={'document_id':src.document_id,'revision':src.revision}
    # Private inspection only. Never include raw source/provider bodies in public review output.
    Path('/reviewout/cited-context-private.json').write_text(json.dumps({'draft':d.draft,'anchors':[{'key':a.anchor_key,'page':a.page_index,'section':a.section,'text':a.anchor_text,'bbox':a.bbox} for a in anchors]},indent=2))
files=[]
for folder in ('erratascope_service','erratascope_domain','migrations','tests_w04'):
    for p in sorted((Path('/review-source')/folder).rglob('*.py')):
        q=Path('/app')/p.relative_to('/review-source')
        files.append((p.relative_to('/review-source').as_posix(),q.is_file() and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(q.read_bytes()).digest()))
report['image_source_files']=len(files)
report['image_source_mismatches']=[p for p,ok in files if not ok]
checks['image_matches_workspace']=len(files)>0 and all(ok for _,ok in files)
report['checks']=checks
Path('/reviewout/runtime-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('missing_ids','reservations')},indent=2));print('missing_count',len(missing))
assert all(checks.values()),checks

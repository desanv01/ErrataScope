"""Bounded local import of the recorded live demonstration snapshot.

This command runs only inside the local deployment. It never creates provider
reservations, never changes ledgers and refuses a source whose bytes do not match
the recorded snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from .. import services
from ..artifacts import ArtifactStore
from ..config import load_settings
from ..db import get_session_factory
from ..models import Artifact, Job
from ..storage_identity import database_identity
from ..ingestion.models import (
    CoverageEntry,
    Extraction,
    ExtractionOutput,
    ModelDraft,
    SourceAnchor,
    SourceVersion,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m erratascope_service.submission.demo_import")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    project_id = uuid.UUID(args.project_id)
    source_id = uuid.UUID(args.source_id)
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1 or snapshot.get("kind") != "recorded_live_demo":
        raise SystemExit("unsupported recorded snapshot")
    settings = load_settings()
    if settings.mode != "local":
        raise SystemExit("recorded demo import is local-only")
    session = get_session_factory(settings)()
    store = ArtifactStore(
        settings.artifact_root,
        database_identity=database_identity(settings.database_url),
    )
    try:
        source = session.get(SourceVersion, source_id)
        if source is None or source.project_id != project_id:
            raise SystemExit("source not found in project")
        artifact = session.get(Artifact, source.artifact_id)
        if artifact is None or artifact.sha256 != snapshot["source"]["sha256"]:
            raise SystemExit("source artifact hash differs from recorded snapshot")
        store.read_bytes(artifact.storage_key, artifact.sha256, artifact.byte_length)
        imported = session.query(ModelDraft).filter(
            ModelDraft.source_id == source_id,
            ModelDraft.response_hash == snapshot["draft"]["response_hash"],
            ModelDraft.status == "validated",
        ).first()
        if imported:
            print("recorded snapshot already imported for this source")
            return 0
        actor_id = source.created_by
        project = session.get(services.Project, project_id)
        if project is None:
            raise SystemExit("project not found")
        # Final manifest artifact is a real immutable bookkeeping artifact, not a provider envelope.
        manifest_bytes = json.dumps(
            {
                "schema_version": 1,
                "kind": "recorded_demo_import",
                "snapshot_sha256": hashlib.sha256(
                    Path(args.snapshot).read_bytes()
                ).hexdigest(),
                "recorded_label": snapshot["recorded_label"],
                "attribution": snapshot["attribution"],
            },
            sort_keys=True,
        ).encode("utf-8")
        manifest_id = uuid.uuid4()
        key, sha, length = store.put_bytes(project_id, manifest_id, manifest_bytes, max_bytes=1024 * 1024)
        manifest_artifact = services.create_artifact_record(
            session,
            project_id=project_id,
            actor_id=actor_id,
            artifact_id=manifest_id,
            storage_key=key,
            sha256=sha,
            byte_length=length,
            media_type="application/json",
            original_name="recorded-demo-import.json",
        )
        job = Job(
            id=uuid.uuid4(),
            project_id=project_id,
            actor_id=actor_id,
            kind="source_extract",
            artifact_id=source.artifact_id,
            status="succeeded",
            attempt_count=1,
            max_attempts=1,
            next_event_seq=0,
            result_artifact_id=manifest_artifact.id,
            result_sha256=manifest_artifact.sha256,
            created_at=services.utcnow(),
            updated_at=services.utcnow(),
        )
        session.add(job)
        session.flush()
        extraction_id = uuid.uuid4()
        extraction = Extraction(
            id=extraction_id,
            project_id=project_id,
            source_id=source_id,
            job_id=job.id,
            mode="live",
            case_kind="real_source",
            selected_entries=snapshot["selected_entries"],
            status="succeeded",
            diagnostics=[
                {
                    "severity": "info",
                    "code": "RECORDED_SNAPSHOT_IMPORT",
                    "message": "Imported recorded live evidence; this is not a new provider call.",
                }
            ],
            current_stage="complete",
            created_by=actor_id,
            created_at=services.utcnow(),
            updated_at=services.utcnow(),
        )
        session.add(extraction)
        session.flush()
        coverage_summary = snapshot["coverage_summary"]
        session.add(
            ExtractionOutput(
                extraction_id=extraction_id,
                project_id=project_id,
                source_id=source_id,
                output_hash=snapshot["draft"]["response_hash"],
                manifest={
                    "schema_version": 1,
                    "source_id": str(source_id),
                    "source_sha256": source.sha256,
                    "parsed": {
                        "schema_version": 1,
                        "source_key": "st-es0620",
                        "document_sha256": source.sha256,
                        "page_count": 38,
                        "parser": snapshot["anchors"][0]["parser"],
                        "identity": {
                            "document_id": source.document_id,
                            "revision": source.revision,
                            "publication_date": None,
                            "anchor_key": next(
                                anchor["anchor_key"]
                                for anchor in snapshot["anchors"]
                                if anchor.get("context_kind") == "source_identity"
                            ),
                        },
                        "inventory": [],
                        "anchors": snapshot["anchors"],
                        "coverage": snapshot["coverage"],
                        "coverage_summary": coverage_summary,
                        "diagnostics": [],
                    },
                    "recorded_snapshot_import": True,
                },
                parser=snapshot["anchors"][0]["parser"],
                selected_scope=snapshot["selected_entries"],
                coverage_summary=coverage_summary,
                created_at=services.utcnow(),
            )
        )
        session.flush()
        for anchor in snapshot["anchors"]:
            session.add(
                SourceAnchor(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    extraction_id=extraction_id,
                    anchor_key=anchor["anchor_key"],
                    source_id=source_id,
                    page_index=anchor["page_index"],
                    printed_page_label=anchor.get("printed_page_label"),
                    section=anchor.get("section"),
                    section_title=anchor.get("section_title"),
                    block_role=anchor["block_role"],
                    context_kind=anchor.get("context_kind"),
                    geometry_kind=anchor["geometry_kind"],
                    anchor_text=anchor["text"],
                    bbox=anchor["bbox"],
                    bbox_original=anchor["bbox_original"],
                    page_width_pt=anchor["page_width_pt"],
                    page_height_pt=anchor["page_height_pt"],
                    page_rotation=anchor["page_rotation"],
                    parser=anchor["parser"],
                    document_sha256=anchor["document_sha256"],
                    created_at=services.utcnow(),
                )
            )
        for entry in snapshot["coverage"]:
            session.add(
                CoverageEntry(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    extraction_id=extraction_id,
                    section=entry["section"],
                    title=entry.get("title"),
                    status=entry["status"],
                    page_indexes=entry["page_indexes"],
                    anchor_keys=entry["anchor_keys"],
                    reason=entry.get("reason"),
                    notes=entry.get("notes", {}),
                    created_at=services.utcnow(),
                )
            )
        draft = snapshot["draft"]
        session.add(
            ModelDraft(
                id=uuid.uuid4(),
                project_id=project_id,
                extraction_id=extraction_id,
                source_id=source_id,
                case_kind="real_source",
                provenance="cached",
                prompt_version=draft["prompt_version"],
                request_hash=draft["request_hash"],
                response_hash=draft["response_hash"],
                draft=draft["draft"],
                validation=draft["validation"],
                status="validated",
                provider_request_id=draft["provider_request_id"],
                usage=draft["usage"],
                created_at=services.utcnow(),
            )
        )
        session.commit()
        print(
            json.dumps(
                {
                    "imported": True,
                    "project_id": str(project_id),
                    "source_id": str(source_id),
                    "extraction_id": str(extraction_id),
                    "recorded_label": snapshot["recorded_label"],
                    "new_provider_calls": 0,
                }
            )
        )
        return 0
    finally:
        store.close()
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())

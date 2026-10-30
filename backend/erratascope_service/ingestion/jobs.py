"""Durable `source_extract` execution: parse, cite, draft and seal in one final fence."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from erratascope_domain.canonical import canonical_bytes

from .. import services
from ..config import Settings
from ..db import get_session_factory
from ..artifacts import ArtifactError, ArtifactStore
from ..models import Artifact, Job, StageResult
from ..storage_identity import database_identity
from . import prompt
from .draft import validate_draft
from .fixture import synthetic_anchors, synthetic_coverage
from .models import (
    CoverageEntry,
    Extraction,
    ExtractionOutput,
    ModelDraft,
    SourceAnchor,
    SourceVersion,
)
from .parser import ParseError, parse_pdf
from .provider import ProviderBlocked, ProviderResult, run_case
from .service import _hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _store(settings: Settings) -> ArtifactStore:
    return ArtifactStore(
        settings.artifact_root,
        database_identity=database_identity(settings.database_url),
    )


def _write_artifact(
    session,
    store: ArtifactStore,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: bytes,
    media_type: str,
    name: str,
) -> Artifact:
    artifact_id = uuid.uuid4()
    key, sha, length = store.put_bytes(project_id, artifact_id, data, max_bytes=settings_max())
    return services.create_artifact_record(
        session,
        project_id=project_id,
        actor_id=actor_id,
        artifact_id=artifact_id,
        storage_key=key,
        sha256=sha,
        byte_length=length,
        media_type=media_type,
        original_name=name,
    )


def settings_max() -> int:
    return 10 * 1024 * 1024


def _cancel_check(settings: Settings, job_id: uuid.UUID, token: uuid.UUID):
    factory = get_session_factory(settings)

    def check() -> bool:
        session = factory()
        try:
            job = session.get(Job, job_id)
            return (
                job is None
                or job.status != "running"
                or job.current_attempt_token != token
                or job.lease_until is None
                or job.lease_until <= _utcnow()
            )
        finally:
            session.close()

    return check


def _lock_job(session, job_id: uuid.UUID, token: uuid.UUID) -> Job | None:
    job = session.scalar(
        select(Job)
        .where(Job.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        job is None
        or job.status != "running"
        or job.current_attempt_token != token
        or job.lease_until is None
        or job.lease_until <= _utcnow()
    ):
        return None
    return job


def _mock_draft(parsed: dict, source: SourceVersion, case_kind: str) -> dict:
    anchors = parsed["anchors"]
    identity_anchor = next(
        (anchor for anchor in anchors if anchor.get("context_kind") == "source_identity"), None
    )
    body_anchor = next(
        (
            anchor
            for anchor in anchors
            if anchor.get("block_role") in {"body", "table_row"}
            and anchor.get("context_kind") is None
        ),
        None,
    )
    claims = []
    identity = parsed.get("identity") or {}
    if identity_anchor is not None and identity.get("document_id") and identity.get("revision"):
        claims.append(
            {
                "field": "source_identity",
                "value": f"{identity['document_id']} - {identity['revision']}",
                "citations": [identity_anchor["anchor_key"]],
                "status": "supported",
            }
        )
    if body_anchor is not None:
        claims.append(
            {
                "field": "consequence" if body_anchor.get("block_role") == "body" else "affected_revision",
                "value": body_anchor["text"][:1000],
                "citations": [body_anchor["anchor_key"]],
                "status": "supported",
            }
        )
    if not claims:
        raise RuntimeError("OFFLINE_DRAFT_NO_ANCHOR")
    unresolved = ["affected_device", "trigger_condition", "exception", "workaround_documented"]
    if not identity.get("document_id"):
        unresolved.append("source_document_id")
    if not identity.get("revision"):
        unresolved.append("source_revision")
    return {
        "schema_version": 1,
        "source_document_id": identity.get("document_id"),
        "source_revision": identity.get("revision"),
        "claims": claims,
        "unresolved_fields": unresolved,
        "limitations": "Offline labeled mock draft. Not a safety verdict. Requires human source review.",
    }


def _expected_identity(parsed: dict, source: SourceVersion, case_kind: str) -> tuple[str | None, str | None, bool]:
    if case_kind == "synthetic_missing_revision":
        return None, None, True
    identity = parsed.get("identity") or {}
    document_id = identity.get("document_id")
    revision = identity.get("revision")
    if document_id is None and source.document_id:
        document_id = source.document_id
    if revision is None and source.revision:
        revision = source.revision
    return document_id, revision, False


def execute_source_extract(settings: Settings, job_id: uuid.UUID, token: uuid.UUID) -> None:
    store = _store(settings)
    try:
        _execute(settings, job_id, token, store)
    except Exception as exc:  # noqa: BLE001 - persisted failure beats silent disappearance
        import traceback

        traceback.print_exc()
        code = getattr(exc, "code", None) or type(exc).__name__.upper()
        _fail(settings, job_id, token, code)
    finally:
        store.close()


def _execute(settings: Settings, job_id: uuid.UUID, token: uuid.UUID, store: ArtifactStore) -> None:
    factory = get_session_factory(settings)
    session = factory()
    try:
        extraction = session.scalar(
            select(Extraction).where(Extraction.job_id == job_id).with_for_update()
        )
        if extraction is None:
            raise RuntimeError("EXTRACTION_MISSING")
        job = session.get(Job, job_id)
        source = session.get(SourceVersion, extraction.source_id)
        if job is None or source is None:
            raise RuntimeError("EXTRACTION_CONTEXT_MISSING")
        artifact = session.get(Artifact, source.artifact_id)
        if artifact is None or artifact.project_id != job.project_id:
            raise ArtifactError("ARTIFACT_MISSING", "source artifact disappeared")
        if extraction.status in ("succeeded", "failed", "cancelled"):
            return
        extraction.status = "running"
        extraction.current_stage = "parse"
        extraction.updated_at = _utcnow()
        session.commit()
        project_id = job.project_id
        actor_id = job.actor_id
        extraction_id = extraction.id
        case_kind = extraction.case_kind or (
            "synthetic_missing_revision" if source.synthetic else "real_source"
        )
        source_sha = source.sha256
        selected_entries = list(extraction.selected_entries)
        declared = {
            "document_id": source.document_id,
            "revision": source.revision,
            "manufacturer": source.manufacturer,
            "published_at": source.published_at,
            "authority": source.authority,
            "synthetic": source.synthetic,
        }
        source_id = source.id
    finally:
        session.close()

    existing = factory()
    try:
        output = existing.get(ExtractionOutput, extraction_id)
        draft_row = existing.scalar(
            select(ModelDraft).where(
                ModelDraft.extraction_id == extraction_id,
                ModelDraft.status == "validated",
            )
        )
        if output is not None and draft_row is not None:
            parsed = output.manifest.get("parsed")
            if parsed is None:
                raise RuntimeError("EXTRACTION_OUTPUT_INVALID")
        else:
            parsed = None
    finally:
        existing.close()

    if parsed is None:
        session = factory()
        try:
            artifact = session.get(Artifact, source.artifact_id) if False else None
        finally:
            session.close()
        # Read source bytes directly from the immutable artifact row.
        session = factory()
        try:
            source_row = session.get(SourceVersion, source_id)
            artifact = session.get(Artifact, source_row.artifact_id)
            data = store.read_bytes(artifact.storage_key, artifact.sha256, artifact.byte_length)
        finally:
            session.close()
        if case_kind == "synthetic_missing_revision":
            anchors = synthetic_anchors()
            coverage = synthetic_coverage()
            parsed = {
                "schema_version": 1,
                "source_key": "w04-synthetic-missing-revision",
                "document_sha256": source_sha,
                "page_count": 1,
                "parser": {
                    "name": "w04-synthetic-fixture",
                    "version": "1",
                    "mode": "synthetic_not_located",
                    "notes": "Original labeled synthetic fixture.",
                },
                "identity": None,
                "inventory": [{"section": "S1", "title": "Synthetic incomplete entry", "page_index": 0}],
                "anchors": anchors,
                "coverage": coverage,
                "coverage_summary": {
                    "inventory_complete": False,
                    "inventory_note": "Synthetic fixture only; no manufacturer inventory is claimed.",
                    "detected_entries": 1,
                    "selected_entries": selected_entries,
                    "supported_selected": 1,
                    "status_counts": {"supported": 1},
                },
                "diagnostics": [],
            }
        else:
            parsed = parse_pdf(
                data,
                source_key="st-es0620",
                document_sha256=source_sha,
                selected_entries=selected_entries,
                timeout_seconds=settings.w04_parse_timeout_seconds,
                memory_mb=settings.w04_parse_memory_mb,
                cancel_check=_cancel_check(settings, job_id, token),
            )

    # Existing immutable extraction output is reused without overwriting it.
    session = factory()
    try:
        output = session.get(ExtractionOutput, extraction_id)
        if output is not None:
            parsed = output.manifest.get("parsed", parsed)
        draft_row = session.scalar(
            select(ModelDraft).where(
                ModelDraft.extraction_id == extraction_id,
                ModelDraft.status == "validated",
            )
        )
    finally:
        session.close()

    if draft_row is not None:
        _finalize(
            settings,
            store,
            job_id,
            token,
            extraction_id,
            project_id,
            actor_id,
            source_id,
            source_sha,
            parsed,
            draft_row=draft_row,
            provenance=draft_row.provenance,
        )
        return

    expected_document_id, expected_revision, enforce_missing = _expected_identity(
        parsed, session.get(SourceVersion, source_id) if False else _source_stub(declared), case_kind
    )
    prompt_user = prompt.build_user_prompt(
        case=case_kind,
        selected_entries=selected_entries,
        declared_identity=declared,
        anchors=parsed["anchors"],
        coverage=parsed["coverage"],
    )
    messages = prompt.build_messages(prompt_user)
    context_hash = _hash(
        {
            "case": case_kind,
            "selected_entries": selected_entries,
            "anchors": [
                {"key": anchor["anchor_key"], "text": anchor["text"], "page": anchor["page_index"]}
                for anchor in parsed["anchors"]
            ],
            "prompt": prompt.prompt_hashes(),
        }
    )
    provider_result: ProviderResult | None = None
    draft_data: dict | None = None
    provenance = "mock" if extraction_mode(settings, job_id) == "offline" else "live"
    if provenance == "live":
        provider_result = run_case(
            settings,
            project_id=project_id,
            job_id=job_id,
            extraction_id=extraction_id,
            source_id=source_id,
            source_sha256=source_sha,
            case_kind=case_kind,
            messages=messages,
            declared_identity=declared,
            context={"context_hash": context_hash},
        )[0]
        if provider_result.cached_draft is not None:
            draft_row = provider_result.cached_draft
            draft_data = draft_row.draft
            validation = draft_row.validation
            provenance = "cached"
        else:
            try:
                raw_draft = json.loads(provider_result.response_text or "")
            except json.JSONDecodeError as exc:
                _persist_rejected_draft(
                    settings,
                    store,
                    job_id,
                    token,
                    extraction_id,
                    project_id,
                    actor_id,
                    source_id,
                    provider_result,
                    parsed,
                    {},
                    {"status": "rejected", "errors": ["provider content is not JSON"]},
                    case_kind,
                )
                raise ProviderBlocked("DRAFT_JSON_INVALID", "provider content is not JSON") from exc
            validation = validate_draft(
                raw_draft,
                anchors=parsed["anchors"],
                selected_entries=selected_entries,
                expected_document_id=expected_document_id,
                expected_revision=expected_revision,
                enforce_missing_identity=enforce_missing,
            )
            draft_data = raw_draft
            if validation["status"] != "validated":
                _persist_rejected_draft(
                    settings,
                    store,
                    job_id,
                    token,
                    extraction_id,
                    project_id,
                    actor_id,
                    source_id,
                    provider_result,
                    parsed,
                    raw_draft,
                    validation,
                    case_kind,
                )
                raise ProviderBlocked("DRAFT_REJECTED", "provider draft failed source-bounded validation")
    else:
        draft_data = _mock_draft(parsed, _source_stub(declared), case_kind)
        validation = validate_draft(
            draft_data,
            anchors=parsed["anchors"],
            selected_entries=selected_entries,
            expected_document_id=expected_document_id,
            expected_revision=expected_revision,
            enforce_missing_identity=enforce_missing,
        )
        if validation["status"] != "validated":
            raise RuntimeError("OFFLINE_DRAFT_INVALID")

    _finalize(
        settings,
        store,
        job_id,
        token,
        extraction_id,
        project_id,
        actor_id,
        source_id,
        source_sha,
        parsed,
        draft_data=draft_data,
        validation=validation,
        provenance=provenance,
        provider_result=provider_result,
        context_hash=context_hash,
    )


def _source_stub(declared: dict) -> SourceVersion:
    return SourceVersion(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        document_id=declared.get("document_id"),
        revision=declared.get("revision"),
        manufacturer=declared.get("manufacturer"),
        source_url=None,
        published_at=declared.get("published_at"),
        predecessor_id=None,
        authority=declared.get("authority", "synthetic"),
        synthetic=bool(declared.get("synthetic")),
        sha256="0" * 64,
        byte_length=0,
        schema_version=1,
        content_hash="0" * 64,
        created_by=uuid.uuid4(),
        created_at=_utcnow(),
        retrieval_utc=_utcnow(),
    )


def extraction_mode(settings: Settings, job_id: uuid.UUID) -> str:
    session = get_session_factory(settings)()
    try:
        extraction = session.scalar(select(Extraction).where(Extraction.job_id == job_id))
        return extraction.mode if extraction else "offline"
    finally:
        session.close()


def _persist_rejected_draft(
    settings,
    store,
    job_id,
    token,
    extraction_id,
    project_id,
    actor_id,
    source_id,
    provider_result,
    parsed,
    raw_draft,
    validation,
    case_kind,
) -> None:
    """Persist a rejected live draft together with its parse/coverage context."""
    session = get_session_factory(settings)()
    try:
        if _lock_job(session, job_id, token) is None:
            session.rollback()
            return
        request_bytes = json.dumps(provider_result.request_payload, sort_keys=True).encode("utf-8")
        response_bytes = json.dumps(
            provider_result.wire_body if provider_result.wire_body is not None else {},
            sort_keys=True,
        ).encode("utf-8")
        request_artifact = _write_artifact(
            session,
            store,
            project_id=project_id,
            actor_id=actor_id,
            data=request_bytes,
            media_type="application/json",
            name="w04-provider-request.json",
        )
        response_artifact = _write_artifact(
            session,
            store,
            project_id=project_id,
            actor_id=actor_id,
            data=response_bytes,
            media_type="application/json",
            name="w04-provider-response.json",
        )
        output = session.get(ExtractionOutput, extraction_id)
        if output is None:
            rejected_hash = _hash({"parsed": parsed, "rejected_validation": validation})
            session.add(
                ExtractionOutput(
                    extraction_id=extraction_id,
                    project_id=project_id,
                    source_id=source_id,
                    output_hash=rejected_hash,
                    manifest={
                        "schema_version": 1,
                        "source_id": str(source_id),
                        "source_sha256": parsed["document_sha256"],
                        "parsed": parsed,
                        "draft_rejected": True,
                    },
                    parser=parsed["parser"],
                    selected_scope=parsed["coverage_summary"]["selected_entries"],
                    coverage_summary=parsed["coverage_summary"],
                    created_at=_utcnow(),
                )
            )
            session.flush()
            for anchor in parsed["anchors"]:
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
                        created_at=_utcnow(),
                    )
                )
            for entry in parsed["coverage"]:
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
                        created_at=_utcnow(),
                    )
                )
        session.add(
            ModelDraft(
                id=uuid.uuid4(),
                project_id=project_id,
                extraction_id=extraction_id,
                source_id=source_id,
                case_kind=case_kind,
                provenance="live",
                prompt_version=settings.w04_prompt_version,
                request_hash=hashlib.sha256(request_bytes).hexdigest(),
                response_hash=provider_result.response_hash
                or hashlib.sha256(response_bytes).hexdigest(),
                draft=raw_draft,
                validation=validation,
                status="rejected",
                provider_request_id=provider_result.provider_request_id,
                usage=provider_result.usage,
                request_artifact_id=request_artifact.id,
                response_artifact_id=response_artifact.id,
                created_at=_utcnow(),
            )
        )
        extraction = session.get(Extraction, extraction_id)
        if extraction is not None:
            extraction.diagnostics = [
                *extraction.diagnostics,
                {
                    "severity": "error",
                    "code": "DRAFT_REJECTED",
                    "message": "provider draft failed source-bounded validation",
                },
            ]
            extraction.updated_at = _utcnow()
        session.commit()
    except Exception:  # noqa: BLE001 - job failure still persisted by caller
        session.rollback()
        import traceback

        traceback.print_exc()
    finally:
        session.close()


def _finalize(
    settings: Settings,
    store: ArtifactStore,
    job_id: uuid.UUID,
    token: uuid.UUID,
    extraction_id: uuid.UUID,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    source_id: uuid.UUID,
    source_sha: str,
    parsed: dict,
    *,
    draft_row: ModelDraft | None = None,
    draft_data: dict | None = None,
    validation: dict | None = None,
    provenance: str = "live",
    provider_result: ProviderResult | None = None,
    context_hash: str = "",
) -> None:
    session = get_session_factory(settings)()
    try:
        job = _lock_job(session, job_id, token)
        if job is None:
            session.rollback()
            return
        output = session.get(ExtractionOutput, extraction_id)
        if output is not None:
            stage = session.get(StageResult, (job_id, "final"))
            if stage is not None:
                job.status = "succeeded"
                job.result_artifact_id = stage.result_artifact_id
                job.result_sha256 = stage.result_sha256
                job.current_attempt_token = None
                job.lease_until = None
                job.updated_at = _utcnow()
                append_job_event(session, job, "succeeded", {"result_artifact_id": str(stage.result_artifact_id)})
                finish_attempt(session, job_id, token, outcome="succeeded")
                extraction = session.get(Extraction, extraction_id)
                if extraction is not None:
                    extraction.status = "succeeded"
                    extraction.current_stage = "complete"
                    extraction.updated_at = _utcnow()
                session.commit()
            return
        parse_bytes = json.dumps({"parsed": parsed}, sort_keys=True).encode("utf-8")
        parse_artifact = _write_artifact(
            session,
            store,
            project_id=project_id,
            actor_id=actor_id,
            data=parse_bytes,
            media_type="application/json",
            name="w04-parse.json",
        )
        draft_artifact_data = {
            "draft": draft_data,
            "validation": validation,
            "provenance": provenance,
            "request_hash": hashlib.sha256(
                json.dumps(provider_result.request_payload, sort_keys=True).encode("utf-8")
            ).hexdigest() if provider_result else None,
            "response_hash": provider_result.response_hash if provider_result else None,
        }
        draft_bytes = json.dumps(draft_artifact_data, sort_keys=True).encode("utf-8")
        draft_artifact = _write_artifact(
            session,
            store,
            project_id=project_id,
            actor_id=actor_id,
            data=draft_bytes,
            media_type="application/json",
            name="w04-draft-evidence.json",
        )
        request_artifact_id = None
        response_artifact_id = None
        if provider_result is not None and provider_result.status != "cached":
            request_bytes = json.dumps(provider_result.request_payload, sort_keys=True).encode("utf-8")
            response_bytes = json.dumps(provider_result.wire_body or {}, sort_keys=True).encode("utf-8")
            request_artifact_id = _write_artifact(
                session,
                store,
                project_id=project_id,
                actor_id=actor_id,
                data=request_bytes,
                media_type="application/json",
                name="w04-provider-request.json",
            ).id
            response_artifact_id = _write_artifact(
                session,
                store,
                project_id=project_id,
                actor_id=actor_id,
                data=response_bytes,
                media_type="application/json",
                name="w04-provider-response.json",
            ).id
        new_draft = draft_row is None
        if draft_row is None:
            draft_row = ModelDraft(
                id=uuid.uuid4(),
                project_id=project_id,
                extraction_id=extraction_id,
                source_id=source_id,
                case_kind=_case_kind(settings, job_id),
                provenance=provenance,
                prompt_version=settings.w04_prompt_version,
                request_hash=hashlib.sha256(
                    json.dumps(provider_result.request_payload, sort_keys=True).encode("utf-8")
                ).hexdigest() if provider_result else context_hash,
                response_hash=(provider_result.response_hash if provider_result and provider_result.response_hash else hashlib.sha256(draft_bytes).hexdigest()),
                draft=draft_data or {},
                validation=validation or {},
                status="validated",
                provider_request_id=provider_result.provider_request_id if provider_result else None,
                usage=provider_result.usage if provider_result else None,
                request_artifact_id=request_artifact_id,
                response_artifact_id=response_artifact_id,
                created_at=_utcnow(),
            )
        output_hash = _hash({"parsed": parsed, "draft": draft_row.draft, "validation": draft_row.validation})
        session.add(
            ExtractionOutput(
                extraction_id=extraction_id,
                project_id=project_id,
                source_id=source_id,
                output_hash=output_hash,
                manifest={
                    "schema_version": 1,
                    "source_id": str(source_id),
                    "source_sha256": source_sha,
                    "parsed": parsed,
                },
                parser=parsed["parser"],
                selected_scope=parsed["coverage_summary"]["selected_entries"],
                coverage_summary=parsed["coverage_summary"],
                created_at=_utcnow(),
            )
        )
        session.flush()
        if new_draft:
            session.add(draft_row)
        anchor_rows = []
        for anchor in parsed["anchors"]:
            row = SourceAnchor(
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
                created_at=_utcnow(),
            )
            session.add(row)
            anchor_rows.append(row)
        for entry in parsed["coverage"]:
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
                    created_at=_utcnow(),
                )
            )
        session.add(
            StageResult(
                project_id=project_id,
                job_id=job_id,
                stage_key="parse",
                input_hash=source_sha,
                result_artifact_id=parse_artifact.id,
                result_sha256=parse_artifact.sha256,
                created_at=_utcnow(),
            )
        )
        session.add(
            StageResult(
                project_id=project_id,
                job_id=job_id,
                stage_key="draft",
                input_hash=output_hash,
                result_artifact_id=draft_artifact.id,
                result_sha256=draft_artifact.sha256,
                created_at=_utcnow(),
            )
        )
        final_manifest = {
            "schema_version": 1,
            "source_id": str(source_id),
            "source_sha256": source_sha,
            "extraction_id": str(extraction_id),
            "output_hash": output_hash,
            "anchor_count": len(anchor_rows),
            "coverage_summary": parsed["coverage_summary"],
            "draft_id": str(draft_row.id),
            "draft_status": draft_row.status,
            "draft_provenance": draft_row.provenance,
            "provider_request_id": draft_row.provider_request_id,
            "provider_usage": draft_row.usage,
            "parse_artifact_id": str(parse_artifact.id),
            "draft_artifact_id": str(draft_artifact.id),
        }
        final_bytes = json.dumps(final_manifest, sort_keys=True).encode("utf-8")
        final_artifact = _write_artifact(
            session,
            store,
            project_id=project_id,
            actor_id=actor_id,
            data=final_bytes,
            media_type="application/json",
            name="w04-extraction-manifest.json",
        )
        session.add(
            StageResult(
                project_id=project_id,
                job_id=job_id,
                stage_key="final",
                input_hash=output_hash,
                result_artifact_id=final_artifact.id,
                result_sha256=final_artifact.sha256,
                created_at=_utcnow(),
            )
        )
        job.status = "succeeded"
        job.result_artifact_id = final_artifact.id
        job.result_sha256 = final_artifact.sha256
        job.current_attempt_token = None
        job.lease_until = None
        job.updated_at = _utcnow()
        append_job_event(
            session,
            job,
            "succeeded",
            {"result_artifact_id": str(final_artifact.id), "output_hash": output_hash},
        )
        finish_attempt(session, job_id, token, outcome="succeeded")
        extraction = session.get(Extraction, extraction_id)
        if extraction is not None:
            extraction.status = "succeeded"
            extraction.current_stage = "complete"
            extraction.updated_at = _utcnow()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _case_kind(settings: Settings, job_id: uuid.UUID) -> str:
    session = get_session_factory(settings)()
    try:
        extraction = session.scalar(select(Extraction).where(Extraction.job_id == job_id))
        if extraction is not None and extraction.case_kind:
            return extraction.case_kind
        return "real_source"
    finally:
        session.close()


def append_job_event(session, job: Job, event_type: str, payload: dict[str, Any]) -> None:
    from .. import jobs as jobs_module

    jobs_module.append_event(session, job, event_type, payload)


def finish_attempt(session, job_id, token, *, outcome: str, error_code=None) -> None:
    from .. import jobs as jobs_module

    jobs_module._finish_attempt(session, job_id, token, outcome=outcome, error_code=error_code)


def _fail(settings: Settings, job_id: uuid.UUID, token: uuid.UUID, code: str) -> None:
    session = get_session_factory(settings)()
    try:
        job = session.scalar(
            select(Job).where(Job.id == job_id).with_for_update().execution_options(populate_existing=True)
        )
        if job is None:
            return
        extraction = session.scalar(
            select(Extraction).where(Extraction.job_id == job_id).with_for_update()
        )
        if extraction is not None and extraction.status not in ("succeeded", "cancelled"):
            extraction.status = "failed"
            extraction.error_code = code[:200]
            extraction.diagnostics = [
                *extraction.diagnostics,
                {"severity": "error", "code": code[:80], "message": "extraction failed; see job events"},
            ]
            extraction.updated_at = _utcnow()
        if job.status == "running" and job.current_attempt_token == token:
            job.status = "failed"
            job.error_code = code[:200]
            job.current_attempt_token = None
            job.lease_until = None
            job.updated_at = _utcnow()
            append_job_event(session, job, "failed", {"error_code": code[:200]})
            finish_attempt(session, job_id, token, outcome="failed", error_code=code[:200])
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
    finally:
        session.close()

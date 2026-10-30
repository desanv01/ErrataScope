"""Source, extraction, proposal and append-only review operations."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from erratascope_domain.canonical import canonical_bytes
from erratascope_domain.errors import DomainValidationError
from erratascope_domain.models import RuleVersion
from erratascope_domain.rules import RuleExpr, collect_selectors, iter_leaves, preflight_ast, validate_ast

from .. import services
from ..errors import ApiError
from ..models import Artifact, Job
from .models import (
    AcceptedRule,
    ConversionProposal,
    CoverageEntry,
    Extraction,
    ExtractionOutput,
    ModelDraft,
    ProposalReview,
    SourceAnchor,
    SourceVersion,
)
from .schemas import ProposalCreate, ReviewCreate, SourceCreate

_TA = TypeAdapter(RuleExpr)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def source_body(row: SourceVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "artifact_id": row.artifact_id,
        "document_id": row.document_id,
        "revision": row.revision,
        "manufacturer": row.manufacturer,
        "source_url": row.source_url,
        "published_at": row.published_at,
        "predecessor_id": row.predecessor_id,
        "authority": row.authority,
        "synthetic": row.synthetic,
        "sha256": row.sha256,
        "byte_length": row.byte_length,
        "schema_version": row.schema_version,
        "content_hash": row.content_hash,
        "created_by": row.created_by,
        "created_at": row.created_at,
        "retrieval_utc": row.retrieval_utc,
    }


def create_source(
    session: Session, project_id: uuid.UUID, actor_id: uuid.UUID, payload: SourceCreate
) -> SourceVersion:
    services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
    artifact = services.get_artifact(session, project_id, payload.artifact_id)
    if payload.synthetic != (payload.authority == "synthetic"):
        raise ApiError(422, "SOURCE_AUTHORITY_INVALID", "synthetic flag must match synthetic authority")
    if payload.source_url is not None and not payload.source_url.startswith("https://"):
        raise ApiError(422, "SOURCE_URL_INVALID", "source_url must use HTTPS")
    predecessor = None
    if payload.predecessor_id is not None:
        predecessor = session.scalar(
            select(SourceVersion).where(
                SourceVersion.project_id == project_id, SourceVersion.id == payload.predecessor_id
            )
        )
        if predecessor is None:
            raise ApiError(404, "SOURCE_NOT_FOUND", "predecessor source not found")
    fields = {
        "artifact_id": str(payload.artifact_id),
        "document_id": _clean(payload.document_id),
        "revision": _clean(payload.revision),
        "manufacturer": _clean(payload.manufacturer),
        "source_url": _clean(payload.source_url),
        "published_at": _clean(payload.published_at),
        "predecessor_id": str(payload.predecessor_id) if payload.predecessor_id else None,
        "authority": payload.authority,
        "synthetic": payload.synthetic,
        "sha256": artifact.sha256,
        "byte_length": artifact.byte_length,
        "schema_version": 1,
    }
    row = SourceVersion(
        id=uuid.uuid4(),
        project_id=project_id,
        artifact_id=artifact.id,
        document_id=fields["document_id"],
        revision=fields["revision"],
        manufacturer=fields["manufacturer"],
        source_url=fields["source_url"],
        published_at=fields["published_at"],
        predecessor_id=payload.predecessor_id,
        authority=payload.authority,
        synthetic=payload.synthetic,
        sha256=artifact.sha256,
        byte_length=artifact.byte_length,
        schema_version=1,
        content_hash=_hash(fields),
        created_by=actor_id,
        created_at=_utcnow(),
        retrieval_utc=_utcnow(),
    )
    session.add(row)
    session.commit()
    return row


def get_source(session: Session, project_id: uuid.UUID, source_id: uuid.UUID) -> SourceVersion:
    row = session.scalar(
        select(SourceVersion).where(
            SourceVersion.project_id == project_id, SourceVersion.id == source_id
        )
    )
    if row is None:
        raise ApiError(404, "SOURCE_NOT_FOUND", "source not found")
    return row


def create_extraction(
    session: Session,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    selected_entries: list[str],
    mode: str,
    case_kind: str | None,
    live_enabled: bool,
) -> tuple[Extraction, Job]:
    services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
    source = get_source(session, project_id, source_id)
    if mode == "live" and not live_enabled:
        raise ApiError(409, "LIVE_DISABLED", "W04 live mode is not enabled in this runtime")
    if mode == "live" and case_kind is None:
        raise ApiError(422, "CASE_REQUIRED", "live extraction requires a case")
    if case_kind == "synthetic_missing_revision" and not source.synthetic:
        raise ApiError(422, "CASE_SOURCE_MISMATCH", "synthetic case requires a synthetic source")
    if case_kind == "real_source" and source.synthetic:
        raise ApiError(422, "CASE_SOURCE_MISMATCH", "real_source case requires a non-synthetic source")
    job = services.create_job(
        session,
        project_id=project_id,
        actor_id=actor_id,
        artifact_id=source.artifact_id,
        kind="source_extract",
        max_attempts=1 if mode == "live" else 2,
    )
    extraction = Extraction(
        id=uuid.uuid4(),
        project_id=project_id,
        source_id=source.id,
        job_id=job.id,
        mode=mode,
        case_kind=case_kind,
        selected_entries=selected_entries,
        status="queued",
        diagnostics=[],
        created_by=actor_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(extraction)
    session.commit()
    return extraction, job


def extraction_body(session: Session, row: Extraction, *, include_output: bool = True) -> dict[str, Any]:
    body = {
        "id": row.id,
        "project_id": row.project_id,
        "source_id": row.source_id,
        "job_id": row.job_id,
        "mode": row.mode,
        "case_kind": row.case_kind,
        "selected_entries": row.selected_entries,
        "status": row.status,
        "diagnostics": row.diagnostics,
        "current_stage": row.current_stage,
        "error_code": row.error_code,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if include_output:
        output = session.get(ExtractionOutput, row.id)
        if output is not None:
            body["output_hash"] = output.output_hash
            body["coverage_summary"] = output.coverage_summary
        body["draft_ids"] = list(
            session.scalars(select(ModelDraft.id).where(ModelDraft.extraction_id == row.id))
        )
    return body


def get_extraction(session: Session, project_id: uuid.UUID, extraction_id: uuid.UUID) -> Extraction:
    row = session.scalar(
        select(Extraction).where(
            Extraction.project_id == project_id, Extraction.id == extraction_id
        )
    )
    if row is None:
        raise ApiError(404, "EXTRACTION_NOT_FOUND", "extraction not found")
    return row


def list_anchors(session: Session, extraction: Extraction) -> list[SourceAnchor]:
    return list(
        session.scalars(
            select(SourceAnchor)
            .where(SourceAnchor.extraction_id == extraction.id)
            .order_by(SourceAnchor.page_index, SourceAnchor.anchor_key)
        )
    )


def anchor_body(row: SourceAnchor) -> dict[str, Any]:
    return {
        "id": row.id,
        "anchor_key": row.anchor_key,
        "page_index": row.page_index,
        "printed_page_label": row.printed_page_label,
        "section": row.section,
        "section_title": row.section_title,
        "block_role": row.block_role,
        "context_kind": row.context_kind,
        "geometry_kind": row.geometry_kind,
        "text": row.anchor_text,
        "bbox": row.bbox,
        "bbox_original": row.bbox_original,
        "page_width_pt": row.page_width_pt,
        "page_height_pt": row.page_height_pt,
        "page_rotation": row.page_rotation,
        "parser": row.parser,
        "document_sha256": row.document_sha256,
    }


def list_coverage(session: Session, extraction: Extraction) -> list[CoverageEntry]:
    return list(
        session.scalars(
            select(CoverageEntry)
            .where(CoverageEntry.extraction_id == extraction.id)
            .order_by(CoverageEntry.section)
        )
    )


def coverage_body(row: CoverageEntry) -> dict[str, Any]:
    return {
        "section": row.section,
        "title": row.title,
        "status": row.status,
        "page_indexes": row.page_indexes,
        "anchor_keys": row.anchor_keys,
        "reason": row.reason,
        "notes": row.notes,
    }


def get_draft(session: Session, project_id: uuid.UUID, draft_id: uuid.UUID) -> ModelDraft:
    row = session.scalar(
        select(ModelDraft).where(
            ModelDraft.project_id == project_id, ModelDraft.id == draft_id
        )
    )
    if row is None:
        raise ApiError(404, "DRAFT_NOT_FOUND", "draft not found")
    return row


def draft_body(row: ModelDraft) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "extraction_id": row.extraction_id,
        "source_id": row.source_id,
        "case_kind": row.case_kind,
        "provenance": row.provenance,
        "prompt_version": row.prompt_version,
        "request_hash": row.request_hash,
        "response_hash": row.response_hash,
        "draft": row.draft,
        "validation": row.validation,
        "status": row.status,
        "provider_request_id": row.provider_request_id,
        "usage": row.usage,
        "created_at": row.created_at,
    }


def _anchors(session: Session, extraction_id: uuid.UUID) -> dict[str, SourceAnchor]:
    return {
        row.anchor_key: row
        for row in session.scalars(
            select(SourceAnchor).where(SourceAnchor.extraction_id == extraction_id)
        )
    }


def _validate_candidate(
    raw_ast: Any,
    path: str,
    *,
    document_version_id: uuid.UUID,
    anchors: dict[str, SourceAnchor],
) -> tuple[Any | None, list[dict[str, Any]]]:
    diagnostics: list[dict[str, Any]] = []
    try:
        preflight_ast(raw_ast, path)
        parsed = _TA.validate_python(raw_ast)
        anchor_objs = {
            key: SimpleNamespace(id=key, document_version_id=document_version_id)
            for key in anchors
        }
        for diagnostic in validate_ast(
            parsed,
            document_version_id=document_version_id,
            anchors_by_id=anchor_objs,
            path=path,
        ):
            diagnostics.append({"code": diagnostic.code, "path": diagnostic.path, "message": diagnostic.message})
        return parsed, diagnostics
    except (ValidationError, DomainValidationError, ValueError) as exc:
        diagnostics.append({"code": "INVALID_AST", "path": path, "message": str(exc)[:500]})
        return None, diagnostics


def create_proposal(
    session: Session,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    draft_id: uuid.UUID,
    payload: ProposalCreate,
) -> ConversionProposal:
    services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
    draft = get_draft(session, project_id, draft_id)
    extraction = get_extraction(session, project_id, draft.extraction_id)
    anchors = _anchors(session, extraction.id)
    blockers: list[str] = []
    if draft.status != "validated":
        blockers.append("draft_not_validated")
    if payload.entry_id not in extraction.selected_entries:
        blockers.append("entry_not_selected")
    evidence_keys = {key for item in payload.evidence for key in item.anchor_keys}
    unknown = sorted(key for key in evidence_keys if key not in anchors)
    if unknown:
        blockers.append(f"foreign_anchors:{','.join(unknown[:5])}")
    target, target_diag = _validate_candidate(
        payload.target, "target", document_version_id=draft.source_id, anchors=anchors
    )
    trigger, trigger_diag = _validate_candidate(
        payload.trigger, "trigger", document_version_id=draft.source_id, anchors=anchors
    )
    exception_asts = []
    exception_diag = []
    for index, raw_exception in enumerate(payload.exceptions):
        parsed, diag = _validate_candidate(
            raw_exception,
            f"exceptions/{index}",
            document_version_id=draft.source_id,
            anchors=anchors,
        )
        if parsed is not None:
            exception_asts.append(parsed)
        exception_diag.extend(diag)
    diagnostics = [*target_diag, *trigger_diag, *exception_diag]
    if diagnostics:
        blockers.append("ast_or_selector_invalid")
    asts = [expr for expr in (target, trigger, *exception_asts) if expr is not None]
    used_anchor_ids = set()
    for expr in asts:
        for _path, leaf in iter_leaves(expr, ""):
            used_anchor_ids.update(leaf.anchor_ids)
    if used_anchor_ids - evidence_keys:
        blockers.append("predicate_anchor_missing_from_evidence")
    constant_or_empty = False
    try:
        for expr in asts:
            for _path, leaf in iter_leaves(expr, ""):
                if getattr(leaf, "op", None) == "constant":
                    constant_or_empty = True
    except Exception:  # noqa: BLE001
        pass
    if not payload.exceptions:
        constant_or_empty = True
    if constant_or_empty and not (payload.reviewer_rationale or "").strip():
        blockers.append("reviewer_rationale_required")
    rule_payload = None
    rule_hash = None
    if target is not None and trigger is not None:
        try:
            rule = RuleVersion(
                id=uuid.uuid4(),
                project_id=project_id,
                document_version_id=draft.source_id,
                entry_id=payload.entry_id,
                review_state="draft",
                reviewer_id=None,
                target=target,
                trigger=trigger,
                exceptions=tuple(exception_asts),
                consequence=payload.consequence,
                anchors=tuple(sorted(used_anchor_ids or evidence_keys)),
            )
            rule_payload = rule.model_dump(mode="json")
            rule_hash = _hash(rule_payload)
        except (ValidationError, DomainValidationError, ValueError) as exc:
            blockers.append(f"rule_invalid:{str(exc)[:180]}")
    candidate = {
        "schema_version": 1,
        "draft_id": str(draft.id),
        "draft_response_hash": draft.response_hash,
        "source_id": str(draft.source_id),
        "source_sha256": session.get(SourceVersion, draft.source_id).sha256,
        "extraction_id": str(extraction.id),
        "entry_id": payload.entry_id,
        "target": payload.target,
        "trigger": payload.trigger,
        "exceptions": payload.exceptions,
        "consequence": payload.consequence,
        "evidence": [item.model_dump(mode="json") for item in payload.evidence],
        "reviewer_rationale": payload.reviewer_rationale,
        "rule": rule_payload,
        "rule_hash": rule_hash,
        "blockers": blockers,
        "validation": diagnostics,
    }
    row = ConversionProposal(
        id=uuid.uuid4(),
        project_id=project_id,
        draft_id=draft.id,
        source_id=draft.source_id,
        extraction_id=extraction.id,
        entry_id=payload.entry_id,
        payload=candidate,
        content_hash=_hash(candidate),
        ineligible_reason=";".join(blockers) if blockers else None,
        reviewer_rationale=payload.reviewer_rationale,
        current_revision=0,
        created_by=actor_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(row)
    session.commit()
    return row


def get_proposal(session: Session, project_id: uuid.UUID, proposal_id: uuid.UUID) -> ConversionProposal:
    row = session.scalar(
        select(ConversionProposal).where(
            ConversionProposal.project_id == project_id,
            ConversionProposal.id == proposal_id,
        )
    )
    if row is None:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", "proposal not found")
    return row


def proposal_body(session: Session, row: ConversionProposal) -> dict[str, Any]:
    reviews = list(
        session.scalars(
            select(ProposalReview)
            .where(ProposalReview.proposal_id == row.id)
            .order_by(ProposalReview.revision)
        )
    )
    accepted = session.scalar(
        select(AcceptedRule).where(AcceptedRule.proposal_id == row.id)
    )
    return {
        "id": row.id,
        "project_id": row.project_id,
        "draft_id": row.draft_id,
        "source_id": row.source_id,
        "extraction_id": row.extraction_id,
        "entry_id": row.entry_id,
        "payload": row.payload,
        "content_hash": row.content_hash,
        "ineligible_reason": row.ineligible_reason,
        "reviewer_rationale": row.reviewer_rationale,
        "current_revision": row.current_revision,
        "created_by": row.created_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "reviews": [
            {
                "id": review.id,
                "revision": review.revision,
                "actor_id": review.actor_id,
                "decision": review.decision,
                "rationale": review.rationale,
                "expected_content_hash": review.expected_content_hash,
                "accepted_rule_version_id": review.accepted_rule_version_id,
                "created_at": review.created_at,
            }
            for review in reviews
        ],
        "accepted_rule": (
            {
                "id": accepted.id,
                "payload": accepted.payload,
                "content_hash": accepted.content_hash,
            }
            if accepted
            else None
        ),
    }


def review_body(row: ProposalReview) -> dict[str, Any]:
    return {
        "id": row.id,
        "proposal_id": row.proposal_id,
        "revision": row.revision,
        "actor_id": row.actor_id,
        "decision": row.decision,
        "rationale": row.rationale,
        "expected_content_hash": row.expected_content_hash,
        "accepted_rule_version_id": row.accepted_rule_version_id,
        "created_at": row.created_at,
    }


def decide_proposal(
    session: Session,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    proposal_id: uuid.UUID,
    payload: ReviewCreate,
) -> tuple[ProposalReview, AcceptedRule | None]:
    services.require_role(session, project_id, actor_id, ("owner", "reviewer"))
    row = session.scalar(
        select(ConversionProposal)
        .where(
            ConversionProposal.project_id == project_id,
            ConversionProposal.id == proposal_id,
        )
        .with_for_update()
    )
    if row is None:
        raise ApiError(404, "PROPOSAL_NOT_FOUND", "proposal not found")
    if payload.expected_revision != row.current_revision:
        raise ApiError(409, "REVIEW_REVISION_CONFLICT", "proposal revision has changed")
    if payload.expected_content_hash != row.content_hash:
        raise ApiError(409, "REVIEW_CONTENT_CONFLICT", "proposal content hash has changed")
    accepted_rule = None
    if payload.decision == "accepted":
        if row.ineligible_reason:
            raise ApiError(409, "PROPOSAL_INELIGIBLE", "proposal has unresolved blockers")
        candidate = row.payload
        rule_payload = candidate.get("rule")
        if not rule_payload:
            raise ApiError(409, "PROPOSAL_INELIGIBLE", "proposal has no validated rule")
        draft = get_draft(session, project_id, row.draft_id)
        anchors = _anchors(session, row.extraction_id)
        target, target_diag = _validate_candidate(
            candidate["target"], "target", document_version_id=row.source_id, anchors=anchors
        )
        trigger, trigger_diag = _validate_candidate(
            candidate["trigger"], "trigger", document_version_id=row.source_id, anchors=anchors
        )
        exceptions = []
        exception_diag = []
        for index, raw_exception in enumerate(candidate["exceptions"]):
            parsed, diagnostics = _validate_candidate(
                raw_exception,
                f"exceptions/{index}",
                document_version_id=row.source_id,
                anchors=anchors,
            )
            exception_diag.extend(diagnostics)
            if parsed is not None:
                exceptions.append(parsed)
        if target is None or trigger is None or target_diag or trigger_diag or exception_diag:
            raise ApiError(409, "PROPOSAL_INELIGIBLE", "rule no longer validates")
        if draft.status != "validated" or draft.response_hash != candidate["draft_response_hash"]:
            raise ApiError(409, "REVIEW_EVIDENCE_CONFLICT", "draft evidence changed")
        try:
            accepted = RuleVersion(
                id=uuid.uuid4(),
                project_id=project_id,
                document_version_id=row.source_id,
                entry_id=row.entry_id,
                review_state="accepted",
                reviewer_id=str(actor_id),
                target=target,
                trigger=trigger,
                exceptions=tuple(exceptions),
                consequence=candidate["consequence"],
                anchors=tuple(sorted(candidate.get("rule", {}).get("anchors", []))),
            )
        except (ValidationError, DomainValidationError, ValueError) as exc:
            raise ApiError(409, "PROPOSAL_INELIGIBLE", f"rule cannot be accepted: {str(exc)[:500]}") from exc
        content_hash = _hash(accepted.model_dump(mode="json"))
        accepted_rule = AcceptedRule(
            id=accepted.id,
            project_id=project_id,
            proposal_id=row.id,
            review_id=uuid.uuid4(),
            source_id=row.source_id,
            entry_id=row.entry_id,
            payload=accepted.model_dump(mode="json"),
            content_hash=content_hash,
            reviewer_id=actor_id,
            created_at=_utcnow(),
        )
        session.add(accepted_rule)
        session.flush()
        review = ProposalReview(
            id=accepted_rule.review_id,
            project_id=project_id,
            proposal_id=row.id,
            revision=row.current_revision + 1,
            actor_id=actor_id,
            decision="accepted",
            rationale=payload.rationale,
            expected_content_hash=payload.expected_content_hash,
            accepted_rule_version_id=accepted.id,
            created_at=_utcnow(),
        )
    else:
        review = ProposalReview(
            id=uuid.uuid4(),
            project_id=project_id,
            proposal_id=row.id,
            revision=row.current_revision + 1,
            actor_id=actor_id,
            decision="rejected",
            rationale=payload.rationale,
            expected_content_hash=payload.expected_content_hash,
            accepted_rule_version_id=None,
            created_at=_utcnow(),
        )
    session.add(review)
    row.current_revision += 1
    row.updated_at = _utcnow()
    session.commit()
    return review, accepted_rule


def list_reviews(session: Session, proposal: ConversionProposal) -> list[ProposalReview]:
    return list(
        session.scalars(
            select(ProposalReview)
            .where(ProposalReview.proposal_id == proposal.id)
            .order_by(ProposalReview.revision)
        )
    )


def get_rule(session: Session, project_id: uuid.UUID, rule_id: uuid.UUID) -> AcceptedRule:
    row = session.scalar(
        select(AcceptedRule).where(
            AcceptedRule.project_id == project_id, AcceptedRule.id == rule_id
        )
    )
    if row is None:
        raise ApiError(404, "RULE_NOT_FOUND", "accepted rule not found")
    return row

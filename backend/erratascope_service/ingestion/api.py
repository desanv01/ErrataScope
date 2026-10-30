"""W04 ingestion APIRouter factory (shares W03 auth/error/idempotency patterns)."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..errors import ApiError
from . import service
from .models import ConversionProposal, Extraction, ModelDraft, SourceVersion
from .schemas import (
    DraftResponse,
    ExtractionCreate,
    ExtractionResponse,
    ProposalCreate,
    ProposalResponse,
    ReviewCreate,
    SourceCreate,
    SourceResponse,
)

DEFAULT_PAGE = 50
MAX_PAGE = 100


def _cursor_encode(created, row_id) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([created.isoformat(), str(row_id)]).encode()
    ).decode()


def _cursor_decode(cursor: str) -> tuple[str, str]:
    try:
        created, row_id = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return str(created), str(row_id)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(400, "INVALID_CURSOR", "cursor is malformed") from exc


def _page(rows, limit: int, cursor: str | None, key) -> dict:
    if cursor:
        created, row_id = _cursor_decode(cursor)
        rows = [row for row in rows if (key(row).isoformat(), str(row.id)) < (created, row_id)]
    items = rows[:limit]
    next_cursor = _cursor_encode(key(items[-1]), items[-1].id) if len(rows) > limit else None
    return {"items": items, "next_cursor": next_cursor}


def build_router(settings, actor_dep, session_dep) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def _role(session: Session, project_id: uuid.UUID, actor_id: uuid.UUID, roles=services.WRITE_ROLES):
        services.require_role(session, project_id, actor_id, roles)

    def _idem(
        session: Session,
        *,
        project_id: uuid.UUID,
        actor_id: uuid.UUID,
        operation: str,
        key: str | None,
        body: Any,
    ) -> tuple[str | None, str | None]:
        if key is None:
            return None, None
        validated = services.validate_idempotency_key(key)
        body_hash = services.request_hash(body)
        record = services.fetch_idempotent(
            session,
            project_id=project_id,
            actor_id=actor_id,
            operation=operation,
            key=validated,
        )
        if record is not None:
            replay = services.replay_idempotent(record, body_hash)
            return validated, json.dumps(replay)
        return validated, None

    @router.post(
        "/projects/{project_id}/sources",
        status_code=201,
        response_model=SourceResponse,
    )
    def create_source(
        project_id: uuid.UUID,
        payload: SourceCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        _role(session, project_id, actor_id)
        key, replay = _idem(
            session,
            project_id=project_id,
            actor_id=actor_id,
            operation="w04.source.create",
            key=idempotency_key,
            body=payload.model_dump(mode="json"),
        )
        if replay is not None:
            return Response(status_code=201, content=replay, media_type="application/json")
        row = service.create_source(session, project_id, actor_id, payload)
        body = service.source_body(row)
        if key:
            services.store_idempotent(
                session,
                project_id=project_id,
                actor_id=actor_id,
                operation="w04.source.create",
                key=key,
                body_hash=services.request_hash(payload.model_dump(mode="json")),
                status=201,
                body=jsonable_encoder(body),
                resource_id=row.id,
            )
            session.commit()
        return body

    @router.get("/projects/{project_id}/sources")
    def list_sources(
        project_id: uuid.UUID,
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        rows = list(
            session.scalars(
                select(SourceVersion)
                .where(SourceVersion.project_id == project_id)
                .order_by(SourceVersion.created_at.desc(), SourceVersion.id.desc())
            )
        )
        page = _page(rows, limit, cursor, lambda row: row.created_at)
        return {
            "items": [service.source_body(row) for row in page["items"]],
            "next_cursor": page["next_cursor"],
        }

    @router.get("/projects/{project_id}/sources/{source_id}")
    def source_detail(
        project_id: uuid.UUID,
        source_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        row = service.get_source(session, project_id, source_id)
        body = service.source_body(row)
        latest = session.scalar(
            select(Extraction)
            .where(Extraction.source_id == row.id)
            .order_by(Extraction.created_at.desc())
        )
        body["latest_extraction"] = (
            service.extraction_body(session, latest, include_output=True) if latest else None
        )
        return body

    @router.post(
        "/projects/{project_id}/sources/{source_id}/extractions",
        status_code=202,
        response_model=ExtractionResponse,
    )
    def create_extraction(
        project_id: uuid.UUID,
        source_id: uuid.UUID,
        payload: ExtractionCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        extraction, job = service.create_extraction(
            session,
            project_id,
            actor_id,
            source_id,
            selected_entries=payload.selected_entries,
            mode=payload.mode,
            case_kind=payload.case_kind,
            live_enabled=settings.w04_live_enabled,
        )
        body = service.extraction_body(session, extraction, include_output=False)
        body["status_url"] = f"/api/v1/projects/{project_id}/jobs/{job.id}"
        return body

    @router.get("/extractions/{extraction_id}", response_model=ExtractionResponse)
    def extraction_detail(
        extraction_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(Extraction, extraction_id)
        if row is None:
            raise ApiError(404, "EXTRACTION_NOT_FOUND", "extraction not found")
        services.membership(session, row.project_id, actor_id)
        return service.extraction_body(session, row)

    @router.get("/extractions/{extraction_id}/anchors")
    def extraction_anchors(
        extraction_id: uuid.UUID,
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(Extraction, extraction_id)
        if row is None:
            raise ApiError(404, "EXTRACTION_NOT_FOUND", "extraction not found")
        services.membership(session, row.project_id, actor_id)
        anchors = service.list_anchors(session, row)
        page = _page(anchors, limit, cursor, lambda anchor: anchor.created_at)
        return {
            "items": [service.anchor_body(anchor) for anchor in page["items"]],
            "next_cursor": page["next_cursor"],
        }

    @router.get("/extractions/{extraction_id}/coverage")
    def extraction_coverage(
        extraction_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(Extraction, extraction_id)
        if row is None:
            raise ApiError(404, "EXTRACTION_NOT_FOUND", "extraction not found")
        services.membership(session, row.project_id, actor_id)
        entries = service.list_coverage(session, row)
        return {
            "items": [service.coverage_body(entry) for entry in entries],
            "next_cursor": None,
            "inventory_complete": False,
        }

    @router.get("/extractions/{extraction_id}/drafts")
    def extraction_drafts(
        extraction_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(Extraction, extraction_id)
        if row is None:
            raise ApiError(404, "EXTRACTION_NOT_FOUND", "extraction not found")
        services.membership(session, row.project_id, actor_id)
        drafts = list(
            session.scalars(
                select(ModelDraft).where(ModelDraft.extraction_id == extraction_id)
            )
        )
        return {"items": [service.draft_body(draft) for draft in drafts], "next_cursor": None}

    @router.get("/drafts/{draft_id}", response_model=DraftResponse)
    def draft_detail(
        draft_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(ModelDraft, draft_id)
        if row is None:
            raise ApiError(404, "DRAFT_NOT_FOUND", "draft not found")
        services.membership(session, row.project_id, actor_id)
        return service.draft_body(row)

    @router.post(
        "/drafts/{draft_id}/proposals",
        status_code=201,
        response_model=ProposalResponse,
    )
    def create_proposal(
        draft_id: uuid.UUID,
        payload: ProposalCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        draft = session.get(ModelDraft, draft_id)
        if draft is None:
            raise ApiError(404, "DRAFT_NOT_FOUND", "draft not found")
        services.membership(session, draft.project_id, actor_id)
        row = service.create_proposal(session, draft.project_id, actor_id, draft_id, payload)
        return service.proposal_body(session, row)

    @router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
    def proposal_detail(
        proposal_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(ConversionProposal, proposal_id)
        if row is None:
            raise ApiError(404, "PROPOSAL_NOT_FOUND", "proposal not found")
        services.membership(session, row.project_id, actor_id)
        return service.proposal_body(session, row)

    @router.post(
        "/proposals/{proposal_id}/reviews",
        status_code=201,
        response_model=dict,
    )
    def review_proposal(
        proposal_id: uuid.UUID,
        payload: ReviewCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        row = session.get(ConversionProposal, proposal_id)
        if row is None:
            raise ApiError(404, "PROPOSAL_NOT_FOUND", "proposal not found")
        services.require_role(session, row.project_id, actor_id, ("owner", "reviewer"))
        key, replay = _idem(
            session,
            project_id=row.project_id,
            actor_id=actor_id,
            operation=f"w04.proposal.review.{proposal_id}",
            key=idempotency_key,
            body=payload.model_dump(mode="json"),
        )
        if replay is not None:
            return Response(status_code=201, content=replay, media_type="application/json")
        review, accepted = service.decide_proposal(
            session, row.project_id, actor_id, proposal_id, payload
        )
        body = {
            "review": service.review_body(review),
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
        if key:
            services.store_idempotent(
                session,
                project_id=row.project_id,
                actor_id=actor_id,
                operation=f"w04.proposal.review.{proposal_id}",
                key=key,
                body_hash=services.request_hash(payload.model_dump(mode="json")),
                status=201,
                body=jsonable_encoder(body),
                resource_id=review.id,
            )
            session.commit()
        return body

    @router.get("/proposals/{proposal_id}/reviews")
    def proposal_reviews(
        proposal_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        row = session.get(ConversionProposal, proposal_id)
        if row is None:
            raise ApiError(404, "PROPOSAL_NOT_FOUND", "proposal not found")
        services.membership(session, row.project_id, actor_id)
        reviews = service.list_reviews(session, row)
        return {"items": [service.review_body(review) for review in reviews], "next_cursor": None}

    @router.get("/rules/{rule_version_id}")
    def rule_detail(
        rule_version_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        from .models import AcceptedRule

        row = session.get(AcceptedRule, rule_version_id)
        if row is None:
            raise ApiError(404, "RULE_NOT_FOUND", "accepted rule not found")
        services.membership(session, row.project_id, actor_id)
        return {
            "id": row.id,
            "project_id": row.project_id,
            "proposal_id": row.proposal_id,
            "review_id": row.review_id,
            "source_id": row.source_id,
            "entry_id": row.entry_id,
            "payload": row.payload,
            "content_hash": row.content_hash,
            "reviewer_id": row.reviewer_id,
            "created_at": row.created_at,
        }

    return router

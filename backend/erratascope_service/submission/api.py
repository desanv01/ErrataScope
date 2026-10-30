"""S01 submission routes: context, interpretation review and summary export."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..errors import ApiError
from ..ingestion.models import ModelDraft
from . import service
from .models import InterpretationReview

PREFIX = "/api/v1"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewRequest(Strict):
    expected_revision: int = Field(ge=0)
    expected_response_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: str = Field(pattern=r"^(reviewed|rejected)$")
    note: str = Field(min_length=1, max_length=2000)


def build_router(settings, actor_dep, session_dep) -> APIRouter:
    router = APIRouter(prefix=PREFIX)

    def _draft(session: Session, actor_id: uuid.UUID, draft_id: uuid.UUID) -> ModelDraft:
        draft = session.get(ModelDraft, draft_id)
        if draft is None:
            raise ApiError(404, "DRAFT_NOT_FOUND", "draft not found")
        services.membership(session, draft.project_id, actor_id)
        return draft

    @router.get("/projects/{project_id}/submission-context")
    def submission_context(
        project_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        return service.submission_context(session, project_id, actor_id)

    @router.get("/drafts/{draft_id}/interpretation-reviews")
    def reviews(
        draft_id: uuid.UUID,
        limit: int = Query(50, ge=1, le=100),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        draft = _draft(session, actor_id, draft_id)
        after = 0
        if cursor:
            try:
                after = int(cursor)
            except ValueError as exc:
                raise ApiError(400, "INVALID_CURSOR", "cursor is malformed") from exc
            if after < 0:
                raise ApiError(400, "INVALID_CURSOR", "cursor is malformed")
        return service.list_reviews(
            session, draft.project_id, draft_id, limit=limit, after_revision=after
        )

    @router.post("/drafts/{draft_id}/interpretation-reviews", status_code=201)
    def record_review(
        draft_id: uuid.UUID,
        payload: ReviewRequest,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        draft = _draft(session, actor_id, draft_id)
        services.require_role(session, draft.project_id, actor_id, ("owner", "reviewer"))
        if idempotency_key is None:
            raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required")
        key = services.validate_idempotency_key(idempotency_key)
        body = payload.model_dump(mode="json")
        body_hash = services.request_hash(body)
        # Serialize replay lookup with review creation. A simultaneous identical
        # request must see the first transaction's receipt, not a stale revision.
        session.scalar(select(ModelDraft).where(ModelDraft.id == draft_id).with_for_update())
        services.require_role(session, draft.project_id, actor_id, ("owner", "reviewer"))
        record = services.fetch_idempotent(
            session,
            project_id=draft.project_id,
            actor_id=actor_id,
            operation=f"s01.interpretation.review.{draft_id}",
            key=key,
        )
        if record is not None:
            replay = services.replay_idempotent(record, body_hash)
            return Response(status_code=201, content=json.dumps(replay["body"]), media_type="application/json")
        review = service.record_review(
            session,
            draft.project_id,
            actor_id,
            draft_id,
            expected_revision=payload.expected_revision,
            expected_response_hash=payload.expected_response_hash,
            decision=payload.decision,
            note=payload.note,
        )
        body_response = {
            "review": service.review_body(review),
            "current_revision": review.revision,
            "decision_effect": "human acknowledgement only; no executable rule created",
        }
        services.store_idempotent(
            session,
            project_id=draft.project_id,
            actor_id=actor_id,
            operation=f"s01.interpretation.review.{draft_id}",
            key=key,
            body_hash=body_hash,
            status=201,
            body=jsonable_encoder(body_response),
            resource_id=review.id,
        )
        session.commit()
        return body_response

    @router.get("/drafts/{draft_id}/review-summary")
    def review_summary(
        draft_id: uuid.UUID,
        format: str = Query("json", pattern="^(json|markdown)$"),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        draft = _draft(session, actor_id, draft_id)
        summary = service.review_summary(session, draft.project_id, draft_id)
        if format == "markdown":
            markdown = service.summary_markdown(summary)
            return Response(content=markdown, media_type="text/markdown; charset=utf-8")
        return summary

    @router.get("/submission/dev-session")
    def dev_session():
        """Local-only demo bootstrap; never available without an explicit dev-auth dir."""
        if settings.mode != "local" or settings.dev_auth_dir is None:
            raise ApiError(404, "DEV_SESSION_UNAVAILABLE", "development auth is not configured")
        tokens_path = Path(settings.dev_auth_dir) / "tokens.json"
        if not tokens_path.exists():
            raise ApiError(404, "DEV_SESSION_UNAVAILABLE", "development auth is not configured")
        try:
            tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
            token = tokens["users"]["user-a"]["token"]
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            raise ApiError(404, "DEV_SESSION_UNAVAILABLE", "development auth is not configured") from exc
        return {
            "token": token,
            "label": "Local development auth (not hosted production identity)",
            "issuer": tokens.get("issuer"),
            "audience": tokens.get("audience"),
        }

    return router

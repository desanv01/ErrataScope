"""FastAPI application for the local W03 foundation (repair 01 contract)."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import Body, Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import services
from .artifacts import (
    ArtifactError,
    ArtifactStore,
    content_disposition,
    normalize_media_type,
    sanitize_filename,
)
from .auth import TokenVerifier
from .config import ConfigError, Settings, load_settings
from .db import database_ready, get_engine, get_session_factory
from .errors import ApiError
from .jobs import broker_ready
from .models import Artifact, Bundle, Job, JobEvent, Membership, Project, ReviewEvent, ReviewItem, UploadStaging
from .storage_identity import database_identity
from .schemas import (
    ArtifactOut,
    ArtifactPage,
    BundleOut,
    BundlePage,
    ErrorBody,
    ErrorEnvelope,
    HealthOut,
    JobCreate,
    JobEventOut,
    JobEventPage,
    JobOut,
    MembershipCreate,
    MembershipOut,
    MembershipPage,
    MembershipRoleUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectPage,
    ReviewDecisionCreate,
    ReviewEventOut,
    ReviewEventPage,
    ReviewItemCreate,
    ReviewItemOut,
)

API_PREFIX = "/api/v1"
DEFAULT_PAGE = 50
MAX_PAGE = 100
logger = logging.getLogger("erratascope.api")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def _error(
    status: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str = "unavailable",
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            details=[
                {"field": item.get("field") or item.get("path"), "message": item.get("message", "")}
                for item in (details or [])
            ],
        ),
        request_id=request_id,
    )
    return JSONResponse(status_code=status, content=payload.model_dump())


def _project_body(project: Project, role: str) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.name,
        "created_by": str(project.created_by),
        "created_at": services.iso(project.created_at),
        "role": role,
    }


def _membership_body(row: Membership) -> dict[str, Any]:
    return {
        "project_id": str(row.project_id),
        "actor_id": str(row.actor_id),
        "role": row.role,
        "created_at": services.iso(row.created_at),
    }


def _artifact_body(row: Artifact) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "sha256": row.sha256,
        "byte_length": row.byte_length,
        "media_type": row.media_type,
        "original_name": row.original_name,
        "state": row.state,
        "created_at": services.iso(row.created_at),
    }


def _bundle_body(row: Bundle) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "input_hash": row.input_hash,
        "schema_version": row.schema_version,
        "evaluator_version": row.evaluator_version,
        "payload": row.payload,
        "created_at": services.iso(row.created_at),
    }


def _review_body(row: ReviewItem) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "artifact_id": str(row.artifact_id),
        "content_hash": row.content_hash,
        "annotation": row.annotation,
        "current_revision": row.current_revision,
        "created_by": str(row.created_by),
        "created_at": services.iso(row.created_at),
    }


def _review_event_body(row: ReviewEvent) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "review_item_id": str(row.review_item_id),
        "revision": row.revision,
        "actor_id": str(row.actor_id),
        "decision": row.decision,
        "rationale": row.rationale,
        "created_at": services.iso(row.created_at),
    }


def _job_body(row: Job) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "kind": row.kind,
        "artifact_id": str(row.artifact_id),
        "status": row.status,
        "attempt_count": row.attempt_count,
        "max_attempts": row.max_attempts,
        "result_artifact_id": str(row.result_artifact_id) if row.result_artifact_id else None,
        "result_sha256": row.result_sha256,
        "error_code": row.error_code,
        "created_at": services.iso(row.created_at),
        "updated_at": services.iso(row.updated_at),
        "status_url": f"{API_PREFIX}/projects/{row.project_id}/jobs/{row.id}",
    }


def _job_event_body(row: JobEvent) -> dict[str, Any]:
    return {
        "seq": row.seq,
        "event_type": row.event_type,
        "payload": row.payload,
        "created_at": services.iso(row.created_at),
    }


def _encode_cursor(values: list[Any]) -> str:
    raw = json.dumps(values, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> list[Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        value = json.loads(raw)
    except (ValueError, binascii.Error, UnicodeError) as exc:
        raise ApiError(400, "INVALID_CURSOR", "cursor is malformed") from exc
    if not isinstance(value, list) or len(value) != 2:
        raise ApiError(400, "INVALID_CURSOR", "cursor is malformed")
    return value


def _created_cursor(stmt, model, cursor: str | None):
    if cursor:
        raw = _decode_cursor(cursor)
        try:
            timestamp = datetime.fromisoformat(str(raw[0]))
            object_id = uuid.UUID(str(raw[1]))
        except (ValueError, TypeError) as exc:
            raise ApiError(400, "INVALID_CURSOR", "cursor is malformed") from exc
        stmt = stmt.where(
            or_(
                model.created_at > timestamp,
                and_(model.created_at == timestamp, model.id > object_id),
            )
        )
    return stmt


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    settings.ensure_startable()
    if settings.mode == "local" and (settings.jwks_path is None or not settings.jwks_path.exists()):
        raise ConfigError("INVALID_CONFIG", "local API startup requires an existing W03_JWKS_PATH")
    verifier = TokenVerifier(settings)
    store = ArtifactStore(
        settings.artifact_root,
        database_identity=database_identity(settings.database_url),
    )
    factory = get_session_factory(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            get_engine(settings)
            yield
        finally:
            store.close()

    app = FastAPI(
        title="ErrataScope local foundation",
        version="w03-repair-01",
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.verifier = verifier
    app.state.store = store

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        # A server-generated UUID is authoritative; caller X-Request-ID is ignored.
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def session_dep():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    def actor_dep(request: Request, authorization: str | None = Header(default=None)) -> uuid.UUID:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise ApiError(401, "UNAUTHENTICATED", "missing bearer token")
        return request.app.state.verifier.verify(authorization.split(" ", 1)[1].strip())

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return _error(exc.status_code, exc.code, exc.message, exc.details, _request_id(request))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(part) for part in item.get("loc", [])),
                "message": item.get("msg", ""),
            }
            for item in exc.errors()
        ]
        return _error(422, "VALIDATION_ERROR", "request validation failed", details, _request_id(request))

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        code = "NOT_FOUND" if exc.status_code == 404 else "METHOD_NOT_ALLOWED" if exc.status_code == 405 else "HTTP_ERROR"
        return _error(exc.status_code, code, "request failed", None, _request_id(request))

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        return _error(409, "DB_CONFLICT", "request conflicts with current data", None, _request_id(request))

    @app.exception_handler(SQLAlchemyError)
    async def database_handler(request: Request, exc: SQLAlchemyError):
        logger.error("database error request_id=%s", _request_id(request))
        return _error(500, "DATABASE_ERROR", "database operation failed", None, _request_id(request))

    @app.exception_handler(ArtifactError)
    async def artifact_handler(request: Request, exc: ArtifactError):
        if exc.code == "ARTIFACT_TOO_LARGE":
            status = 413
        elif exc.code in (
            "STAGING_LEASE_LOST",
            "STAGING_LOST",
            "UPLOAD_CONFLICT",
            "ARTIFACT_STAGING_EXISTS",
        ):
            status = 409
        elif exc.code in (
            "ARTIFACT_INTEGRITY",
            "ARTIFACT_MISSING",
            "ARTIFACT_READ_ERROR",
            "ARTIFACT_STORE_ERROR",
        ):
            status = 500
        else:
            status = 422
        return _error(status, exc.code, exc.message, None, _request_id(request))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.error("unhandled error request_id=%s type=%s", _request_id(request), type(exc).__name__)
        return _error(500, "INTERNAL_ERROR", "internal server error", None, _request_id(request))

    def idempotent(
        session: Session,
        *,
        scope_project: uuid.UUID,
        actor_id: uuid.UUID,
        operation: str,
        key: str,
        body_hash: str,
        authorize: Callable[[], None],
        fn: Callable[[], tuple[int, dict[str, Any], uuid.UUID | None]],
        replayed_project: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        """Authorize before every replay/original path, including race fallback."""
        authorize()
        existing = services.fetch_idempotent(
            session, project_id=scope_project, actor_id=actor_id, operation=operation, key=key
        )
        if existing is not None:
            if replayed_project and existing.resource_id is not None:
                services.membership(session, existing.resource_id, actor_id)
            return _replay_payload(services.replay_idempotent(existing, body_hash))
        try:
            status, body, resource_id = fn()
            services.store_idempotent(
                session,
                project_id=scope_project,
                actor_id=actor_id,
                operation=operation,
                key=key,
                body_hash=body_hash,
                status=status,
                body=body,
                resource_id=resource_id,
            )
            session.commit()
            return status, body
        except IntegrityError:
            session.rollback()
            existing = services.fetch_idempotent(
                session, project_id=scope_project, actor_id=actor_id, operation=operation, key=key
            )
            if existing is not None:
                authorize()
                if replayed_project and existing.resource_id is not None:
                    services.membership(session, existing.resource_id, actor_id)
                return _replay_payload(services.replay_idempotent(existing, body_hash))
            raise ApiError(409, "CONFLICT", "concurrent modification conflict") from None
        except Exception:
            session.rollback()
            raise

    def _replay_payload(replay: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return replay["status"], replay["body"]

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    @app.get("/health/live", response_model=HealthOut)
    def health_live() -> HealthOut:
        return HealthOut(status="ok", mode=settings.mode, database=False, broker=False)

    @app.get("/health/ready")
    def health_ready():
        db_ok = database_ready(get_engine(settings))
        broker_ok = broker_ready(settings)
        body = HealthOut(
            status="ok" if db_ok and broker_ok else "degraded",
            mode=settings.mode,
            database=db_ok,
            broker=broker_ok,
        )
        return JSONResponse(status_code=200 if db_ok and broker_ok else 503, content=body.model_dump())

    # ------------------------------------------------------------------
    # Projects and membership
    # ------------------------------------------------------------------
    @app.post(
        f"{API_PREFIX}/projects",
        status_code=201,
        response_model=ProjectOut,
        responses={
            401: {"model": ErrorEnvelope},
            403: {"model": ErrorEnvelope},
            404: {"model": ErrorEnvelope},
            409: {"model": ErrorEnvelope},
            422: {"model": ErrorEnvelope},
        },
    )
    def create_project(
        payload: ProjectCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(payload.model_dump())

        def run():
            project = services.create_project(session, actor_id=actor_id, name=payload.name)
            return 201, _project_body(project, "owner"), project.id

        status, body = idempotent(
            session,
            scope_project=services.NIL_PROJECT,
            actor_id=actor_id,
            operation="create_project",
            key=key,
            body_hash=body_hash,
            authorize=lambda: None,
            fn=run,
            replayed_project=True,
        )
        return JSONResponse(status_code=status, content=body)

    @app.get(f"{API_PREFIX}/projects", response_model=ProjectPage)
    def list_projects(
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        stmt = (
            select(Project, Membership.role)
            .join(Membership, Membership.project_id == Project.id)
            .where(Membership.actor_id == actor_id)
        )
        stmt = _created_cursor(stmt, Project, cursor)
        rows = session.execute(
            stmt.order_by(Project.created_at, Project.id).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [_project_body(project, role) for project, role in rows]
        next_cursor = (
            _encode_cursor([rows[-1][0].created_at.isoformat(), str(rows[-1][0].id)])
            if has_more and rows
            else None
        )
        return {"items": items, "next_cursor": next_cursor}

    @app.get(f"{API_PREFIX}/projects/{{project_id}}", response_model=ProjectOut)
    def project_detail(
        project_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        project, role = services.get_project_detail(session, project_id, actor_id)
        return _project_body(project, role)

    @app.get(f"{API_PREFIX}/projects/{{project_id}}/members", response_model=MembershipPage)
    def list_members(
        project_id: uuid.UUID,
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.require_role(session, project_id, actor_id, ("owner",))
        stmt = select(Membership).where(Membership.project_id == project_id)
        if cursor:
            raw = _decode_cursor(cursor)
            try:
                timestamp = datetime.fromisoformat(str(raw[0]))
                member_id = uuid.UUID(str(raw[1]))
            except (ValueError, TypeError) as exc:
                raise ApiError(400, "INVALID_CURSOR", "cursor is malformed") from exc
            stmt = stmt.where(
                or_(
                    Membership.created_at > timestamp,
                    and_(
                        Membership.created_at == timestamp,
                        Membership.actor_id > member_id,
                    ),
                )
            )
        rows = session.scalars(
            stmt.order_by(Membership.created_at, Membership.actor_id).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            _encode_cursor([rows[-1].created_at.isoformat(), str(rows[-1].actor_id)])
            if has_more and rows
            else None
        )
        return {"items": [_membership_body(row) for row in rows], "next_cursor": next_cursor}

    @app.post(
        f"{API_PREFIX}/projects/{{project_id}}/members",
        status_code=201,
        response_model=MembershipOut,
    )
    def add_member(
        project_id: uuid.UUID,
        payload: MembershipCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(
            {"actor_id": str(payload.actor_id), "role": payload.role, "project_id": str(project_id)}
        )

        def run():
            row = services.add_member(
                session,
                project_id=project_id,
                actor_id=actor_id,
                new_actor=payload.actor_id,
                role=payload.role,
            )
            return 201, _membership_body(row), None

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="add_member",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, ("owner",)),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    @app.put(
        f"{API_PREFIX}/projects/{{project_id}}/members/{{target_actor}}",
        status_code=200,
        response_model=MembershipOut,
    )
    def upsert_member(
        project_id: uuid.UUID,
        target_actor: uuid.UUID,
        payload: MembershipRoleUpdate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(
            {"target": str(target_actor), "role": payload.role, "project_id": str(project_id)}
        )

        def run():
            row = services.upsert_membership(
                session,
                project_id=project_id,
                actor_id=actor_id,
                target_actor=target_actor,
                role=payload.role,
            )
            return 200, _membership_body(row), None

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="upsert_member",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, ("owner",)),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    @app.delete(f"{API_PREFIX}/projects/{{project_id}}/members/{{target_actor}}", status_code=204)
    def delete_member(
        project_id: uuid.UUID,
        target_actor: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(
            {"target": str(target_actor), "project_id": str(project_id), "operation": "delete_member"}
        )

        def run():
            services.remove_membership(
                session,
                project_id=project_id,
                actor_id=actor_id,
                target_actor=target_actor,
            )
            return 204, {}, None

        status, _body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="delete_member",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, ("owner",)),
            fn=run,
        )
        return Response(status_code=status)

    # ------------------------------------------------------------------
    # Artifacts (bounded streaming staging)
    # ------------------------------------------------------------------
    @app.post(
        f"{API_PREFIX}/projects/{{project_id}}/artifacts",
        status_code=201,
        response_model=ArtifactOut,
    )
    async def upload_artifact(
        project_id: uuid.UUID,
        request: Request,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
        session.commit()  # close the authorization transaction before body I/O
        media_type = normalize_media_type(request.headers.get("content-type"))
        raw_name = request.headers.get("x-filename")
        if raw_name:
            try:
                # HTTP headers are transported as latin-1; recover UTF-8 names.
                raw_name = raw_name.encode("latin-1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            if "%" in raw_name:
                from urllib.parse import unquote

                try:
                    raw_name = unquote(raw_name, errors="strict")
                except (UnicodeDecodeError, ValueError):
                    pass
        original_name = sanitize_filename(raw_name)
        artifact_id = uuid.uuid4()
        staging_key = store.staging_key(project_id, artifact_id)
        final_key = store.final_key(project_id, artifact_id)
        upload = store.begin_staging(project_id, artifact_id)
        try:
            session.add(
                UploadStaging(
                    artifact_id=artifact_id,
                    project_id=project_id,
                    actor_id=actor_id,
                    staging_key=staging_key,
                    state="active",
                    owner_kind="upload",
                    lease_until=services.utcnow()
                    + timedelta(seconds=settings.staging_lease_seconds),
                    created_at=services.utcnow(),
                    updated_at=services.utcnow(),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            upload.abort()
            raise
        body_hash = ""

        def renew_staging() -> None:
            fresh = factory()
            try:
                now = services.utcnow()
                result = fresh.execute(
                    update(UploadStaging)
                    .where(
                        UploadStaging.artifact_id == artifact_id,
                        UploadStaging.state == "active",
                        UploadStaging.owner_kind == "upload",
                        UploadStaging.owner_job_id.is_(None),
                        UploadStaging.lease_until > now,
                    )
                    .values(
                        lease_until=now
                        + timedelta(seconds=settings.staging_lease_seconds),
                        updated_at=now,
                    )
                )
                if result.rowcount != 1:
                    fresh.rollback()
                    raise ArtifactError(
                        "STAGING_LEASE_LOST", "upload staging ownership was lost"
                    )
                fresh.commit()
            finally:
                fresh.close()

        def mark_ambiguous() -> None:
            fresh = factory()
            try:
                fresh.execute(
                    update(UploadStaging)
                    .where(
                        UploadStaging.artifact_id == artifact_id,
                        UploadStaging.state == "active",
                    )
                    .values(state="ambiguous", updated_at=services.utcnow())
                )
                fresh.commit()
            except SQLAlchemyError:
                fresh.rollback()
            finally:
                fresh.close()

        def cleanup_own_bytes(proven_uncommitted: bool) -> None:
            upload.abort()
            if proven_uncommitted:
                store.delete(final_key)
            fresh = factory()
            try:
                row = fresh.get(UploadStaging, artifact_id)
                if row is not None:
                    fresh.delete(row)
                    fresh.commit()
            except SQLAlchemyError:
                fresh.rollback()
            finally:
                fresh.close()

        try:
            total = 0
            last_renewed = time.monotonic()
            renew_interval = max(1.0, min(2.0, settings.staging_lease_seconds / 2))
            async for chunk in request.stream():
                total += len(chunk)
                if total > settings.max_artifact_bytes:
                    raise ArtifactError(
                        "ARTIFACT_TOO_LARGE", "artifact exceeds the configured maximum size"
                    )
                if chunk:
                    upload.write(chunk, settings.max_artifact_bytes)
                if time.monotonic() - last_renewed >= renew_interval:
                    renew_staging()
                    last_renewed = time.monotonic()
            sha256, length = upload.finish()
            body_hash = services.request_hash(
                {
                    "sha256": sha256,
                    "media_type": media_type,
                    "name": original_name,
                    "length": length,
                }
            )
            existing = services.fetch_idempotent(
                session,
                project_id=project_id,
                actor_id=actor_id,
                operation="upload_artifact",
                key=key,
            )
            if existing is not None:
                services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
                replay = services.replay_idempotent(existing, body_hash)
                cleanup_own_bytes(proven_uncommitted=True)
                return JSONResponse(status_code=replay["status"], content=replay["body"])

            failpoint = (
                os.environ.get("W03_TEST_UPLOAD_FAILPOINT", "") if settings.test_mode else ""
            )
            if failpoint == "hold_before_finalize":
                time.sleep(float(os.environ.get("W03_TEST_UPLOAD_HOLD_SECONDS", "2")))

            services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
            row = session.execute(
                select(UploadStaging)
                .where(UploadStaging.artifact_id == artifact_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalar_one_or_none()
            now = services.utcnow()
            if (
                row is None
                or row.state != "active"
                or row.owner_kind != "upload"
                or row.owner_job_id is not None
                or row.lease_until <= now
            ):
                raise ArtifactError(
                    "STAGING_LEASE_LOST", "upload staging ownership was lost"
                )
            promoted_key = upload.promote()
            if not store.verify_bytes(promoted_key, sha256, length):
                raise ArtifactError("ARTIFACT_INTEGRITY", "uploaded bytes failed verification")
            failpoint = (
                os.environ.get("W03_TEST_UPLOAD_FAILPOINT", "") if settings.test_mode else ""
            )
            rejected_length = -1 if failpoint == "db_reject" else length
            artifact = services.create_artifact_record(
                session,
                project_id=project_id,
                actor_id=actor_id,
                artifact_id=artifact_id,
                storage_key=promoted_key,
                sha256=sha256,
                byte_length=rejected_length,
                media_type=media_type,
                original_name=original_name,
            )
            row.state = "finalized"
            body = _artifact_body(artifact)
            services.store_idempotent(
                session,
                project_id=project_id,
                actor_id=actor_id,
                operation="upload_artifact",
                key=key,
                body_hash=body_hash,
                status=201,
                body=body,
                resource_id=artifact_id,
            )
            session.commit()
            if failpoint == "ambiguous_after_commit":
                raise RuntimeError("simulated upload acknowledgement loss after commit")
            return JSONResponse(status_code=201, content=body)
        except ArtifactError:
            session.rollback()
            cleanup_own_bytes(proven_uncommitted=True)
            raise
        except IntegrityError:
            session.rollback()
            existing = services.fetch_idempotent(
                session,
                project_id=project_id,
                actor_id=actor_id,
                operation="upload_artifact",
                key=key,
            )
            if existing is not None:
                services.require_role(session, project_id, actor_id, services.WRITE_ROLES)
                replay = services.replay_idempotent(existing, body_hash)
                cleanup_own_bytes(proven_uncommitted=True)
                return JSONResponse(status_code=replay["status"], content=replay["body"])
            cleanup_own_bytes(proven_uncommitted=True)
            raise ApiError(409, "UPLOAD_REJECTED", "artifact persistence was rejected") from None
        except Exception:
            session.rollback()
            # Ambiguous outcome: a fresh session decides whether bytes are committed.
            fresh = factory()
            try:
                committed = fresh.scalar(
                    select(Artifact).where(
                        Artifact.project_id == project_id, Artifact.id == artifact_id
                    )
                )
            except Exception:
                fresh.close()
                mark_ambiguous()
                raise ApiError(
                    500, "UPLOAD_UNKNOWN", "artifact outcome could not be established"
                ) from None
            if committed is not None:
                try:
                    store.read_bytes(
                        committed.storage_key, committed.sha256, committed.byte_length
                    )
                except ArtifactError:
                    fresh.close()
                    mark_ambiguous()
                    raise ApiError(
                        500, "UPLOAD_INTEGRITY", "committed artifact bytes are not intact"
                    ) from None
                staged = fresh.get(UploadStaging, artifact_id)
                if staged is not None and staged.state != "finalized":
                    staged.state = "finalized"
                    fresh.commit()
                fresh.close()
                return JSONResponse(status_code=201, content=_artifact_body(committed))
            fresh.close()
            cleanup_own_bytes(proven_uncommitted=True)
            raise ApiError(500, "UPLOAD_FAILED", "artifact could not be finalized") from None
        except BaseException:
            # Disconnect/cancellation must still release the staging fd/bytes.
            session.rollback()
            cleanup_own_bytes(proven_uncommitted=True)
            raise

    @app.get(f"{API_PREFIX}/projects/{{project_id}}/artifacts", response_model=ArtifactPage)
    def list_artifacts(
        project_id: uuid.UUID,
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        stmt = _created_cursor(
            select(Artifact).where(Artifact.project_id == project_id), Artifact, cursor
        )
        rows = session.scalars(
            stmt.order_by(Artifact.created_at, Artifact.id).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            _encode_cursor([rows[-1].created_at.isoformat(), str(rows[-1].id)])
            if has_more and rows
            else None
        )
        return {"items": [_artifact_body(row) for row in rows], "next_cursor": next_cursor}

    @app.get(
        f"{API_PREFIX}/projects/{{project_id}}/artifacts/{{artifact_id}}",
        response_model=ArtifactOut,
    )
    def artifact_metadata(
        project_id: uuid.UUID,
        artifact_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        return _artifact_body(services.get_artifact(session, project_id, artifact_id))

    @app.get(f"{API_PREFIX}/projects/{{project_id}}/artifacts/{{artifact_id}}/content")
    def artifact_content(
        project_id: uuid.UUID,
        artifact_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        row = services.get_artifact(session, project_id, artifact_id)
        data = store.read_bytes(row.storage_key, row.sha256, row.byte_length)
        filename = sanitize_filename(row.original_name) or f"artifact-{row.id.hex[:8]}"
        headers = {
            "Content-Disposition": content_disposition(filename),
            "Cache-Control": "private, no-store",
            "ETag": f'"{row.sha256}"',
        }
        return Response(content=data, media_type=row.media_type, headers=headers)

    # ------------------------------------------------------------------
    # Bundles
    # ------------------------------------------------------------------
    @app.post(
        f"{API_PREFIX}/projects/{{project_id}}/bundles", status_code=201, response_model=BundleOut
    )
    def create_bundle(
        project_id: uuid.UUID,
        payload: dict[str, Any] = Body(...),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(payload)

        def run():
            row = services.persist_bundle(
                session, project_id=project_id, actor_id=actor_id, raw_bundle=payload
            )
            return 201, _bundle_body(row), row.id

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="create_bundle",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, services.WRITE_ROLES),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    @app.get(f"{API_PREFIX}/projects/{{project_id}}/bundles", response_model=BundlePage)
    def list_bundles(
        project_id: uuid.UUID,
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        cursor: str | None = Query(default=None),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        stmt = _created_cursor(
            select(Bundle).where(Bundle.project_id == project_id), Bundle, cursor
        )
        rows = session.scalars(
            stmt.order_by(Bundle.created_at, Bundle.id).limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            _encode_cursor([rows[-1].created_at.isoformat(), str(rows[-1].id)])
            if has_more and rows
            else None
        )
        return {"items": [_bundle_body(row) for row in rows], "next_cursor": next_cursor}

    @app.get(
        f"{API_PREFIX}/projects/{{project_id}}/bundles/{{bundle_id}}", response_model=BundleOut
    )
    def bundle_detail(
        project_id: uuid.UUID,
        bundle_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        return _bundle_body(services.get_bundle(session, project_id, bundle_id))

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
    @app.post(
        f"{API_PREFIX}/projects/{{project_id}}/review-items",
        status_code=201,
        response_model=ReviewItemOut,
    )
    def create_review_item(
        project_id: uuid.UUID,
        payload: ReviewItemCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(
            {
                "artifact_id": str(payload.artifact_id),
                "content_hash": payload.content_hash,
                "annotation": payload.annotation,
                "project_id": str(project_id),
            }
        )

        def run():
            row = services.create_review_item(
                session,
                project_id=project_id,
                actor_id=actor_id,
                artifact_id=payload.artifact_id,
                content_hash=payload.content_hash,
                annotation=payload.annotation,
            )
            return 201, _review_body(row), row.id

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="create_review_item",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, services.REVIEW_ROLES),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    @app.get(f"{API_PREFIX}/projects/{{project_id}}/review-items/{{item_id}}")
    def review_item_detail(
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        item = services.get_review_item(session, project_id, item_id)
        all_events = services.list_review_events(session, project_id, item_id)
        events = all_events[:limit]
        has_more = len(all_events) > len(events)
        return {
            "item": _review_body(item),
            "events": {
                "items": [_review_event_body(event) for event in events],
                "next_cursor": events[-1].revision if has_more and events else None,
            },
        }

    @app.get(
        f"{API_PREFIX}/projects/{{project_id}}/review-items/{{item_id}}/events",
        response_model=ReviewEventPage,
    )
    def review_events(
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        after_seq: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        services.get_review_item(session, project_id, item_id)
        rows = session.scalars(
            select(ReviewEvent)
            .where(ReviewEvent.project_id == project_id, ReviewEvent.review_item_id == item_id, ReviewEvent.revision > after_seq)
            .order_by(ReviewEvent.revision)
            .limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        return {
            "items": [_review_event_body(row) for row in rows],
            "next_cursor": rows[-1].revision if has_more and rows else None,
        }

    @app.post(
        f"{API_PREFIX}/projects/{{project_id}}/review-items/{{item_id}}/decisions",
        status_code=201,
        response_model=ReviewEventOut,
    )
    def decide_review(
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: ReviewDecisionCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(
            {
                "item_id": str(item_id),
                "decision": payload.decision,
                "rationale": payload.rationale,
                "expected_revision": payload.expected_revision,
            }
        )

        def run():
            services.decide_review(
                session,
                project_id=project_id,
                actor_id=actor_id,
                item_id=item_id,
                decision=payload.decision,
                rationale=payload.rationale,
                expected_revision=payload.expected_revision,
            )
            events = services.list_review_events(session, project_id, item_id)
            latest = events[-1]
            return 201, _review_event_body(latest), latest.id

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="decide_review",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, services.REVIEW_ROLES),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------
    @app.post(f"{API_PREFIX}/projects/{{project_id}}/jobs", status_code=202, response_model=JobOut)
    def create_job(
        project_id: uuid.UUID,
        payload: JobCreate,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash(
            {"kind": payload.kind, "artifact_id": str(payload.artifact_id), "project_id": str(project_id)}
        )

        def run():
            job = services.create_job(
                session,
                project_id=project_id,
                actor_id=actor_id,
                artifact_id=payload.artifact_id,
                kind=payload.kind,
            )
            return 202, _job_body(job), job.id

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="create_job",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, services.WRITE_ROLES),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    @app.get(f"{API_PREFIX}/projects/{{project_id}}/jobs/{{job_id}}", response_model=JobOut)
    def job_detail(
        project_id: uuid.UUID,
        job_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        return _job_body(services.get_job(session, project_id, job_id))

    @app.get(
        f"{API_PREFIX}/projects/{{project_id}}/jobs/{{job_id}}/events",
        response_model=JobEventPage,
    )
    def job_events(
        project_id: uuid.UUID,
        job_id: uuid.UUID,
        after_seq: int = Query(0, ge=0),
        limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
    ):
        services.membership(session, project_id, actor_id)
        services.get_job(session, project_id, job_id)
        rows = session.scalars(
            select(JobEvent)
            .where(JobEvent.project_id == project_id, JobEvent.job_id == job_id, JobEvent.seq > after_seq)
            .order_by(JobEvent.seq)
            .limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        return {
            "items": [_job_event_body(row) for row in rows],
            "next_cursor": rows[-1].seq if has_more and rows else None,
        }

    @app.post(
        f"{API_PREFIX}/projects/{{project_id}}/jobs/{{job_id}}/cancel", response_model=JobOut
    )
    def cancel_job(
        project_id: uuid.UUID,
        job_id: uuid.UUID,
        actor_id: uuid.UUID = Depends(actor_dep),
        session: Session = Depends(session_dep),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ):
        key = services.validate_idempotency_key(idempotency_key)
        body_hash = services.request_hash({"job_id": str(job_id), "operation": "cancel"})

        def run():
            job = services.cancel_job(session, project_id, job_id, actor_id)
            return 200, _job_body(job), job.id

        status, body = idempotent(
            session,
            scope_project=project_id,
            actor_id=actor_id,
            operation="cancel_job",
            key=key,
            body_hash=body_hash,
            authorize=lambda: services.require_role(session, project_id, actor_id, services.WRITE_ROLES),
            fn=run,
        )
        return JSONResponse(status_code=status, content=body)

    return app


app = create_app()




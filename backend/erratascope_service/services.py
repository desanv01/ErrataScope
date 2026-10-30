"""Transactional application services for projects, artifacts, bundles, reviews, jobs."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from erratascope_domain.errors import DomainValidationError

from . import domain_adapter
from .errors import ApiError
from .models import (
    Artifact,
    Bundle,
    BundleMember,
    DomainVersion,
    IdempotencyRecord,
    Job,
    JobAttempt,
    JobEvent,
    Membership,
    Outbox,
    Project,
    ReviewEvent,
    ReviewItem,
)

NIL_PROJECT = uuid.UUID(int=0)
WRITE_ROLES = ("owner", "editor")
REVIEW_ROLES = ("owner", "reviewer")
ALL_ROLES = ("owner", "editor", "reviewer", "viewer")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def request_hash(body: Any) -> str:
    return canonical_hash(body if body is not None else {})


def validate_idempotency_key(key: str | None) -> str:
    if key is None or not (16 <= len(key) <= 128) or any(not (32 <= ord(ch) <= 126) for ch in key):
        raise ApiError(
            400,
            "IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency-Key header is required (16-128 printable ASCII characters)",
        )
    return key


def membership(session: Session, project_id: uuid.UUID, actor_id: uuid.UUID) -> Membership:
    row = session.get(Membership, (project_id, actor_id))
    if row is None:
        raise ApiError(404, "PROJECT_NOT_FOUND", "project not found")
    return row


def require_role(
    session: Session, project_id: uuid.UUID, actor_id: uuid.UUID, allowed: tuple[str, ...]
) -> Membership:
    row = membership(session, project_id, actor_id)
    if row.role not in allowed:
        raise ApiError(403, "FORBIDDEN", "role is not permitted for this operation")
    return row


def create_project(
    session: Session, *, actor_id: uuid.UUID, name: str, project_id: uuid.UUID | None = None
) -> Project:
    project = Project(
        id=project_id or uuid.uuid4(),
        name=name.strip(),
        created_by=actor_id,
        created_at=utcnow(),
    )
    if not project.name:
        raise ApiError(400, "INVALID_REQUEST", "project name must not be blank")
    session.add(project)
    session.flush()
    session.add(
        Membership(
            project_id=project.id,
            actor_id=actor_id,
            role="owner",
            created_at=utcnow(),
        )
    )
    session.flush()
    return project


def list_projects(session: Session, actor_id: uuid.UUID) -> list[tuple[Project, str]]:
    rows = session.execute(
        select(Project, Membership.role)
        .join(Membership, Membership.project_id == Project.id)
        .where(Membership.actor_id == actor_id)
        .order_by(Project.created_at, Project.id)
    ).all()
    return [(project, role) for project, role in rows]


def add_member(
    session: Session, *, project_id: uuid.UUID, actor_id: uuid.UUID, new_actor: uuid.UUID, role: str
) -> Membership:
    require_role(session, project_id, actor_id, ("owner",))
    if role not in ALL_ROLES:
        raise ApiError(400, "INVALID_ROLE", "unsupported membership role")
    if new_actor == actor_id:
        raise ApiError(409, "CANNOT_CHANGE_SELF", "owners cannot add themselves")
    project = _lock_project(session, project_id)
    if project is None:
        raise ApiError(404, "PROJECT_NOT_FOUND", "project not found")
    existing = session.get(Membership, (project_id, new_actor))
    if existing is not None:
        raise ApiError(409, "MEMBERSHIP_EXISTS", "actor is already a member of this project")
    row = Membership(project_id=project_id, actor_id=new_actor, role=role, created_at=utcnow())
    session.add(row)
    session.flush()
    return row


def _lock_project(session: Session, project_id: uuid.UUID) -> Project | None:
    return session.execute(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()


def _owner_count(session: Session, project_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.project_id == project_id, Membership.role == "owner")
        )
        or 0
    )


def get_project_detail(
    session: Session, project_id: uuid.UUID, actor_id: uuid.UUID
) -> tuple[Project, str]:
    role = membership(session, project_id, actor_id).role
    project = session.get(Project, project_id)
    if project is None:
        raise ApiError(404, "PROJECT_NOT_FOUND", "project not found")
    return project, role


def upsert_membership(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    target_actor: uuid.UUID,
    role: str,
) -> Membership:
    """Owner-only create/update; project-row lock serializes owner races."""
    require_role(session, project_id, actor_id, ("owner",))
    if role not in ALL_ROLES:
        raise ApiError(400, "INVALID_ROLE", "unsupported membership role")
    if _lock_project(session, project_id) is None:
        raise ApiError(404, "PROJECT_NOT_FOUND", "project not found")
    if target_actor == actor_id and role != "owner":
        raise ApiError(
            409,
            "SELF_MEMBERSHIP_CHANGE",
            "owners cannot demote or remove themselves through this route",
        )
    existing = session.execute(
        select(Membership)
        .where(Membership.project_id == project_id, Membership.actor_id == target_actor)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if existing is None:
        row = Membership(project_id=project_id, actor_id=target_actor, role=role, created_at=utcnow())
        session.add(row)
        session.flush()
        return row
    if existing.role == "owner" and role != "owner" and _owner_count(session, project_id) <= 1:
        raise ApiError(409, "LAST_OWNER", "the last owner cannot be demoted")
    existing.role = role
    session.flush()
    return existing


def remove_membership(
    session: Session, *, project_id: uuid.UUID, actor_id: uuid.UUID, target_actor: uuid.UUID
) -> None:
    require_role(session, project_id, actor_id, ("owner",))
    if _lock_project(session, project_id) is None:
        raise ApiError(404, "PROJECT_NOT_FOUND", "project not found")
    if target_actor == actor_id:
        raise ApiError(409, "SELF_REMOVAL", "owners cannot remove themselves")
    row = session.execute(
        select(Membership)
        .where(Membership.project_id == project_id, Membership.actor_id == target_actor)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "MEMBERSHIP_NOT_FOUND", "membership not found")
    if row.role == "owner" and _owner_count(session, project_id) <= 1:
        raise ApiError(409, "LAST_OWNER", "the last owner cannot be removed")
    session.delete(row)
    session.flush()


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------
def create_artifact_record(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    artifact_id: uuid.UUID,
    storage_key: str,
    sha256: str,
    byte_length: int,
    media_type: str,
    original_name: str | None,
) -> Artifact:
    record = Artifact(
        id=artifact_id,
        project_id=project_id,
        storage_key=storage_key,
        sha256=sha256,
        byte_length=byte_length,
        media_type=media_type,
        original_name=original_name,
        state="ready",
        created_by=actor_id,
        created_at=utcnow(),
    )
    session.add(record)
    session.flush()
    return record


def get_artifact(session: Session, project_id: uuid.UUID, artifact_id: uuid.UUID) -> Artifact:
    row = session.scalar(
        select(Artifact).where(Artifact.project_id == project_id, Artifact.id == artifact_id)
    )
    if row is None:
        raise ApiError(404, "ARTIFACT_NOT_FOUND", "artifact not found")
    return row


def list_artifacts(session: Session, project_id: uuid.UUID) -> list[Artifact]:
    return list(
        session.scalars(
            select(Artifact)
            .where(Artifact.project_id == project_id)
            .order_by(Artifact.created_at, Artifact.id)
        )
    )


# ---------------------------------------------------------------------------
# Bundles / domain versions
# ---------------------------------------------------------------------------
def _domain_version_record(project_id: uuid.UUID, record: dict[str, Any]) -> DomainVersion:
    return DomainVersion(
        id=uuid.uuid4(),
        project_id=project_id,
        kind=record["kind"],
        version_id=record["version_id"],
        payload=record["payload"],
        payload_hash=record["payload_hash"],
        created_at=utcnow(),
    )


def persist_bundle(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    raw_bundle: dict[str, Any],
) -> Bundle:
    try:
        bundle_model, payload, input_hash = domain_adapter.canonical_bundle(raw_bundle)
    except DomainValidationError as exc:
        raise ApiError(
            422,
            "BUNDLE_INVALID",
            "bundle failed domain validation",
            details=exc.as_list(),
        ) from exc
    if str(bundle_model.project_id) != str(project_id):
        raise ApiError(409, "PROJECT_MISMATCH", "bundle project does not match the request project")

    existing_bundle = session.scalar(
        select(Bundle).where(Bundle.project_id == project_id, Bundle.input_hash == input_hash)
    )
    if existing_bundle is not None:
        return existing_bundle

    records = domain_adapter.extract_versions(bundle_model)
    for record in records:
        existing = session.scalar(
            select(DomainVersion).where(
                DomainVersion.project_id == project_id,
                DomainVersion.kind == record["kind"],
                DomainVersion.version_id == record["version_id"],
            )
        )
        if existing is not None:
            if existing.payload_hash != record["payload_hash"]:
                raise ApiError(
                    409,
                    "DOMAIN_VERSION_CONFLICT",
                    f"{record['kind']} {record['version_id']} already exists with different content",
                )
            continue
        session.add(_domain_version_record(project_id, record))
    session.flush()

    bundle = Bundle(
        id=uuid.uuid4(),
        project_id=project_id,
        input_hash=input_hash,
        schema_version=bundle_model.schema_version,
        evaluator_version=bundle_model.evaluator_version,
        payload=payload,
        created_by=actor_id,
        created_at=utcnow(),
    )
    session.add(bundle)
    session.flush()
    for record in records:
        session.add(
            BundleMember(
                project_id=project_id,
                bundle_id=bundle.id,
                kind=record["kind"],
                version_id=record["version_id"],
                payload_hash=record["payload_hash"],
            )
        )
    session.flush()
    return bundle


def get_bundle(session: Session, project_id: uuid.UUID, bundle_id: uuid.UUID) -> Bundle:
    row = session.scalar(select(Bundle).where(Bundle.project_id == project_id, Bundle.id == bundle_id))
    if row is None:
        raise ApiError(404, "BUNDLE_NOT_FOUND", "bundle not found")
    try:
        domain_adapter.load_bundle(row.payload, row.input_hash)
    except DomainValidationError as exc:
        raise ApiError(
            500, "BUNDLE_INTEGRITY", "persisted bundle failed revalidation", details=exc.as_list()
        ) from exc
    return row


def list_bundles(session: Session, project_id: uuid.UUID) -> list[Bundle]:
    return list(
        session.scalars(
            select(Bundle).where(Bundle.project_id == project_id).order_by(Bundle.created_at, Bundle.id)
        )
    )


# ---------------------------------------------------------------------------
# Reviews with optimistic concurrency
# ---------------------------------------------------------------------------
def create_review_item(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    artifact_id: uuid.UUID,
    content_hash: str,
    annotation: str,
) -> ReviewItem:
    require_role(session, project_id, actor_id, REVIEW_ROLES)
    artifact = get_artifact(session, project_id, artifact_id)
    if artifact.sha256 != content_hash:
        raise ApiError(409, "ARTIFACT_HASH_MISMATCH", "content hash does not match the stored artifact")
    item = ReviewItem(
        id=uuid.uuid4(),
        project_id=project_id,
        artifact_id=artifact_id,
        content_hash=content_hash,
        annotation=annotation.strip(),
        current_revision=0,
        created_by=actor_id,
        created_at=utcnow(),
    )
    if not item.annotation:
        raise ApiError(400, "INVALID_REQUEST", "annotation must not be blank")
    session.add(item)
    session.flush()
    return item


def get_review_item(session: Session, project_id: uuid.UUID, item_id: uuid.UUID) -> ReviewItem:
    row = session.scalar(
        select(ReviewItem).where(ReviewItem.project_id == project_id, ReviewItem.id == item_id)
    )
    if row is None:
        raise ApiError(404, "REVIEW_ITEM_NOT_FOUND", "review item not found")
    return row


def list_review_events(session: Session, project_id: uuid.UUID, item_id: uuid.UUID) -> list[ReviewEvent]:
    return list(
        session.scalars(
            select(ReviewEvent)
            .where(ReviewEvent.project_id == project_id, ReviewEvent.review_item_id == item_id)
            .order_by(ReviewEvent.revision)
        )
    )


def decide_review(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    item_id: uuid.UUID,
    decision: str,
    rationale: str,
    expected_revision: int,
) -> ReviewItem:
    require_role(session, project_id, actor_id, REVIEW_ROLES)
    item = session.execute(
        select(ReviewItem)
        .where(ReviewItem.project_id == project_id, ReviewItem.id == item_id)
        .with_for_update()
    ).scalar_one_or_none()
    if item is None:
        raise ApiError(404, "REVIEW_ITEM_NOT_FOUND", "review item not found")
    if item.current_revision != expected_revision:
        raise ApiError(
            409,
            "REVIEW_REVISION_CONFLICT",
            "review item has advanced since the expected revision",
            details=[
                {
                    "field": "expected_revision",
                    "message": f"current revision is {item.current_revision}",
                }
            ],
        )
    if decision not in ("accepted", "rejected"):
        raise ApiError(400, "INVALID_DECISION", "decision must be accepted or rejected")
    rationale = rationale.strip()
    if not rationale:
        raise ApiError(400, "INVALID_REQUEST", "rationale must not be blank")
    new_revision = expected_revision + 1
    item.current_revision = new_revision
    session.add(
        ReviewEvent(
            id=uuid.uuid4(),
            project_id=project_id,
            review_item_id=item.id,
            revision=new_revision,
            actor_id=actor_id,
            decision=decision,
            rationale=rationale,
            created_at=utcnow(),
        )
    )
    session.flush()
    return item


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------
def fetch_idempotent(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    operation: str,
    key: str,
) -> IdempotencyRecord | None:
    return session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.project_id == project_id,
            IdempotencyRecord.actor_id == actor_id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.key == key,
        )
    )


def replay_idempotent(record: IdempotencyRecord, body_hash: str) -> dict[str, Any]:
    if record.request_hash != body_hash:
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "this idempotency key was already used with a different request",
        )
    return {
        "status": record.response_status,
        "body": record.response_body,
        "resource_id": record.resource_id,
    }


def store_idempotent(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    operation: str,
    key: str,
    body_hash: str,
    status: int,
    body: dict[str, Any],
    resource_id: uuid.UUID | None,
) -> None:
    session.add(
        IdempotencyRecord(
            id=uuid.uuid4(),
            project_id=project_id,
            actor_id=actor_id,
            operation=operation,
            key=key,
            request_hash=body_hash,
            response_status=status,
            response_body=body,
            resource_id=resource_id,
            created_at=utcnow(),
        )
    )


# ---------------------------------------------------------------------------
# Jobs and events
# ---------------------------------------------------------------------------
def append_event(session: Session, job: Job, event_type: str, payload: dict[str, Any]) -> JobEvent:
    job.next_event_seq += 1
    event = JobEvent(
        id=uuid.uuid4(),
        project_id=job.project_id,
        job_id=job.id,
        seq=job.next_event_seq,
        event_type=event_type,
        payload=payload,
        created_at=utcnow(),
    )
    session.add(event)
    session.flush()
    return event


def create_job(
    session: Session,
    *,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    artifact_id: uuid.UUID,
    kind: str = "artifact_digest",
    max_attempts: int = 3,
) -> Job:
    require_role(session, project_id, actor_id, WRITE_ROLES)
    get_artifact(session, project_id, artifact_id)
    if not 1 <= max_attempts <= 3:
        raise ApiError(422, "INVALID_JOB_ATTEMPTS", "max_attempts must be 1-3")
    job = Job(
        id=uuid.uuid4(),
        project_id=project_id,
        actor_id=actor_id,
        kind=kind,
        artifact_id=artifact_id,
        status="queued",
        attempt_count=0,
        max_attempts=max_attempts,
        next_event_seq=0,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(job)
    session.flush()
    append_event(session, job, "queued", {"status": "queued"})
    session.add(
        Outbox(
            id=uuid.uuid4(),
            project_id=project_id,
            job_id=job.id,
            dispatch_generation=1,
            available_at=utcnow(),
            created_at=utcnow(),
        )
    )
    session.flush()
    return job


def get_job(session: Session, project_id: uuid.UUID, job_id: uuid.UUID, *, lock: bool = False) -> Job:
    query = select(Job).where(Job.project_id == project_id, Job.id == job_id)
    if lock:
        query = query.with_for_update()
    row = session.execute(query).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "JOB_NOT_FOUND", "job not found")
    return row


def list_job_events(
    session: Session, project_id: uuid.UUID, job_id: uuid.UUID, after_seq: int = 0
) -> list[JobEvent]:
    return list(
        session.scalars(
            select(JobEvent)
            .where(
                JobEvent.project_id == project_id,
                JobEvent.job_id == job_id,
                JobEvent.seq > after_seq,
            )
            .order_by(JobEvent.seq)
            .limit(500)
        )
    )


def cancel_job(session: Session, project_id: uuid.UUID, job_id: uuid.UUID, actor_id: uuid.UUID) -> Job:
    require_role(session, project_id, actor_id, WRITE_ROLES)
    job = session.execute(
        select(Job)
        .where(Job.project_id == project_id, Job.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if job is None:
        raise ApiError(404, "JOB_NOT_FOUND", "job not found")
    if job.status == "succeeded":
        raise ApiError(409, "JOB_ALREADY_COMPLETED", "a succeeded job cannot be cancelled")
    if job.status != "cancelled":
        token = job.current_attempt_token
        if token is not None:
            attempt = session.execute(
                select(JobAttempt)
                .where(JobAttempt.job_id == job.id, JobAttempt.token == token)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalar_one_or_none()
            if attempt is not None and attempt.ended_at is None:
                attempt.ended_at = utcnow()
                attempt.outcome = "cancelled"
        job.status = "cancelled"
        job.current_attempt_token = None
        job.lease_until = None
        job.updated_at = utcnow()
        append_event(session, job, "cancelled", {"status": "cancelled"})
        session.flush()
    return job

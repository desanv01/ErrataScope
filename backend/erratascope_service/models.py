"""SQLAlchemy models mirroring the W03 foundation migration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "erratascope"
metadata = MetaData(schema=SCHEMA)


class Base(DeclarativeBase):
    metadata = metadata


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class Membership(TimestampMixin, Base):
    __tablename__ = "memberships"
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'editor', 'reviewer', 'viewer')", name="memberships_role_check"
        ),
        ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.id"], name="memberships_project_fk"),
    )


class Artifact(TimestampMixin, Base):
    __tablename__ = "artifacts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="artifacts_project_id_uq"),
        ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.id"], name="artifacts_project_fk"),
        CheckConstraint(
            "media_type IN ('application/pdf', 'text/plain', 'application/json')",
            name="artifacts_media_type_check",
        ),
        CheckConstraint("byte_length >= 0 AND byte_length <= 10485760", name="artifacts_size_check"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="artifacts_sha_check"),
    )


class UploadStaging(TimestampMixin, Base):
    """Tracks bytes written before their owning artifact row is committed.

    Rows are mutable only for lifecycle transitions; they are never exposed as
    artifacts. Reconciliation uses state/lease plus fresh artifact references.
    """

    __tablename__ = "upload_staging"
    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    staging_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    owner_kind: Mapped[str] = mapped_column(Text, nullable=False, default="upload")
    owner_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    owner_attempt_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    __table_args__ = (
        ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.id"], name="staging_project_fk"),
        CheckConstraint(
            "state IN ('active', 'finalized', 'abandoned', 'ambiguous')",
            name="staging_state_check",
        ),
        CheckConstraint(
            "owner_kind IN ('upload', 'result')", name="staging_owner_kind_check"
        ),
    )


class Bundle(TimestampMixin, Base):
    __tablename__ = "bundles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluator_version: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("project_id", "input_hash", name="bundles_project_input_uq"),
        UniqueConstraint("project_id", "id", name="bundles_project_id_uq"),
        ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.id"], name="bundles_project_fk"),
    )


class DomainVersion(TimestampMixin, Base):
    __tablename__ = "domain_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    version_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        UniqueConstraint("project_id", "kind", "version_id", name="domain_versions_project_kind_uq"),
        UniqueConstraint("project_id", "id", name="domain_versions_project_id_uq"),
        ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="domain_versions_project_fk"
        ),
    )


class BundleMember(Base):
    __tablename__ = "bundle_members"
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bundle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    version_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint("bundle_id", "kind", "version_id", name="bundle_members_pk"),
        ForeignKeyConstraint(
            ["project_id", "bundle_id"],
            [f"{SCHEMA}.bundles.project_id", f"{SCHEMA}.bundles.id"],
            name="bundle_members_bundle_fk",
        ),
        ForeignKeyConstraint(
            ["project_id", "kind", "version_id"],
            [
                f"{SCHEMA}.domain_versions.project_id",
                f"{SCHEMA}.domain_versions.kind",
                f"{SCHEMA}.domain_versions.version_id",
            ],
            name="bundle_members_version_fk",
        ),
    )


class ReviewItem(TimestampMixin, Base):
    __tablename__ = "review_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    annotation: Mapped[str] = mapped_column(Text, nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="review_items_project_id_uq"),
        ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], name="review_items_project_fk"
        ),
        ForeignKeyConstraint(
            ["project_id", "artifact_id"],
            [f"{SCHEMA}.artifacts.project_id", f"{SCHEMA}.artifacts.id"],
            name="review_items_artifact_fk",
        ),
    )


class ReviewEvent(TimestampMixin, Base):
    __tablename__ = "review_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    review_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint("review_item_id", "revision", name="review_events_revision_uq"),
        ForeignKeyConstraint(
            ["project_id", "review_item_id"],
            [f"{SCHEMA}.review_items.project_id", f"{SCHEMA}.review_items.id"],
            name="review_events_item_fk",
        ),
        CheckConstraint("decision IN ('accepted', 'rejected')", name="review_events_decision_check"),
    )


class IdempotencyRecord(TimestampMixin, Base):
    __tablename__ = "idempotency"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    __table_args__ = (
        UniqueConstraint(
            "project_id", "actor_id", "operation", "key", name="idempotency_scope_uq"
        ),
    )


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    current_attempt_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_event_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    result_sha256: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="jobs_project_id_uq"),
        ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.id"], name="jobs_project_fk"),
        ForeignKeyConstraint(
            ["project_id", "artifact_id"],
            [f"{SCHEMA}.artifacts.project_id", f"{SCHEMA}.artifacts.id"],
            name="jobs_artifact_fk",
        ),
        ForeignKeyConstraint(
            ["project_id", "result_artifact_id"],
            [f"{SCHEMA}.artifacts.project_id", f"{SCHEMA}.artifacts.id"],
            name="jobs_result_artifact_fk",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="jobs_status_check",
        ),
    )


class JobAttempt(Base):
    __tablename__ = "job_attempts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    token: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="job_attempts_number_uq"),
        UniqueConstraint("job_id", "token", name="job_attempts_token_uq"),
        ForeignKeyConstraint(
            ["project_id", "job_id"],
            [f"{SCHEMA}.jobs.project_id", f"{SCHEMA}.jobs.id"],
            name="job_attempts_job_fk",
        ),
    )


class Outbox(TimestampMixin, Base):
    __tablename__ = "outbox"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dispatch_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    claim_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("job_id", "dispatch_generation", name="outbox_generation_uq"),
        ForeignKeyConstraint(
            ["project_id", "job_id"],
            [f"{SCHEMA}.jobs.project_id", f"{SCHEMA}.jobs.id"],
            name="outbox_job_fk",
        ),
    )


class JobEvent(TimestampMixin, Base):
    __tablename__ = "job_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        UniqueConstraint("job_id", "seq", name="job_events_seq_uq"),
        ForeignKeyConstraint(
            ["project_id", "job_id"],
            [f"{SCHEMA}.jobs.project_id", f"{SCHEMA}.jobs.id"],
            name="job_events_job_fk",
        ),
    )


class StageResult(Base):
    __tablename__ = "stage_results"
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage_key: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    result_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        PrimaryKeyConstraint("job_id", "stage_key", name="stage_results_pk"),
        ForeignKeyConstraint(
            ["project_id", "job_id"],
            [f"{SCHEMA}.jobs.project_id", f"{SCHEMA}.jobs.id"],
            name="stage_results_job_fk",
        ),
        ForeignKeyConstraint(
            ["project_id", "result_artifact_id"],
            [f"{SCHEMA}.artifacts.project_id", f"{SCHEMA}.artifacts.id"],
            name="stage_results_artifact_fk",
        ),
    )

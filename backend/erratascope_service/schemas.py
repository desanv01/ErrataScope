"""Typed API request/response models (OpenAPI-visible)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(StrictModel):
    field: str | None = None
    message: str


class ErrorBody(StrictModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorEnvelope(StrictModel):
    error: ErrorBody
    request_id: str


class ProjectCreate(StrictModel):
    name: StrictStr = Field(min_length=1, max_length=120)


class ProjectOut(StrictModel):
    id: uuid.UUID
    name: str
    created_by: uuid.UUID
    created_at: str
    role: str


class MembershipCreate(StrictModel):
    actor_id: uuid.UUID
    role: Literal["owner", "editor", "reviewer", "viewer"]


class MembershipRoleUpdate(StrictModel):
    role: Literal["owner", "editor", "reviewer", "viewer"]


class MembershipOut(StrictModel):
    project_id: uuid.UUID
    actor_id: uuid.UUID
    role: str
    created_at: str


class ArtifactOut(StrictModel):
    id: uuid.UUID
    project_id: uuid.UUID
    sha256: str
    byte_length: int
    media_type: str
    original_name: str | None
    state: str
    created_at: str


class BundleOut(StrictModel):
    id: uuid.UUID
    project_id: uuid.UUID
    input_hash: str
    schema_version: int
    evaluator_version: str
    payload: dict[str, Any]
    created_at: str


class ReviewItemCreate(StrictModel):
    artifact_id: uuid.UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    annotation: StrictStr = Field(min_length=1, max_length=4000)


class ReviewItemOut(StrictModel):
    id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: uuid.UUID
    content_hash: str
    annotation: str
    current_revision: int
    created_by: uuid.UUID
    created_at: str


class ReviewEventOut(StrictModel):
    id: uuid.UUID
    review_item_id: uuid.UUID
    revision: int
    actor_id: uuid.UUID
    decision: str
    rationale: str
    created_at: str


class ProjectPage(StrictModel):
    items: list[ProjectOut]
    next_cursor: str | None


class MembershipPage(StrictModel):
    items: list[MembershipOut]
    next_cursor: str | None


class ArtifactPage(StrictModel):
    items: list[ArtifactOut]
    next_cursor: str | None


class BundlePage(StrictModel):
    items: list[BundleOut]
    next_cursor: str | None


class JobEventPage(StrictModel):
    items: list["JobEventOut"]
    next_cursor: int | None


class ReviewEventPage(StrictModel):
    items: list[ReviewEventOut]
    next_cursor: int | None


class ReviewDecisionCreate(StrictModel):
    decision: Literal["accepted", "rejected"]
    rationale: StrictStr = Field(min_length=1, max_length=4000)
    expected_revision: StrictInt = Field(ge=0)


class JobCreate(StrictModel):
    kind: Literal["artifact_digest"] = "artifact_digest"
    artifact_id: uuid.UUID


class JobOut(StrictModel):
    id: uuid.UUID
    project_id: uuid.UUID
    kind: str
    artifact_id: uuid.UUID
    status: str
    attempt_count: int
    max_attempts: int
    result_artifact_id: uuid.UUID | None
    result_sha256: str | None
    error_code: str | None
    created_at: str
    updated_at: str
    status_url: str


class JobEventOut(StrictModel):
    seq: int
    event_type: str
    payload: dict[str, Any]
    created_at: str


class HealthOut(StrictModel):
    status: str
    mode: str
    database: bool
    broker: bool


JobEventPage.model_rebuild()

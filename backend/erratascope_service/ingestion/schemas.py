"""Strict Pydantic contracts for W04 ingestion, drafts, proposals and reviews."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ANCHOR_SCHEMA_VERSION = 1
DRAFT_SCHEMA_VERSION = 1
SECTION_RE = r"^\d+(?:\.\d+)+$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BBox(Strict):
    left: float = Field(ge=0.0, le=1.0)
    top: float = Field(ge=0.0, le=1.0)
    right: float = Field(ge=0.0, le=1.0)
    bottom: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _order(self) -> "BBox":
        if not self.left < self.right or not self.top < self.bottom:
            raise ValueError("invalid bbox ordering")
        return self


class ParserInfo(Strict):
    name: str
    version: str
    mode: str
    notes: str | None = None


class AnchorRecord(Strict):
    anchor_key: str
    document_sha256: str
    source_key: str
    page_index: int = Field(ge=0)
    printed_page_label: str | None = None
    section: str | None = None
    section_title: str | None = None
    block_role: Literal["heading", "section_number", "label", "body", "code", "table_row", "table_header"]
    context_kind: Literal["source_identity", "revision_header", "status_legend", "footnote"] | None = None
    geometry_kind: Literal["located", "synthetic_not_located"] = "located"
    text: str = Field(min_length=1)
    bbox: BBox
    bbox_original: dict[str, Any]
    page_width_pt: float = Field(gt=0)
    page_height_pt: float = Field(gt=0)
    page_rotation: int = Field(ge=0, le=359)
    coordinate_system: str = "top_left_x_right_y_down_normalized"
    parser: ParserInfo


class CoverageRecord(Strict):
    section: str
    title: str | None = None
    status: Literal[
        "discovered", "selected", "supported", "reviewed", "failed", "unsupported", "ambiguous", "missing"
    ]
    page_indexes: list[int]
    anchor_keys: list[str]
    reason: str | None = None
    notes: dict[str, Any] = Field(default_factory=dict)


class CoverageSummary(Strict):
    inventory_complete: bool
    inventory_note: str
    detected_entries: int = Field(ge=0)
    selected_entries: list[str]
    supported_selected: int = Field(ge=0)
    status_counts: dict[str, int]


class IdentityRecord(Strict):
    document_id: str | None
    revision: str | None
    publication_date: str | None
    anchor_key: str


class ParseResult(Strict):
    schema_version: int = Field(ge=1, le=1)
    source_key: str
    document_sha256: str
    page_count: int = Field(ge=1, le=100)
    parser: ParserInfo
    identity: IdentityRecord | None
    inventory: list[dict[str, Any]]
    anchors: list[AnchorRecord] = Field(min_length=1, max_length=10000)
    coverage: list[CoverageRecord]
    coverage_summary: CoverageSummary
    diagnostics: list[dict[str, Any]]


class Claim(Strict):
    field: Literal[
        "source_identity",
        "affected_device",
        "affected_revision",
        "trigger_condition",
        "exception",
        "consequence",
        "workaround_documented",
        "workaround_restriction",
        "unresolved_field",
    ]
    value: str = Field(min_length=1, max_length=4000)
    citations: list[str] = Field(min_length=1, max_length=20)
    status: Literal["supported", "unresolved"] = "supported"


class DraftInterpretation(Strict):
    schema_version: int = Field(ge=1, le=1)
    source_document_id: str | None = None
    source_revision: str | None = None
    claims: list[Claim] = Field(min_length=1, max_length=40)
    unresolved_fields: list[str] = Field(default_factory=list)
    limitations: str = Field(
        default="Draft model interpretation. Not a safety verdict. Requires human source review.",
        max_length=500,
    )

    @model_validator(mode="after")
    def _unresolved(self) -> "DraftInterpretation":
        if "source_document_id" in self.unresolved_fields and self.source_document_id:
            raise ValueError("source_document_id asserted and unresolved")
        if "source_revision" in self.unresolved_fields and self.source_revision:
            raise ValueError("source_revision asserted and unresolved")
        return self


class SourceCreate(Strict):
    artifact_id: uuid.UUID
    document_id: str | None = Field(default=None, max_length=200)
    revision: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    published_at: str | None = Field(default=None, max_length=100)
    predecessor_id: uuid.UUID | None = None
    authority: Literal["manufacturer", "forum", "synthetic"]
    synthetic: bool = False


class ExtractionCreate(Strict):
    selected_entries: list[str] = Field(min_length=1, max_length=20)
    mode: Literal["offline", "live"] = "offline"
    case_kind: Literal["real_source", "synthetic_missing_revision"] | None = None

    @field_validator("selected_entries")
    @classmethod
    def _sections(cls, value: list[str]) -> list[str]:
        import re

        if len(set(value)) != len(value):
            raise ValueError("selected_entries must be unique")
        for item in value:
            if not re.fullmatch(SECTION_RE, item):
                raise ValueError("invalid section identifier")
        return value

    @model_validator(mode="after")
    def _live_case(self) -> "ExtractionCreate":
        if self.mode == "live" and self.case_kind is None:
            raise ValueError("live extraction requires case_kind")
        return self


class EvidenceMapping(Strict):
    path: str = Field(pattern=r"^(target|trigger|exceptions(\.\d+)?|consequence)$")
    anchor_keys: list[str] = Field(min_length=1, max_length=20)


class ProposalCreate(Strict):
    draft_id: uuid.UUID
    entry_id: str = Field(min_length=1, max_length=100)
    target: dict[str, Any]
    trigger: dict[str, Any]
    exceptions: list[dict[str, Any]] = Field(default_factory=list)
    consequence: str = Field(min_length=1, max_length=2000)
    evidence: list[EvidenceMapping] = Field(min_length=1, max_length=50)
    reviewer_rationale: str | None = Field(default=None, max_length=2000)


class ReviewCreate(Strict):
    decision: Literal["accepted", "rejected"]
    rationale: str = Field(min_length=1, max_length=4000)
    expected_revision: int = Field(ge=0)
    expected_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceResponse(Strict):
    id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: uuid.UUID
    document_id: str | None
    revision: str | None
    manufacturer: str | None
    source_url: str | None
    published_at: str | None
    predecessor_id: uuid.UUID | None
    authority: str
    synthetic: bool
    sha256: str
    byte_length: int
    schema_version: int
    content_hash: str
    created_by: uuid.UUID
    created_at: datetime
    retrieval_utc: datetime


class ExtractionResponse(Strict):
    id: uuid.UUID
    project_id: uuid.UUID
    source_id: uuid.UUID
    job_id: uuid.UUID
    mode: str
    case_kind: str | None
    selected_entries: list[str]
    status: str
    diagnostics: list[dict[str, Any]]
    current_stage: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    output_hash: str | None = None
    coverage_summary: dict[str, Any] | None = None
    draft_ids: list[uuid.UUID] = Field(default_factory=list)
    status_url: str | None = None


class DraftResponse(Strict):
    id: uuid.UUID
    project_id: uuid.UUID
    extraction_id: uuid.UUID
    source_id: uuid.UUID
    case_kind: str
    provenance: str
    prompt_version: str
    request_hash: str
    response_hash: str
    draft: dict[str, Any]
    validation: dict[str, Any]
    status: str
    provider_request_id: str | None
    usage: dict[str, Any] | None
    created_at: datetime


class ProposalResponse(Strict):
    id: uuid.UUID
    project_id: uuid.UUID
    draft_id: uuid.UUID
    source_id: uuid.UUID
    extraction_id: uuid.UUID
    entry_id: str
    payload: dict[str, Any]
    content_hash: str
    ineligible_reason: str | None
    reviewer_rationale: str | None
    current_revision: int
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    accepted_rule: dict[str, Any] | None = None

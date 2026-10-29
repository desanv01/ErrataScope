"""Pydantic schemas for source manifests, anchors, coverage, and model drafts.

Schema version 1. These are spike schemas: they are deliberately narrower than
the W02 persistence model and are not an accepted contract.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import (
    ANCHOR_SCHEMA_VERSION,
    BBOX_EPSILON,
    DRAFT_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
)


class ParserInfo(BaseModel):
    """Parser/version provenance recorded on every anchor."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    mode: str = Field(description="e.g. 'words+lines' or 'docling-text-items'")
    notes: str | None = None


class BBox(BaseModel):
    """Normalized bounding box: top-left origin, x right, y down, [0, 1]."""

    model_config = ConfigDict(extra="forbid")

    left: float
    top: float
    right: float
    bottom: float

    @field_validator("left", "top", "right", "bottom")
    @classmethod
    def _in_unit_range(cls, value: float) -> float:
        if not (-BBOX_EPSILON <= value <= 1.0 + BBOX_EPSILON):
            raise ValueError(f"coordinate outside [0,1]: {value}")
        return min(1.0, max(0.0, float(value)))

    @model_validator(mode="after")
    def _ordering(self) -> BBox:
        if not self.left < self.right:
            raise ValueError("left must be < right")
        if not self.top < self.bottom:
            raise ValueError("top must be < bottom")
        return self

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.left, self.top, self.right, self.bottom)


class Anchor(BaseModel):
    """One inspectable, citable span of source text."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = ANCHOR_SCHEMA_VERSION
    anchor_id: str
    document_sha256: str
    source_key: str
    page_index: int = Field(ge=0, description="Zero-based physical page index")
    printed_page_label: str | None = None
    section: str | None = None
    section_title: str | None = None
    block_id: str
    block_role: Literal["heading", "section_number", "label", "body", "code", "table_row", "table_header"]
    context_kind: Literal[
        "source_identity", "revision_header", "status_legend", "footnote"
    ] | None = Field(
        default=None,
        description=(
            "R3 context role: identity/provenance spans, governing revision-column headers, "
            "status legend entries, and material footnotes used in interpretation."
        ),
    )
    geometry_kind: Literal["located", "synthetic_not_located"] = Field(
        default="located",
        description=(
            "located = bbox is parser geometry from a real page; synthetic_not_located = "
            "text-only fixture with no page geometry (bbox is the full synthetic page)."
        ),
    )
    text: str
    bbox: BBox
    bbox_original: dict = Field(
        description="Unmodified parser coordinates plus their unit/origin, for debugging conversion"
    )
    page_width_pt: float = Field(gt=0)
    page_height_pt: float = Field(gt=0)
    page_rotation: int = Field(ge=0, le=359)
    coordinate_system: str = "top_left_x_right_y_down_normalized"
    parser: ParserInfo

    @model_validator(mode="after")
    def _page_consistency(self) -> Anchor:
        if self.page_index < 0:
            raise ValueError("page_index must be >= 0")
        return self


class AnchorDocument(BaseModel):
    """All anchors for one sealed source document."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = ANCHOR_SCHEMA_VERSION
    source_key: str
    document_sha256: str
    page_count: int = Field(ge=1)
    coordinate_system: str = "top_left_x_right_y_down_normalized"
    generated_utc: str
    parsers: list[ParserInfo]
    anchors: list[Anchor]

    @model_validator(mode="after")
    def _unique_ids(self) -> AnchorDocument:
        ids = [a.anchor_id for a in self.anchors]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate anchor_id values")
        for anchor in self.anchors:
            if anchor.document_sha256 != self.document_sha256:
                raise ValueError(f"anchor {anchor.anchor_id} belongs to a different document")
            if anchor.page_index >= self.page_count:
                raise ValueError(f"anchor {anchor.anchor_id} page_index outside page_count")
        return self


class SourceRecord(BaseModel):
    """Public-safe provenance for one retrieved source or synthetic fixture."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = MANIFEST_SCHEMA_VERSION
    source_key: str
    kind: Literal[
        "manufacturer_document",
        "manufacturer_notice",
        "forum_clarification",
        "synthetic_fixture",
    ]
    title: str
    manufacturer: str | None = None
    document_id: str | None = None
    revision: str | None = None
    publication_date: str | None = None
    retrieval_utc: str | None = None
    request_url: str | None = None
    final_url: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    byte_size: int | None = Field(default=None, ge=0)
    sha256: str | None = None
    page_count: int | None = Field(default=None, ge=1)
    artifact_path: str | None = Field(
        default=None, description="Project-relative private path; never a public download"
    )
    redistribution: Literal["unknown", "permitted", "prohibited"] = "unknown"
    redistribution_reference: str | None = None
    authority: str | None = None
    synthetic: bool = False
    notes: list[str] = Field(default_factory=list)


class SourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = MANIFEST_SCHEMA_VERSION
    generated_utc: str
    sources: list[SourceRecord]
    retrieval_attempts: list[dict]
    selection: dict = Field(
        default_factory=dict,
        description="Explicit selected subset; selection is not whole-document coverage",
    )


class CoverageEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    section: str
    section_title: str | None = None
    status: Literal["anchored", "missing", "ambiguous", "unsupported"]
    page_indexes: list[int] = Field(default_factory=list)
    anchor_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    generated_utc: str
    document_sha256: str
    inventory_complete: bool
    inventory_notes: list[str]
    selected_sections: list[str]
    entries: list[CoverageEntry]
    counts: dict


# ---------------------------------------------------------------------------
# Model draft schema (Task 5.4) — a draft, not an accepted interpretation.
# ---------------------------------------------------------------------------
CLAIM_FIELDS = (
    "source_identity",
    "affected_device",
    "affected_revision",
    "trigger_condition",
    "exception",
    "consequence",
    "workaround_documented",
    "workaround_restriction",
    "unresolved_field",
)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal[CLAIM_FIELDS]  # type: ignore[valid-type]
    statement: str = Field(min_length=1, max_length=2000)
    anchor_ids: list[str] = Field(min_length=1)
    status: Literal["supported", "unresolved"] = "supported"

    @field_validator("statement")
    @classmethod
    def _no_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("statement must not be blank")
        return value.strip()


class DraftInterpretation(BaseModel):
    """Structured DRAFT interpretation produced by the model."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = DRAFT_SCHEMA_VERSION
    source_document_id: str | None = None
    source_revision: str | None = None
    claims: list[Claim] = Field(min_length=1)
    unresolved_fields: list[str] = Field(default_factory=list)
    limitations: str = Field(
        default="Draft model interpretation. Not a safety verdict. Requires human source review.",
        max_length=500,
    )

    @model_validator(mode="after")
    def _unresolved_requires_null_values(self) -> DraftInterpretation:
        # Invariant: a field listed unresolved may not also be asserted.
        if "source_revision" in self.unresolved_fields and self.source_revision:
            raise ValueError("source_revision asserted while also listed as unresolved")
        if "source_document_id" in self.unresolved_fields and self.source_document_id:
            raise ValueError("source_document_id asserted while also listed as unresolved")
        return self

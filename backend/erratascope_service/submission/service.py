"""S01 submission context, interpretation review and export service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import services
from ..errors import ApiError
from ..ingestion.models import (
    CoverageEntry,
    Extraction,
    ExtractionOutput,
    ModelDraft,
    SourceAnchor,
    SourceVersion,
)
from .models import InterpretationReview

DECISION_VALUES = ("reviewed", "rejected")
WIRE_HASH_LIMITATION = (
    "The preserved live response artifact is normalized JSON. The recorded response hash "
    "binds the original provider wire bytes; it cannot be re-derived from the normalized "
    "artifact. This limitation is retained rather than presenting a fabricated wire re-verification."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _latest_review(session: Session, draft_id: uuid.UUID) -> InterpretationReview | None:
    return session.scalar(
        select(InterpretationReview)
        .where(InterpretationReview.draft_id == draft_id)
        .order_by(InterpretationReview.revision.desc())
        .limit(1)
    )


def review_body(review: InterpretationReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "draft_id": review.draft_id,
        "revision": review.revision,
        "response_hash": review.response_hash,
        "decision": review.decision,
        "note": review.note,
        "actor_id": review.actor_id,
        "created_at": review.created_at,
    }


def submission_context(session: Session, project_id: uuid.UUID, actor_id: uuid.UUID) -> dict[str, Any]:
    services.membership(session, project_id, actor_id)
    project = session.get(services.Project, project_id)
    cases = []
    sources = list(
        session.scalars(
            select(SourceVersion)
            .where(SourceVersion.project_id == project_id)
            .order_by(SourceVersion.created_at.desc())
        )
    )
    for source in sources:
        extractions = list(
            session.scalars(
                select(Extraction)
                .where(
                    Extraction.project_id == project_id,
                    Extraction.source_id == source.id,
                    Extraction.status == "succeeded",
                )
                .order_by(Extraction.created_at.desc())
            )
        )
        for extraction in extractions:
            output = session.get(ExtractionOutput, extraction.id)
            drafts = list(
                session.scalars(
                    select(ModelDraft)
                    .where(
                        ModelDraft.project_id == project_id,
                        ModelDraft.extraction_id == extraction.id,
                    )
                    .order_by(ModelDraft.created_at.desc())
                )
            )
            for draft in drafts:
                latest_review = _latest_review(session, draft.id)
                recorded_live = (
                    not source.synthetic
                    and draft.status == "validated"
                    and draft.provenance in ("live", "cached")
                )
                synthetic = source.synthetic or draft.provenance in ("mock", "offline")
                kind = "recorded_live" if recorded_live else ("synthetic_offline" if synthetic else "recorded")
                cases.append(
                    {
                        "kind": kind,
                        "label": (
                            "Recorded live Nemotron result"
                            if kind == "recorded_live"
                            else "Synthetic / offline example"
                            if kind == "synthetic_offline"
                            else "Recorded draft"
                        ),
                        "source_id": source.id,
                        "extraction_id": extraction.id,
                        "draft_id": draft.id,
                        "document_id": source.document_id,
                        "revision": source.revision,
                        "manufacturer": source.manufacturer,
                        "source_url": source.source_url,
                        "source_sha256": source.sha256,
                        "authority": source.authority,
                        "synthetic": source.synthetic,
                        "selected_entries": extraction.selected_entries,
                        "draft_status": draft.status,
                        "draft_provenance": draft.provenance,
                        "prompt_version": draft.prompt_version,
                        "provider_request_id": draft.provider_request_id,
                        "usage": draft.usage,
                        "coverage_summary": output.coverage_summary if output else None,
                        "review": review_body(latest_review) if latest_review else None,
                        "current_revision": latest_review.revision if latest_review else 0,
                    }
                )
    cases.sort(key=lambda item: (item["kind"] != "recorded_live", item["label"]))
    return {
        "project_id": project_id,
        "project_name": project.name if project else None,
        "cases": cases,
        "default_case": cases[0] if cases else None,
        "development_auth": True,
        "provenance_note": WIRE_HASH_LIMITATION,
    }


def record_review(
    session: Session,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    draft_id: uuid.UUID,
    *,
    expected_revision: int,
    expected_response_hash: str,
    decision: str,
    note: str,
) -> InterpretationReview:
    services.require_role(session, project_id, actor_id, ("owner", "reviewer"))
    if decision not in DECISION_VALUES:
        raise ApiError(422, "INVALID_DECISION", "decision must be reviewed or rejected")
    trimmed = note.strip()
    if not 1 <= len(trimmed) <= 2000:
        raise ApiError(422, "INVALID_NOTE", "note must be 1-2000 characters")
    draft = session.scalar(
        select(ModelDraft)
        .where(ModelDraft.project_id == project_id, ModelDraft.id == draft_id)
        .with_for_update()
    )
    if draft is None:
        raise ApiError(404, "DRAFT_NOT_FOUND", "draft not found")
    if expected_response_hash != draft.response_hash:
        raise ApiError(409, "RESPONSE_HASH_CONFLICT", "draft response hash has changed")
    current_revision = session.scalar(
        select(func.max(InterpretationReview.revision)).where(
            InterpretationReview.draft_id == draft_id
        )
    ) or 0
    if expected_revision != current_revision:
        raise ApiError(409, "REVIEW_REVISION_CONFLICT", "interpretation review revision has changed")
    review = InterpretationReview(
        id=uuid.uuid4(),
        project_id=project_id,
        draft_id=draft_id,
        revision=current_revision + 1,
        response_hash=draft.response_hash,
        decision=decision,
        note=trimmed,
        actor_id=actor_id,
        created_at=_utcnow(),
    )
    session.add(review)
    # The route commits this row and its idempotency receipt together.
    session.flush()
    return review


def list_reviews(
    session: Session, project_id: uuid.UUID, draft_id: uuid.UUID, *, limit: int, after_revision: int
) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(InterpretationReview)
            .where(
                InterpretationReview.project_id == project_id,
                InterpretationReview.draft_id == draft_id,
                InterpretationReview.revision > after_revision,
            )
            .order_by(InterpretationReview.revision)
            .limit(limit + 1)
        )
    )
    items = rows[:limit]
    current = session.scalar(
        select(func.max(InterpretationReview.revision)).where(
            InterpretationReview.draft_id == draft_id
        )
    ) or 0
    return {
        "items": [review_body(row) for row in items],
        "next_cursor": str(items[-1].revision) if len(rows) > limit else None,
        "current_revision": current,
    }


def _draft_summary(session: Session, draft: ModelDraft) -> dict[str, Any]:
    extraction = session.get(Extraction, draft.extraction_id)
    source = session.get(SourceVersion, draft.source_id)
    output = session.get(ExtractionOutput, draft.extraction_id)
    anchors = {
        row.anchor_key: row
        for row in session.scalars(
            select(SourceAnchor).where(SourceAnchor.extraction_id == draft.extraction_id)
        )
    }
    coverage_rows = list(
        session.scalars(
            select(CoverageEntry).where(CoverageEntry.extraction_id == draft.extraction_id)
        )
    )
    reviews = list(
        session.scalars(
            select(InterpretationReview)
            .where(InterpretationReview.draft_id == draft.id)
            .order_by(InterpretationReview.revision)
        )
    )
    claims = []
    for claim in draft.draft.get("claims", []):
        citations = []
        for key in claim.get("citations", []):
            anchor = anchors.get(key)
            if anchor is None:
                citations.append({"anchor_key": key, "missing": True})
                continue
            citations.append(
                {
                    "anchor_key": key,
                    "text": anchor.anchor_text,
                    "page_index": anchor.page_index,
                    "physical_page": anchor.page_index + 1 if anchor.geometry_kind == "located" else None,
                    "printed_page_label": anchor.printed_page_label,
                    "section": anchor.section,
                    "section_title": anchor.section_title,
                    "block_role": anchor.block_role,
                    "context_kind": anchor.context_kind,
                    "geometry_kind": anchor.geometry_kind,
                    "bbox": anchor.bbox,
                }
            )
        claims.append(
            {
                "field": claim.get("field"),
                "value": claim.get("value"),
                "status": claim.get("status"),
                "citations": citations,
            }
        )
    coverage_counts: dict[str, int] = {}
    for row in coverage_rows:
        coverage_counts[row.status] = coverage_counts.get(row.status, 0) + 1
    recorded_live = (
        not source.synthetic
        and draft.status == "validated"
        and draft.provenance in ("live", "cached")
    )
    synthetic = source.synthetic or draft.provenance in ("mock", "offline")
    return {
        "source": {
            "id": source.id,
            "document_id": source.document_id,
            "revision": source.revision,
            "manufacturer": source.manufacturer,
            "source_url": source.source_url,
            "published_at": source.published_at,
            "authority": source.authority,
            "synthetic": source.synthetic,
            "sha256": source.sha256,
            "byte_length": source.byte_length,
            "content_hash": source.content_hash,
        },
        "extraction": {
            "id": extraction.id,
            "status": extraction.status,
            "mode": extraction.mode,
            "case_kind": extraction.case_kind,
            "selected_entries": extraction.selected_entries,
            "coverage_summary": output.coverage_summary if output else None,
        },
        "draft": {
            "id": draft.id,
            "case_kind": draft.case_kind,
            "provenance": draft.provenance,
            "recorded_label": (
                "Recorded live Nemotron result"
                if recorded_live
                else "Synthetic / offline example"
                if synthetic
                else "Recorded draft"
            ),
            "model": "nvidia/Nemotron-3.5-Super-VL" if recorded_live else None,
            "provider": "Nebius Token Factory" if recorded_live else None,
            "prompt_version": draft.prompt_version,
            "request_hash": draft.request_hash,
            "response_hash": draft.response_hash,
            "provider_request_id": draft.provider_request_id,
            "usage": draft.usage,
            "status": draft.status,
            "created_at": draft.created_at,
            "wire_hash_limitation": WIRE_HASH_LIMITATION if recorded_live else None,
        },
        "claims": claims,
        "unresolved_fields": draft.draft.get("unresolved_fields", []),
        "limitations": draft.draft.get("limitations"),
        "coverage": {
            "selected_entries": extraction.selected_entries,
            "status_counts": coverage_counts,
            "inventory_complete": False,
            "selected_entries_supported": [
                row.section for row in coverage_rows if row.status == "supported"
            ],
        },
        "review": {
            "latest": review_body(reviews[-1]) if reviews else None,
            "history": [review_body(row) for row in reviews],
            "current_revision": reviews[-1].revision if reviews else 0,
        },
        "known_limitations": [
            "Selected entries only; document inventory is not complete.",
            "A reviewed interpretation is human acknowledgement, not an accepted executable rule.",
            "No applicability assessment, fact editing or VerifForge execution is included.",
            "Historical wire-byte hashes cannot be re-derived from normalized response artifacts."
            if recorded_live
            else "Synthetic/offline data is not a manufacturer-source live result.",
        ],
        "generated_utc": _utcnow().isoformat(),
    }


def review_summary(
    session: Session, project_id: uuid.UUID, draft_id: uuid.UUID
) -> dict[str, Any]:
    draft = session.get(ModelDraft, draft_id)
    if draft is None or draft.project_id != project_id:
        raise ApiError(404, "DRAFT_NOT_FOUND", "draft not found")
    return _draft_summary(session, draft)


def summary_markdown(summary: dict[str, Any]) -> str:
    source = summary["source"]
    draft = summary["draft"]
    lines = [
        "# ErrataScope interpretation review summary",
        "",
        f"- Document: {source['document_id'] or 'unknown'} {source['revision'] or ''}".rstrip(),
        f"- Manufacturer: {source['manufacturer'] or 'unknown'}",
        f"- Source URL: {source['source_url'] or 'not recorded'}",
        f"- Source SHA-256: `{source['sha256']}`",
        f"- Source authority: {source['authority']}",
        f"- Provenance: **{draft['recorded_label']}**",
        f"- Prompt version: `{draft['prompt_version']}`",
        f"- Response hash: `{draft['response_hash']}`",
        f"- Provider request ID: {draft['provider_request_id'] or 'not recorded'}",
        f"- Model: {draft['model'] or 'not applicable'}",
        f"- Selected coverage: {', '.join(summary['coverage']['selected_entries'])}",
        f"- Inventory complete: {summary['coverage']['inventory_complete']}",
        "",
        "## Interpretation",
        "",
    ]
    if draft.get("wire_hash_limitation"):
        lines.extend([f"> Provenance limitation: {draft['wire_hash_limitation']}", ""])
    for index, claim in enumerate(summary["claims"], 1):
        lines.append(f"### {index}. {claim['field']} ({claim['status']})")
        lines.append("")
        lines.append(claim["value"])
        lines.append("")
        for citation in claim["citations"]:
            if citation.get("missing"):
                lines.append(f"- Missing anchor: `{citation['anchor_key']}`")
            else:
                location = (
                    "synthetic excerpt (no PDF location)"
                    if citation["geometry_kind"] == "synthetic_not_located"
                    else f"page {citation['physical_page']} (printed {citation['printed_page_label'] or 'n/a'})"
                )
                lines.append(
                    f"- `{citation['anchor_key']}` — {location}, "
                    f"{citation['section'] or 'context'}; {citation['text'][:220]}"
                )
        lines.append("")
    lines.extend(
        [
            "## Unresolved fields",
            "",
            ", ".join(summary["unresolved_fields"]) or "None listed",
            "",
            "## Review history",
            "",
        ]
    )
    for review in summary["review"]["history"]:
        lines.append(
            f"- Revision {review['revision']}: **{review['decision']}** by {review['actor_id']} "
            f"at {review['created_at']} — {review['note']}"
        )
    if not summary["review"]["history"]:
        lines.append("- No interpretation review recorded.")
    lines.extend(
        [
            "",
            "## Known limitations",
            "",
            *[f"- {item}" for item in summary["known_limitations"]],
            "",
            "A reviewed interpretation is not an accepted executable rule.",
            "",
        ]
    )
    return "\n".join(lines)

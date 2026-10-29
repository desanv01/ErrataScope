"""Runnable provider cases with case-bound identity and expectations (repair R3/R4).

Two cases exist and are selected explicitly on the command line:

* ``real_source`` — bounded ES0620 anchors with citable identity/revision context.
* ``synthetic_missing_revision`` — a synthetic excerpt with no document identity or
  revision; the draft must leave those unresolved instead of inventing them.

Payload identity is read from the sealed manifest, never from literals.
"""

from __future__ import annotations

import hashlib
import json
import re

from . import config
from .util import sha256_bytes, utc_now_iso

PROMPT_VERSION = "draft-v4-grounded-no-thinking"
REVISION_TOKEN_RE = re.compile(r"\bRev(?:ision)?\.?\s*[A-Z0-9]\b")
DOC_ID_RE = re.compile(r"\b[A-Z]{2,5}\d{3,5}\b")


def anchors_fingerprint(anchors) -> str:
    """Stable fingerprint of the pinned case inputs (IDs, document, text)."""
    payload = [
        {
            "anchor_id": anchor.anchor_id,
            "document_sha256": anchor.document_sha256,
            "text": anchor.text,
        }
        for anchor in anchors
    ]
    payload.sort(key=lambda item: item["anchor_id"])
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class CaseError(RuntimeError):
    """Case inputs are missing or inconsistent with the sealed evidence."""


def source_identity_from_manifest(manifest: dict) -> dict:
    """Build the expected identity from the sealed source record (no literals)."""
    record = next(
        (source for source in manifest.get("sources", []) if source.get("source_key") == config.ST_ERRATA["source_key"]),
        None,
    )
    if record is None:
        raise CaseError("ST source record is missing from the sealed manifest")
    if not record.get("document_id") or not record.get("revision"):
        raise CaseError("Sealed source record lacks a document ID or revision; identity is unknown")
    return {
        "source_key": record["source_key"],
        "document_id": record["document_id"],
        "revision": record["revision"],
        "publication_date": record.get("publication_date"),
        "manufacturer": record.get("manufacturer"),
        "sha256": record.get("sha256"),
        "page_count": record.get("page_count"),
        "title": record.get("title"),
    }


def _anchor_line(anchor) -> str:
    kind = anchor.context_kind or anchor.block_role
    return f"[{anchor.anchor_id}] ({kind}, page_index={anchor.page_index}) {anchor.text}"


def _matrix_lines(matrix: dict, anchors_document) -> list[str]:
    by_section: dict[str, list[str]] = {}
    for anchor in anchors_document.anchors:
        by_section.setdefault(anchor.section or "", []).append(anchor.anchor_id)
    lines = []
    for section, row in matrix.items():
        statuses = row.get("status_by_revision") or {}
        ordered = ", ".join(f"Rev. {letter}={statuses[letter]}" for letter in ("Z", "B", "X") if letter in statuses)
        row_anchor = f"{config.ST_ERRATA['source_key']}:p{row['page_index']:02d}:row-{section.replace('.', '-')}"
        headers = [
            anchor.anchor_id
            for anchor in anchors_document.anchors
            if anchor.context_kind == "revision_header" and anchor.page_index == row["page_index"]
        ]
        lines.append(
            f"- {section}: {ordered} "
            f"(row anchor {row_anchor}; governing header anchors: {', '.join(headers) or 'none'})"
        )
    return lines


def build_real_source_payload(anchors_document, coverage: dict, matrix: dict, identity: dict) -> dict:
    """Text-only payload for the real-source case."""
    anchors = anchors_document.anchors
    identity_anchors = [a for a in anchors if a.context_kind == "source_identity"]
    header_anchors = [a for a in anchors if a.context_kind == "revision_header"]
    legend_anchors = [a for a in anchors if a.context_kind == "status_legend"]
    footnote_anchors = [a for a in anchors if a.context_kind == "footnote"]
    section_anchors = [
        a
        for a in anchors
        if a.section in config.SELECTED_SECTIONS and a.context_kind is None
    ]
    if not identity_anchors:
        raise CaseError("No source-identity anchor available; refusing to build an uncited payload")

    lines: list[str] = []
    for section in config.SELECTED_SECTIONS:
        lines.append(f"## Section {section}")
        for anchor in section_anchors:
            if anchor.section == section:
                lines.append(_anchor_line(anchor))

    context_lines = ["## Citable source identity and interpretation context"]
    for anchor in identity_anchors:
        context_lines.append(_anchor_line(anchor))
    for anchor in header_anchors:
        context_lines.append(_anchor_line(anchor))
    for anchor in legend_anchors:
        context_lines.append(_anchor_line(anchor))
    for anchor in footnote_anchors:
        context_lines.append(_anchor_line(anchor))

    identity_block = {
        "document_id": identity["document_id"],
        "revision": identity["revision"],
        "publication_date": identity["publication_date"],
        "manufacturer": identity["manufacturer"],
        "sha256": identity["sha256"],
        "page_count": identity["page_count"],
        "identity_anchor_ids": [anchor.anchor_id for anchor in identity_anchors],
    }

    user_text = _load_prompt("draft_v2_user.md")
    for token, value in (
        ("<<DOCUMENT_IDENTITY>>", _json(identity_block)),
        ("<<CONTEXT_ANCHORS>>", "\n".join(context_lines)),
        ("<<REVISION_MATRIX>>", "\n".join(_matrix_lines(matrix, anchors_document)) or "- unavailable"),
        ("<<ANCHORS>>", "\n".join(lines)),
        ("<<SCHEMA>>", _load_prompt("draft_v4_schema.md").strip()),
    ):
        user_text = user_text.replace(token, value)

    return _payload(user_text, case="real_source", prompt_version=PROMPT_VERSION)


def _json(value) -> str:
    import json

    return json.dumps(value, indent=2, ensure_ascii=False)


def _load_prompt(name: str) -> str:
    path = config.PROMPT_DIR / name
    if not path.exists():
        raise CaseError(f"prompt file missing: {name}")
    return path.read_text(encoding="utf-8")


def _payload(user_text: str, *, case: str, prompt_version: str) -> dict:
    system_text = _load_prompt("draft_v4_system.md")
    return {
        "model": config.PROVIDER["model_id"],
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": config.BUDGET["max_output_tokens_per_request"],
        "temperature": 0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "case": case,
        "prompt_metadata": {
            "prompt_version": prompt_version,
            "case": case,
            "response_format": None,
            "note": (
                "Strict JSON mode was not confirmed in the accessible public documentation; "
                "the adapter parses and validates JSON server-side instead."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Synthetic missing-revision case
# ---------------------------------------------------------------------------
SYNTHETIC_FIXTURE = config.FIXTURE_DIR / "synthetic" / "SYNTHETIC_missing_revision.md"


def build_synthetic_anchors() -> tuple[dict, list]:
    """Build text-only synthetic anchors from the labeled fixture.

    There is no page geometry for a hand-authored excerpt, so anchors are marked
    ``synthetic_not_located`` with a full-page placeholder box; the text itself is
    the fixture's exact bytes.
    """
    if not SYNTHETIC_FIXTURE.exists():
        raise CaseError("synthetic missing-revision fixture is missing")
    data = SYNTHETIC_FIXTURE.read_bytes()
    text = data.decode("utf-8")
    digest = sha256_bytes(data)
    paragraphs = [block.strip() for block in text.split("\n\n") if block.strip()]
    anchors = []
    for index, block in enumerate(paragraphs):
        anchors.append(
            {
                "anchor_id": f"synthetic-missing-revision:p00:{index:03d}",
                "document_sha256": digest,
                "source_key": "synthetic-missing-revision",
                "page_index": 0,
                "printed_page_label": None,
                "section": None,
                "section_title": None,
                "block_id": "synthetic-missing-revision:p00",
                "block_role": "body",
                "context_kind": None,
                "geometry_kind": "synthetic_not_located",
                "text": block,
                "bbox": {"left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0},
                "bbox_original": {
                    "unit": "none",
                    "origin": "synthetic",
                    "note": "Hand-authored excerpt has no page geometry; no span was located.",
                },
                "page_width_pt": 1.0,
                "page_height_pt": 1.0,
                "page_rotation": 0,
                "coordinate_system": "top_left_x_right_y_down_normalized",
                "parser": {
                    "name": "synthetic-fixture",
                    "version": "1",
                    "mode": "paragraph-split",
                    "notes": "SYNTHETIC fixture text; not a manufacturer document.",
                },
            }
        )
    document = {
        "schema_version": config.ANCHOR_SCHEMA_VERSION,
        "source_key": "synthetic-missing-revision",
        "document_sha256": digest,
        "page_count": 1,
        "coordinate_system": "top_left_x_right_y_down_normalized",
        "generated_utc": utc_now_iso(),
        "parsers": [
            {
                "name": "synthetic-fixture",
                "version": "1",
                "mode": "paragraph-split",
                "notes": "SYNTHETIC fixture; no manufacturer authority.",
            }
        ],
        "anchors": anchors,
    }
    from .schemas import AnchorDocument

    validated = AnchorDocument(**document)
    return validated.model_dump(mode="json"), validated.anchors


def build_synthetic_payload(anchors: list[dict]) -> dict:
    body_lines = [f"[{anchor['anchor_id']}] {anchor['text']}" for anchor in anchors]
    user_text = _load_prompt("synthetic_missing_user.md")
    for token, value in (
        ("<<EXCERPT>>", "\n".join(body_lines)),
        ("<<SCHEMA>>", _load_prompt("draft_v4_schema.md").strip()),
    ):
        user_text = user_text.replace(token, value)
    return _payload(user_text, case="synthetic_missing_revision", prompt_version=PROMPT_VERSION)


def evaluate_missing_information(draft) -> dict:
    """Structural expectation for the omission case.

    The output passes only when identity/revision stay null and are recorded as
    unresolved, and no claim asserts a concrete revision token.
    """
    problems: list[str] = []
    if draft.source_revision:
        problems.append(f"asserted source_revision {draft.source_revision!r}")
    if draft.source_document_id:
        problems.append(f"asserted source_document_id {draft.source_document_id!r}")
    unresolved = set(draft.unresolved_fields)
    if not unresolved & {"source_revision", "source_document_id", "affected_revision"}:
        problems.append("no revision/identity field recorded as unresolved")
    for claim in draft.claims:
        if claim.field == "affected_revision" and claim.status == "supported":
            problems.append("affected_revision claim marked supported without revision evidence")
        match = REVISION_TOKEN_RE.search(claim.statement)
        if match:
            problems.append(f"claim '{claim.field}' asserts revision token {match.group(0)!r}")
    return {
        "status": "pass" if not problems else "fail",
        "problems": problems,
        "expectation": "identity and revision remain unresolved; no invented revision",
    }


def expected_identity_for(case: str, identity: dict | None, synthetic_doc_sha: str | None) -> dict:
    if case == "real_source":
        if not identity:
            raise CaseError("real-source case requires the sealed source identity")
        return {
            "document_id": identity["document_id"],
            "revision": identity["revision"],
            "sha256": identity["sha256"],
        }
    if case == "synthetic_missing_revision":
        return {"document_id": None, "revision": None, "sha256": synthetic_doc_sha}
    raise CaseError(f"unknown case {case!r}")

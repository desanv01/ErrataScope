"""Citable source-identity and interpretation-context anchors (repair R3).

The model must be able to cite the document identity, the governing revision
columns, the status legend, and material footnotes instead of receiving them
only as uncited prompt text. These anchors are located with pdfplumber word
geometry on the real pages, so their boxes remain inspectable.
"""

from __future__ import annotations

import re

from .extract_pdfplumber import page_lines, page_words, pdfplumber_version

IDENTITY_RE = re.compile(r"(ES\d{4})\s*-\s*(Rev\s*\d+)\s*-\s*([A-Z][a-z]+\s+\d{4})")
LEGEND_RE = re.compile(r"^([ANP-])\s+(Limitation\b.+)$")
REVISION_LETTERS = ("Z", "B", "X")


def _norm(bbox_pt, width: float, height: float) -> dict:
    left, top, right, bottom = bbox_pt
    return {
        "left": max(0.0, min(1.0, left / width)),
        "top": max(0.0, min(1.0, top / height)),
        "right": max(0.0, min(1.0, right / width)),
        "bottom": max(0.0, min(1.0, bottom / height)),
    }


def _base_anchor(
    *,
    source_key: str,
    document_sha256: str,
    page_index: int,
    printed_label: str | None,
    block_role: str,
    context_kind: str,
    text: str,
    bbox_pt,
    page_width: float,
    page_height: float,
    rotation: int,
    anchor_id: str,
    origin_note: str,
) -> dict:
    return {
        "anchor_id": anchor_id,
        "document_sha256": document_sha256,
        "source_key": source_key,
        "page_index": page_index,
        "printed_page_label": printed_label,
        "section": None,
        "section_title": None,
        "block_id": f"{source_key}:p{page_index:02d}:context",
        "block_role": block_role,
        "context_kind": context_kind,
        "geometry_kind": "located",
        "text": text,
        "bbox": _norm(bbox_pt, page_width, page_height),
        "bbox_original": {
            "unit": "pdf_points",
            "origin": "top_left_y_down",
            "left": bbox_pt[0],
            "top": bbox_pt[1],
            "right": bbox_pt[2],
            "bottom": bbox_pt[3],
            "note": origin_note,
        },
        "page_width_pt": page_width,
        "page_height_pt": page_height,
        "page_rotation": rotation,
        "coordinate_system": "top_left_x_right_y_down_normalized",
        "parser": {
            "name": "pdfplumber",
            "version": pdfplumber_version(),
            "mode": "word-geometry-context",
            "notes": "Recorded fallback geometry for context spans; Docling remains primary for prose.",
        },
    }


def _find_identity_line(pdf, max_pages: int = 4):
    for page_index in range(min(max_pages, len(pdf.pages))):
        page = pdf.pages[page_index]
        for line in page_lines(page):
            if IDENTITY_RE.search(line.text):
                return page_index, page, line
    return None, None, None


def _revision_header_anchors(pdf, summary_page_index: int) -> list[tuple[str, str, list[float], float, float, int]]:
    """Locate 'Rev. Z/B/X' header cells and return id/text/bbox per column."""
    page = pdf.pages[summary_page_index]
    words = page_words(page)
    width, height = float(page.width), float(page.height)
    rotation = int(page.rotation or 0)
    results = []
    for rev_word in [w for w in words if w["text"] == "Rev."]:
        candidates = [
            w
            for w in words
            if w["text"] in REVISION_LETTERS
            and 0 <= (w["top"] - rev_word["bottom"]) <= 14
            and abs(((w["x0"] + w["x1"]) / 2) - ((rev_word["x0"] + rev_word["x1"]) / 2)) < 12
        ]
        if not candidates:
            continue
        letter = min(candidates, key=lambda w: abs(w["top"] - rev_word["bottom"]))
        left = min(rev_word["x0"], letter["x0"])
        right = max(rev_word["x1"], letter["x1"])
        top = rev_word["top"]
        bottom = letter["bottom"]
        results.append(
            (
                f"rev-{letter['text']}",
                f"Rev. {letter['text']}",
                [left, top, right, bottom],
                width,
                height,
                rotation,
            )
        )
    return results


def build_context_anchors(
    pdf,
    *,
    source_key: str,
    document_sha256: str,
    printed_labels: dict[int, str | None],
    summary_page_indexes: list[int],
    generated_utc: str | None = None,
) -> list[dict]:
    """Build identity/header/legend/footnote anchors from the real pages."""
    anchors: list[dict] = []

    identity_page, identity_pdf_page, identity_line = _find_identity_line(pdf)
    if identity_line is not None:
        width, height = float(identity_pdf_page.width), float(identity_pdf_page.height)
        anchors.append(
            _base_anchor(
                source_key=source_key,
                document_sha256=document_sha256,
                page_index=identity_page,
                printed_label=printed_labels.get(identity_page),
                block_role="body",
                context_kind="source_identity",
                text=identity_line.text,
                bbox_pt=[identity_line.x0, identity_line.top, identity_line.x1, identity_line.bottom],
                page_width=width,
                page_height=height,
                rotation=int(identity_pdf_page.rotation or 0),
                anchor_id=f"{source_key}:p{identity_page:02d}:ctx-identity",
                origin_note="Footer identity line; text captured from the PDF text layer.",
            )
        )

    for page_index in summary_page_indexes:
        page = pdf.pages[page_index]
        width, height = float(page.width), float(page.height)
        rotation = int(page.rotation or 0)
        for slug, text, bbox_pt, width, height, rotation in _revision_header_anchors(pdf, page_index):
            anchors.append(
                _base_anchor(
                    source_key=source_key,
                    document_sha256=document_sha256,
                    page_index=page_index,
                    printed_label=printed_labels.get(page_index),
                    block_role="table_header",
                    context_kind="revision_header",
                    text=text,
                    bbox_pt=bbox_pt,
                    page_width=width,
                    page_height=height,
                    rotation=rotation,
                    anchor_id=f"{source_key}:p{page_index:02d}:ctx-{slug}",
                    origin_note="Union of the 'Rev.' header cell and its revision letter.",
                )
            )
        for line in page_lines(page):
            match = LEGEND_RE.match(line.text)
            if not match:
                continue
            token = match.group(1)
            anchors.append(
                _base_anchor(
                    source_key=source_key,
                    document_sha256=document_sha256,
                    page_index=page_index,
                    printed_label=printed_labels.get(page_index),
                    block_role="body",
                    context_kind="status_legend",
                    text=line.text,
                    bbox_pt=[line.x0, line.top, line.x1, line.bottom],
                    page_width=width,
                    page_height=height,
                    rotation=rotation,
                    anchor_id=f"{source_key}:p{page_index:02d}:ctx-legend-{token}",
                    origin_note="Status legend row: token plus its definition.",
                )
            )

    if len(pdf.pages) > 0:
        page = pdf.pages[0]
        width, height = float(page.width), float(page.height)
        rotation = int(page.rotation or 0)
        for line in page_lines(page):
            lowered = line.text.lower()
            if "refer to the device datasheet" in lowered:
                slug = "footnote-datasheet"
            elif "rev_id" in lowered and "bitfield" in lowered:
                slug = "footnote-rev-id"
            else:
                continue
            anchors.append(
                _base_anchor(
                    source_key=source_key,
                    document_sha256=document_sha256,
                    page_index=0,
                    printed_label=printed_labels.get(0),
                    block_role="body",
                    context_kind="footnote",
                    text=line.text,
                    bbox_pt=[line.x0, line.top, line.x1, line.bottom],
                    page_width=width,
                    page_height=height,
                    rotation=rotation,
                    anchor_id=f"{source_key}:p00:ctx-{slug}",
                    origin_note="Device-variant table footnote used for revision identification.",
                )
            )

    return anchors

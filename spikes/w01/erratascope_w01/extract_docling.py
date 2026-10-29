"""Docling extraction of paragraph-level anchors from bounded source pages.

Docling is the preferred parser for prose sections. Its bounding boxes use a
bottom-left origin with y increasing upward, in PDF points; this module converts
them to the spike convention (top-left origin, x right, y down, normalized).

Docling is optional: when it cannot be imported or executed the caller records
the limitation and falls back to pdfplumber line anchors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SECTION_HEADER_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(\S.*)$")
LABEL_WORDS = {"Description", "Workaround", "Note", "Notes", "Introduction"}


@dataclass
class DoclingItem:
    label: str
    text: str
    page_no: int
    left: float
    top: float
    right: float
    bottom: float


def docling_version() -> str:
    try:
        import docling

        return getattr(docling, "__version__", "unknown")
    except Exception:  # pragma: no cover - import failure is reported by caller
        return "unavailable"


def convert_pages(pdf_path: str, page_numbers_1based: list[int]) -> tuple[Any, list[DoclingItem]]:
    """Convert specific 1-based pages and return items in reading order."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = False
    options.do_table_structure = True
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    pages = sorted(set(page_numbers_1based))
    document = converter.convert(pdf_path, page_range=(pages[0], pages[-1])).document

    items: list[DoclingItem] = []
    for item, _level in document.iterate_items():
        prov = getattr(item, "prov", None) or []
        if not prov:
            continue
        bbox = getattr(prov[0], "bbox", None)
        page_no = getattr(prov[0], "page_no", None)
        if bbox is None or page_no is None or page_no not in pages:
            continue
        items.append(
            DoclingItem(
                label=str(getattr(item, "label", "")),
                text=(getattr(item, "text", "") or "").strip(),
                page_no=int(page_no),
                left=float(bbox.l),
                top=float(bbox.t),
                right=float(bbox.r),
                bottom=float(bbox.b),
            )
        )
    return document, items


def page_sizes(document: Any) -> dict[int, tuple[float, float]]:
    return {
        int(no): (float(page.size.width), float(page.size.height))
        for no, page in document.pages.items()
    }


def item_to_normalized(item: DoclingItem, page_size: tuple[float, float]) -> dict:
    """Convert a bottom-left-origin bbox to normalized top-left coordinates."""
    width, height = page_size
    left = max(0.0, min(1.0, item.left / width))
    right = max(0.0, min(1.0, item.right / width))
    bottom = max(0.0, min(1.0, 1.0 - (item.bottom / height)))
    top = max(0.0, min(1.0, 1.0 - (item.top / height)))
    if right <= left:
        right = min(1.0, left + 1e-6)
    if bottom <= top:
        bottom = min(1.0, top + 1e-6)
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "bbox_original": {
            "unit": "pdf_points",
            "origin": "bottom_left_y_up",
            "left": item.left,
            "bottom": item.bottom,
            "right": item.right,
            "top": item.top,
        },
    }


def section_anchors(
    items: list[DoclingItem],
    page_sizes: dict[int, tuple[float, float]],
    source_key: str,
    document_sha256: str,
    printed_labels: dict[int, str | None],
    page_index_offset: int = 1,
) -> list[dict]:
    """Turn Docling items into anchor dicts with section attribution.

    `page_index_offset` converts 1-based Docling page numbers to the zero-based
    physical page indexes recorded in anchors.
    """
    anchors: list[dict] = []
    current_section: str | None = None
    current_title: str | None = None
    ordinals: dict[int, int] = {}

    for item in items:
        text = item.text
        if not text:
            continue
        role = "body"
        section = current_section
        title = current_title

        is_numbered_heading = item.label == "section_header" and SECTION_HEADER_RE.match(text)
        if is_numbered_heading:
            match = SECTION_HEADER_RE.match(text)
            assert match is not None
            section, title = match.group(1), match.group(2).strip()
            current_section, current_title = section, title
            role = "heading"
        elif item.label == "section_header":
            role = "label" if text.strip(":") in LABEL_WORDS else "heading"
        elif item.label == "list_item":
            role = "body"
        elif item.label == "code":
            role = "code"

        page_index = item.page_no - page_index_offset
        page_size = page_sizes[item.page_no]
        normalized = item_to_normalized(item, page_size)
        ordinal = ordinals.get(page_index, 0)
        ordinals[page_index] = ordinal + 1
        anchors.append(
            {
                "anchor_id": f"{source_key}:p{page_index:02d}:{ordinal:03d}",
                "document_sha256": document_sha256,
                "source_key": source_key,
                "page_index": page_index,
                "printed_page_label": printed_labels.get(page_index),
                "section": section,
                "section_title": title,
                "block_id": f"{source_key}:p{page_index:02d}",
                "block_role": role,
                "text": text,
                "bbox": {
                    "left": normalized["left"],
                    "top": normalized["top"],
                    "right": normalized["right"],
                    "bottom": normalized["bottom"],
                },
                "bbox_original": normalized["bbox_original"],
                "page_width_pt": page_size[0],
                "page_height_pt": page_size[1],
                "page_rotation": 0,
                "coordinate_system": "top_left_x_right_y_down_normalized",
                "parser": {
                    "name": "docling",
                    "version": docling_version(),
                    "mode": "bounded-page-items",
                    "notes": "bbox converted from bottom-left points; rotation 0 assumed",
                },
            }
        )
    return anchors

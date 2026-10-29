"""Assembly of anchored evidence: Docling prose anchors + pdfplumber table rows."""

from __future__ import annotations

import time
from pathlib import Path

import pdfplumber
import pymupdf

from . import config
from .extract_docling import convert_pages, docling_version, page_sizes, section_anchors
from .extract_pdfplumber import (
    build_inventory,
    extract_summary_row,
    find_section_page,
    page_dimensions,
    pdfplumber_version,
    printed_label,
    summary_pages,
)
from .schemas import AnchorDocument, CoverageEntry, CoverageSummary, ParserInfo
from .util import read_json, rel, sha256_file, utc_now_iso, write_json


class ParseError(RuntimeError):
    """Raised when mandatory evidence cannot be produced honestly."""


def _st_record(manifest: dict) -> dict:
    for record in manifest["sources"]:
        if record["source_key"] == config.ST_ERRATA["source_key"]:
            return record
    raise ParseError("ST source record missing from fixtures/manifests/w01/sources.json")


def _docling_cache_path(page_index: int) -> Path:
    return config.RESULT_DIR / "docling" / f"page-{page_index:02d}.raw.json"


def _convert_cached(pdf_path: Path, page_indexes: list[int]) -> tuple[list[dict], dict, dict]:
    """Convert only missing pages, caching Docling items per page."""
    cached: list[dict] = []
    pending: list[int] = []
    for page_index in page_indexes:
        cache_path = _docling_cache_path(page_index)
        if cache_path.exists():
            payload = read_json(cache_path)
            # Guard against a stale cache built from different source bytes.
            if payload.get("document_sha256") == _st_record(read_json(config.MANIFEST_PATH))["sha256"]:
                cached.extend(payload["items"])
                continue
        pending.append(page_index)

    timings = {"cached_pages": len(page_indexes) - len(pending), "converted_pages": len(pending)}
    sizes: dict[int, tuple[float, float]] = {}
    if pending:
        started = time.perf_counter()
        document, items = convert_pages(str(pdf_path), [p + 1 for p in pending])
        timings["docling_seconds"] = round(time.perf_counter() - started, 2)
        sizes = page_sizes(document)
        by_page: dict[int, list[dict]] = {}
        for item in items:
            page_index = item.page_no - 1
            by_page.setdefault(page_index, []).append(
                {
                    "label": item.label,
                    "text": item.text,
                    "page_no": item.page_no,
                    "left": item.left,
                    "top": item.top,
                    "right": item.right,
                    "bottom": item.bottom,
                }
            )
        manifest = read_json(config.MANIFEST_PATH)
        digest = _st_record(manifest)["sha256"]
        for page_index in pending:
            page_items = by_page.get(page_index, [])
            write_json(
                _docling_cache_path(page_index),
                {
                    "document_sha256": digest,
                    "page_index": page_index,
                    "page_size_pt": list(sizes.get(page_index + 1, (0, 0))),
                    "items": page_items,
                },
            )
            cached.extend(page_items)
        # Rehydrate sizes for cached pages too.
    else:
        timings["docling_seconds"] = 0.0

    # Sizes for every page: prefer freshly converted, else page points from cache.
    for page_index in page_indexes:
        if page_index + 1 in sizes:
            continue
        cache_path = _docling_cache_path(page_index)
        if cache_path.exists():
            cached_payload = read_json(cache_path)
            size = cached_payload.get("page_size_pt") or [0, 0]
            sizes[page_index + 1] = (float(size[0]), float(size[1]))

    return cached, sizes, timings


def _items_to_docling_objects(items: list[dict]):
    """Recreate lightweight objects accepted by extract_docling.section_anchors."""
    from .extract_docling import DoclingItem

    return [
        DoclingItem(
            label=item["label"],
            text=item["text"],
            page_no=item["page_no"],
            left=item["left"],
            top=item["top"],
            right=item["right"],
            bottom=item["bottom"],
        )
        for item in items
    ]


def _summary_row_anchor(pdf, section: str) -> tuple[dict | None, dict | None]:
    row = extract_summary_row(pdf, section)
    if row is None:
        return None, None
    page = pdf.pages[row["page_index"]]
    width, height = row["page_size_pt"]
    left, top, right, bottom = row["row_bbox_pt"]
    cells = row["cell_bboxes_pt"]
    # Source cell text in reading order; the status columns are recorded in
    # bbox_original so the revision mapping is auditable, not invented.
    pieces = [row["section"]]
    if row["title"]:
        pieces.append(row["title"])
    pieces.extend(row["status_by_revision"][letter] for letter in row["revision_columns"])
    anchor = {
        "anchor_id": f"{config.ST_ERRATA['source_key']}:p{row['page_index']:02d}:row-{section.replace('.', '-')}",
        "document_sha256": _st_record(read_json(config.MANIFEST_PATH))["sha256"],
        "source_key": config.ST_ERRATA["source_key"],
        "page_index": row["page_index"],
        "printed_page_label": printed_label(page),
        "section": section,
        "section_title": row["title"],
        "block_id": f"{config.ST_ERRATA['source_key']}:p{row['page_index']:02d}:summary",
        "block_role": "table_row",
        "text": " | ".join(pieces),
        "bbox": {
            "left": max(0.0, left / width),
            "top": max(0.0, top / height),
            "right": min(1.0, right / width),
            "bottom": min(1.0, bottom / height),
        },
        "bbox_original": {
            "unit": "pdf_points",
            "origin": "top_left_y_down",
            "row": [left, top, right, bottom],
            "cells": cells,
            "revision_columns": row["revision_columns"],
        },
        "page_width_pt": width,
        "page_height_pt": height,
        "page_rotation": row["page_rotation"],
        "coordinate_system": "top_left_x_right_y_down_normalized",
        "parser": {
            "name": "pdfplumber",
            "version": pdfplumber_version(),
            "mode": "word-band-table-row",
            "notes": (
                "Allowed recorded fallback for table cells: Docling prose anchors are primary, "
                "cell x-centers are aligned to the Rev. Z / Rev. B / Rev. X header centers."
            ),
        },
    }
    return anchor, row


def parse_source() -> dict:
    """Produce anchors, coverage, revision matrix, and page renders."""
    if not config.MANIFEST_PATH.exists():
        raise ParseError(
            "Source manifest missing. Run 'fetch-source' first (fixtures/manifests/w01/sources.json)."
        )
    manifest = read_json(config.MANIFEST_PATH)
    record = _st_record(manifest)
    pdf_path = config.PROJECT_ROOT / record["artifact_path"]
    if not pdf_path.exists():
        raise ParseError(f"Source bytes missing at {record['artifact_path']}; run fetch-source.")
    actual_hash = sha256_file(pdf_path)
    if actual_hash != record["sha256"]:
        raise ParseError(
            f"Source hash mismatch: manifest {record['sha256']} != file {actual_hash}. "
            "Stopping; bytes are not the sealed source."
        )

    started = time.perf_counter()
    with pdfplumber.open(pdf_path) as pdf:
        inventory = build_inventory(pdf)
        labels = {index: printed_label(page) for index, page in enumerate(pdf.pages)}
        dims = {index: page_dimensions(page) for index, page in enumerate(pdf.pages)}
        summary_page_indexes = summary_pages(pdf)

        section_pages: dict[str, int] = {}
        missing_sections: list[str] = []
        for section in config.SELECTED_SECTIONS:
            page_index = find_section_page(pdf, section)
            if page_index is None:
                missing_sections.append(section)
            else:
                section_pages[section] = page_index
        if missing_sections:
            raise ParseError(
                "Selected sections not found by document contents: "
                + ", ".join(missing_sections)
            )

        rows: dict[str, dict] = {}
        row_anchors: list[dict] = []
        ambiguous_rows: list[str] = []
        for section in config.SELECTED_SECTIONS:
            anchor, row = _summary_row_anchor(pdf, section)
            if anchor is None or row is None:
                ambiguous_rows.append(section)
                continue
            row_anchors.append(anchor)
            rows[section] = row

        # R3: citable identity / revision-header / legend / footnote context.
        # Built while the PDF is still open; these are real page geometries.
        from .context import build_context_anchors

        context_pages = sorted({row["page_index"] for row in rows.values()}) or summary_page_indexes[:1]
        context_anchors = build_context_anchors(
            pdf,
            source_key=config.ST_ERRATA["source_key"],
            document_sha256=record["sha256"],
            printed_labels=labels,
            summary_page_indexes=context_pages,
        )
        if not any(anchor.get("context_kind") == "source_identity" for anchor in context_anchors):
            raise ParseError(
                "Source identity line was not located in the document text layer; "
                "cannot provide citable revision evidence."
            )
        if not any(anchor.get("context_kind") == "revision_header" for anchor in context_anchors):
            raise ParseError(
                "Governing revision-column headers were not located; "
                "refusing to present an uncited revision matrix."
            )

    page_list = sorted(set(section_pages.values()) | set(summary_page_indexes))
    items, sizes, timings = _convert_cached(pdf_path, page_list)
    if not items:
        raise ParseError("Docling returned no text items for the selected pages.")

    anchors = section_anchors(
        _items_to_docling_objects(items),
        sizes,
        config.ST_ERRATA["source_key"],
        record["sha256"],
        labels,
    )
    anchors.extend(row_anchors)
    anchors.extend(context_anchors)

    document = AnchorDocument(
        schema_version=config.ANCHOR_SCHEMA_VERSION,
        source_key=config.ST_ERRATA["source_key"],
        document_sha256=record["sha256"],
        page_count=int(record["page_count"]),
        generated_utc=utc_now_iso(),
        parsers=[
            ParserInfo(
                name="docling",
                version=docling_version(),
                mode="bounded-page-items",
                notes="Primary parser for prose anchors on selected pages.",
            ),
            ParserInfo(
                name="pdfplumber",
                version=pdfplumber_version(),
                mode="word-band-table-row",
                notes="Recorded fallback for summary-table cell coordinates and inventory.",
            ),
        ],
        anchors=anchors,
    )

    entries: list[CoverageEntry] = []
    for section in config.SELECTED_SECTIONS:
        section_anchor_ids = [
            anchor.anchor_id
            for anchor in document.anchors
            if anchor.section == section and anchor.block_role != "table_row"
        ]
        row_anchor_ids = [
            anchor.anchor_id
            for anchor in document.anchors
            if anchor.section == section and anchor.block_role == "table_row"
        ]
        heading = [
            anchor
            for anchor in document.anchors
            if anchor.section == section and anchor.block_role == "heading"
        ]
        status = "anchored" if section_anchor_ids and heading else "missing"
        notes = []
        if section in ambiguous_rows:
            notes.append("Summary-table revision row could not be resolved; revision matrix unavailable.")
        if section in rows:
            notes.append(
                "Revision matrix: "
                + ", ".join(
                    f"Rev. {letter}={value}"
                    for letter, value in rows[section]["status_by_revision"].items()
                )
            )
        entries.append(
            CoverageEntry(
                source_key=config.ST_ERRATA["source_key"],
                section=section,
                section_title=heading[0].section_title if heading else None,
                status=status,
                page_indexes=sorted({anchor.page_index for anchor in document.anchors if anchor.section == section}),
                anchor_ids=section_anchor_ids + row_anchor_ids,
                notes=notes,
            )
        )

    coverage = CoverageSummary(
        schema_version=1,
        generated_utc=utc_now_iso(),
        document_sha256=record["sha256"],
        inventory_complete=False,
        inventory_notes=[
            "Text-layer heading inventory only: entries whose heading is followed by a 'Description' label.",
            "Scanned or image-only entries would not be detected; this document has a full text layer.",
        ],
        selected_sections=list(config.SELECTED_SECTIONS),
        entries=entries,
        counts={
            "inventory_entries": len(inventory),
            "selected_sections": len(config.SELECTED_SECTIONS),
            "anchored_sections": sum(1 for entry in entries if entry.status == "anchored"),
            "missing_sections": sum(1 for entry in entries if entry.status == "missing"),
            "ambiguous_revision_rows": len(ambiguous_rows),
            "anchors_total": len(document.anchors),
            "context_anchors": sum(1 for anchor in document.anchors if anchor.context_kind),
            "pages_parsed": sorted({anchor.page_index for anchor in document.anchors}),
        },
    )

    write_json(config.RESULT_DIR / "anchors.json", document.model_dump(mode="json"))
    write_json(config.RESULT_DIR / "coverage.json", coverage.model_dump(mode="json"))

    # Record the measured inventory/coverage facts in the public manifest so it
    # does not keep the pre-parse placeholder.
    manifest["selection"].update(
        {
            "inventory_complete": False,
            "inventory_entries": len(inventory),
            "anchored_sections": [
                entry.section for entry in entries if entry.status == "anchored"
            ],
            "parse_generated_utc": utc_now_iso(),
        }
    )
    write_json(config.MANIFEST_PATH, manifest)
    matrix = {
        "generated_utc": utc_now_iso(),
        "document_sha256": record["sha256"],
        "method": (
            "pdfplumber words; row band from the section-number word; status cells assigned to "
            "the nearest Rev. Z / Rev. B / Rev. X header center; rows rejected on ambiguity."
        ),
        "rows": rows,
        "ambiguous_sections": ambiguous_rows,
    }
    write_json(config.RESULT_DIR / "revision_matrix.json", matrix)
    write_json(
        config.RESULT_DIR / "inventory.json",
        {
            "generated_utc": utc_now_iso(),
            "document_sha256": record["sha256"],
            "page_count": int(record["page_count"]),
            "printed_page_labels": {str(k): v for k, v in labels.items()},
            "page_dimensions_pt": {str(k): list(v) for k, v in dims.items()},
            "inventory": inventory,
            "inventory_complete": False,
            "method": "pdfplumber text-layer lines; heading must be followed by a 'Description' label",
        },
    )

    return {
        "document": document,
        "coverage": coverage,
        "rows": rows,
        "section_pages": section_pages,
        "summary_pages": summary_page_indexes,
        "inventory": inventory,
        "timings": {**timings, "parse_seconds": round(time.perf_counter() - started, 2)},
        "pdf_path": pdf_path,
        "labels": labels,
    }


def anchor_rects(anchors, page_index: int) -> list[tuple[float, float, float, float]]:
    rects = []
    for anchor in anchors:
        if anchor.page_index != page_index:
            continue
        width, height = anchor.page_width_pt, anchor.page_height_pt
        rects.append(
            (
                anchor.bbox.left * width,
                anchor.bbox.top * height,
                anchor.bbox.right * width,
                anchor.bbox.bottom * height,
            )
        )
    return rects


def render_selected_pages(parsed: dict) -> list[dict]:
    """Render selected pages plain and with anchor overlays."""
    config.PAGE_DIR.mkdir(parents=True, exist_ok=True)
    document = parsed["document"]
    pages = sorted({anchor.page_index for anchor in document.anchors})
    results = []
    with pymupdf.open(parsed["pdf_path"]) as pdf:
        for page_index in pages:
            page = pdf[page_index]
            plain = config.PAGE_DIR / f"page-{page_index:02d}.png"
            marked = config.PAGE_DIR / f"page-{page_index:02d}-anchors.png"
            page.get_pixmap(dpi=150, alpha=False).save(str(plain))
            rects = anchor_rects(document.anchors, page_index)
            for rect in rects:
                page.draw_rect(
                    pymupdf.Rect(*rect),
                    color=(0.85, 0.05, 0.05),
                    width=1.2,
                )
            page.get_pixmap(dpi=150, alpha=False).save(str(marked))
            results.append(
                {
                    "page_index": page_index,
                    "plain": rel(plain),
                    "anchors_overlay": rel(marked),
                    "rectangles": len(rects),
                }
            )
    write_json(config.RESULT_DIR / "renders.json", {"pages": results})
    return results

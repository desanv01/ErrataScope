"""Bounded digital-PDF parser subprocess for ST ES0620.

Runs with only explicit input/output paths and a sanitized environment.
Emits immutable anchor/coverage JSON; it performs no provider or database I/O.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import pdfplumber

SECTION_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.*\S)\s*$")
IDENTITY_RE = re.compile(r"(ES\d{4})\s*-\s*(Rev\s*\d+)\s*-\s*([A-Z][a-z]+\s+\d{4})")
FOOTER_RE = re.compile(r"page\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)
LEGEND_RE = re.compile(r"^([ANP-])\s+(Limitation\b.+)$")
REVISION_COLUMNS = ("Z", "B", "X")
ROW_STATUS_TOKENS = {"A", "N", "P", "-"}
LABELS = {"Description", "Workaround", "Affected devices"}
MAX_ANCHORS = 10000
MAX_TEXT_BYTES = 2 * 1024 * 1024


class ParseFailure(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class Line:
    def __init__(self, text: str, x0: float, top: float, x1: float, bottom: float) -> None:
        self.text = text
        self.x0 = x0
        self.top = top
        self.x1 = x1
        self.bottom = bottom


def group_lines(words: Iterable[dict]) -> list[Line]:
    ordered = sorted(words, key=lambda word: (round(word["top"], 1), word["x0"]))
    lines: list[Line] = []
    for word in ordered:
        placed = False
        for line in lines:
            overlap = min(line.bottom, word["bottom"]) - max(line.top, word["top"])
            height = min(line.bottom - line.top, word["bottom"] - word["top"]) or 1.0
            if overlap > 0.5 * height:
                line.text = f"{line.text} {word['text']}"
                line.x0 = min(line.x0, word["x0"])
                line.x1 = max(line.x1, word["x1"])
                line.top = min(line.top, word["top"])
                line.bottom = max(line.bottom, word["bottom"])
                placed = True
                break
        if not placed:
            lines.append(Line(word["text"], word["x0"], word["top"], word["x1"], word["bottom"]))
    return sorted(lines, key=lambda line: (line.top, line.x0))


def page_lines(page) -> list[Line]:
    return group_lines(page.extract_words(use_text_flow=False, keep_blank_chars=False))


def page_words(page) -> list[dict]:
    return page.extract_words(use_text_flow=False, keep_blank_chars=False)


def norm_bbox(bbox_pt, width: float, height: float) -> dict:
    left, top, right, bottom = bbox_pt
    return {
        "left": max(0.0, min(1.0, left / width)),
        "top": max(0.0, min(1.0, top / height)),
        "right": max(0.0, min(1.0, right / width)),
        "bottom": max(0.0, min(1.0, bottom / height)),
    }


def printed_label(page) -> str | None:
    matches = FOOTER_RE.findall(page.extract_text() or "")
    return matches[-1][0] if matches else None


def build_inventory(pdf) -> list[dict]:
    inventory = []
    for page_index, page in enumerate(pdf.pages):
        lines = page_lines(page)
        for index, line in enumerate(lines):
            match = SECTION_RE.match(line.text)
            if not match:
                continue
            section, title = match.group(1), match.group(2).strip()
            window = lines[index + 1 : index + 3]
            if len(window) < 2 or window[0].text.strip() != "Description":
                continue
            inventory.append(
                {
                    "section": section,
                    "title": title,
                    "page_index": page_index,
                    "line_top": round(line.top, 2),
                }
            )
    return inventory


def summary_pages(pdf) -> list[int]:
    pages = []
    for index, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if (
            "Status" in text
            and "Rev." in text
            and "Section" in text
            and ("Summary of device limitations" in text or "Summary of device errata" in text)
        ):
            pages.append(index)
    return pages


def header_columns(pdf, page_index: int) -> dict[str, float]:
    page = pdf.pages[page_index]
    words = page_words(page)
    columns: dict[str, float] = {}
    for rev in [word for word in words if word["text"] == "Rev."]:
        candidates = [
            word
            for word in words
            if word["text"] in REVISION_COLUMNS
            and 0 <= (word["top"] - rev["bottom"]) <= 14
            and abs(((word["x0"] + word["x1"]) / 2) - ((rev["x0"] + rev["x1"]) / 2)) < 12
        ]
        if not candidates:
            continue
        chosen = min(candidates, key=lambda word: abs(word["top"] - rev["bottom"]))
        columns[chosen["text"]] = (chosen["x0"] + chosen["x1"]) / 2
    return columns


def extract_summary_row(pdf, section: str) -> dict | None:
    for page_index in summary_pages(pdf):
        page = pdf.pages[page_index]
        words = page_words(page)
        section_words = [word for word in words if word["text"] == section]
        if not section_words:
            continue
        columns = header_columns(pdf, page_index)
        if not columns:
            continue
        anchor_word = section_words[0]
        band = [
            word
            for word in words
            if word["top"] >= anchor_word["top"] - 3 and word["bottom"] <= anchor_word["bottom"] + 13
        ]
        others = [
            word
            for word in band
            if word is not anchor_word
            and re.fullmatch(r"\d+(?:\.\d+)+", word["text"])
            and word["text"] != section
        ]
        if others:
            return None
        band.sort(key=lambda word: word["x0"])
        title_words = [
            word
            for word in band
            if word["x0"] > anchor_word["x1"] and word["x0"] < min(columns.values()) - 8
        ]
        status: dict[str, str] = {}
        cell_boxes: dict[str, list[float]] = {}
        for letter, center in columns.items():
            cells = [
                word
                for word in band
                if word["text"] in ROW_STATUS_TOKENS
                and abs(((word["x0"] + word["x1"]) / 2) - center) <= 14
            ]
            if len(cells) != 1:
                return None
            status[letter] = cells[0]["text"]
            cell_boxes[letter] = [cells[0]["x0"], cells[0]["top"], cells[0]["x1"], cells[0]["bottom"]]
        if len(status) != len(columns):
            return None
        title_box = None
        if title_words:
            title_box = [
                min(word["x0"] for word in title_words),
                min(word["top"] for word in title_words),
                max(word["x1"] for word in title_words),
                max(word["bottom"] for word in title_words),
            ]
        left_edge = [anchor_word["x0"]] + ([title_box[0]] if title_box else [])
        row_box = [
            min(left_edge),
            anchor_word["top"],
            max(box[2] for box in cell_boxes.values()),
            anchor_word["bottom"],
        ]
        return {
            "page_index": page_index,
            "section": section,
            "title": " ".join(word["text"] for word in title_words) if title_words else None,
            "status_by_revision": status,
            "revision_columns": list(columns.keys()),
            "row_bbox_pt": row_box,
            "cell_bboxes_pt": cell_boxes,
            "page_size_pt": [float(page.width), float(page.height)],
            "page_rotation": int(page.rotation or 0),
        }
    return None


def context_anchors(pdf, source_key: str, document_sha256: str, printed_labels: dict[int, str | None]) -> list[dict]:
    anchors: list[dict] = []
    identity_line = None
    identity_page = 0
    for page_index in range(min(4, len(pdf.pages))):
        for line in page_lines(pdf.pages[page_index]):
            if IDENTITY_RE.search(line.text):
                identity_line = line
                identity_page = page_index
                break
        if identity_line:
            break
    if identity_line is not None:
        page = pdf.pages[identity_page]
        anchors.append(
            _anchor(
                source_key,
                document_sha256,
                identity_page,
                printed_labels.get(identity_page),
                None,
                None,
                "body",
                "source_identity",
                identity_line.text,
                [identity_line.x0, identity_line.top, identity_line.x1, identity_line.bottom],
                page,
                f"{source_key}:ctx-identity",
            )
        )
    summary = summary_pages(pdf)
    if summary:
        page_index = summary[0]
        page = pdf.pages[page_index]
        words = page_words(page)
        columns = header_columns(pdf, page_index)
        for letter, center in columns.items():
            candidates = [
                word
                for word in words
                if word["text"] in REVISION_COLUMNS
                and abs(((word["x0"] + word["x1"]) / 2) - center) <= 14
            ]
            if candidates:
                word = candidates[0]
                anchors.append(
                    _anchor(
                        source_key,
                        document_sha256,
                        page_index,
                        printed_labels.get(page_index),
                        None,
                        None,
                        "table_header",
                        "revision_header",
                        f"Rev. {letter}",
                        [word["x0"], word["top"], word["x1"], word["bottom"]],
                        page,
                        f"{source_key}:ctx-rev-{letter}",
                    )
                )
        for line in page_lines(page):
            match = LEGEND_RE.match(line.text)
            if match:
                anchors.append(
                    _anchor(
                        source_key,
                        document_sha256,
                        page_index,
                        printed_labels.get(page_index),
                        None,
                        None,
                        "body",
                        "status_legend",
                        line.text,
                        [line.x0, line.top, line.x1, line.bottom],
                        page,
                        f"{source_key}:ctx-legend-{match.group(1)}",
                    )
                )
    for page_index in range(min(2, len(pdf.pages))):
        page = pdf.pages[page_index]
        for line in page_lines(page):
            lowered = line.text.lower()
            if "device" in lowered and ("revision" in lowered or "rev." in lowered):
                anchors.append(
                    _anchor(
                        source_key,
                        document_sha256,
                        page_index,
                        printed_labels.get(page_index),
                        None,
                        None,
                        "body",
                        "footnote",
                        line.text,
                        [line.x0, line.top, line.x1, line.bottom],
                        page,
                        f"{source_key}:ctx-footnote-p{page_index}-{len(anchors)}",
                    )
                )
    return anchors


def _anchor(
    source_key: str,
    document_sha256: str,
    page_index: int,
    printed_page_label: str | None,
    section: str | None,
    section_title: str | None,
    block_role: str,
    context_kind: str | None,
    text: str,
    bbox_pt,
    page,
    anchor_key: str,
) -> dict:
    width, height = float(page.width), float(page.height)
    rotation = int(page.rotation or 0)
    return {
        "anchor_key": anchor_key,
        "document_sha256": document_sha256,
        "source_key": source_key,
        "page_index": page_index,
        "printed_page_label": printed_page_label,
        "section": section,
        "section_title": section_title,
        "block_role": block_role,
        "context_kind": context_kind,
        "geometry_kind": "located",
        "text": text,
        "bbox": norm_bbox(bbox_pt, width, height),
        "bbox_original": {
            "unit": "pdf_points",
            "origin": "top_left_y_down",
            "left": bbox_pt[0],
            "top": bbox_pt[1],
            "right": bbox_pt[2],
            "bottom": bbox_pt[3],
        },
        "page_width_pt": width,
        "page_height_pt": height,
        "page_rotation": rotation,
        "coordinate_system": "top_left_x_right_y_down_normalized",
        "parser": {
            "name": "pdfplumber",
            "version": getattr(pdfplumber, "__version__", "unknown"),
            "mode": "words+table-geometry",
            "notes": "Bounded digital-text parser; no OCR or network access.",
        },
    }


def section_lines(pdf, inventory: list[dict], section: str) -> list[tuple[int, Line]]:
    entries = sorted(inventory, key=lambda item: (item["page_index"], item["line_top"]))
    start_index = next((i for i, item in enumerate(entries) if item["section"] == section), None)
    if start_index is None:
        return []
    start = entries[start_index]
    next_entry = entries[start_index + 1] if start_index + 1 < len(entries) else None
    collected: list[tuple[int, Line]] = []
    for page_index in range(start["page_index"], len(pdf.pages)):
        if page_index - start["page_index"] > 12:
            break
        page = pdf.pages[page_index]
        for line in page_lines(page):
            position = (page_index, line.top)
            if position < (start["page_index"], start["line_top"] - 0.5):
                continue
            if next_entry is not None and position >= (next_entry["page_index"], next_entry["line_top"] - 0.5):
                return collected
            stripped = line.text.strip()
            if (
                not stripped
                or stripped == "STM32N6xxxx"
                or stripped == "Description of device errata"
                or re.fullmatch(r"ES\d{4}\s*-\s*Rev\s*\d+\s+page\s+\d+/\d+", stripped)
            ):
                continue
            collected.append((page_index, line))
        if next_entry is not None and page_index >= next_entry["page_index"]:
            break
    return collected


def code_like(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("/*", "//", "#include", "volatile ", "if(", "if (", "{", "}")):
        return True
    return "->" in stripped and ";" in stripped


def build() -> int:
    if len(sys.argv) != 6:
        raise ParseFailure("USAGE", "expected input.pdf output.json source_key document_sha256 selected_json")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    source_key = sys.argv[3]
    document_sha256 = sys.argv[4]
    try:
        selected_entries = json.loads(sys.argv[5])
    except json.JSONDecodeError as exc:
        raise ParseFailure("SELECTION_INVALID", "selected entries are not JSON") from exc
    if (
        not isinstance(selected_entries, list)
        or not selected_entries
        or len(selected_entries) > 20
        or any(not isinstance(item, str) or not re.fullmatch(r"\d+(?:\.\d+)+", item) for item in selected_entries)
    ):
        raise ParseFailure("SELECTION_INVALID", "selected entries must be 1-20 section identifiers")
    if len(set(selected_entries)) != len(selected_entries):
        raise ParseFailure("SELECTION_INVALID", "selected entries must be unique")
    try:
        pdf = pdfplumber.open(str(input_path))
    except Exception as exc:  # noqa: BLE001
        raise ParseFailure("PDF_INVALID", f"cannot open PDF: {type(exc).__name__}") from exc
    with pdf:
        page_count = len(pdf.pages)
        if page_count > 100:
            raise ParseFailure("PDF_PAGE_LIMIT", "PDF exceeds 100 pages")
        printed_labels = {index: printed_label(page) for index, page in enumerate(pdf.pages)}
        inventory = build_inventory(pdf)
        anchors = context_anchors(pdf, source_key, document_sha256, printed_labels)
        coverage: list[dict] = []
        by_section = {item["section"]: item for item in inventory}
        for entry in inventory:
            section = entry["section"]
            page = pdf.pages[entry["page_index"]]
            if section not in selected_entries:
                coverage.append(
                    {
                        "section": section,
                        "title": entry["title"],
                        "status": "discovered",
                        "page_indexes": [entry["page_index"]],
                        "anchor_keys": [],
                        "reason": "not_selected",
                        "notes": {"selected": False, "inventory_source": "detected_heading"},
                    }
                )
                continue
            lines = section_lines(pdf, inventory, section)
            if not lines:
                coverage.append(
                    {
                        "section": section,
                        "title": entry["title"],
                        "status": "failed",
                        "page_indexes": [entry["page_index"]],
                        "anchor_keys": [],
                        "reason": "section_body_unavailable",
                        "notes": {"selected": True},
                    }
                )
                continue
            section_anchor_keys: list[str] = []
            for ordinal, (page_index, line) in enumerate(lines):
                role = "heading" if ordinal == 0 else (
                    "label" if line.text.strip() in LABELS else ("code" if code_like(line.text) else "body")
                )
                page = pdf.pages[page_index]
                key = f"{source_key}:p{page_index:02d}:s{section}:a{ordinal:03d}"
                anchors.append(
                    _anchor(
                        source_key,
                        document_sha256,
                        page_index,
                        printed_labels.get(page_index),
                        section,
                        entry["title"],
                        role,
                        None,
                        line.text,
                        [line.x0, line.top, line.x1, line.bottom],
                        page,
                        key,
                    )
                )
                section_anchor_keys.append(key)
            row = extract_summary_row(pdf, section)
            if row is None:
                coverage.append(
                    {
                        "section": section,
                        "title": entry["title"],
                        "status": "ambiguous",
                        "page_indexes": [entry["page_index"]],
                        "anchor_keys": section_anchor_keys,
                        "reason": "summary_row_or_revision_columns_ambiguous",
                        "notes": {"selected": True},
                    }
                )
                continue
            statuses = row["status_by_revision"]
            row_page = pdf.pages[row["page_index"]]
            row_text = (
                f"{section} | {row['title'] or entry['title']} | "
                + " | ".join(f"Rev. {letter}={statuses[letter]}" for letter in ("Z", "B", "X") if letter in statuses)
            )
            row_key = f"{source_key}:p{row['page_index']:02d}:row-{section.replace('.', '-')}"
            anchors.append(
                _anchor(
                    source_key,
                    document_sha256,
                    row["page_index"],
                    printed_labels.get(row["page_index"]),
                    section,
                    entry["title"],
                    "table_row",
                    None,
                    row_text,
                    row["row_bbox_pt"],
                    row_page,
                    row_key,
                )
            )
            coverage.append(
                {
                    "section": section,
                    "title": entry["title"],
                    "status": "supported",
                    "page_indexes": sorted({*[p for p, _ in lines], row["page_index"]}),
                    "anchor_keys": [*section_anchor_keys, row_key],
                    "reason": None,
                    "notes": {
                        "selected": True,
                        "status_by_revision": statuses,
                        "revision_columns": row["revision_columns"],
                        "row_cell_bboxes_pt": row["cell_bboxes_pt"],
                        "inventory_source": "detected_heading",
                    },
                }
            )
        for section in selected_entries:
            if section not in by_section:
                coverage.append(
                    {
                        "section": section,
                        "title": None,
                        "status": "missing",
                        "page_indexes": [],
                        "anchor_keys": [],
                        "reason": "selected_section_not_detected",
                        "notes": {"selected": True},
                    }
                )
        text_bytes = sum(len(anchor["text"].encode("utf-8")) for anchor in anchors)
        if len(anchors) > MAX_ANCHORS or text_bytes > MAX_TEXT_BYTES:
            raise ParseFailure("PARSE_OUTPUT_LIMIT", "anchors exceed the bounded output size")
        identity = None
        for anchor in anchors:
            if anchor["context_kind"] == "source_identity":
                match = IDENTITY_RE.search(anchor["text"])
                if match:
                    identity = {
                        "document_id": match.group(1),
                        "revision": match.group(2),
                        "publication_date": match.group(3),
                        "anchor_key": anchor["anchor_key"],
                    }
                break
        counts: dict[str, int] = {}
        for entry in coverage:
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        supported = sum(1 for entry in coverage if entry["status"] == "supported")
        coverage_summary = {
            "inventory_complete": False,
            "inventory_note": "Digital-text headings followed by a Description label only; scanned/OCR content is not claimed.",
            "detected_entries": len(inventory),
            "selected_entries": selected_entries,
            "supported_selected": supported,
            "status_counts": counts,
        }
        diagnostics = []
        for entry in coverage:
            if entry["status"] in ("ambiguous", "failed", "missing"):
                diagnostics.append(
                    {
                        "section": entry["section"],
                        "severity": "error",
                        "code": entry["status"].upper(),
                        "message": entry["reason"],
                    }
                )
        payload = {
            "schema_version": 1,
            "source_key": source_key,
            "document_sha256": document_sha256,
            "page_count": page_count,
            "parser": {
                "name": "pdfplumber",
                "version": getattr(pdfplumber, "__version__", "unknown"),
                "mode": "words+table-geometry",
            },
            "identity": identity,
            "inventory": inventory,
            "anchors": anchors,
            "coverage": coverage,
            "coverage_summary": coverage_summary,
            "diagnostics": diagnostics,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(build())
    except ParseFailure as failure:
        print(json.dumps({"error": failure.code, "message": failure.message}), file=sys.stderr)
        raise SystemExit(2)

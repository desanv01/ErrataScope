"""pdfplumber extraction: page inventory, printed labels, summary-table rows.

pdfplumber is used here as an allowed, recorded fallback for text-layer
inventory and table-cell coordinates. It keeps PDF top-left coordinates
(x right, y down) in points, which is the convention this spike normalizes to.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

import pdfplumber

SECTION_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.*\S)\s*$")
SECTION_NUMBER_ONLY_RE = re.compile(r"^(\d+(?:\.\d+)+)\s*$")
FOOTER_RE = re.compile(r"page\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)
ROW_STATUS_TOKENS = {"A", "N", "P", "-"}
REVISION_COLUMNS = ("Z", "B", "X")


@dataclass
class Line:
    text: str
    x0: float
    top: float
    x1: float
    bottom: float


def pdfplumber_version() -> str:
    return getattr(pdfplumber, "__version__", "unknown")


def _group_lines(words: Iterable[dict]) -> list[Line]:
    """Cluster words into lines by vertical overlap, ordered by y then x."""
    ordered = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
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
            lines.append(
                Line(
                    text=word["text"],
                    x0=word["x0"],
                    top=word["top"],
                    x1=word["x1"],
                    bottom=word["bottom"],
                )
            )
    return sorted(lines, key=lambda line: (line.top, line.x0))


def page_words(page) -> list[dict]:
    return page.extract_words(use_text_flow=False, keep_blank_chars=False)


def page_lines(page) -> list[Line]:
    return _group_lines(page_words(page))


def page_dimensions(page) -> tuple[float, float, int]:
    return float(page.width), float(page.height), int(page.rotation or 0)


def printed_label(page) -> str | None:
    """Return the printed page label from a 'page N/M' footer, if present."""
    matches = FOOTER_RE.findall(page.extract_text() or "")
    if not matches:
        return None
    return matches[-1][0]


def build_inventory(pdf) -> list[dict]:
    """List section entries that have a heading followed by a 'Description' label.

    This is a text-layer inventory only. It is stated as complete for detected
    headings, not for scanned or image-only entries.
    """
    inventory: list[dict] = []
    for page_index, page in enumerate(pdf.pages):
        lines = page_lines(page)
        for idx, line in enumerate(lines):
            match = SECTION_RE.match(line.text)
            if not match:
                continue
            section, title = match.group(1), match.group(2).strip()
            window = lines[idx + 1 : idx + 3]
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


def find_section_page(pdf, section: str) -> int | None:
    """Locate the page holding the section's descriptive heading."""
    for item in build_inventory(pdf):
        if item["section"] == section:
            return int(item["page_index"])
    return None


def summary_pages(pdf) -> list[int]:
    """Pages that actually carry the summary table header, not pages that merely
    mention it (for example the table of contents)."""
    pages = []
    for index, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        has_table_header = "Status" in text and "Rev." in text and "Section" in text
        if has_table_header and (
            "Summary of device limitations" in text or "Summary of device errata" in text
        ):
            pages.append(index)
    return pages


def _header_columns(pdf, page_index: int) -> dict[str, float]:
    """Map revision letter -> x center from the 'Rev.' header row on a page."""
    page = pdf.pages[page_index]
    words = page_words(page)
    rev_words = [w for w in words if w["text"] == "Rev."]
    columns: dict[str, float] = {}
    for rev in rev_words:
        # The revision letter sits directly below the 'Rev.' cell.
        candidates = [
            w
            for w in words
            if w["text"] in REVISION_COLUMNS
            and 0 <= (w["top"] - rev["bottom"]) <= 14
            and abs(((w["x0"] + w["x1"]) / 2) - ((rev["x0"] + rev["x1"]) / 2)) < 12
        ]
        if not candidates:
            continue
        chosen = min(candidates, key=lambda w: abs(w["top"] - rev["bottom"]))
        columns[chosen["text"]] = (chosen["x0"] + chosen["x1"]) / 2
    return columns


def extract_summary_row(pdf, section: str) -> dict | None:
    """Extract one summary-table row with its revision columns and cell bounds.

    Returns None when the row or the revision header cannot be resolved
    reliably; the caller must then record an ambiguous/unsupported coverage
    entry rather than guess.
    """
    for page_index in summary_pages(pdf):
        page = pdf.pages[page_index]
        words = page_words(page)
        section_words = [w for w in words if w["text"] == section]
        if not section_words:
            continue
        columns = _header_columns(pdf, page_index)
        if not columns:
            continue
        anchor_word = section_words[0]
        band = [
            w
            for w in words
            if w["top"] >= anchor_word["top"] - 3 and w["bottom"] <= anchor_word["bottom"] + 13
        ]
        # Reject a band that swallowed a different section number (row bleed).
        others = [
            w
            for w in band
            if w is not anchor_word and SECTION_NUMBER_ONLY_RE.match(w["text"]) and w["text"] != section
        ]
        if others:
            return None
        band.sort(key=lambda w: w["x0"])
        title_words = [
            w for w in band if w["x0"] > anchor_word["x1"] and w["x0"] < min(columns.values()) - 8
        ]
        status: dict[str, str] = {}
        for letter, center in columns.items():
            cells = [
                w
                for w in band
                if w["text"] in ROW_STATUS_TOKENS and abs(((w["x0"] + w["x1"]) / 2) - center) <= 14
            ]
            if len(cells) == 1:
                status[letter] = cells[0]["text"]
        if len(status) != len(columns):
            return None
        cell_boxes = {
            "section": [anchor_word["x0"], anchor_word["top"], anchor_word["x1"], anchor_word["bottom"]],
            "title": None,
            "status": {},
        }
        if title_words:
            cell_boxes["title"] = [
                min(w["x0"] for w in title_words),
                min(w["top"] for w in title_words),
                max(w["x1"] for w in title_words),
                max(w["bottom"] for w in title_words),
            ]
        for letter, center in columns.items():
            cell = [
                w
                for w in band
                if w["text"] == status[letter] and abs(((w["x0"] + w["x1"]) / 2) - center) <= 14
            ][0]
            cell_boxes["status"][letter] = [cell["x0"], cell["top"], cell["x1"], cell["bottom"]]
        left_edge = [anchor_word["x0"]]
        if cell_boxes["title"]:
            left_edge.append(cell_boxes["title"][0])
        row_box = [
            min(left_edge),
            anchor_word["top"],
            max(box[2] for box in cell_boxes["status"].values()),
            anchor_word["bottom"],
        ]
        return {
            "page_index": page_index,
            "section": section,
            "title": " ".join(w["text"] for w in title_words) if title_words else None,
            "status_by_revision": status,
            "revision_columns": list(columns.keys()),
            "row_bbox_pt": row_box,
            "cell_bboxes_pt": cell_boxes,
            "page_size_pt": [float(page.width), float(page.height)],
            "page_rotation": int(page.rotation or 0),
        }
    return None

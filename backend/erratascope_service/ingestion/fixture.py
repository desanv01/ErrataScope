"""Original labeled synthetic missing-revision fixture for the W04 live case."""

from __future__ import annotations

SYNTHETIC_SOURCE_KEY = "w04-synthetic-missing-revision"
SYNTHETIC_TEXT = (
    "Synthetic ErrataScope fixture. This deliberately incomplete excerpt is not a manufacturer document. "
    "The synthetic device may skip its first reset pulse after a power-on event. "
    "No document identifier, publication date, or document revision is stated in this excerpt."
)


def synthetic_anchors() -> list[dict]:
    parser = {
        "name": "w04-synthetic-fixture",
        "version": "1",
        "mode": "synthetic_not_located",
        "notes": "Original labeled test fixture; no manufacturer identity or geometry is claimed.",
    }
    text = SYNTHETIC_TEXT

    def anchor(key: str, role: str, value: str) -> dict:
        return {
            "anchor_key": key,
            "document_sha256": "0" * 64,
            "source_key": SYNTHETIC_SOURCE_KEY,
            "page_index": 0,
            "printed_page_label": None,
            "section": "2.9.99",
            "section_title": "Synthetic incomplete entry",
            "block_role": role,
            "context_kind": None,
            "geometry_kind": "synthetic_not_located",
            "text": value,
            "bbox": {"left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0},
            "bbox_original": {
                "unit": "synthetic_page",
                "origin": "top_left_y_down",
                "left": 0.0,
                "top": 0.0,
                "right": 1.0,
                "bottom": 1.0,
            },
            "page_width_pt": 612.0,
            "page_height_pt": 792.0,
            "page_rotation": 0,
            "coordinate_system": "top_left_x_right_y_down_normalized",
            "parser": parser,
        }

    return [
        anchor(f"{SYNTHETIC_SOURCE_KEY}:s2-9-99:a0", "heading", "Synthetic incomplete entry"),
        anchor(f"{SYNTHETIC_SOURCE_KEY}:s2-9-99:a1", "body", text),
    ]


def synthetic_coverage() -> list[dict]:
    return [
        {
            "section": "2.9.99",
            "title": "Synthetic incomplete entry",
            "status": "supported",
            "page_indexes": [0],
            "anchor_keys": [f"{SYNTHETIC_SOURCE_KEY}:s2-9-99:a0", f"{SYNTHETIC_SOURCE_KEY}:s2-9-99:a1"],
            "reason": None,
            "notes": {"selected": True, "synthetic": True, "inventory_complete": False},
        }
    ]


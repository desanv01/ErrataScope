"""Versioned W04 prompt assembly and hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"
PROMPT_VERSION = "w04-draft-v5-grounded-no-thinking"
MAX_INPUT_TOKEN_BOUND = 16000


def read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def prompt_hashes() -> dict[str, str]:
    files = {
        "system": read_prompt("v5_system.md"),
        "schema": read_prompt("v5_schema.md"),
        "user_template": read_prompt("v5_user.md"),
    }
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in files.items()}


def prompt_bundle() -> dict[str, str]:
    return {
        "version": PROMPT_VERSION,
        "system": read_prompt("v5_system.md"),
        "schema": read_prompt("v5_schema.md"),
        "user_template": read_prompt("v5_user.md"),
    }


def _anchor_line(anchor: dict) -> str:
    kind = anchor.get("context_kind") or anchor.get("block_role")
    section = anchor.get("section") or "-"
    return (
        f"[{anchor['anchor_key']}] ({kind}, page_index={anchor['page_index']}, section={section}) "
        f"{anchor['text']}"
    )


def build_user_prompt(
    *,
    case: str,
    selected_entries: list[str],
    declared_identity: dict | None,
    anchors: list[dict],
    coverage: list[dict],
) -> str:
    matrix_lines = []
    for entry in coverage:
        if entry["status"] == "supported":
            statuses = entry.get("notes", {}).get("status_by_revision", {})
            ordered = ", ".join(
                f"Rev. {letter}={statuses[letter]}" for letter in ("Z", "B", "X") if letter in statuses
            )
            keys = ", ".join(entry.get("anchor_keys", [])[-1:])
            matrix_lines.append(f"- {entry['section']}: {ordered} (row anchor {keys})")
    context = "\n".join(_anchor_line(anchor) for anchor in anchors)
    user = prompt_bundle()["user_template"]
    user = user.replace("<<CASE>>", case)
    user = user.replace("<<SELECTIONS>>", ", ".join(selected_entries))
    user = user.replace("<<DECLARED_IDENTITY>>", json.dumps(declared_identity, sort_keys=True))
    user = user.replace("<<MATRIX>>", "\n".join(matrix_lines) or "- none")
    user = user.replace("<<ANCHORS>>", context)
    user = user.replace("<<SCHEMA>>", prompt_bundle()["schema"])
    return user


def estimate_input_token_bound(messages: list[dict]) -> int:
    """Conservative UTF-8 bound, including message overhead; no tokenizer dependency."""
    payload = json.dumps({"messages": messages}, ensure_ascii=False, separators=(",", ":"))
    return len(payload.encode("utf-8")) // 3 + 64 * len(messages) + 64


def build_messages(user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt_bundle()["system"]},
        {"role": "user", "content": user_prompt},
    ]

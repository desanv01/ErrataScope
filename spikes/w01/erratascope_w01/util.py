"""Small standard-library helpers: time, hashing, JSON, paths."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with a Z suffix."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> Path:
    ensure_dir(path.parent)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
    return path


def atomic_write_json(path: Path, payload: Any) -> Path:
    """Crash-safe JSON write: fsync a sibling temp file, then os.replace.

    The budget/reservation ledger must never be left half-written: a torn write
    could hide a dispatch and permit extra paid calls after a crash.
    """
    ensure_dir(path.parent)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    return path


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: Path, text: str) -> Path:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def rel(path: Path) -> str:
    """Project-relative POSIX path, for public manifests and reports."""
    try:
        return Path(os.path.relpath(path, PROJECT_ROOT)).as_posix()
    except ValueError:  # pragma: no cover - different drive on Windows
        return path.as_posix()


def canonical_json_bytes(payload: Any) -> bytes:
    """Stable JSON encoding used for content-derived identifiers."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def redact_url(url: str) -> str:
    """Strip userinfo and query/fragment so a URL can be stored publicly."""
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    host = parts.hostname or ""
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))

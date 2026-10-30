"""Persistent-store identity binding (no credentials in markers)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

MARKER_NAME = ".store-identity.json"
MARKER_VERSION = 1


class StoreIdentityError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def database_identity(database_url: str) -> str:
    """Stable, credential-free identity: host:port/database."""
    url = make_url(database_url)
    host = url.host or "local"
    port = url.port or 5432
    database = url.database or "unknown"
    return f"{host}:{port}/{database}"


def _read_marker(root: Path) -> dict | None:
    marker = root / MARKER_NAME
    if not marker.exists():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StoreIdentityError("STORE_IDENTITY_INVALID", "store identity marker is unreadable") from exc
    if data.get("schema_version") != MARKER_VERSION or "database_identity" not in data:
        raise StoreIdentityError("STORE_IDENTITY_INVALID", "store identity marker is invalid")
    return data


def write_identity(root: Path, identity: str, *, store_id: str | None = None) -> dict:
    marker = root / MARKER_NAME
    data = {
        "schema_version": MARKER_VERSION,
        "store_id": store_id or str(uuid.uuid4()),
        "database_identity": identity,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    temp = marker.with_name(f".{MARKER_NAME}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, marker)
    return data


def ensure_identity(root: Path, identity: str, *, adopt: bool = False) -> dict:
    """Load/create the store marker; refuse silent takeover of populated stores."""
    existing = _read_marker(root)
    if existing is not None:
        if existing["database_identity"] != identity:
            raise StoreIdentityError(
                "STORE_IDENTITY_MISMATCH",
                "artifact store is bound to a different database identity",
            )
        return existing
    has_content = any(
        entry.name != MARKER_NAME and entry.name != ".tmp"
        for entry in root.iterdir()
    )
    if has_content and not adopt:
        raise StoreIdentityError(
            "STORE_IDENTITY_MISSING",
            "populated artifact store has no identity marker; explicit adoption is required",
        )
    return write_identity(root, identity)


def _read_marker_fd(root_fd: int) -> dict | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(MARKER_NAME, flags, dir_fd=root_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise StoreIdentityError(
            "STORE_IDENTITY_INVALID", "store identity marker is unreadable"
        ) from exc
    try:
        handle = os.fdopen(fd, "rb")
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    with handle:
        try:
            data = json.loads(handle.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise StoreIdentityError(
                "STORE_IDENTITY_INVALID", "store identity marker is unreadable"
            ) from exc
    if data.get("schema_version") != MARKER_VERSION or "database_identity" not in data:
        raise StoreIdentityError("STORE_IDENTITY_INVALID", "store identity marker is invalid")
    return data


def write_identity_fd(root_fd: int, identity: str, *, store_id: str | None = None) -> dict:
    data = {
        "schema_version": MARKER_VERSION,
        "store_id": store_id or str(uuid.uuid4()),
        "database_identity": identity,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    temp_name = f".{MARKER_NAME}.{uuid.uuid4().hex}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temp_name, flags, 0o600, dir_fd=root_fd)
    try:
        handle = os.fdopen(fd, "wb")
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_name, dir_fd=root_fd)
        except OSError:
            pass
        raise
    try:
        with handle:
            handle.write(json.dumps(data, indent=2).encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, MARKER_NAME, src_dir_fd=root_fd, dst_dir_fd=root_fd)
    except Exception:
        try:
            os.unlink(temp_name, dir_fd=root_fd)
        except OSError:
            pass
        raise
    return data


def ensure_identity_fd(root_fd: int, identity: str, *, adopt: bool = False) -> dict:
    existing = _read_marker_fd(root_fd)
    if existing is not None:
        if existing["database_identity"] != identity:
            raise StoreIdentityError(
                "STORE_IDENTITY_MISMATCH",
                "artifact store is bound to a different database identity",
            )
        return existing
    try:
        entries = os.listdir(root_fd)
    except OSError as exc:
        raise StoreIdentityError("STORE_IDENTITY_INVALID", "artifact store is unreadable") from exc
    has_content = any(entry not in (MARKER_NAME, ".tmp") for entry in entries)
    if has_content and not adopt:
        raise StoreIdentityError(
            "STORE_IDENTITY_MISSING",
            "populated artifact store has no identity marker; explicit adoption is required",
        )
    return write_identity_fd(root_fd, identity)

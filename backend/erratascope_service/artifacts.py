"""Private artifact storage using directory-relative no-follow Linux operations."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from .models import Artifact, Job, UploadStaging
from .storage_identity import (
    MARKER_NAME,
    StoreIdentityError,
    database_identity,
    ensure_identity_fd,
)

ALLOWED_MEDIA_TYPES = ("application/pdf", "text/plain", "application/json")
STAGING_DIR = ".staging"
FINAL_RE = re.compile(r"^(?P<project>[0-9a-f]{32})/(?P<artifact>[0-9a-f]{32})\.bin$")
STAGING_RE = re.compile(
    r"^\.staging/(?P<project>[0-9a-f]{32})/(?P<artifact>[0-9a-f]{32})\.part$"
)
FINAL_NAME_RE = re.compile(r"^(?P<artifact>[0-9a-f]{32})\.bin$")
STAGING_NAME_RE = re.compile(r"^(?P<artifact>[0-9a-f]{32})\.part$")
PROJECT_RE = re.compile(r"^[0-9a-f]{32}$")
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)


class ArtifactError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def normalize_media_type(value: str | None) -> str:
    if not value:
        raise ArtifactError("UNSUPPORTED_MEDIA_TYPE", "Content-Type is required")
    media = value.split(";", 1)[0].strip().lower()
    if media not in ALLOWED_MEDIA_TYPES:
        raise ArtifactError(
            "UNSUPPORTED_MEDIA_TYPE", "only PDF, text/plain and application/json are accepted"
        )
    return media


def sanitize_filename(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = "".join(
        ch for ch in value if ch.isprintable() and ch not in {'"', "\\", "/", "\r", "\n"}
    )
    cleaned = cleaned.strip()
    return cleaned[:200] or None


def content_disposition(filename: str) -> str:
    fallback = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in {'"', "\\"} else "_" for ch in filename
    )
    fallback = fallback[:200] or "artifact"
    from urllib.parse import quote

    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


def session_store_identity(session: Session) -> str:
    """Derive the store identity from the actual bound database session."""
    bind = session.get_bind()
    if isinstance(bind, Connection):
        url = bind.engine.url
    elif isinstance(bind, Engine):
        url = bind.url
    else:
        raise StoreIdentityError(
            "STORE_SESSION_UNBOUND", "collector session has no usable database binding"
        )
    database = session.execute(text("SELECT current_database()")).scalar()
    if not database:
        raise StoreIdentityError(
            "STORE_SESSION_UNBOUND", "collector session database is unknown"
        )
    host = url.host or "local"
    port = url.port or 5432
    return f"{host}:{port}/{database}"


def _validate_root_path(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise StoreIdentityError(
                "STORE_PATH_INVALID", "configured artifact root traverses a symlink"
            )
        if current == absolute and not stat.S_ISDIR(metadata.st_mode):
            raise StoreIdentityError(
                "STORE_PATH_INVALID", "configured artifact root is not a directory"
            )


class StagingUpload:
    def __init__(self, store: "ArtifactStore", project_hex: str, artifact_hex: str) -> None:
        self.store = store
        self.project_hex = project_hex
        self.artifact_hex = artifact_hex
        self.name = f"{artifact_hex}.part"
        self.project_fd = None
        self._handle = None
        self._finished = False
        self._hash = hashlib.sha256()
        self.length = 0
        fd = None
        wrapped = False
        try:
            self.project_fd = store._project_fd("staging", project_hex, create=True)
            store._fault("before_staging_create")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_NOFOLLOW
            fd = os.open(self.name, flags, 0o600, dir_fd=self.project_fd)
            self._handle = os.fdopen(fd, "wb")
            wrapped = True
        except BaseException:
            if fd is not None and not wrapped:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if self._handle is not None:
                try:
                    self._handle.close()
                except OSError:
                    pass
            self._close_project()
            raise

    def write(self, chunk: bytes, maximum: int) -> None:
        if self._finished:
            raise ArtifactError("ARTIFACT_STORE_ERROR", "staging upload is already finished")
        self.length += len(chunk)
        if self.length > maximum:
            raise ArtifactError("ARTIFACT_TOO_LARGE", "artifact exceeds the configured maximum size")
        self._hash.update(chunk)
        self._handle.write(chunk)

    def finish(self) -> tuple[str, int]:
        if not self._finished:
            self._handle.flush()
            os.fsync(self._handle.fileno())
            self._handle.close()
            self._finished = True
        return self._hash.hexdigest(), self.length

    def promote(self) -> str:
        self.finish()
        final_fd = None
        try:
            final_fd = self.store._project_fd("final", self.project_hex, create=True)
            self.store._fault("before_promote_rename")
            os.replace(
                self.name,
                f"{self.artifact_hex}.bin",
                src_dir_fd=self.project_fd,
                dst_dir_fd=final_fd,
            )
            metadata = os.stat(f"{self.artifact_hex}.bin", dir_fd=final_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise ArtifactError(
                    "ARTIFACT_PATH_INVALID", "promoted artifact path is not a regular file"
                )
        except BaseException:
            if final_fd is not None:
                try:
                    os.close(final_fd)
                except OSError:
                    pass
                final_fd = None
            if getattr(self, "project_fd", None) is not None:
                try:
                    metadata = os.stat(self.name, dir_fd=self.project_fd, follow_symlinks=False)
                    if stat.S_ISREG(metadata.st_mode):
                        os.unlink(self.name, dir_fd=self.project_fd)
                except OSError:
                    pass
            self._close_project()
            raise
        finally:
            if final_fd is not None:
                try:
                    os.close(final_fd)
                except OSError:
                    pass
        self._close_project()
        return self.store.final_key_for_hex(self.project_hex, self.artifact_hex)

    def abort(self) -> None:
        try:
            if not self._finished and self._handle is not None:
                self._handle.close()
                self._finished = True
        except OSError:
            pass
        if getattr(self, "project_fd", None) is None:
            return
        try:
            self.store._fault("before_abort_unlink")
            metadata = os.stat(self.name, dir_fd=self.project_fd, follow_symlinks=False)
            if stat.S_ISREG(metadata.st_mode):
                os.unlink(self.name, dir_fd=self.project_fd)
        except (OSError, FileNotFoundError):
            pass
        finally:
            self._close_project()

    def _close_project(self) -> None:
        if getattr(self, "project_fd", None) is not None:
            try:
                os.close(self.project_fd)
            except OSError:
                pass
            self.project_fd = None


class ArtifactStore:
    def __init__(
        self,
        root: Path,
        *,
        database_identity: str | None = None,
        adopt: bool = False,
        fault_hook=None,
    ) -> None:
        self._root_fd = None
        self.fault_hook = fault_hook
        self.identity = None
        try:
            _validate_root_path(root)
            self.root = root.absolute()
            self.root.mkdir(parents=True, exist_ok=True)
            self._root_fd = os.open(self.root, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
            if database_identity is not None:
                marker = ensure_identity_fd(self._root_fd, database_identity, adopt=adopt)
                self.identity = marker["database_identity"]
            else:
                from .storage_identity import _read_marker_fd

                marker = _read_marker_fd(self._root_fd)
                if marker is not None:
                    self.identity = marker["database_identity"]
            for name in (".tmp", STAGING_DIR):
                try:
                    fd = os.open(
                        name, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW, dir_fd=self._root_fd
                    )
                except FileNotFoundError:
                    os.mkdir(name, 0o700, dir_fd=self._root_fd)
                    fd = os.open(
                        name, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW, dir_fd=self._root_fd
                    )
                os.close(fd)
            self.tmp = self.root / ".tmp"
            self.staging_root = self.root / STAGING_DIR
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        fd = getattr(self, "_root_fd", None)
        if fd is not None:
            self._root_fd = None
            try:
                os.close(fd)
            except OSError:
                pass

    def __enter__(self) -> "ArtifactStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _fault(self, point: str) -> None:
        if self.fault_hook is not None:
            self.fault_hook(point)

    def assert_identity(self, database_identity_value: str | None) -> None:
        if self.identity is None:
            raise StoreIdentityError(
                "STORE_IDENTITY_MISSING",
                "collector requires an identity-bound artifact store",
            )
        if database_identity_value is not None and self.identity != database_identity_value:
            raise StoreIdentityError(
                "STORE_IDENTITY_MISMATCH",
                "collector database does not own this artifact store",
            )

    def final_key(self, project_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
        return self.final_key_for_hex(project_id.hex, artifact_id.hex)

    def final_key_for_hex(self, project_hex: str, artifact_hex: str) -> str:
        return f"{project_hex}/{artifact_hex}.bin"

    def staging_key(self, project_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
        return f"{STAGING_DIR}/{project_id.hex}/{artifact_id.hex}.part"

    def _parse_key(self, key: str) -> tuple[str, str, str, str]:
        final = FINAL_RE.fullmatch(key)
        if final is not None:
            return "final", final.group("project"), final.group("artifact"), final.group("artifact") + ".bin"
        staging = STAGING_RE.fullmatch(key)
        if staging is not None:
            return "staging", staging.group("project"), staging.group("artifact"), staging.group("artifact") + ".part"
        raise ArtifactError("ARTIFACT_PATH_INVALID", "artifact storage key is not canonical")

    def _open_dir(self, name: str, dir_fd: int) -> int | None:
        try:
            return os.open(name, os.O_RDONLY | O_DIRECTORY | O_NOFOLLOW, dir_fd=dir_fd)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ArtifactError("ARTIFACT_PATH_INVALID", "artifact directory is not confined") from exc

    def _project_fd(self, kind: str, project_hex: str, *, create: bool = False) -> int:
        if kind not in ("final", "staging"):
            raise ArtifactError("ARTIFACT_PATH_INVALID", "unknown artifact store layout")
        if not PROJECT_RE.fullmatch(project_hex):
            raise ArtifactError("ARTIFACT_PATH_INVALID", "artifact project id is not canonical")
        base_fd = None
        project_fd = None
        close_base = False
        try:
            if kind == "staging":
                base_fd = self._open_dir(STAGING_DIR, self._root_fd)
                if base_fd is None:
                    raise ArtifactError("ARTIFACT_STORE_ERROR", "staging directory is missing")
                close_base = True
            else:
                base_fd = self._root_fd
            project_fd = self._open_dir(project_hex, base_fd)
            if project_fd is None:
                if not create:
                    raise ArtifactError("ARTIFACT_MISSING", "artifact directory is missing")
                try:
                    os.mkdir(project_hex, 0o700, dir_fd=base_fd)
                except FileExistsError:
                    pass
                project_fd = self._open_dir(project_hex, base_fd)
                if project_fd is None:
                    raise ArtifactError(
                        "ARTIFACT_PATH_INVALID", "artifact directory is not confined"
                    )
            self._fault("after_project_dir_open")
            return project_fd
        except BaseException:
            if project_fd is not None:
                try:
                    os.close(project_fd)
                except OSError:
                    pass
            raise
        finally:
            if close_base and base_fd is not None:
                try:
                    os.close(base_fd)
                except OSError:
                    pass

    def begin_staging(self, project_id: uuid.UUID, artifact_id: uuid.UUID) -> StagingUpload:
        return StagingUpload(self, project_id.hex, artifact_id.hex)

    def put_bytes(
        self,
        project_id: uuid.UUID,
        artifact_id: uuid.UUID,
        data: bytes,
        *,
        max_bytes: int,
    ) -> tuple[str, str, int]:
        upload = self.begin_staging(project_id, artifact_id)
        try:
            upload.write(data, max_bytes)
            sha, length = upload.finish()
            final_key = upload.promote()
        except Exception:
            upload.abort()
            raise
        return final_key, sha, length

    def _read_key_bytes(self, key: str) -> bytes:
        kind, project_hex, _artifact_hex, name = self._parse_key(key)
        if kind != "final":
            raise ArtifactError("ARTIFACT_PATH_INVALID", "read requires a final artifact key")
        project_fd = self._project_fd("final", project_hex)
        try:
            self._fault("before_read_open")
            fd = os.open(name, os.O_RDONLY | O_NOFOLLOW, dir_fd=project_fd)
            try:
                handle = os.fdopen(fd, "rb")
            except BaseException:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            with handle:
                return handle.read()
        except FileNotFoundError as exc:
            raise ArtifactError("ARTIFACT_MISSING", "artifact bytes are missing") from exc
        except OSError as exc:
            raise ArtifactError("ARTIFACT_READ_ERROR", "artifact bytes cannot be read") from exc
        finally:
            os.close(project_fd)

    def verify_bytes(self, storage_key: str, expected_sha256: str, expected_length: int) -> bool:
        data = self._read_key_bytes(storage_key)
        return len(data) == expected_length and hashlib.sha256(data).hexdigest() == expected_sha256

    def read_bytes(self, storage_key: str, expected_sha256: str, expected_length: int) -> bytes:
        data = self._read_key_bytes(storage_key)
        if len(data) != expected_length or hashlib.sha256(data).hexdigest() != expected_sha256:
            raise ArtifactError(
                "ARTIFACT_INTEGRITY", "stored artifact bytes failed integrity verification"
            )
        return data

    def delete(self, storage_key: str) -> None:
        try:
            kind, project_hex, _artifact_hex, name = self._parse_key(storage_key)
            project_fd = self._project_fd(kind, project_hex)
        except (OSError, ArtifactError):
            return
        try:
            self._fault("before_delete_unlink")
            try:
                metadata = os.stat(name, dir_fd=project_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            if stat.S_ISREG(metadata.st_mode):
                os.unlink(name, dir_fd=project_fd)
        except (OSError, ArtifactError):
            return
        finally:
            os.close(project_fd)

    def iter_owned_files(self) -> list[tuple[str, str, float]]:
        files: list[tuple[str, str, float]] = []
        try:
            project_dirs = os.listdir(self._root_fd)
        except OSError:
            return files
        for project_name in project_dirs:
            if project_name in (".tmp", STAGING_DIR, MARKER_NAME) or not PROJECT_RE.fullmatch(project_name):
                continue
            project_fd = self._open_dir(project_name, self._root_fd)
            if project_fd is None:
                continue
            try:
                for name in os.listdir(project_fd):
                    match = FINAL_NAME_RE.fullmatch(name)
                    if match is None:
                        continue
                    try:
                        metadata = os.stat(name, dir_fd=project_fd, follow_symlinks=False)
                    except OSError:
                        continue
                    if not stat.S_ISREG(metadata.st_mode):
                        continue
                    key = f"{project_name}/{name}"
                    files.append(("final", key, metadata.st_mtime))
            finally:
                os.close(project_fd)
        staging_fd = self._open_dir(STAGING_DIR, self._root_fd)
        if staging_fd is not None:
            try:
                for project_name in os.listdir(staging_fd):
                    if not PROJECT_RE.fullmatch(project_name):
                        continue
                    project_fd = self._open_dir(project_name, staging_fd)
                    if project_fd is None:
                        continue
                    try:
                        for name in os.listdir(project_fd):
                            if STAGING_NAME_RE.fullmatch(name) is None:
                                continue
                            try:
                                metadata = os.stat(name, dir_fd=project_fd, follow_symlinks=False)
                            except OSError:
                                continue
                            if not stat.S_ISREG(metadata.st_mode):
                                continue
                            key = f"{STAGING_DIR}/{project_name}/{name}"
                            files.append(("staging", key, metadata.st_mtime))
                    finally:
                        os.close(project_fd)
            finally:
                os.close(staging_fd)
        return files

    def _checked_path(self, storage_key: str) -> Path:
        """Lexical test/inspection path only; data operations use directory fds."""
        self._parse_key(storage_key)
        return self.root / storage_key

    def close(self) -> None:
        if getattr(self, "_root_fd", None) is not None:
            try:
                os.close(self._root_fd)
            except OSError:
                pass
            self._root_fd = None


def reconcile_orphans(
    session: Session,
    store: ArtifactStore,
    *,
    grace_seconds: int,
    database_identity: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Derive ownership from the actual session, then run fenced GC."""
    actual_identity = session_store_identity(session)
    if database_identity is not None and database_identity != actual_identity:
        raise StoreIdentityError(
            "STORE_IDENTITY_MISMATCH",
            "caller identity does not match the actual collector database session",
        )
    store.assert_identity(actual_identity)
    now = now or datetime.now(timezone.utc)
    removed_files = 0
    kept_committed = 0
    protected_live = 0
    abandoned_rows = 0
    released_rows = 0
    candidate_cutoff = now - timedelta(seconds=grace_seconds)

    rows = session.scalars(
        select(UploadStaging)
        .where(
            UploadStaging.state == "active",
            UploadStaging.lease_until < candidate_cutoff,
        )
        .order_by(UploadStaging.lease_until)
        .limit(200)
        .with_for_update(skip_locked=True)
    ).all()
    for row in rows:
        artifact = session.scalar(
            select(Artifact).where(
                Artifact.project_id == row.project_id, Artifact.id == row.artifact_id
            )
        )
        if artifact is not None:
            row.state = "finalized"
            kept_committed += 1
            continue
        if row.owner_job_id is not None:
            job = session.get(Job, row.owner_job_id)
            if (
                job is not None
                and job.status == "running"
                and job.lease_until is not None
                and job.lease_until > now
                and job.current_attempt_token == row.owner_attempt_token
            ):
                row.lease_until = now + timedelta(seconds=max(grace_seconds, 30))
                protected_live += 1
                continue
        for key in (row.staging_key, store.final_key(row.project_id, row.artifact_id)):
            try:
                store.delete(key)
                removed_files += 1
            except Exception:
                continue
        session.delete(row)
        abandoned_rows += 1
        released_rows += 1
    session.flush()

    artifact_keys = set(session.scalars(select(Artifact.storage_key)))
    journal_keys: set[str] = set()
    for journal in session.scalars(select(UploadStaging)):
        journal_keys.add(journal.staging_key)
        journal_keys.add(store.final_key(journal.project_id, journal.artifact_id))
    for _kind, key, modified_epoch in store.iter_owned_files():
        if key in artifact_keys or key in journal_keys:
            continue
        age = now.timestamp() - modified_epoch
        if age < grace_seconds:
            continue
        try:
            store.delete(key)
            removed_files += 1
        except Exception:
            continue
    session.flush()
    return {
        "staging_rows": len(rows),
        "abandoned_rows": abandoned_rows,
        "kept_committed": kept_committed,
        "protected_live": protected_live,
        "removed_files": removed_files,
        "released_rows": released_rows,
    }

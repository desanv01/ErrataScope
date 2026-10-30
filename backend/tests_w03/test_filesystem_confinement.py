"""W03 repair-03 R3: directory-relative no-follow confinement under parent swaps."""

from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from pathlib import Path

from sqlalchemy import select

from erratascope_service import services
from erratascope_service.artifacts import ArtifactError, ArtifactStore
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact
from erratascope_service.storage_identity import StoreIdentityError, database_identity

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


class DirectoryConfinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="confinement")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _identity(self) -> str:
        return database_identity(load_settings().database_url)

    def _store(self, hook=None) -> ArtifactStore:
        return ArtifactStore(
            load_settings().artifact_root,
            database_identity=self._identity(),
            fault_hook=hook,
        )

    def _artifact_row(self, artifact_id: str) -> Artifact:
        db = get_session_factory()()
        try:
            return db.get(Artifact, uuid.UUID(artifact_id))
        finally:
            db.close()

    def test_delete_uses_pinned_parent_under_swap(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"original delete bytes")
        row = self._artifact_row(artifact["id"])
        project_hex = uuid.UUID(self.project_id).hex
        root = load_settings().artifact_root
        moved = root / f"moved-{uuid.uuid4().hex}"
        external = Path(tempfile.mkdtemp(prefix="w03-external-"))
        external_file = external / f"{uuid.UUID(artifact['id']).hex}.bin"
        external_file.write_bytes(b"external sentinel")
        fired = {"value": False}

        def hook(point: str) -> None:
            if point == "before_delete_unlink" and not fired["value"]:
                fired["value"] = True
                os.rename(root / project_hex, moved)
                os.symlink(external, root / project_hex)

        try:
            self._store(hook).delete(row.storage_key)
            self.assertTrue(external_file.exists())
            self.assertFalse((moved / external_file.name).exists())
        finally:
            (root / project_hex).unlink(missing_ok=True)
            moved.rename(root / project_hex)
            external_file.unlink(missing_ok=True)
            external.rmdir()

    def test_read_uses_pinned_parent_under_swap(self) -> None:
        payload = b"original read bytes"
        artifact = H.upload_text(self.client, self.project_id, payload)
        row = self._artifact_row(artifact["id"])
        project_hex = uuid.UUID(self.project_id).hex
        root = load_settings().artifact_root
        moved = root / f"moved-{uuid.uuid4().hex}"
        external = Path(tempfile.mkdtemp(prefix="w03-external-"))
        external_file = external / f"{uuid.UUID(artifact['id']).hex}.bin"
        external_file.write_bytes(b"external read bytes")
        fired = {"value": False}

        def hook(point: str) -> None:
            if point == "before_read_open" and not fired["value"]:
                fired["value"] = True
                os.rename(root / project_hex, moved)
                os.symlink(external, root / project_hex)

        try:
            data = self._store(hook).read_bytes(row.storage_key, row.sha256, row.byte_length)
            self.assertEqual(data, payload)
            self.assertEqual(external_file.read_bytes(), b"external read bytes")
        finally:
            (root / project_hex).unlink(missing_ok=True)
            moved.rename(root / project_hex)
            external_file.unlink(missing_ok=True)
            external.rmdir()

    def test_promotion_uses_pinned_destination_under_swap(self) -> None:
        artifact_id = uuid.uuid4()
        project_id = uuid.uuid4()
        root = load_settings().artifact_root
        project_hex = project_id.hex
        moved = root / f"moved-{uuid.uuid4().hex}"
        external = Path(tempfile.mkdtemp(prefix="w03-external-"))
        external_file = external / f"{artifact_id.hex}.bin"
        external_file.write_bytes(b"external promotion sentinel")
        fired = {"value": False}

        def hook(point: str) -> None:
            if point == "before_promote_rename" and not fired["value"]:
                fired["value"] = True
                if (root / project_hex).exists():
                    os.rename(root / project_hex, moved)
                else:
                    moved.mkdir()
                os.symlink(external, root / project_hex)

        store = self._store(hook)
        try:
            upload = store.begin_staging(project_id, artifact_id)
            upload.write(b"promoted bytes", 1024)
            upload.finish()
            upload.promote()
            self.assertEqual(external_file.read_bytes(), b"external promotion sentinel")
            moved_file = moved / f"{artifact_id.hex}.bin"
            self.assertTrue(moved_file.exists())
            self.assertEqual(moved_file.read_bytes(), b"promoted bytes")
        finally:
            link = root / project_hex
            if link.is_symlink():
                link.unlink()
            (moved / f"{artifact_id.hex}.bin").unlink(missing_ok=True)
            if moved.exists():
                moved.rmdir()
            external_file.unlink(missing_ok=True)
            external.rmdir()

    def test_abort_uses_pinned_parent_under_swap(self) -> None:
        artifact_id = uuid.uuid4()
        project_id = uuid.uuid4()
        root = load_settings().artifact_root
        project_hex = project_id.hex
        staging_parent = root / ".staging" / project_hex
        moved = root / ".staging" / f"moved-{uuid.uuid4().hex}"
        external = Path(tempfile.mkdtemp(prefix="w03-external-"))
        external_file = external / f"{artifact_id.hex}.part"
        external_file.write_bytes(b"external abort sentinel")
        fired = {"value": False}

        def hook(point: str) -> None:
            if point == "before_abort_unlink" and not fired["value"]:
                fired["value"] = True
                os.rename(staging_parent, moved)
                os.symlink(external, staging_parent)

        store = self._store(hook)
        try:
            upload = store.begin_staging(project_id, artifact_id)
            upload.write(b"to be aborted", 1024)
            upload.finish()
            upload.abort()
            self.assertEqual(external_file.read_bytes(), b"external abort sentinel")
            self.assertFalse((moved / f"{artifact_id.hex}.part").exists())
        finally:
            link = root / ".staging" / project_hex
            if link.is_symlink():
                link.unlink()
            if moved.exists():
                moved.rmdir()
            external_file.unlink(missing_ok=True)
            external.rmdir()

    def test_symlinked_configured_root_rejected(self) -> None:
        real = Path(tempfile.mkdtemp(prefix="w03-real-root-"))
        link = real.parent / f"w03-root-link-{uuid.uuid4().hex}"
        os.symlink(real, link)
        try:
            with self.assertRaises(StoreIdentityError):
                ArtifactStore(link, database_identity=self._identity())
        finally:
            link.unlink(missing_ok=True)
            real.rmdir()

    def test_trailing_newline_and_unknown_keys_preserved(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"newline key bytes")
        row = self._artifact_row(artifact["id"])
        store = self._store()
        bad_key = row.storage_key + "\n"
        store.delete(bad_key)
        with self.assertRaises(ArtifactError):
            store.read_bytes(bad_key, row.sha256, row.byte_length)
        self.assertTrue(store.verify_bytes(row.storage_key, row.sha256, row.byte_length))
        notes = store.root / "notes"
        notes.mkdir(exist_ok=True)
        keep = notes / "keep.bin"
        keep.write_bytes(b"unknown")
        self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()


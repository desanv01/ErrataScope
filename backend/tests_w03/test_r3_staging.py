"""W03 repair R3: bounded staging, short transactions and safe orphan cleanup."""

from __future__ import annotations

import os
import threading
import time
import unittest
import uuid
from datetime import timedelta

from sqlalchemy import select

from erratascope_service import services
from erratascope_service.api import create_app
from erratascope_service.artifacts import ArtifactStore, reconcile_orphans
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.storage_identity import database_identity
from erratascope_service.models import Artifact, UploadStaging

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


def store() -> ArtifactStore:
    return ArtifactStore(load_settings().artifact_root)


def session():
    return get_session_factory()()


def make_staging(project_id: uuid.UUID, *, lease_seconds: int, promote: bool = False):
    artifact_id = uuid.uuid4()
    artifact_store = store()
    upload = artifact_store.begin_staging(project_id, artifact_id)
    upload.write(b"staged synthetic bytes", load_settings().max_artifact_bytes)
    sha, length = upload.finish()
    key = upload.promote() if promote else artifact_store.staging_key(project_id, artifact_id)
    row = UploadStaging(
        artifact_id=artifact_id,
        project_id=project_id,
        actor_id=H.subject_for("user-a"),
        staging_key=artifact_store.staging_key(project_id, artifact_id),
        state="active",
        lease_until=services.utcnow() + timedelta(seconds=lease_seconds),
        created_at=services.utcnow(),
        updated_at=services.utcnow(),
    )
    db = session()
    try:
        db.add(row)
        db.commit()
    finally:
        db.close()
    return artifact_id, key, sha, length


class StagingUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="staging")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_db_rejection_after_staging_leaves_no_orphan(self) -> None:
        project_id = H.create_project(self.client, name="db-reject")
        os.environ["W03_TEST_UPLOAD_FAILPOINT"] = "db_reject"
        try:
            response = self.client.post(
                f"/api/v1/projects/{project_id}/artifacts",
                headers={
                    **H.auth("user-a"),
                    "Idempotency-Key": H.new_key(),
                    "Content-Type": "text/plain",
                    "X-Filename": "rejected.txt",
                },
                content=b"will be rejected by real DB CHECK",
            )
        finally:
            os.environ.pop("W03_TEST_UPLOAD_FAILPOINT", None)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(H.error_code(response), "UPLOAD_REJECTED")
        db = session()
        try:
            rows = db.scalars(
                select(UploadStaging).where(
                    UploadStaging.project_id == uuid.UUID(project_id)
                )
            ).all()
            self.assertEqual(rows, [])
            artifacts = db.scalars(
                select(Artifact).where(Artifact.project_id == uuid.UUID(project_id))
            ).all()
            self.assertEqual(artifacts, [])
        finally:
            db.close()
        keys = [key for _kind, key, _path in store().iter_owned_files() if project_id.replace("-", "") in key]
        self.assertEqual(keys, [])

    def test_streaming_file_and_short_transactions(self) -> None:
        body = H.upload_text(self.client, self.project_id, b"stream me\n")
        db = session()
        try:
            rows = db.scalars(
                select(UploadStaging).where(UploadStaging.artifact_id == uuid.UUID(body["id"]))
            ).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].state, "finalized")
        finally:
            db.close()

    def test_non_ascii_filename_disposition(self) -> None:
        # Clients percent-encode the display name; the API stores and encodes it.
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/artifacts",
            headers={
                **H.auth("user-a"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "text/plain",
                "X-Filename": "r%C3%A9sum%C3%A9.txt",
            },
            content=b"unicode filename\n",
        )
        self.assertEqual(response.status_code, 201, response.text)
        artifact_id = response.json()["id"]
        content = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{artifact_id}/content",
            headers=H.auth("user-a"),
        )
        disposition = content.headers["content-disposition"]
        self.assertIn("filename*=UTF-8''", disposition)
        self.assertIn("r%C3%A9sum%C3%A9.txt", disposition)

    def test_no_length_oversize_stream_rejected(self) -> None:
        import dataclasses

        small = dataclasses.replace(load_settings(), max_artifact_bytes=8)
        from fastapi.testclient import TestClient

        with TestClient(create_app(small)) as client:
            project_id = H.create_project(client, name="chunked-limit")
            response = client.post(
                f"/api/v1/projects/{project_id}/artifacts",
                headers={
                    **H.auth("user-a"),
                    "Idempotency-Key": H.new_key(),
                    "Content-Type": "text/plain",
                },
                content=(chunk for chunk in (b"12345", b"6789")),
            )
            self.assertEqual(response.status_code, 413, response.text)
            self.assertEqual(H.error_code(response), "ARTIFACT_TOO_LARGE")


class OrphanReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = uuid.UUID(H.create_project(cls.client, name="orphans"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _reconcile(self, grace: int) -> dict:
        db = session()
        try:
            result = reconcile_orphans(db, store(), grace_seconds=grace)
            db.commit()
            return result
        finally:
            db.close()

    def test_stale_interrupted_staging_collected(self) -> None:
        artifact_id, key, _sha, _length = make_staging(self.project_id, lease_seconds=-5)
        path = store()._checked_path(key)
        self.assertTrue(path.exists())
        result = self._reconcile(grace=0)
        self.assertGreaterEqual(result["removed_files"], 1)
        self.assertFalse(path.exists())
        db = session()
        try:
            self.assertIsNone(db.get(UploadStaging, artifact_id))
        finally:
            db.close()

    def test_live_staging_survives(self) -> None:
        artifact_id, key, _sha, _length = make_staging(self.project_id, lease_seconds=120)
        path = store()._checked_path(key)
        self._reconcile(grace=0)
        self.assertTrue(path.exists())
        db = session()
        try:
            row = db.get(UploadStaging, artifact_id)
            self.assertEqual(row.state, "active")
        finally:
            db.close()

    def test_committed_bytes_survive_reconciliation(self) -> None:
        body = H.upload_text(self.client, str(self.project_id), b"committed survives\n")
        self._reconcile(grace=0)
        response = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{body['id']}/content",
            headers=H.auth("user-a"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"committed survives\n")

    def test_untracked_stale_file_collected_but_recent_kept(self) -> None:
        artifact_store = store()
        directory = artifact_store.staging_root / self.project_id.hex
        directory.mkdir(parents=True, exist_ok=True)
        stale = directory / f"{uuid.uuid4().hex}.part"
        stale.write_bytes(b"stale")
        old = time.time() - 3600
        os.utime(stale, (old, old))
        recent = directory / f"{uuid.uuid4().hex}.part"
        recent.write_bytes(b"recent")
        self._reconcile(grace=5)
        self.assertFalse(stale.exists())
        self.assertTrue(recent.exists())

    def test_symlink_is_not_followed_or_deleted(self) -> None:
        outside = store().root.parent / f"outside-{uuid.uuid4().hex}.txt"
        outside.write_bytes(b"outside data")
        directory = store().staging_root / self.project_id.hex
        directory.mkdir(parents=True, exist_ok=True)
        link = directory / f"{uuid.uuid4().hex}.part"
        try:
            os.symlink(outside, link)
        except (OSError, NotImplementedError):
            outside.unlink(missing_ok=True)
            self.skipTest("symlinks unavailable")
        try:
            self._reconcile(grace=0)
            self.assertTrue(outside.exists())
            self.assertTrue(link.is_symlink())
        finally:
            link.unlink(missing_ok=True)
            outside.unlink(missing_ok=True)

    def test_symlinked_staging_directory_rejected(self) -> None:
        project_id = uuid.uuid4()
        outside_dir = store().root.parent / f"outside-dir-{uuid.uuid4().hex}"
        outside_dir.mkdir()
        staging_parent = store().staging_root / project_id.hex
        try:
            os.symlink(outside_dir, staging_parent)
        except (OSError, NotImplementedError):
            outside_dir.rmdir()
            self.skipTest("symlinks unavailable")
        try:
            with self.assertRaises(Exception):
                store().begin_staging(project_id, uuid.uuid4())
        finally:
            staging_parent.unlink(missing_ok=True)
            outside_dir.rmdir()

    def test_concurrent_cleanup_does_not_delete_live_upload(self) -> None:
        artifact_id, key, sha, length = make_staging(self.project_id, lease_seconds=120, promote=True)
        path = store()._checked_path(key)
        results = []

        def cleanup() -> None:
            results.append(self._reconcile(grace=0))

        thread = threading.Thread(target=cleanup)
        thread.start()
        db = session()
        try:
            services.create_artifact_record(
                db,
                project_id=self.project_id,
                actor_id=H.subject_for("user-a"),
                artifact_id=artifact_id,
                storage_key=key,
                sha256=sha,
                byte_length=length,
                media_type="text/plain",
                original_name="concurrent.txt",
            )
            db.commit()
        finally:
            db.close()
        thread.join(timeout=30)
        self.assertTrue(path.exists())
        response = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{artifact_id}/content",
            headers=H.auth("user-a"),
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()



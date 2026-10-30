"""W03 repair-02 R2/R3: staging lease renewal, GC/finalizer safety, exact paths."""

from __future__ import annotations

import dataclasses
import os
import threading
import time
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from erratascope_service import jobs, services
from erratascope_service.api import create_app
from erratascope_service.artifacts import ArtifactStore, reconcile_orphans
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, Job, Outbox, StageResult, UploadStaging
from erratascope_service.storage_identity import database_identity

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


def store() -> ArtifactStore:
    settings = load_settings()
    return ArtifactStore(
        settings.artifact_root,
        database_identity=database_identity(settings.database_url),
    )


def session():
    return get_session_factory()()


class UploadRenewalTests(unittest.TestCase):
    def test_slow_upload_renews_staging_lease(self) -> None:
        settings = dataclasses.replace(load_settings(), staging_lease_seconds=3)
        old_slow = os.environ.get("W03_TEST_UPLOAD_SLOW_CHUNK_SECONDS")
        os.environ["W03_TEST_UPLOAD_SLOW_CHUNK_SECONDS"] = "1.5"
        try:
            with TestClient(create_app(settings)) as client:
                project_id = H.create_project(client, name="renew-upload")
                response = client.post(
                    f"/api/v1/projects/{project_id}/artifacts",
                    headers={
                        **H.auth("user-a"),
                        "Idempotency-Key": H.new_key(),
                        "Content-Type": "text/plain",
                    },
                    content=iter([b"first-chunk", b"second-chunk", b"last-chunk"]),
                )
                self.assertEqual(response.status_code, 201, response.text)
                content = client.get(
                    f"/api/v1/projects/{project_id}/artifacts/{response.json()['id']}/content",
                    headers=H.auth("user-a"),
                )
                self.assertEqual(content.content, b"first-chunksecond-chunklast-chunk")
        finally:
            if old_slow is None:
                os.environ.pop("W03_TEST_UPLOAD_SLOW_CHUNK_SECONDS", None)
            else:
                os.environ["W03_TEST_UPLOAD_SLOW_CHUNK_SECONDS"] = old_slow

    def test_expired_staging_cannot_finalize_upload(self) -> None:
        settings = dataclasses.replace(load_settings(), staging_lease_seconds=2)
        old_failpoint = os.environ.get("W03_TEST_UPLOAD_FAILPOINT")
        old_hold = os.environ.get("W03_TEST_UPLOAD_HOLD_SECONDS")
        os.environ["W03_TEST_UPLOAD_FAILPOINT"] = "hold_before_finalize"
        os.environ["W03_TEST_UPLOAD_HOLD_SECONDS"] = "4"
        with TestClient(create_app(settings)) as client:
            project_id = H.create_project(client, name="expire-upload")
            result = {}

            def upload() -> None:
                result["response"] = client.post(
                    f"/api/v1/projects/{project_id}/artifacts",
                    headers={
                        **H.auth("user-a"),
                        "Idempotency-Key": H.new_key(),
                        "Content-Type": "text/plain",
                    },
                    content=b"will lose its staging lease",
                )

            thread = threading.Thread(target=upload)
            try:
                thread.start()
                deadline = time.time() + 20
                row = None
                while time.time() < deadline:
                    db = session()
                    try:
                        row = db.scalars(
                            select(UploadStaging).where(
                                UploadStaging.project_id == uuid.UUID(project_id),
                                UploadStaging.state == "active",
                            )
                        ).first()
                    finally:
                        db.close()
                    if row is not None:
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(row)
                db = session()
                try:
                    db.execute(
                        update(UploadStaging)
                        .where(UploadStaging.artifact_id == row.artifact_id)
                        .values(lease_until=services.utcnow())
                    )
                    db.commit()
                    reconcile_orphans(db, store(), grace_seconds=0)
                    db.commit()
                finally:
                    db.close()
                thread.join(timeout=30)
            finally:
                thread.join(timeout=30)
                for name, value in (
                    ("W03_TEST_UPLOAD_FAILPOINT", old_failpoint),
                    ("W03_TEST_UPLOAD_HOLD_SECONDS", old_hold),
                ):
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
            response = result.get("response")
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(H.error_code(response), "STAGING_LEASE_LOST")
            db = session()
            try:
                artifacts = db.scalars(
                    select(Artifact).where(Artifact.project_id == uuid.UUID(project_id))
                ).all()
                self.assertEqual(artifacts, [])
                staging = db.scalars(
                    select(UploadStaging).where(
                        UploadStaging.project_id == uuid.UUID(project_id)
                    )
                ).all()
                self.assertEqual(staging, [])
            finally:
                db.close()


    def test_expired_staging_without_gc_rejected(self) -> None:
        settings = dataclasses.replace(load_settings(), staging_lease_seconds=2)
        old_failpoint = os.environ.get("W03_TEST_UPLOAD_FAILPOINT")
        old_hold = os.environ.get("W03_TEST_UPLOAD_HOLD_SECONDS")
        os.environ["W03_TEST_UPLOAD_FAILPOINT"] = "hold_before_finalize"
        os.environ["W03_TEST_UPLOAD_HOLD_SECONDS"] = "3"
        with TestClient(create_app(settings)) as client:
            project_id = H.create_project(client, name="expire-no-gc")
            key = H.new_key()
            result = {}

            def upload() -> None:
                result["response"] = client.post(
                    f"/api/v1/projects/{project_id}/artifacts",
                    headers={
                        **H.auth("user-a"),
                        "Idempotency-Key": key,
                        "Content-Type": "text/plain",
                    },
                    content=b"expired without collection",
                )

            thread = threading.Thread(target=upload)
            try:
                thread.start()
                deadline = time.time() + 20
                row = None
                while time.time() < deadline:
                    db = session()
                    try:
                        row = db.scalars(
                            select(UploadStaging).where(
                                UploadStaging.project_id == uuid.UUID(project_id),
                                UploadStaging.state == "active",
                            )
                        ).first()
                    finally:
                        db.close()
                    if row is not None:
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(row)
                db = session()
                try:
                    db.execute(
                        update(UploadStaging)
                        .where(UploadStaging.artifact_id == row.artifact_id)
                        .values(lease_until=services.utcnow() - __import__("datetime").timedelta(seconds=10))
                    )
                    db.commit()
                finally:
                    db.close()
                thread.join(timeout=30)
            finally:
                thread.join(timeout=30)
                for name, value in (
                    ("W03_TEST_UPLOAD_FAILPOINT", old_failpoint),
                    ("W03_TEST_UPLOAD_HOLD_SECONDS", old_hold),
                ):
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
            response = result.get("response")
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(H.error_code(response), "STAGING_LEASE_LOST")
            db = session()
            try:
                self.assertEqual(
                    db.scalars(
                        select(Artifact).where(Artifact.project_id == uuid.UUID(project_id))
                    ).all(),
                    [],
                )
                self.assertEqual(
                    db.scalars(
                        select(UploadStaging).where(
                            UploadStaging.project_id == uuid.UUID(project_id)
                        )
                    ).all(),
                    [],
                )
                from erratascope_service.models import IdempotencyRecord

                self.assertIsNone(
                    db.scalars(
                        select(IdempotencyRecord).where(
                            IdempotencyRecord.project_id == uuid.UUID(project_id),
                            IdempotencyRecord.key == key,
                        )
                    ).first()
                )
            finally:
                db.close()


class ReceiptStagingFencingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="receipt-stage-fence")
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"receipt stage fence\n")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _isolated_job(self) -> str:
        db = session()
        try:
            job = services.create_job(
                db,
                project_id=uuid.UUID(self.project_id),
                actor_id=H.subject_for("user-a"),
                artifact_id=uuid.UUID(self.artifact["id"]),
            )
            db.execute(
                update(Outbox)
                .where(Outbox.job_id == job.id)
                .values(available_at=services.utcnow() + timedelta(hours=1))
            )
            db.commit()
            return str(job.id)
        finally:
            db.close()

    def test_receipt_stage_expiry_with_valid_job_cannot_lose_committed_bytes(self) -> None:
        job_id = self._isolated_job()
        old_failpoint = os.environ.get("W03_TEST_FAILPOINT")
        old_hold = os.environ.get("W03_TEST_HOLD_SECONDS")
        os.environ["W03_TEST_FAILPOINT"] = "hold_after_stage"
        os.environ["W03_TEST_HOLD_SECONDS"] = "3"
        thread = threading.Thread(target=jobs.execute, args=(job_id,))
        try:
            thread.start()
            deadline = time.time() + 20
            row = None
            while time.time() < deadline:
                db = session()
                try:
                    row = db.scalars(
                        select(UploadStaging).where(
                            UploadStaging.owner_job_id == uuid.UUID(job_id),
                            UploadStaging.state == "active",
                        )
                    ).first()
                finally:
                    db.close()
                if row is not None:
                    break
                time.sleep(0.1)
            self.assertIsNotNone(row)
            db = session()
            try:
                db.execute(
                    update(UploadStaging)
                    .where(UploadStaging.artifact_id == row.artifact_id)
                    .values(lease_until=services.utcnow())
                )
                db.commit()
                result = jobs.reconcile_once(
                    dataclasses.replace(load_settings(), orphan_grace_seconds=0)
                )
                self.assertGreaterEqual(result["orphans_removed"], 0)
            finally:
                db.close()
            thread.join(timeout=30)
        finally:
            thread.join(timeout=30)
            if old_failpoint is None:
                os.environ.pop("W03_TEST_FAILPOINT", None)
            else:
                os.environ["W03_TEST_FAILPOINT"] = old_failpoint
            if old_hold is None:
                os.environ.pop("W03_TEST_HOLD_SECONDS", None)
            else:
                os.environ["W03_TEST_HOLD_SECONDS"] = old_hold
        db = session()
        try:
            job = db.get(Job, uuid.UUID(job_id))
            self.assertEqual(job.status, "succeeded", (job.error_code, job.attempt_count))
            stage = db.get(StageResult, (uuid.UUID(job_id), "receipt"))
            self.assertIsNotNone(stage)
            receipt = db.get(Artifact, stage.result_artifact_id)
            self.assertTrue(
                store().verify_bytes(receipt.storage_key, receipt.sha256, receipt.byte_length)
            )
        finally:
            db.close()


class ExactPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="exact-paths")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_unknown_notes_and_staging_contents_preserved(self) -> None:
        artifact_store = store()
        notes = artifact_store.root / "notes"
        notes.mkdir(exist_ok=True)
        keep = notes / "keep.bin"
        keep.write_bytes(b"unknown but not ours")
        old = time.time() - 3600
        os.utime(keep, (old, old))
        staging_unknown = artifact_store.staging_root / "notes"
        staging_unknown.mkdir(exist_ok=True)
        staging_keep = staging_unknown / "keep.part"
        staging_keep.write_bytes(b"staging unknown")
        os.utime(staging_keep, (old, old))
        db = session()
        try:
            reconcile_orphans(db, artifact_store, grace_seconds=0)
            db.commit()
        finally:
            db.close()
        self.assertTrue(keep.exists())
        self.assertTrue(staging_keep.exists())

    def test_internal_symlink_is_not_followed_or_deleted(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"symlink target\n")
        artifact_store = store()
        db = session()
        try:
            row = db.get(Artifact, uuid.UUID(artifact["id"]))
            target = artifact_store._checked_path(row.storage_key)
        finally:
            db.close()
        project_hex = uuid.UUID(self.project_id).hex
        link = artifact_store.staging_root / project_hex / f"{uuid.uuid4().hex}.part"
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, link)
        with self.assertRaises(Exception):
            artifact_store.read_bytes(
                link.relative_to(artifact_store.root).as_posix(), row.sha256, row.byte_length
            )
        db = session()
        try:
            reconcile_orphans(db, artifact_store, grace_seconds=0)
            db.commit()
        finally:
            db.close()
        self.assertTrue(link.is_symlink())
        self.assertTrue(target.exists())

    def test_symlinked_project_directory_rejected_for_new_uploads(self) -> None:
        artifact_store = store()
        project = uuid.uuid4()
        outside = artifact_store.root / f"outside-{uuid.uuid4().hex}"
        outside.mkdir()
        link = artifact_store.staging_root / project.hex
        os.symlink(outside, link)
        try:
            with self.assertRaises(Exception):
                artifact_store.begin_staging(project, uuid.uuid4())
        finally:
            link.unlink(missing_ok=True)
            outside.rmdir()

    def test_ambiguous_upload_commit_preserves_bytes(self) -> None:
        old = os.environ.get("W03_TEST_UPLOAD_FAILPOINT")
        os.environ["W03_TEST_UPLOAD_FAILPOINT"] = "ambiguous_after_commit"
        try:
            response = self.client.post(
                f"/api/v1/projects/{self.project_id}/artifacts",
                headers={
                    **H.auth("user-a"),
                    "Idempotency-Key": H.new_key(),
                    "Content-Type": "text/plain",
                },
                content=b"ambiguous but committed upload",
            )
        finally:
            if old is None:
                os.environ.pop("W03_TEST_UPLOAD_FAILPOINT", None)
            else:
                os.environ["W03_TEST_UPLOAD_FAILPOINT"] = old
        self.assertEqual(response.status_code, 201, response.text)
        content = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{response.json()['id']}/content",
            headers=H.auth("user-a"),
        )
        self.assertEqual(content.status_code, 200)
        self.assertEqual(content.content, b"ambiguous but committed upload")


if __name__ == "__main__":
    unittest.main()

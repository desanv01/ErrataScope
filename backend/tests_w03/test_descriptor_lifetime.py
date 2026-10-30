"""W03 repair-04 R1: deterministic descriptor ownership and cleanup."""

from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, update

from erratascope_service import jobs, services
from erratascope_service.api import create_app
from erratascope_service.artifacts import ArtifactStore
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, Job, Outbox, StageResult
from erratascope_service.storage_identity import (
    MARKER_NAME,
    StoreIdentityError,
    database_identity,
    write_identity,
)

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


SETTINGS = load_settings()


def session():
    return get_session_factory()()


def test_store_fds(root: Path) -> int:
    target = os.path.realpath(root)
    count = 0
    try:
        entries = os.listdir("/proc/self/fd")
    except OSError:
        raise AssertionError("real /proc/self/fd is required for descriptor tests")
    for name in entries:
        try:
            link = os.readlink(f"/proc/self/fd/{name}")
        except OSError:
            continue
        if link == target or link.startswith(target + os.sep):
            count += 1
    return count


def detached_identity_store(root: Path) -> ArtifactStore:
    return ArtifactStore(root, database_identity=database_identity(SETTINGS.database_url))


class ReceiptVerificationLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="fd-receipts")
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"descriptor receipt source\n")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _succeeded_job(self) -> str:
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
            job_id = str(job.id)
        finally:
            db.close()
        jobs.execute(job_id)
        return job_id

    def test_repeated_verify_receipt_is_bounded(self) -> None:
        job_id = self._succeeded_job()
        root = SETTINGS.artifact_root
        jobs.verify_receipt(SETTINGS, uuid.UUID(job_id))
        jobs.verify_receipt(SETTINGS, uuid.UUID(job_id))
        baseline = test_store_fds(root)
        for _ in range(12):
            self.assertTrue(jobs.verify_receipt(SETTINGS, uuid.UUID(job_id)))
        self.assertLessEqual(test_store_fds(root), baseline)
        db = session()
        try:
            stage = db.get(StageResult, (uuid.UUID(job_id), "receipt"))
            receipt = db.get(Artifact, stage.result_artifact_id)
            store = detached_identity_store(root)
            try:
                data = store.read_bytes(
                    receipt.storage_key, receipt.sha256, receipt.byte_length
                )
            finally:
                store.close()
            self.assertIn(self.artifact["sha256"].encode(), data)
        finally:
            db.close()

    def test_repeated_reconcile_with_receipt_is_bounded(self) -> None:
        job_id = self._succeeded_job()
        root = SETTINGS.artifact_root
        jobs.reconcile_once(SETTINGS)
        jobs.reconcile_once(SETTINGS)
        baseline = test_store_fds(root)
        for _ in range(8):
            jobs.reconcile_once(SETTINGS)
            self.assertLessEqual(test_store_fds(root), baseline)
        db = session()
        try:
            state = db.get(Job, uuid.UUID(job_id))
            self.assertEqual(state.status, "succeeded")
        finally:
            db.close()

    def test_missing_receipt_reconciliation_is_bounded(self) -> None:
        job_id = self._succeeded_job()
        db = session()
        try:
            stage = db.get(StageResult, (uuid.UUID(job_id), "receipt"))
            receipt = db.get(Artifact, stage.result_artifact_id)
            store = detached_identity_store(SETTINGS.artifact_root)
            try:
                path = store._checked_path(receipt.storage_key)
            finally:
                store.close()
        finally:
            db.close()
        path.unlink()
        root = SETTINGS.artifact_root
        baseline = test_store_fds(root)
        for _ in range(8):
            jobs.reconcile_once(SETTINGS)
            jobs.verify_receipt(SETTINGS, uuid.UUID(job_id))
            self.assertLessEqual(test_store_fds(root), baseline)

    def test_cancelled_execution_releases_store(self) -> None:
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
            job_id = str(job.id)
        finally:
            db.close()
        db = session()
        try:
            services.cancel_job(
                db, uuid.UUID(self.project_id), uuid.UUID(job_id), H.subject_for("user-a")
            )
            db.commit()
        finally:
            db.close()
        root = SETTINGS.artifact_root
        baseline = test_store_fds(root)
        for _ in range(8):
            jobs.execute(job_id)
            self.assertLessEqual(test_store_fds(root), baseline)


class ConstructionFailureLifetimeTests(unittest.TestCase):
    def test_identity_mismatch_constructor_releases_root_fd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w03-fd-identity-") as directory:
            root = Path(directory)
            store = detached_identity_store(root)
            store.close()
            baseline = test_store_fds(root)
            for _ in range(8):
                with self.assertRaises(StoreIdentityError):
                    ArtifactStore(root, database_identity="db-other")
            self.assertEqual(test_store_fds(root), baseline)

    def test_malformed_marker_constructor_releases_root_fd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w03-fd-marker-") as directory:
            root = Path(directory)
            (root / MARKER_NAME).write_text("{not-json", encoding="utf-8")
            baseline = test_store_fds(root)
            for _ in range(8):
                with self.assertRaises(StoreIdentityError):
                    ArtifactStore(root, database_identity="db-a")
            self.assertEqual(test_store_fds(root), baseline)

    def test_staging_symlink_and_duplicate_paths_release_fds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w03-fd-staging-") as directory:
            root = Path(directory)
            store = detached_identity_store(root)
            try:
                project_hex = uuid.uuid4().hex
                external = root / f"external-{uuid.uuid4().hex}"
                external.mkdir()
                link = root / ".staging" / project_hex
                os.symlink(external, link)
                baseline = test_store_fds(root)
                for _ in range(8):
                    with self.assertRaises(Exception):
                        store.begin_staging(uuid.UUID(project_hex), uuid.uuid4())
                self.assertEqual(test_store_fds(root), baseline)
                link.unlink()
                external.rmdir()
            finally:
                store.close()

        with tempfile.TemporaryDirectory(prefix="w03-fd-duplicate-") as directory:
            root = Path(directory)
            store = detached_identity_store(root)
            project = uuid.uuid4()
            artifact = uuid.uuid4()
            try:
                baseline = test_store_fds(root)
                for _ in range(8):
                    upload = store.begin_staging(project, artifact)
                    upload.write(b"first", 1024)
                    with self.assertRaises(Exception):
                        store.begin_staging(project, artifact)
                    upload.abort()
                self.assertEqual(test_store_fds(root), baseline)
            finally:
                store.close()

    def test_hook_and_open_failures_release_descriptors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w03-fd-hook-") as directory:
            root = Path(directory)
            project = uuid.uuid4()
            artifact = uuid.uuid4()
            baseline = test_store_fds(root)
            for point, action in (
                ("after_project_dir_open", "begin"),
                ("before_staging_create", "begin"),
                ("before_promote_rename", "promote"),
            ):
                def hook(current: str, expected: str = point, mode: str = action) -> None:
                    if current == expected:
                        raise RuntimeError("injected hook failure")

                store = ArtifactStore(
                    root,
                    database_identity=database_identity(SETTINGS.database_url),
                    fault_hook=hook,
                )
                try:
                    with self.assertRaises(RuntimeError):
                        if action == "begin":
                            store.begin_staging(project, artifact)
                        else:
                            upload = store.begin_staging(project, artifact)
                            upload.write(b"promotion", 1024)
                            upload.finish()
                            upload.promote()
                finally:
                    store.close()
            self.assertEqual(test_store_fds(root), baseline)


class ApplicationLifetimeTests(unittest.TestCase):
    def test_app_shutdown_closes_owned_store(self) -> None:
        from fastapi.testclient import TestClient

        root = SETTINGS.artifact_root
        with TestClient(create_app(SETTINGS)) as client:
            self.assertEqual(client.get("/health/live").status_code, 200)
            self.assertGreaterEqual(test_store_fds(root), 1)
        baseline = test_store_fds(root)
        with TestClient(create_app(SETTINGS)) as client:
            client.get("/health/live")
        self.assertLessEqual(test_store_fds(root), baseline)


if __name__ == "__main__":
    unittest.main()

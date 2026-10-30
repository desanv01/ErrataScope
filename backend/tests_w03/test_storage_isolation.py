"""W03 repair-02 R1: store/database identity isolation and main-data sentinel."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path

import httpx

from erratascope_service import jobs, services
from erratascope_service.artifacts import ArtifactStore, reconcile_orphans
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, UploadStaging
from erratascope_service.storage_identity import (
    MARKER_NAME,
    StoreIdentityError,
    database_identity,
    ensure_identity,
)

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


def test_store() -> ArtifactStore:
    settings = load_settings()
    return ArtifactStore(
        settings.artifact_root,
        database_identity=database_identity(settings.database_url),
    )


def app_api() -> tuple[str, str]:
    base = os.environ.get("W03_APP_API_URL")
    if not base:
        raise AssertionError("W03_APP_API_URL is required for the main-data sentinel")
    tokens = json.loads(Path("/local/dev-auth/tokens.json").read_text(encoding="utf-8"))
    return base.rstrip("/"), tokens["users"]["user-a"]["token"]


def main_request(client: httpx.Client, method: str, path: str, *, key=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if key:
        headers["Idempotency-Key"] = key
    return client.request(method, path, headers=headers, **kwargs)


class StoreIdentityTests(unittest.TestCase):
    def test_populated_store_requires_explicit_adoption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w03-identity-") as directory:
            root = Path(directory)
            (root / "keep.bin").write_bytes(b"sentinel")
            with self.assertRaises(StoreIdentityError) as context:
                ensure_identity(root, "db-a")
            self.assertEqual(context.exception.code, "STORE_IDENTITY_MISSING")
            marker = ensure_identity(root, "db-a", adopt=True)
            self.assertEqual(marker["database_identity"], "db-a")
            with self.assertRaises(StoreIdentityError) as mismatch:
                ensure_identity(root, "db-b")
            self.assertEqual(mismatch.exception.code, "STORE_IDENTITY_MISMATCH")

    def test_collector_refuses_mismatched_identity_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w03-collector-") as directory:
            root = Path(directory)
            store = ArtifactStore(root, database_identity="db-a")
            project_hex = uuid.uuid4().hex
            artifact_hex = uuid.uuid4().hex
            directory_path = root / project_hex
            directory_path.mkdir()
            sentinel = directory_path / f"{artifact_hex}.bin"
            sentinel.write_bytes(b"keep")
            session = get_session_factory()()
            try:
                with self.assertRaises(StoreIdentityError):
                    reconcile_orphans(
                        session,
                        store,
                        grace_seconds=0,
                        database_identity="db-b",
                    )
            finally:
                session.close()
            self.assertTrue(sentinel.exists())

    def test_test_root_is_physically_separate_from_application_root(self) -> None:
        settings = load_settings()
        self.assertIn("test-artifacts", str(settings.artifact_root))
        self.assertFalse(
            Path("/var/lib/erratascope/artifacts").resolve()
            == settings.artifact_root.resolve()
        )
        marker = settings.artifact_root / MARKER_NAME
        self.assertTrue(marker.exists())


class MainDataSentinelTests(unittest.TestCase):
    """Create main API objects, run isolated test reset/GC, then re-verify."""

    def test_main_artifact_and_receipt_survive_isolated_test_workflow(self) -> None:
        base, token = app_api()
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(base_url=base, timeout=30.0, headers=headers) as client:
            ready = client.get("/health/ready")
            self.assertEqual(ready.status_code, 200, ready.text)
            project = main_request(
                client,
                "POST",
                "/api/v1/projects",
                key=H.new_key(),
                json={"name": "repair-02-sentinel"},
            )
            self.assertEqual(project.status_code, 201, project.text)
            project_id = project.json()["id"]
            payload = b"repair-02 main sentinel artifact\n"
            artifact = main_request(
                client,
                "POST",
                f"/api/v1/projects/{project_id}/artifacts",
                key=H.new_key(),
                content=payload,
                headers={"Content-Type": "text/plain", "X-Filename": "sentinel.txt"},
            )
            self.assertEqual(artifact.status_code, 201, artifact.text)
            artifact_id = artifact.json()["id"]
            job = main_request(
                client,
                "POST",
                f"/api/v1/projects/{project_id}/jobs",
                key=H.new_key(),
                json={"kind": "artifact_digest", "artifact_id": artifact_id},
            )
            self.assertEqual(job.status_code, 202, job.text)
            job_id = job.json()["id"]
            deadline = time.time() + 120
            state = job.json()
            while time.time() < deadline:
                state = client.get(
                    f"/api/v1/projects/{project_id}/jobs/{job_id}"
                ).json()
                if state["status"] in ("succeeded", "failed", "cancelled"):
                    break
                time.sleep(1)
            self.assertEqual(state["status"], "succeeded", state)
            receipt_id = state["result_artifact_id"]
            first_artifact = client.get(
                f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/content"
            )
            first_receipt = client.get(
                f"/api/v1/projects/{project_id}/artifacts/{receipt_id}/content"
            )
            self.assertEqual(first_artifact.content, payload)
            artifact_digest = first_artifact.headers.get("etag")
            receipt_bytes = first_receipt.content
            receipt_hash = __import__("hashlib").sha256(receipt_bytes).hexdigest()

            # Complete isolated test-database reset plus test-store collector.
            H.reset_database()
            store = test_store()
            session = get_session_factory()()
            try:
                reconcile_orphans(session, store, grace_seconds=0)
                session.commit()
            finally:
                session.close()

            second_artifact = client.get(
                f"/api/v1/projects/{project_id}/artifacts/{artifact_id}/content"
            )
            second_receipt = client.get(
                f"/api/v1/projects/{project_id}/artifacts/{receipt_id}/content"
            )
            self.assertEqual(second_artifact.status_code, 200)
            self.assertEqual(second_artifact.content, payload)
            self.assertEqual(second_artifact.headers.get("etag"), artifact_digest)
            self.assertEqual(second_receipt.status_code, 200)
            self.assertEqual(second_receipt.content, receipt_bytes)
            self.assertEqual(
                __import__("hashlib").sha256(second_receipt.content).hexdigest(),
                receipt_hash,
            )
            self.assertEqual(second_receipt.content, receipt_bytes)
            evidence = {
                "schema_version": 1,
                "scope": "main application artifact+receipt across isolated test reset/GC",
                "project_id": project_id,
                "artifact_id": artifact_id,
                "receipt_artifact_id": receipt_id,
                "artifact_etag": artifact_digest,
                "artifact_sha256": __import__("hashlib").sha256(payload).hexdigest(),
                "receipt_sha256": receipt_hash,
                "before_after_artifact_equal": first_artifact.content == second_artifact.content,
                "before_after_receipt_equal": first_receipt.content == second_receipt.content,
                "passed": True,
            }
            output = Path(os.environ.get("W03_SENTINEL_OUTPUT", "/local/sentinel-attempt-05.json"))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


class ActualSessionOwnershipTests(unittest.TestCase):
    def test_collector_derives_app_session_identity_and_refuses_without_hint(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        test_identity = database_identity(load_settings().database_url)
        with tempfile.TemporaryDirectory(prefix="w03-session-store-") as directory:
            root = Path(directory)
            store = ArtifactStore(root, database_identity=test_identity)
            project_id = uuid.uuid4()
            artifact_id = uuid.uuid4()
            db = get_session_factory()()
            try:
                services.create_project(
                    db,
                    actor_id=H.subject_for("user-a"),
                    name="session-owner",
                    project_id=project_id,
                )
                key, sha, length = store.put_bytes(
                    project_id, artifact_id, b"owned sentinel bytes", max_bytes=1024
                )
                services.create_artifact_record(
                    db,
                    project_id=project_id,
                    actor_id=H.subject_for("user-a"),
                    artifact_id=artifact_id,
                    storage_key=key,
                    sha256=sha,
                    byte_length=length,
                    media_type="text/plain",
                    original_name="sentinel.txt",
                )
                db.commit()
            finally:
                db.close()
            app_url = os.environ.get("W03_APP_DATABASE_URL")
            self.assertTrue(app_url, "W03_APP_DATABASE_URL is required for the ownership probe")
            app_engine = create_engine(app_url)
            AppSession = sessionmaker(bind=app_engine)
            app_session = AppSession()
            try:
                # (a) omitted hint: derive from the actual app-DB session.
                with self.assertRaises(StoreIdentityError):
                    reconcile_orphans(app_session, store, grace_seconds=0)
                self.assertTrue(store.verify_bytes(key, sha, length))
                # (b) forged hint: the caller string cannot override the session.
                with self.assertRaises(StoreIdentityError):
                    reconcile_orphans(
                        app_session,
                        store,
                        grace_seconds=0,
                        database_identity=test_identity,
                    )
                self.assertTrue(store.verify_bytes(key, sha, length))
            finally:
                app_session.close()
                app_engine.dispose()

            # (c) service entry point with app DB settings against test storage.
            from erratascope_service.config import load_settings as current_settings
            import dataclasses

            app_settings = dataclasses.replace(current_settings(), database_url=app_url)
            with self.assertRaises(StoreIdentityError):
                jobs.reconcile_once(app_settings)
            self.assertTrue(store.verify_bytes(key, sha, length))
            store.close()


if __name__ == "__main__":
    unittest.main()



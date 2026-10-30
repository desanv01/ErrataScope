"""W03 artifact storage and API tests against real PostgreSQL and volume bytes."""

from __future__ import annotations

import dataclasses
import unittest

from sqlalchemy import select

from erratascope_service.artifacts import ArtifactStore
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.storage_identity import database_identity
from erratascope_service.models import Artifact

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client)
        cls.actor = H.subject_for("user-a")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _artifact_row(self, artifact_id: str) -> Artifact:
        session = get_session_factory()()
        try:
            return session.get(Artifact, __import__("uuid").UUID(artifact_id))
        finally:
            session.close()

    def test_roundtrip_metadata_and_content(self) -> None:
        payload = b"binary\x00synthetic artifact bytes\n"
        body = H.upload_text(self.client, self.project_id, payload)
        self.assertEqual(body["sha256"], __import__("hashlib").sha256(payload).hexdigest())
        metadata = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{body['id']}", headers=H.auth("user-a")
        )
        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(metadata.json()["byte_length"], len(payload))
        content = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{body['id']}/content",
            headers=H.auth("user-a"),
        )
        self.assertEqual(content.status_code, 200)
        self.assertEqual(content.content, payload)
        self.assertIn("attachment", content.headers["content-disposition"])
        self.assertEqual(content.headers["cache-control"], "private, no-store")
        self.assertEqual(content.headers["x-content-type-options"], "nosniff")

    def test_unsupported_media_type_rejected(self) -> None:
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/artifacts",
            headers={
                **H.auth("user-a"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "application/zip",
            },
            content=b"zip",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(H.error_code(response), "UNSUPPORTED_MEDIA_TYPE")

    def test_oversize_rejected_before_persisting(self) -> None:
        small = dataclasses.replace(load_settings(), max_artifact_bytes=32)
        from erratascope_service.api import create_app
        from fastapi.testclient import TestClient

        with TestClient(create_app(small)) as client:
            project_id = H.create_project(client)
            response = client.post(
                f"/api/v1/projects/{project_id}/artifacts",
                headers={
                    **H.auth("user-a"),
                    "Idempotency-Key": H.new_key(),
                    "Content-Type": "text/plain",
                },
                content=b"x" * 33,
            )
            self.assertEqual(response.status_code, 413)
            listing = client.get(
                f"/api/v1/projects/{project_id}/artifacts", headers=H.auth("user-a")
            )
            self.assertEqual(H.items(listing), [])

    def test_corrupted_bytes_detected(self) -> None:
        body = H.upload_text(self.client, self.project_id, b"integrity check\n")
        row = self._artifact_row(body["id"])
        settings = load_settings()
        store = ArtifactStore(
            settings.artifact_root,
            database_identity=database_identity(settings.database_url),
        )
        path = store._checked_path(row.storage_key)
        original = path.read_bytes()
        try:
            path.write_bytes(b"tampered bytes\n")
            response = self.client.get(
                f"/api/v1/projects/{self.project_id}/artifacts/{body['id']}/content",
                headers=H.auth("user-a"),
            )
            self.assertEqual(response.status_code, 500)
            self.assertEqual(H.error_code(response), "ARTIFACT_INTEGRITY")
        finally:
            path.write_bytes(original)

    def test_missing_bytes_detected(self) -> None:
        body = H.upload_text(self.client, self.project_id, b"missing check\n")
        row = self._artifact_row(body["id"])
        settings = load_settings()
        store = ArtifactStore(
            settings.artifact_root,
            database_identity=database_identity(settings.database_url),
        )
        path = store._checked_path(row.storage_key)
        original = path.read_bytes()
        try:
            path.unlink()
            response = self.client.get(
                f"/api/v1/projects/{self.project_id}/artifacts/{body['id']}/content",
                headers=H.auth("user-a"),
            )
            self.assertEqual(response.status_code, 500)
            self.assertEqual(H.error_code(response), "ARTIFACT_MISSING")
        finally:
            path.write_bytes(original)

    def test_foreign_project_artifact_hidden(self) -> None:
        body = H.upload_text(self.client, self.project_id, b"private\n")
        for user in ("user-b", "user-c"):
            response = self.client.get(
                f"/api/v1/projects/{self.project_id}/artifacts/{body['id']}", headers=H.auth(user)
            )
            self.assertEqual(response.status_code, 404)

    def test_review_hash_mismatch_rejected(self) -> None:
        body = H.upload_text(self.client, self.project_id, b"review hash\n")
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": body["id"],
                "content_hash": "0" * 64,
                "annotation": "wrong hash",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(H.error_code(response), "ARTIFACT_HASH_MISMATCH")


if __name__ == "__main__":
    unittest.main()




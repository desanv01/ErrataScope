"""W03 persistence tests: immutable bundles/versions, hashes and DB constraints."""

from __future__ import annotations

import json
import unittest
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError

from erratascope_domain import canonical, evaluate, parse_bundle

from erratascope_service import services
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, Bundle, DomainVersion

from tests import helpers as D
from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


class PersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.actor = H.subject_for("user-a")
        H.ensure_project(D.PROJECT, cls.actor)
        cls.fixture = json.loads((D.FIXTURE_DIR / "applicable.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _post_bundle(self, project_id: uuid.UUID, payload: dict):
        return self.client.post(
            f"/api/v1/projects/{project_id}/bundles",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json=payload,
        )

    def test_01_bundle_persists_with_domain_hash_and_reloads(self) -> None:
        domain_bundle = parse_bundle(self.fixture)
        expected_hash = canonical.bundle_input_hash(domain_bundle)
        response = self._post_bundle(D.PROJECT, self.fixture)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["input_hash"], expected_hash)
        self.assertEqual(body["evaluator_version"], "domain-v1")

        detail = self.client.get(
            f"/api/v1/projects/{D.PROJECT}/bundles/{body['id']}", headers=H.auth("user-a")
        )
        self.assertEqual(detail.status_code, 200)
        reloaded = parse_bundle(detail.json()["payload"])
        self.assertEqual(canonical.bundle_input_hash(reloaded), expected_hash)
        self.assertEqual(
            evaluate(reloaded).result_hash, evaluate(domain_bundle).result_hash
        )

        session = get_session_factory()()
        try:
            versions = session.scalar(
                select(func.count()).select_from(DomainVersion).where(DomainVersion.project_id == D.PROJECT)
            )
            members = session.scalar(select(func.count()).select_from(DomainVersion).where(DomainVersion.project_id == D.PROJECT))
            self.assertGreater(versions, 5)
            self.assertGreaterEqual(versions, 1)
            stored = session.scalar(select(Bundle).where(Bundle.id == uuid.UUID(body["id"])))
            self.assertEqual(stored.payload["project_id"], str(D.PROJECT))
        finally:
            session.close()

    def test_02_duplicate_bundle_is_idempotent_by_input_hash(self) -> None:
        first = self._post_bundle(D.PROJECT, self.fixture)
        second = self._post_bundle(D.PROJECT, self.fixture)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["id"], second.json()["id"])

    def test_03_altered_version_content_conflicts(self) -> None:
        altered = json.loads(json.dumps(self.fixture))
        altered["rules"][0]["consequence"] = "Altered synthetic consequence"
        response = self._post_bundle(D.PROJECT, altered)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(H.error_code(response), "DOMAIN_VERSION_CONFLICT")

    def test_04_bundle_project_mismatch_rejected(self) -> None:
        other = H.create_project(self.client, name="other-project")
        response = self._post_bundle(uuid.UUID(other), self.fixture)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(H.error_code(response), "PROJECT_MISMATCH")

    def test_05_invalid_bundle_rejected_with_diagnostics(self) -> None:
        broken = json.loads(json.dumps(self.fixture))
        broken["snapshot"]["component_instances"][0]["identity"]["manufacturer"] = None
        broken["rules"][0]["target"] = {"op": "eq", "selector": "unknown.selector", "value": {"kind": "text", "value": "x"}}
        response = self._post_bundle(D.PROJECT, broken)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(H.error_code(response), "BUNDLE_INVALID")
        self.assertGreaterEqual(len(response.json()["error"]["details"]), 1)

    def test_06_immutable_artifact_row_cannot_be_updated(self) -> None:
        artifact = H.upload_text(self.client, str(D.PROJECT))
        session = get_session_factory()()
        try:
            with self.assertRaises(DBAPIError) as context:
                session.execute(
                    update(Artifact)
                    .where(Artifact.id == uuid.UUID(artifact["id"]))
                    .values(sha256="0" * 64)
                )
                session.commit()
            self.assertIn("IMMUTABLE_TABLE", str(context.exception))
        finally:
            session.rollback()
            session.close()


if __name__ == "__main__":
    unittest.main()





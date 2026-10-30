"""W03 repair R1: current authorization before every replay and role boundary."""

from __future__ import annotations

import os
import unittest

from erratascope_service.config import ConfigError, load_settings

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


def membership(client, project_id: str, target: str, role: str, actor: str = "user-a"):
    return client.put(
        f"/api/v1/projects/{project_id}/members/{target}",
        headers={**H.auth(actor), "Idempotency-Key": H.new_key()},
        json={"role": role},
    )


def remove_membership(client, project_id: str, target: str, actor: str = "user-a"):
    return client.delete(
        f"/api/v1/projects/{project_id}/members/{target}",
        headers={**H.auth(actor), "Idempotency-Key": H.new_key()},
    )


class ReplayAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = H.client()
        self.client.__enter__()
        self.project_id = H.create_project(self.client)
        assert membership(self.client, self.project_id, str(H.subject_for("user-b")), "reviewer").status_code == 200
        assert membership(self.client, self.project_id, str(H.subject_for("user-c")), "editor").status_code == 200

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_current_member_replay_succeeds(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"replay auth\n")
        key = H.new_key()
        payload = {
            "artifact_id": artifact["id"],
            "content_hash": artifact["sha256"],
            "annotation": "replay auth",
        }
        first = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        replay = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(first.json()["id"], replay.json()["id"])

    def test_revoked_actor_replay_denied(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"revoked replay\n")
        key = H.new_key()
        payload = {
            "artifact_id": artifact["id"],
            "content_hash": artifact["sha256"],
            "annotation": "revoked",
        }
        created = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        removed = remove_membership(
            self.client, self.project_id, str(H.subject_for("user-b")), actor="user-a"
        )
        self.assertEqual(removed.status_code, 204, removed.text)
        replay = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(replay.status_code, 404)
        self.assertEqual(H.error_code(replay), "PROJECT_NOT_FOUND")

    def test_demoted_actor_replay_denied(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"demoted replay\n")
        key = H.new_key()
        payload = {
            "artifact_id": artifact["id"],
            "content_hash": artifact["sha256"],
            "annotation": "demoted",
        }
        created = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        demoted = membership(
            self.client, self.project_id, str(H.subject_for("user-b")), "viewer"
        )
        self.assertEqual(demoted.status_code, 200, demoted.text)
        replay = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(replay.status_code, 403)
        self.assertEqual(H.error_code(replay), "FORBIDDEN")

    def test_job_replay_denied_after_demotion(self) -> None:
        artifact = H.upload_text(self.client, self.project_id, b"job replay\n")
        key = H.new_key()
        payload = {"kind": "artifact_digest", "artifact_id": artifact["id"]}
        created = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs",
            headers={**H.auth("user-c"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(created.status_code, 202, created.text)
        demoted = membership(self.client, self.project_id, str(H.subject_for("user-c")), "viewer")
        self.assertEqual(demoted.status_code, 200, demoted.text)
        replay = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs",
            headers={**H.auth("user-c"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(replay.status_code, 403)
        self.assertEqual(H.error_code(replay), "FORBIDDEN")

    def test_create_project_replay_checks_continuing_access(self) -> None:
        key = H.new_key()
        payload = {"name": "revoked-create-replay"}
        created = self.client.post(
            "/api/v1/projects",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        project_id = created.json()["id"]
        added = membership(self.client, project_id, str(H.subject_for("user-a")), "owner", actor="user-b")
        self.assertEqual(added.status_code, 200, added.text)
        removed = remove_membership(self.client, project_id, str(H.subject_for("user-b")), actor="user-a")
        self.assertEqual(removed.status_code, 204, removed.text)
        replay = self.client.post(
            "/api/v1/projects",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(replay.status_code, 404)
        self.assertEqual(H.error_code(replay), "PROJECT_NOT_FOUND")


class RoleBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client)
        assert membership(cls.client, cls.project_id, str(H.subject_for("user-b")), "viewer").status_code == 200
        assert membership(cls.client, cls.project_id, str(H.subject_for("user-c")), "reviewer").status_code == 200

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_member_listing_owner_only(self) -> None:
        for user in ("user-b", "user-c"):
            response = self.client.get(
                f"/api/v1/projects/{self.project_id}/members", headers=H.auth(user)
            )
            self.assertEqual(response.status_code, 403, (user, response.text))
            self.assertEqual(H.error_code(response), "FORBIDDEN")
        owner = self.client.get(
            f"/api/v1/projects/{self.project_id}/members", headers=H.auth("user-a")
        )
        self.assertEqual(owner.status_code, 200)
        self.assertIn("items", owner.json())

    def test_viewer_cannot_write_but_can_read(self) -> None:
        read = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts", headers=H.auth("user-b")
        )
        self.assertEqual(read.status_code, 200)
        write = self.client.post(
            f"/api/v1/projects/{self.project_id}/artifacts",
            headers={
                **H.auth("user-b"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "text/plain",
            },
            content=b"denied",
        )
        self.assertEqual(write.status_code, 403)

    def test_editor_cannot_review(self) -> None:
        project_id = H.create_project(self.client, name="editor-review")
        assert membership(
            self.client, project_id, str(H.subject_for("user-b")), "editor"
        ).status_code == 200
        artifact = H.upload_text(self.client, project_id, b"editor review\n")
        response = self.client.post(
            f"/api/v1/projects/{project_id}/review-items",
            headers={
                **H.auth("user-b"),
                "Idempotency-Key": H.new_key(),
            },
            json={
                "artifact_id": artifact["id"],
                "content_hash": artifact["sha256"],
                "annotation": "editor cannot review",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_reviewer_cannot_write_artifacts(self) -> None:
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/artifacts",
            headers={
                **H.auth("user-c"),
                "Idempotency-Key": H.new_key(),
                "Content-Type": "text/plain",
            },
            content=b"reviewer cannot write",
        )
        self.assertEqual(response.status_code, 403)

    def test_jwt_allowlist_rejects_other_algorithms(self) -> None:
        old = os.environ.get("W03_JWT_ALGORITHMS")
        os.environ["W03_JWT_ALGORITHMS"] = "RS384"
        try:
            with self.assertRaises(ConfigError):
                load_settings()
        finally:
            if old is None:
                os.environ.pop("W03_JWT_ALGORITHMS", None)
            else:
                os.environ["W03_JWT_ALGORITHMS"] = old


if __name__ == "__main__":
    unittest.main()

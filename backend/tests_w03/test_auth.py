"""W03 authentication/authorization tests against the real local API."""

from __future__ import annotations

import dataclasses
import unittest
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from erratascope_service.auth import TokenVerifier
from erratascope_service.config import ConfigError, load_settings

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


class TokenVerificationTests(unittest.TestCase):
    def test_valid_token_verifies_subject(self) -> None:
        verifier = TokenVerifier(load_settings())
        self.assertEqual(verifier.verify(H.token_for("user-a")), H.subject_for("user-a"))

    def test_expired_token_rejected(self) -> None:
        claims = H.valid_claims(exp=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()))
        verifier = TokenVerifier(load_settings())
        with self.assertRaises(Exception) as context:
            verifier.verify(H.sign_claims(claims))
        self.assertIn("UNAUTHENTICATED", str(context.exception))

    def test_wrong_issuer_and_audience_rejected(self) -> None:
        verifier = TokenVerifier(load_settings())
        for claims in (
            H.valid_claims(iss="https://attacker.example"),
            H.valid_claims(aud="other-audience"),
        ):
            with self.subTest(claims=claims):
                with self.assertRaises(Exception):
                    verifier.verify(H.sign_claims(claims))

    def test_disallowed_algorithm_rejected(self) -> None:
        claims = H.valid_claims()
        token = jwt.encode(claims, "synthetic-hmac-secret", algorithm="HS256", headers={"kid": "x"})
        with self.assertRaises(Exception):
            TokenVerifier(load_settings()).verify(token)

    def test_missing_or_malformed_bearer_rejected(self) -> None:
        with H.client() as client:
            self.assertEqual(client.get("/api/v1/projects").status_code, 401)
            self.assertEqual(
                client.get(
                    "/api/v1/projects", headers={"Authorization": "Bearer not-a-token"}
                ).status_code,
                401,
            )

    def test_hosted_mode_fails_closed(self) -> None:
        hosted = dataclasses.replace(
            load_settings(),
            mode="hosted",
            jwks_url="https://example.test/jwks.json",
            issuer="https://example.test",
            jwks_path=None,
        )
        with self.assertRaises(ConfigError) as context:
            hosted.ensure_startable()
        self.assertEqual(context.exception.code, "HOSTED_STORAGE_NOT_READY")


class ProjectAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client)
        member = cls.client.post(
            f"/api/v1/projects/{cls.project_id}/members",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"actor_id": str(H.subject_for("user-b")), "role": "viewer"},
        )
        assert member.status_code == 201, member.text

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_foreign_user_gets_not_found(self) -> None:
        response = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts", headers=H.auth("user-c")
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(H.error_code(response), "PROJECT_NOT_FOUND")

    def test_viewer_can_read_but_not_write(self) -> None:
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
        self.assertEqual(H.error_code(write), "FORBIDDEN")

    def test_viewer_cannot_manage_members(self) -> None:
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/members",
            headers={**H.auth("user-b"), "Idempotency-Key": H.new_key()},
            json={"actor_id": str(uuid.uuid4()), "role": "viewer"},
        )
        self.assertEqual(response.status_code, 403)

    def test_mutations_require_idempotency_key(self) -> None:
        response = self.client.post(
            "/api/v1/projects", headers=H.auth("user-a"), json={"name": "missing-key"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(H.error_code(response), "IDEMPOTENCY_KEY_REQUIRED")


if __name__ == "__main__":
    unittest.main()


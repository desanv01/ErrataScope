"""W03 repair R2: bound routes, nested envelopes, server request IDs, pagination."""

from __future__ import annotations

import threading
import unittest
import uuid

from sqlalchemy import update

from erratascope_service import services
from erratascope_service.db import get_session_factory
from erratascope_service.models import Job, JobEvent, Membership

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


def put_role(client, project_id: str, target: str, role: str, actor: str = "user-a"):
    return client.put(
        f"/api/v1/projects/{project_id}/members/{target}",
        headers={**H.auth(actor), "Idempotency-Key": H.new_key()},
        json={"role": role},
    )


def delete_role(client, project_id: str, target: str, actor: str = "user-a"):
    return client.delete(
        f"/api/v1/projects/{project_id}/members/{target}",
        headers={**H.auth(actor), "Idempotency-Key": H.new_key()},
    )


def collect(client, path: str, headers: dict, limit: int) -> list[dict]:
    items: list[dict] = []
    cursor = None
    for _ in range(50):
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get(path, headers=headers, params=params)
        assert response.status_code == 200, response.text
        body = response.json()
        assert isinstance(body, dict) and "items" in body and "next_cursor" in body
        items.extend(body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    return items


class ProjectAndMembershipRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="routes")
        assert put_role(cls.client, cls.project_id, str(H.subject_for("user-b")), "viewer").status_code == 200

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_project_detail_route_and_foreign_denial(self) -> None:
        response = self.client.get(f"/api/v1/projects/{self.project_id}", headers=H.auth("user-a"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], self.project_id)
        self.assertEqual(response.json()["role"], "owner")
        fresh = H.create_project(self.client, name="foreign-detail")
        foreign = self.client.get(f"/api/v1/projects/{fresh}", headers=H.auth("user-c"))
        self.assertEqual(foreign.status_code, 404)

    def test_put_upserts_membership_and_returns_body(self) -> None:
        target = str(H.subject_for("user-c"))
        created = put_role(self.client, self.project_id, target, "reviewer")
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["role"], "reviewer")
        updated = put_role(self.client, self.project_id, target, "editor")
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["role"], "editor")
        viewer_list = self.client.get(
            f"/api/v1/projects/{self.project_id}/members", headers=H.auth("user-b")
        )
        self.assertEqual(viewer_list.status_code, 403)

    def test_delete_revokes_and_denies_next_request(self) -> None:
        target = str(H.subject_for("user-c"))
        assert put_role(self.client, self.project_id, target, "viewer").status_code == 200
        removed = delete_role(self.client, self.project_id, target)
        self.assertEqual(removed.status_code, 204, removed.text)
        self.assertEqual(removed.content, b"")
        denied = self.client.get(f"/api/v1/projects/{self.project_id}", headers=H.auth("user-c"))
        self.assertEqual(denied.status_code, 404)
        missing = delete_role(self.client, self.project_id, target)
        self.assertEqual(missing.status_code, 404, missing.text)

    def test_self_protections(self) -> None:
        self_change = put_role(
            self.client, self.project_id, str(H.subject_for("user-a")), "viewer"
        )
        self.assertEqual(self_change.status_code, 409)
        self.assertEqual(H.error_code(self_change), "SELF_MEMBERSHIP_CHANGE")
        self_remove = delete_role(self.client, self.project_id, str(H.subject_for("user-a")))
        self.assertEqual(self_remove.status_code, 409)
        self.assertEqual(H.error_code(self_remove), "SELF_REMOVAL")

    def test_member_pagination_is_stable(self) -> None:
        for user in ("user-b", "user-c"):
            put_role(self.client, self.project_id, str(H.subject_for(user)), "viewer")
        items = collect(self.client, f"/api/v1/projects/{self.project_id}/members", H.auth("user-a"), 2)
        actor_ids = [item["actor_id"] for item in items]
        self.assertEqual(len(actor_ids), len(set(actor_ids)))
        self.assertGreaterEqual(len(actor_ids), 3)


class ConcurrentOwnerTests(unittest.TestCase):
    def test_two_owners_cannot_remove_each_other(self) -> None:
        with H.client() as client:
            project_id = H.create_project(client)
            owner_b = str(H.subject_for("user-b"))
            self.assertEqual(put_role(client, project_id, owner_b, "owner").status_code, 200)
            results = []
            barrier = threading.Barrier(2)

            def remove_as(actor: str, target: str) -> None:
                with H.client() as thread_client:
                    barrier.wait()
                    response = thread_client.delete(
                        f"/api/v1/projects/{project_id}/members/{target}",
                        headers={**H.auth(actor), "Idempotency-Key": H.new_key()},
                    )
                    results.append(response.status_code)

            threads = [
                threading.Thread(target=remove_as, args=("user-a", owner_b)),
                threading.Thread(
                    target=remove_as, args=("user-b", str(H.subject_for("user-a")))
                ),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
            self.assertEqual(sorted(results)[0], 204)
            self.assertIn(sorted(results)[1], (403, 404, 409))
            session = get_session_factory()()
            try:
                count = session.query(Membership).filter_by(project_id=uuid.UUID(project_id)).count()
                self.assertGreaterEqual(count, 1)
            finally:
                session.close()


class ErrorEnvelopeTests(unittest.TestCase):
    def test_nested_error_and_server_uuid(self) -> None:
        with H.client() as client:
            response = client.get(
                "/api/v1/projects",
                headers={"Authorization": "Bearer invalid-token", "X-Request-ID": "caller-value"},
            )
            body = response.json()
            self.assertEqual(response.status_code, 401)
            self.assertIn("error", body)
            self.assertEqual(set(body["error"]), {"code", "message", "details"})
            self.assertEqual(body["error"]["code"], "UNAUTHENTICATED")
            request_id = body["request_id"]
            uuid.UUID(request_id)
            self.assertNotEqual(request_id, "caller-value")
            self.assertEqual(response.headers["x-request-id"], request_id)

    def test_validation_and_not_found_envelopes(self) -> None:
        with H.client() as client:
            invalid = client.get("/api/v1/projects?limit=0", headers=H.auth("user-a"))
            self.assertEqual(invalid.status_code, 422)
            self.assertEqual(H.error_code(invalid), "VALIDATION_ERROR")
            self.assertGreaterEqual(len(invalid.json()["error"]["details"]), 1)
            missing = client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=H.auth("user-a"))
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(H.error_code(missing), "PROJECT_NOT_FOUND")
            route_missing = client.get("/api/v1/does-not-exist", headers=H.auth("user-a"))
            self.assertEqual(route_missing.status_code, 404)
            self.assertEqual(H.error_code(route_missing), "NOT_FOUND")

    def test_invalid_and_excessive_limits(self) -> None:
        with H.client() as client:
            for limit in (0, 101, -1):
                response = client.get(f"/api/v1/projects?limit={limit}", headers=H.auth("user-a"))
                self.assertEqual(response.status_code, 422, limit)
                self.assertEqual(H.error_code(response), "VALIDATION_ERROR")
            bad_cursor = client.get(
                "/api/v1/projects?limit=2&cursor=not-a-cursor", headers=H.auth("user-a")
            )
            self.assertEqual(bad_cursor.status_code, 400)
            self.assertEqual(H.error_code(bad_cursor), "INVALID_CURSOR")


class PaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_ids = [H.create_project(cls.client, name=f"page-{i}") for i in range(5)]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_project_pagination_no_duplicates_or_omissions(self) -> None:
        items = collect(self.client, "/api/v1/projects", H.auth("user-a"), 2)
        ids = [item["id"] for item in items]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(self.project_ids) <= set(ids))

    def test_artifact_pagination(self) -> None:
        project_id = H.create_project(self.client, name="artifact-page")
        created = [
            H.upload_text(self.client, project_id, f"page-bytes-{i}\n".encode())["id"]
            for i in range(3)
        ]
        items = collect(
            self.client, f"/api/v1/projects/{project_id}/artifacts", H.auth("user-a"), 1
        )
        self.assertEqual([item["id"] for item in items], created)

    def test_job_events_cursor_and_limit(self) -> None:
        project_id = H.create_project(self.client, name="event-page")
        artifact = H.upload_text(self.client, project_id, b"event page\n")
        job = self.client.post(
            f"/api/v1/projects/{project_id}/jobs",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"kind": "artifact_digest", "artifact_id": artifact["id"]},
        ).json()
        session = get_session_factory()()
        try:
            row = session.get(Job, uuid.UUID(job["id"]))
            session.execute(update(Job).where(Job.id == row.id).values(next_event_seq=3))
            for seq, event_type in ((2, "running"), (3, "succeeded")):
                session.add(
                    JobEvent(
                        id=uuid.uuid4(),
                        project_id=row.project_id,
                        job_id=row.id,
                        seq=seq,
                        event_type=event_type,
                        payload={"status": event_type},
                        created_at=services.utcnow(),
                    )
                )
            session.commit()
        finally:
            session.close()
        collected = []
        cursor = None
        while True:
            params = {"limit": 1}
            if cursor is not None:
                params["after_seq"] = cursor
            response = self.client.get(
                f"/api/v1/projects/{project_id}/jobs/{job['id']}/events",
                headers=H.auth("user-a"),
                params=params,
            )
            body = response.json()
            self.assertEqual(len(body["items"]), 1)
            collected.extend(item["seq"] for item in body["items"])
            cursor = body["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(collected, [1, 2, 3])

    def test_review_event_pagination(self) -> None:
        project_id = H.create_project(self.client, name="review-page")
        artifact = H.upload_text(self.client, project_id, b"review events\n")
        item = self.client.post(
            f"/api/v1/projects/{project_id}/review-items",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": artifact["id"],
                "content_hash": artifact["sha256"],
                "annotation": "page events",
            },
        ).json()
        for revision in (0, 1):
            response = self.client.post(
                f"/api/v1/projects/{project_id}/review-items/{item['id']}/decisions",
                headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
                json={
                    "decision": "accepted",
                    "rationale": "page",
                    "expected_revision": revision,
                },
            )
            self.assertEqual(response.status_code, 201, response.text)
        page = self.client.get(
            f"/api/v1/projects/{project_id}/review-items/{item['id']}/events?limit=1",
            headers=H.auth("user-a"),
        ).json()
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["next_cursor"], 1)
        second = self.client.get(
            f"/api/v1/projects/{project_id}/review-items/{item['id']}/events?limit=1&after_seq=1",
            headers=H.auth("user-a"),
        ).json()
        self.assertEqual([row["revision"] for row in second["items"]], [2])
        self.assertIsNone(second["next_cursor"])

    def test_openapi_matches_new_surface(self) -> None:
        schema = self.client.get("/openapi.json").json()
        paths = schema["paths"]
        self.assertIn("put", paths["/api/v1/projects/{project_id}/members/{target_actor}"])
        self.assertIn("delete", paths["/api/v1/projects/{project_id}/members/{target_actor}"])
        self.assertIn("get", paths["/api/v1/projects/{project_id}"])
        event_schema = paths["/api/v1/projects/{project_id}/jobs/{job_id}/events"]["get"]
        self.assertIn("JobEventPage", str(event_schema["responses"]))
        self.assertIn("ErrorEnvelope", str(schema["components"]["schemas"]))


if __name__ == "__main__":
    unittest.main()

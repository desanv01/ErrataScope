"""W03 idempotency and optimistic review-concurrency tests."""

from __future__ import annotations

import threading
import unittest

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


class IdempotencyTests(unittest.TestCase):
    def test_same_key_same_body_replays(self) -> None:
        key = H.new_key()
        payload = {"name": "idempotent-project"}
        with H.client() as client:
            first = client.post(
                "/api/v1/projects",
                headers={**H.auth("user-a"), "Idempotency-Key": key},
                json=payload,
            )
            second = client.post(
                "/api/v1/projects",
                headers={**H.auth("user-a"), "Idempotency-Key": key},
                json=payload,
            )
            self.assertEqual(first.status_code, 201)
            self.assertEqual(second.status_code, 201)
            self.assertEqual(first.json()["id"], second.json()["id"])

    def test_same_key_different_body_conflicts(self) -> None:
        key = H.new_key()
        with H.client() as client:
            client.post(
                "/api/v1/projects",
                headers={**H.auth("user-a"), "Idempotency-Key": key},
                json={"name": "first-name"},
            )
            second = client.post(
                "/api/v1/projects",
                headers={**H.auth("user-a"), "Idempotency-Key": key},
                json={"name": "second-name"},
            )
            self.assertEqual(second.status_code, 409)
            self.assertEqual(H.error_code(second), "IDEMPOTENCY_CONFLICT")

    def test_concurrent_same_key_converges(self) -> None:
        key = H.new_key()
        payload = {"name": "concurrent-idempotency"}
        results = []
        barrier = threading.Barrier(2)

        def create() -> None:
            with H.client() as client:
                barrier.wait()
                response = client.post(
                    "/api/v1/projects",
                    headers={**H.auth("user-a"), "Idempotency-Key": key},
                    json=payload,
                )
                results.append((response.status_code, response.json()))

        threads = [threading.Thread(target=create) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertEqual([status for status, _ in results], [201, 201])
        self.assertEqual(results[0][1]["id"], results[1][1]["id"])


class ReviewConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client)
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"review candidate\n")
        response = cls.client.post(
            f"/api/v1/projects/{cls.project_id}/review-items",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": cls.artifact["id"],
                "content_hash": cls.artifact["sha256"],
                "annotation": "synthetic candidate",
            },
        )
        assert response.status_code == 201, response.text
        cls.item_id = response.json()["id"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _decision(self, client, revision: int, key: str | None = None):
        return client.post(
            f"/api/v1/projects/{self.project_id}/review-items/{self.item_id}/decisions",
            headers={**H.auth("user-a"), "Idempotency-Key": key or H.new_key()},
            json={
                "decision": "accepted",
                "rationale": "synthetic review",
                "expected_revision": revision,
            },
        )

    def test_stale_revision_rejected_and_event_recorded(self) -> None:
        # Seed a fresh item for this test's revision sequence.
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": self.artifact["id"],
                "content_hash": self.artifact["sha256"],
                "annotation": "stale revision sequence",
            },
        )
        item_id = response.json()["id"]
        first = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items/{item_id}/decisions",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"decision": "accepted", "rationale": "first", "expected_revision": 0},
        )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json()["revision"], 1)
        stale = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items/{item_id}/decisions",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"decision": "rejected", "rationale": "stale", "expected_revision": 0},
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(H.error_code(stale), "REVIEW_REVISION_CONFLICT")
        detail = self.client.get(
            f"/api/v1/projects/{self.project_id}/review-items/{item_id}", headers=H.auth("user-a")
        )
        self.assertEqual(detail.json()["item"]["current_revision"], 1)
        self.assertEqual([event["revision"] for event in detail.json()["events"]["items"]], [1])

    def test_concurrent_decisions_only_one_wins(self) -> None:
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/review-items",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": self.artifact["id"],
                "content_hash": self.artifact["sha256"],
                "annotation": "concurrent race",
            },
        )
        item_id = response.json()["id"]
        results = []
        barrier = threading.Barrier(2)

        def decide(decision: str) -> None:
            with H.client() as client:
                barrier.wait()
                response = client.post(
                    f"/api/v1/projects/{self.project_id}/review-items/{item_id}/decisions",
                    headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
                    json={
                        "decision": decision,
                        "rationale": f"race {decision}",
                        "expected_revision": 0,
                    },
                )
                results.append(response.status_code)

        threads = [
            threading.Thread(target=decide, args=("accepted",)),
            threading.Thread(target=decide, args=("rejected",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertEqual(sorted(results), [201, 409])


if __name__ == "__main__":
    unittest.main()



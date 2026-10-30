"""S01 submission backend tests: review authorization/concurrency, summary, evidence CLI."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from erratascope_service import jobs, services
from erratascope_service.db import get_session_factory
from erratascope_service.ingestion.cli import verify_evidence

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()


def session():
    return get_session_factory()()


class SubmissionBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name=f"s01-{uuid.uuid4().hex[:8]}")
        artifact = H.upload_text(cls.client, cls.project_id, b"source document\n")
        source = cls.client.post(
            f"/api/v1/projects/{cls.project_id}/sources",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={
                "artifact_id": artifact["id"],
                "document_id": "S01-DOC",
                "revision": "Rev 1",
                "manufacturer": "Test Manufacturer",
                "authority": "synthetic",
                "synthetic": True,
            },
        )
        assert source.status_code == 201, source.text
        cls.source = source.json()
        extraction = cls.client.post(
            f"/api/v1/projects/{cls.project_id}/sources/{cls.source['id']}/extractions",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            json={"selected_entries": ["2.9.99"], "mode": "offline"},
        )
        assert extraction.status_code == 202, extraction.text
        cls.extraction = extraction.json()
        jobs.execute(cls.extraction["job_id"])
        drafts = cls.client.get(
            f"/api/v1/extractions/{cls.extraction['id']}/drafts", headers=H.auth("user-a")
        ).json()["items"]
        cls.draft = drafts[0]
        database = session()
        try:
            services.add_member(
                database,
                project_id=uuid.UUID(cls.project_id),
                actor_id=H.subject_for("user-a"),
                new_actor=H.subject_for("user-b"),
                role="reviewer",
            )
            services.add_member(
                database,
                project_id=uuid.UUID(cls.project_id),
                actor_id=H.subject_for("user-a"),
                new_actor=H.subject_for("user-c"),
                role="editor",
            )
            database.commit()
        finally:
            database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _current_revision(self) -> int:
        response = self.client.get(
            f"/api/v1/drafts/{self.draft['id']}/interpretation-reviews",
            headers=H.auth("user-a"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["current_revision"]

    def _review(self, user: str, decision: str = "reviewed", revision: int | None = None, key: str | None = None):
        return self.client.post(
            f"/api/v1/drafts/{self.draft['id']}/interpretation-reviews",
            headers={**H.auth(user), "Idempotency-Key": key or H.new_key()},
            json={
                "expected_revision": self._current_revision() if revision is None else revision,
                "expected_response_hash": self.draft["response_hash"],
                "decision": decision,
                "note": f"{decision} note from {user}",
            },
        )


class SubmissionContextTests(SubmissionBase):
    def test_context_and_summary_are_real_and_secret_free(self) -> None:
        response = self.client.get(
            f"/api/v1/projects/{self.project_id}/submission-context", headers=H.auth("user-a")
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["cases"])
        case = body["default_case"]
        self.assertEqual(case["kind"], "synthetic_offline")
        self.assertEqual(case["source_sha256"], self.source["sha256"])
        self.assertEqual(case["draft_id"], self.draft["id"])
        summary = self.client.get(
            f"/api/v1/drafts/{self.draft['id']}/review-summary?format=json",
            headers=H.auth("user-a"),
        )
        self.assertEqual(summary.status_code, 200, summary.text)
        payload = summary.json()
        self.assertEqual(payload["draft"]["recorded_label"], "Synthetic / offline example")
        self.assertGreaterEqual(len(payload["claims"]), 1)
        for claim in payload["claims"]:
            for citation in claim["citations"]:
                self.assertFalse(citation.get("missing"))
                self.assertEqual(citation["geometry_kind"], "synthetic_not_located")
                self.assertIsNone(citation["physical_page"])
        text_body = summary.text.lower()
        self.assertNotIn("authorization", text_body)
        self.assertNotIn("bearer", text_body)
        markdown = self.client.get(
            f"/api/v1/drafts/{self.draft['id']}/review-summary?format=markdown",
            headers=H.auth("user-a"),
        )
        self.assertEqual(markdown.status_code, 200)
        self.assertIn("# ErrataScope interpretation review summary", markdown.text)
        self.assertIn("Synthetic / offline example", markdown.text)


class InterpretationReviewTests(SubmissionBase):
    def setUp(self) -> None:
        database = session()
        try:
            services.upsert_membership(
                database,
                project_id=uuid.UUID(self.project_id),
                actor_id=H.subject_for("user-a"),
                target_actor=H.subject_for("user-b"),
                role="reviewer",
            )
            services.upsert_membership(
                database,
                project_id=uuid.UUID(self.project_id),
                actor_id=H.subject_for("user-a"),
                target_actor=H.subject_for("user-c"),
                role="editor",
            )
            database.commit()
        finally:
            database.close()

    def test_role_denial_stale_and_immutability(self) -> None:
        denied = self._review("user-c")
        self.assertEqual(denied.status_code, 403, denied.text)
        current = self._current_revision()
        first = self._review("user-b", revision=current)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json()["review"]["revision"], current + 1)
        stale = self._review("user-b", revision=current)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(H.error_code(stale), "REVIEW_REVISION_CONFLICT")
        after_first = self._current_revision()
        bad_hash = self.client.post(
            f"/api/v1/drafts/{self.draft['id']}/interpretation-reviews",
            headers={**H.auth("user-b"), "Idempotency-Key": H.new_key()},
            json={
                "expected_revision": after_first,
                "expected_response_hash": "0" * 64,
                "decision": "rejected",
                "note": "hash conflict",
            },
        )
        self.assertEqual(bad_hash.status_code, 409)
        self.assertEqual(H.error_code(bad_hash), "RESPONSE_HASH_CONFLICT")
        database = session()
        try:
            with self.assertRaises(DBAPIError):
                database.execute(
                    text("UPDATE erratascope.interpretation_reviews SET note='mutated'")
                )
                database.commit()
        finally:
            database.rollback()
            database.close()

    def test_idempotent_replay_and_revoked_role(self) -> None:
        key = H.new_key()
        current = self._current_revision()
        first = self._review("user-b", revision=current, key=key)
        self.assertEqual(first.status_code, 201, first.text)
        replay = self._review("user-b", revision=current, key=key)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json()["review"]["id"], first.json()["review"]["id"])
        conflict = self.client.post(
            f"/api/v1/drafts/{self.draft['id']}/interpretation-reviews",
            headers={**H.auth("user-b"), "Idempotency-Key": key},
            json={
                "expected_revision": current,
                "expected_response_hash": self.draft["response_hash"],
                "decision": "rejected",
                "note": "different body",
            },
        )
        self.assertEqual(conflict.status_code, 409)
        database = session()
        try:
            services.remove_membership(
                database,
                project_id=uuid.UUID(self.project_id),
                actor_id=H.subject_for("user-a"),
                target_actor=H.subject_for("user-b"),
            )
            database.commit()
        finally:
            database.close()
        revoked = self._review("user-b", key=key)
        self.assertIn(revoked.status_code, (403, 404))

    def test_concurrent_reviews_cannot_silently_overwrite(self) -> None:
        results: list[int] = []
        current = self._current_revision()

        def attempt() -> None:
            response = self._review("user-b", revision=current)
            results.append(response.status_code)

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [201, 409])

    def test_review_and_idempotency_receipt_roll_back_together(self) -> None:
        before = self._current_revision()
        with patch("erratascope_service.submission.api.services.store_idempotent", side_effect=RuntimeError("injected receipt failure")):
            with self.assertRaises(RuntimeError):
                self._review("user-a", revision=before)
        self.assertEqual(self._current_revision(), before)

    def test_concurrent_same_key_replays_one_review(self) -> None:
        current = self._current_revision()
        key = H.new_key()
        results = []
        barrier = threading.Barrier(2)
        def attempt():
            barrier.wait()
            results.append(self._review("user-a", revision=current, key=key))
        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertEqual([r.status_code for r in results], [201, 201])
        self.assertEqual(results[0].json()["review"]["id"], results[1].json()["review"]["id"])
        self.assertEqual(self._current_revision(), current + 1)


class EvidenceCommandTests(unittest.TestCase):
    def _manifest(self, root: Path, gate_status: str = "pass", file_status: str = "valid") -> tuple[Path, Path]:
        artifact = root / "artifact.json"
        artifact.write_text('{"ok": true}\n', encoding="utf-8")
        digest = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
        files = [{"path": str(artifact), "sha256": digest}]
        if file_status == "missing":
            files = [{"path": str(root / "absent.json"), "sha256": digest}]
        if file_status == "mismatch":
            files[0]["sha256"] = "0" * 64
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "status": "pass" if gate_status == "pass" else gate_status,
                    "gates": {"S01": {"status": gate_status}},
                    "files": files,
                }
            ),
            encoding="utf-8",
        )
        return manifest, artifact

    def test_truthful_evidence_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = [
                ("pass", "valid", 0),
                ("partial", "valid", 2),
                ("blocked", "valid", 2),
                ("fail", "valid", 2),
                ("pass", "missing", 2),
                ("pass", "mismatch", 2),
            ]
            for gate, file_status, expected in cases:
                manifest, _ = self._manifest(root, gate_status=gate, file_status=file_status)
                exit_code = verify_evidence(str(manifest))
                self.assertEqual(exit_code, expected, f"{gate}/{file_status}")

    def test_malformed_and_empty_manifests_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malformed = root / "bad.json"
            malformed.write_text("{not json", encoding="utf-8")
            self.assertEqual(verify_evidence(str(malformed)), 2)
            empty = root / "empty.json"
            empty.write_text("{}", encoding="utf-8")
            self.assertEqual(verify_evidence(str(empty)), 2)
            empty_files = root / "empty-files.json"
            empty_files.write_text(
                json.dumps({"status": "pass", "gates": {"X": {"status": "pass"}}, "files": []}),
                encoding="utf-8",
            )
            self.assertEqual(verify_evidence(str(empty_files)), 2)

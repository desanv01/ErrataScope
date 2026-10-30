"""W03 repair R4: durable receipts, heartbeat/attempt fencing and outbox claims."""

from __future__ import annotations

import os
import threading
import time
import unittest
import uuid
from datetime import timedelta

from sqlalchemy import select, update

from erratascope_service import jobs, services
from erratascope_service.artifacts import ArtifactStore
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.storage_identity import database_identity
from erratascope_service.models import Artifact, Job, JobAttempt, JobEvent, Outbox, StageResult

from tests_w03 import helpers as H

SETTINGS = load_settings()


def setUpModule() -> None:
    H.reset_database()


def session():
    return get_session_factory()()


def create_isolated_job(project_id: str, artifact_id: str) -> str:
    db = session()
    try:
        job = services.create_job(
            db,
            project_id=uuid.UUID(project_id),
            actor_id=H.subject_for("user-a"),
            artifact_id=uuid.UUID(artifact_id),
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


def job_row(job_id: str) -> Job:
    db = session()
    try:
        row = db.get(Job, uuid.UUID(job_id))
        db.expunge(row)
        return row
    finally:
        db.close()


class ReceiptDurabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="receipts")
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"receipt source\n")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _job(self) -> str:
        return create_isolated_job(self.project_id, self.artifact["id"])

    def test_ack_loss_after_commit_preserves_receipt(self) -> None:
        job_id = self._job()
        old = os.environ.get("W03_TEST_FAILPOINT")
        os.environ["W03_TEST_FAILPOINT"] = "ack_loss_after_commit"
        try:
            jobs.execute(job_id)
        finally:
            if old is None:
                os.environ.pop("W03_TEST_FAILPOINT", None)
            else:
                os.environ["W03_TEST_FAILPOINT"] = old
        state = job_row(job_id)
        self.assertEqual(state.status, "succeeded")
        self.assertEqual(state.attempt_count, 1)
        db = session()
        try:
            stage = db.get(StageResult, (uuid.UUID(job_id), "receipt"))
            self.assertIsNotNone(stage)
            receipt = db.get(Artifact, stage.result_artifact_id)
            data = ArtifactStore(
                SETTINGS.artifact_root,
                database_identity=database_identity(SETTINGS.database_url),
            ).read_bytes(
                receipt.storage_key, receipt.sha256, receipt.byte_length
            )
            self.assertIn(self.artifact["sha256"].encode(), data)
            stage_id = stage.result_artifact_id
        finally:
            db.close()
        jobs.execute(job_id)  # redelivery must not mint a replacement
        db = session()
        try:
            stages = db.scalars(
                select(StageResult).where(StageResult.job_id == uuid.UUID(job_id))
            ).all()
            self.assertEqual(len(stages), 1)
            self.assertEqual(stages[0].result_artifact_id, stage_id)
            events = db.scalars(
                select(JobEvent)
                .where(JobEvent.job_id == uuid.UUID(job_id))
                .order_by(JobEvent.seq)
            ).all()
            self.assertEqual([event.seq for event in events], list(range(1, len(events) + 1)))
            self.assertEqual([event.event_type for event in events].count("succeeded"), 1)
        finally:
            db.close()

    def test_corrupt_and_missing_receipt_detected_without_new_success(self) -> None:
        for fault in ("corrupt", "missing"):
            with self.subTest(fault=fault):
                job_id = self._job()
                jobs.execute(job_id)
                db = session()
                try:
                    stage = db.get(StageResult, (uuid.UUID(job_id), "receipt"))
                    receipt = db.get(Artifact, stage.result_artifact_id)
                    store = ArtifactStore(
                        SETTINGS.artifact_root,
                        database_identity=database_identity(SETTINGS.database_url),
                    )
                    path = store._checked_path(receipt.storage_key)
                    if fault == "corrupt":
                        path.write_bytes(b"corrupted")
                    else:
                        path.unlink()
                    original_id = stage.result_artifact_id
                finally:
                    db.close()
                self.assertFalse(jobs.verify_receipt(SETTINGS, uuid.UUID(job_id)))
                db = session()
                try:
                    state = db.get(Job, uuid.UUID(job_id))
                    self.assertEqual(state.status, "succeeded")
                    self.assertEqual(state.result_artifact_id, original_id)
                    events = db.scalars(
                        select(JobEvent).where(
                            JobEvent.job_id == uuid.UUID(job_id),
                            JobEvent.event_type == "receipt_integrity_failed",
                        )
                    ).all()
                    self.assertEqual(len(events), 1)
                    stages = db.scalars(
                        select(StageResult).where(StageResult.job_id == uuid.UUID(job_id))
                    ).all()
                    self.assertEqual(len(stages), 1)
                finally:
                    db.close()


class HeartbeatFencingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="heartbeat")
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"heartbeat source\n")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_expired_attempt_cannot_revive_lease(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        db = session()
        try:
            claimed = jobs.claim_job(db, uuid.UUID(job_id), SETTINGS)
            token = claimed["token"]
            db.execute(
                update(Job)
                .where(Job.id == uuid.UUID(job_id))
                .values(lease_until=services.utcnow() - timedelta(seconds=5))
            )
            db.commit()
        finally:
            db.close()
        self.assertFalse(jobs.heartbeat(SETTINGS, uuid.UUID(job_id), token))
        self.assertEqual(job_row(job_id).status, "running")
        jobs.reconcile_once(SETTINGS)
        self.assertEqual(job_row(job_id).status, "queued")
        db = session()
        try:
            new = jobs.claim_job(db, uuid.UUID(job_id), SETTINGS)
            self.assertIsNotNone(new)
            self.assertNotEqual(new["token"], token)
            self.assertIsNone(jobs._fence(db, uuid.UUID(job_id), token))
            self.assertIsNotNone(jobs._fence(db, uuid.UUID(job_id), new["token"]))
        finally:
            db.close()
        self.assertFalse(jobs.heartbeat(SETTINGS, uuid.UUID(job_id), token))
        db = session()
        try:
            db.execute(
                update(Job)
                .where(Job.id == uuid.UUID(job_id))
                .values(lease_until=services.utcnow() - timedelta(seconds=5))
            )
            db.commit()
        finally:
            db.close()
        jobs.reconcile_once(SETTINGS)
        jobs.execute(job_id)
        self.assertEqual(job_row(job_id).status, "succeeded")

    def test_real_heartbeat_thread_extends_lease(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        old_lease = os.environ.get("W03_LEASE_SECONDS")
        old_heartbeat = os.environ.get("W03_HEARTBEAT_SECONDS")
        old_failpoint = os.environ.get("W03_TEST_FAILPOINT")
        old_hold = os.environ.get("W03_TEST_HOLD_SECONDS")
        os.environ["W03_LEASE_SECONDS"] = "10"
        os.environ["W03_HEARTBEAT_SECONDS"] = "1"
        os.environ["W03_TEST_HOLD_SECONDS"] = "2.5"
        os.environ["W03_TEST_FAILPOINT"] = "hold_after_stage"
        thread = threading.Thread(target=jobs.execute, args=(job_id,))
        try:
            thread.start()
            deadline = time.time() + 30
            first_lease = None
            while time.time() < deadline:
                row = job_row(job_id)
                if row.status == "running" and row.lease_until is not None:
                    first_lease = row.lease_until
                    break
                time.sleep(0.1)
            self.assertIsNotNone(first_lease)
            time.sleep(2.0)
            extended = job_row(job_id).lease_until
            self.assertIsNotNone(extended)
            self.assertGreater(extended, first_lease)
            thread.join(timeout=30)
        finally:
            thread.join(timeout=30)
            for name, value in (
                ("W03_LEASE_SECONDS", old_lease),
                ("W03_HEARTBEAT_SECONDS", old_heartbeat),
                ("W03_TEST_FAILPOINT", old_failpoint),
                ("W03_TEST_HOLD_SECONDS", old_hold),
            ):
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        self.assertFalse(thread.is_alive())
        self.assertEqual(job_row(job_id).status, "succeeded")

    def test_cancellation_closes_attempt_and_blocks_commit(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        old_failpoint = os.environ.get("W03_TEST_FAILPOINT")
        old_hold = os.environ.get("W03_TEST_HOLD_SECONDS")
        os.environ["W03_TEST_FAILPOINT"] = "hold_after_stage"
        os.environ["W03_TEST_HOLD_SECONDS"] = "2"
        thread = threading.Thread(target=jobs.execute, args=(job_id,))
        try:
            thread.start()
            deadline = time.time() + 20
            while time.time() < deadline and job_row(job_id).status != "running":
                time.sleep(0.1)
            response = self.client.post(
                f"/api/v1/projects/{self.project_id}/jobs/{job_id}/cancel",
                headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
            )
            self.assertEqual(response.status_code, 200, response.text)
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
        state = job_row(job_id)
        self.assertEqual(state.status, "cancelled")
        db = session()
        try:
            attempts = db.scalars(
                select(JobAttempt).where(JobAttempt.job_id == uuid.UUID(job_id))
            ).all()
            self.assertEqual(len(attempts), 1)
            self.assertIsNotNone(attempts[0].ended_at)
            self.assertEqual(attempts[0].outcome, "cancelled")
            stage = db.get(StageResult, (uuid.UUID(job_id), "receipt"))
            self.assertIsNone(stage)
            self.assertIsNone(state.result_artifact_id)
        finally:
            db.close()


class RetryAndOutboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client, name="retries")
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"retry source\n")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def test_bounded_retries_and_delays(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        db = session()
        try:
            artifact = db.get(Artifact, uuid.UUID(self.artifact["id"]))
            store = ArtifactStore(
                        SETTINGS.artifact_root,
                        database_identity=database_identity(SETTINGS.database_url),
                    )
            path = store._checked_path(artifact.storage_key)
            original = path.read_bytes()
            path.unlink()
        finally:
            db.close()
        try:
            jobs.execute(job_id)
            first = job_row(job_id)
            self.assertEqual(first.status, "queued")
            self.assertEqual(first.attempt_count, 1)
            db = session()
            try:
                outbox = db.scalars(
                    select(Outbox)
                    .where(Outbox.job_id == uuid.UUID(job_id), Outbox.sent_at.is_(None))
                    .order_by(Outbox.dispatch_generation.desc())
                ).first()
                delay = (outbox.available_at - services.utcnow()).total_seconds()
                self.assertGreater(delay, 0)
                self.assertLessEqual(delay, 2.0)
            finally:
                db.close()
            jobs.execute(job_id)
            second = job_row(job_id)
            self.assertEqual(second.attempt_count, 2)
            jobs.execute(job_id)
            final = job_row(job_id)
            self.assertEqual(final.status, "failed")
            self.assertEqual(final.attempt_count, 3)
            self.assertIn(final.error_code, ("ARTIFACT_MISSING", "ARTIFACTINTEGRITY"))
            self.assertIsNone(final.current_attempt_token)
        finally:
            path.write_bytes(original)

    def test_concurrent_dispatch_finalizes_outbox_once(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        db = session()
        try:
            db.execute(
                update(Outbox)
                .where(Outbox.job_id == uuid.UUID(job_id))
                .values(available_at=services.utcnow())
            )
            db.commit()
        finally:
            db.close()
        results = []
        barrier = threading.Barrier(2)

        def dispatch() -> None:
            barrier.wait()
            results.append(jobs.dispatch_once(SETTINGS, limit=5))

        threads = [threading.Thread(target=dispatch) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        db = session()
        try:
            rows = db.scalars(select(Outbox).where(Outbox.job_id == uuid.UUID(job_id))).all()
            self.assertEqual(len(rows), 1)
            self.assertIsNotNone(rows[0].sent_at)
            self.assertIsNone(rows[0].claim_token)
        finally:
            db.close()
        jobs.execute(job_id)
        self.assertEqual(job_row(job_id).status, "succeeded")

    def test_outbox_finalization_is_fenced_by_claim_token(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        db = session()
        try:
            db.execute(
                update(Outbox)
                .where(Outbox.job_id == uuid.UUID(job_id))
                .values(available_at=services.utcnow())
            )
            db.commit()
        finally:
            db.close()
        original_enqueue = jobs.enqueue_job

        def hijacked_enqueue(settings, job_id_value):  # noqa: ANN001
            # Simulate a second dispatcher taking the claim, then losing it.
            other = session()
            try:
                other.execute(
                    update(Outbox)
                    .where(Outbox.job_id == job_id_value)
                    .values(
                        claim_token=uuid.uuid4(),
                        lease_until=services.utcnow() - timedelta(seconds=1),
                    )
                )
                other.commit()
            finally:
                other.close()
            original_enqueue(settings, job_id_value)

        from unittest import mock

        with mock.patch.object(jobs, "enqueue_job", side_effect=hijacked_enqueue):
            jobs.dispatch_once(SETTINGS, limit=5)
        db = session()
        try:
            row = db.scalars(select(Outbox).where(Outbox.job_id == uuid.UUID(job_id))).one()
            self.assertIsNone(row.sent_at)
        finally:
            db.close()
        jobs.dispatch_once(SETTINGS, limit=5)
        db = session()
        try:
            row = db.scalars(select(Outbox).where(Outbox.job_id == uuid.UUID(job_id))).one()
            self.assertIsNotNone(row.sent_at)
        finally:
            db.close()
        jobs.execute(job_id)
        self.assertEqual(job_row(job_id).status, "succeeded")

    def test_concurrent_reconciler_serializes_redispatch(self) -> None:
        job_id = create_isolated_job(self.project_id, self.artifact["id"])
        db = session()
        try:
            db.execute(
                update(Outbox)
                .where(Outbox.job_id == uuid.UUID(job_id))
                .values(sent_at=services.utcnow())
            )
            db.execute(
                update(Job)
                .where(Job.id == uuid.UUID(job_id))
                .values(updated_at=services.utcnow() - timedelta(seconds=10))
            )
            db.commit()
        finally:
            db.close()
        barrier = threading.Barrier(2)

        def reconcile() -> None:
            barrier.wait()
            jobs.reconcile_once(SETTINGS, limit=10)

        threads = [threading.Thread(target=reconcile) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        db = session()
        try:
            pending = db.scalars(
                select(Outbox).where(
                    Outbox.job_id == uuid.UUID(job_id), Outbox.sent_at.is_(None)
                )
            ).all()
            self.assertEqual(len(pending), 1)
            events = db.scalars(
                select(JobEvent).where(
                    JobEvent.job_id == uuid.UUID(job_id),
                    JobEvent.event_type == "redispatched",
                )
            ).all()
            self.assertEqual(len(events), 1)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()



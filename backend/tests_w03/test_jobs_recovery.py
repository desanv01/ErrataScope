"""W03 durable job tests: RQ delivery, tokens, outbox reconciliation and recovery."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
import uuid
from datetime import timedelta

from sqlalchemy import select, update

from erratascope_service import jobs, services
from erratascope_service.artifacts import ArtifactStore
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Job, Outbox, StageResult

from tests_w03 import helpers as H


def setUpModule() -> None:
    H.reset_database()

SETTINGS = load_settings()


def _session():
    return get_session_factory()()


def _job(job_id: str) -> Job:
    session = _session()
    try:
        return session.get(Job, uuid.UUID(job_id))
    finally:
        session.close()


def _create_job(client, project_id: str, artifact_id: str) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/jobs",
        headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
        json={"kind": "artifact_digest", "artifact_id": artifact_id},
    )
    assert response.status_code == 202, response.text
    return response.json()


def _suppress_dispatch(job_id: uuid.UUID) -> None:
    session = _session()
    try:
        session.execute(
            update(Outbox)
            .where(Outbox.job_id == job_id)
            .values(sent_at=services.utcnow(), claim_token=None, lease_until=None)
        )
        session.commit()
    finally:
        session.close()


def _wait_success(client, project_id: str, job_id: str, timeout: float = 90) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(
            f"/api/v1/projects/{project_id}/jobs/{job_id}", headers=H.auth("user-a")
        )
        body = response.json()
        if body["status"] in ("succeeded", "failed", "cancelled"):
            return body
        time.sleep(0.5)
    raise AssertionError("job did not reach a terminal state")


def _rq_burst() -> subprocess.CompletedProcess:
    code = (
        "from rq import Worker;"
        "from rq.serializers import JSONSerializer;"
        "from erratascope_service.config import load_settings;"
        "from erratascope_service.jobs import queue, broker;"
        "s=load_settings();"
        "Worker([queue(s)], connection=broker(s), serializer=JSONSerializer).work(burst=True)"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd="/app",
        env={**os.environ, "PYTHONPATH": "/app"},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


class DurableJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = H.client()
        cls.client.__enter__()
        cls.project_id = H.create_project(cls.client)
        cls.artifact = H.upload_text(cls.client, cls.project_id, b"durable digest source\n")
        H.ensure_project(uuid.uuid4(), H.subject_for("user-a"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def _new_job(self) -> dict:
        return _create_job(self.client, self.project_id, self.artifact["id"])

    def _isolated_job(self) -> dict:
        """Create a job whose outbox is parked in the future (no container race)."""
        session = _session()
        try:
            job = services.create_job(
                session,
                project_id=uuid.UUID(self.project_id),
                actor_id=H.subject_for("user-a"),
                artifact_id=uuid.UUID(self.artifact["id"]),
            )
            session.execute(
                update(Outbox)
                .where(Outbox.job_id == job.id)
                .values(available_at=services.utcnow() + timedelta(hours=1))
            )
            session.commit()
            return {"id": str(job.id), "status": job.status}
        finally:
            session.close()

    def test_successful_digest_flow_with_events_and_receipt(self) -> None:
        job = self._new_job()
        dispatched = jobs.dispatch_once(SETTINGS)
        self.assertGreaterEqual(dispatched["claimed"], 0)
        completed = _rq_burst()
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        state = _wait_success(self.client, self.project_id, job["id"])
        self.assertEqual(state["status"], "succeeded", state)
        self.assertEqual(state["attempt_count"], 1)

        events = H.items(self.client.get(
            f"/api/v1/projects/{self.project_id}/jobs/{job['id']}/events", headers=H.auth("user-a")
        ))
        self.assertEqual([event["event_type"] for event in events], ["queued", "running", "succeeded"])
        self.assertEqual([event["seq"] for event in events], [1, 2, 3])

        receipt = self.client.get(
            f"/api/v1/projects/{self.project_id}/artifacts/{state['result_artifact_id']}/content",
            headers=H.auth("user-a"),
        )
        self.assertEqual(receipt.status_code, 200)
        receipt_body = json.loads(receipt.content)
        self.assertEqual(receipt_body["sha256"], self.artifact["sha256"])
        self.assertEqual(receipt_body["byte_length"], self.artifact["byte_length"])
        self.assertEqual(receipt_body["artifact_id"], self.artifact["id"])

        stage = _session()
        try:
            row = stage.get(StageResult, (uuid.UUID(job["id"]), "receipt"))
            self.assertIsNotNone(row)
            self.assertEqual(row.input_hash, self.artifact["sha256"])
        finally:
            stage.close()

    def test_duplicate_delivery_is_noop(self) -> None:
        job = self._new_job()
        jobs.dispatch_once(SETTINGS)
        _rq_burst()
        state = _wait_success(self.client, self.project_id, job["id"])
        jobs.execute(job["id"])
        again = _job(job["id"])
        self.assertEqual(again.status, "succeeded")
        self.assertEqual(again.attempt_count, state["attempt_count"])
        session = _session()
        try:
            events = session.scalars(
                select(services.JobEvent)
                .where(services.JobEvent.job_id == uuid.UUID(job["id"]))
                .order_by(services.JobEvent.seq)
            ).all()
            self.assertEqual([event.event_type for event in events].count("succeeded"), 1)
        finally:
            session.close()

    def test_cancel_before_delivery_prevents_execution(self) -> None:
        job = self._isolated_job()
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs/{job['id']}/cancel",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "cancelled")
        jobs.execute(job["id"])
        self.assertEqual(_job(job["id"]).status, "cancelled")

    def test_stale_lease_is_reconciled_and_retried(self) -> None:
        job = self._isolated_job()
        session = _session()
        try:
            claimed = jobs.claim_job(session, uuid.UUID(job["id"]), SETTINGS)
            self.assertIsNotNone(claimed)
            token = claimed["token"]
            self.assertTrue(jobs.heartbeat(SETTINGS, uuid.UUID(job["id"]), token))
            session.execute(
                update(Job)
                .where(Job.id == uuid.UUID(job["id"]))
                .values(lease_until=services.utcnow() - timedelta(seconds=5))
            )
            session.commit()
        finally:
            session.close()
        self.assertFalse(jobs.heartbeat(SETTINGS, uuid.UUID(job["id"]), uuid.uuid4()))
        reconciled = jobs.reconcile_once(SETTINGS)
        self.assertGreaterEqual(reconciled["stale_requeued"], 1)
        self.assertEqual(_job(job["id"]).status, "queued")
        jobs.dispatch_once(SETTINGS)
        _rq_burst()
        state = _wait_success(self.client, self.project_id, job["id"])
        self.assertEqual(state["status"], "succeeded")
        self.assertEqual(state["attempt_count"], 2)

    def test_lost_broker_message_is_redispatched(self) -> None:
        job = self._isolated_job()
        _suppress_dispatch(uuid.UUID(job["id"]))
        session = _session()
        try:
            session.execute(
                update(Job)
                .where(Job.id == uuid.UUID(job["id"]))
                .values(updated_at=services.utcnow() - timedelta(seconds=10))
            )
            session.commit()
        finally:
            session.close()
        reconciled = jobs.reconcile_once(SETTINGS)
        self.assertGreaterEqual(reconciled["queued_redispatched"], 1)
        jobs.dispatch_once(SETTINGS)
        _rq_burst()
        state = _wait_success(self.client, self.project_id, job["id"])
        self.assertEqual(state["status"], "succeeded")

    def test_job_create_is_idempotent(self) -> None:
        key = H.new_key()
        payload = {"kind": "artifact_digest", "artifact_id": self.artifact["id"]}
        first = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs",
            headers={**H.auth("user-a"), "Idempotency-Key": key},
            json=payload,
        )
        second = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs",
            headers={**H.auth("user-a"), "Idempotency-Key": key},
            json=payload,
        )
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["id"], second.json()["id"])

    def test_cancelling_succeeded_job_conflicts(self) -> None:
        job = self._new_job()
        jobs.dispatch_once(SETTINGS)
        _rq_burst()
        _wait_success(self.client, self.project_id, job["id"])
        response = self.client.post(
            f"/api/v1/projects/{self.project_id}/jobs/{job['id']}/cancel",
            headers={**H.auth("user-a"), "Idempotency-Key": H.new_key()},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(H.error_code(response), "JOB_ALREADY_COMPLETED")


if __name__ == "__main__":
    unittest.main()





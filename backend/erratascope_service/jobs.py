"""Durable job execution with lease/attempt fencing and receipt preservation."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import uuid
from datetime import timedelta

from redis import Redis
from rq import Queue, Worker
from rq.serializers import JSONSerializer
from sqlalchemy import func, select, update

from . import services
from .artifacts import ArtifactError, ArtifactStore, reconcile_orphans
from .config import Settings, load_settings
from .db import get_session_factory
from .models import Artifact, Job, JobAttempt, JobEvent, Outbox, StageResult, UploadStaging
from .services import append_event, utcnow
from .storage_identity import database_identity

QUEUE_NAME = "w03"
logger = logging.getLogger("erratascope.jobs")


def broker(settings: Settings) -> Redis:
    return Redis.from_url(
        settings.broker_url,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def queue(settings: Settings) -> Queue:
    return Queue(settings.queue_name, connection=broker(settings), serializer=JSONSerializer())


def broker_ready(settings: Settings) -> bool:
    try:
        return bool(broker(settings).ping())
    except Exception:
        return False


def store_for(settings: Settings) -> ArtifactStore:
    return ArtifactStore(
        settings.artifact_root,
        database_identity=database_identity(settings.database_url),
    )


def enqueue_job(settings: Settings, job_id: uuid.UUID) -> None:
    queue(settings).enqueue(
        "erratascope_service.jobs.execute",
        str(job_id),
        job_timeout=300,
        result_ttl=0,
        failure_ttl=0,
    )


def _crash_if(failpoint: str, expected: str) -> None:
    if failpoint == expected:
        os._exit(42 if expected.startswith("crash_before") else 43)


def _fresh_job(session, job_id: uuid.UUID, *, lock: bool = True) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    if lock:
        stmt = stmt.with_for_update()
    return session.execute(
        stmt.execution_options(populate_existing=True)
    ).scalar_one_or_none()


def _attempt(session, job_id: uuid.UUID, token: uuid.UUID) -> JobAttempt | None:
    return session.execute(
        select(JobAttempt)
        .where(JobAttempt.job_id == job_id, JobAttempt.token == token)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()


def claim_job(session, job_id: uuid.UUID, settings: Settings):
    job = _fresh_job(session, job_id)
    if job is None:
        return None
    now = utcnow()
    if job.status in ("succeeded", "cancelled", "failed"):
        return None
    if job.status == "running" and job.lease_until is not None and job.lease_until > now:
        return None
    if job.attempt_count >= job.max_attempts:
        return None
    attempt_number = job.attempt_count + 1
    token = uuid.uuid4()
    job.status = "running"
    job.attempt_count = attempt_number
    job.current_attempt_token = token
    job.lease_until = now + timedelta(seconds=settings.lease_seconds)
    job.error_code = None
    job.updated_at = now
    session.add(
        JobAttempt(
            id=uuid.uuid4(),
            project_id=job.project_id,
            job_id=job.id,
            attempt_number=attempt_number,
            token=token,
            started_at=now,
            outcome="running",
        )
    )
    append_event(session, job, "running", {"attempt": attempt_number})
    session.commit()
    return {"job": job, "token": token, "attempt": attempt_number}


def heartbeat(settings: Settings, job_id: uuid.UUID, token: uuid.UUID) -> bool:
    """Extend a lease only when the attempt is current and not already expired."""
    factory = get_session_factory(settings)
    with factory() as session:
        job = _fresh_job(session, job_id)
        now = utcnow()
        if (
            job is None
            or job.status != "running"
            or job.current_attempt_token != token
            or job.lease_until is None
            or job.lease_until <= now
        ):
            session.rollback()
            return False
        job.lease_until = now + timedelta(seconds=settings.lease_seconds)
        session.execute(
            update(UploadStaging)
            .where(
                UploadStaging.owner_job_id == job_id,
                UploadStaging.owner_attempt_token == token,
                UploadStaging.state == "active",
            )
            .values(lease_until=job.lease_until)
        )
        session.commit()
        return True


class _HeartbeatLoop:
    """Bounded real heartbeat thread wired into execution."""

    def __init__(self, settings: Settings, job_id: uuid.UUID, token: uuid.UUID) -> None:
        self.settings = settings
        self.job_id = job_id
        self.token = token
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        interval = max(1, min(self.settings.heartbeat_seconds, self.settings.lease_seconds // 2))
        while not self._stop.wait(interval):
            try:
                if not heartbeat(self.settings, self.job_id, self.token):
                    return
            except Exception:  # noqa: BLE001 - heartbeat failure must not crash the job thread
                return

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def _fence(session, job_id: uuid.UUID, token: uuid.UUID) -> Job | None:
    job = _fresh_job(session, job_id)
    if job is None or job.status != "running":
        return None
    if job.current_attempt_token != token:
        return None
    if job.lease_until is None or job.lease_until <= utcnow():
        return None
    return job


def _finish_attempt(session, job_id: uuid.UUID, token: uuid.UUID, *, outcome: str, error_code=None) -> None:
    attempt = session.execute(
        select(JobAttempt)
        .where(JobAttempt.job_id == job_id, JobAttempt.token == token)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if attempt is not None and attempt.ended_at is None:
        attempt.ended_at = utcnow()
        attempt.outcome = outcome
        attempt.error_code = error_code


def _retry_or_fail(session, job: Job, token: uuid.UUID, error_code: str, settings: Settings) -> None:
    job = _fresh_job(session, job.id)
    if job is None or job.current_attempt_token != token or job.status != "running":
        return
    now = utcnow()
    job.current_attempt_token = None
    job.lease_until = None
    job.updated_at = now
    if job.attempt_count < job.max_attempts:
        job.status = "queued"
        job.error_code = error_code
        append_event(session, job, "retry_queued", {"error_code": error_code, "attempt": job.attempt_count})
        delay = settings.retry_delays_seconds[
            min(max(job.attempt_count - 1, 0), len(settings.retry_delays_seconds) - 1)
        ]
        _enqueue_outbox(session, job, available_in=timedelta(seconds=delay))
    else:
        job.status = "failed"
        job.error_code = error_code
        append_event(session, job, "failed", {"error_code": error_code, "attempt": job.attempt_count})
    _finish_attempt(session, job.id, token, outcome="failed", error_code=error_code)


def _enqueue_outbox(session, job: Job, *, available_in: timedelta = timedelta(0)) -> Outbox:
    """Must be called with the job row locked; serializes generation allocation."""
    generation = session.scalar(
        select(func.max(Outbox.dispatch_generation)).where(Outbox.job_id == job.id)
    ) or 0
    row = Outbox(
        id=uuid.uuid4(),
        project_id=job.project_id,
        job_id=job.id,
        dispatch_generation=generation + 1,
        available_at=utcnow() + available_in,
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def verify_receipt(settings: Settings, job_id: uuid.UUID, *, emit_event: bool = True) -> bool:
    """Verify a succeeded job's committed receipt; never mint a replacement."""
    factory = get_session_factory(settings)
    store = store_for(settings)
    session = factory()
    try:
        job = session.get(Job, job_id)
        if job is None:
            return False
        if job.status != "succeeded":
            return False
        if job.result_artifact_id is None:
            return False
        artifact = session.get(Artifact, job.result_artifact_id)
        if artifact is None:
            ok = False
        else:
            try:
                store.read_bytes(artifact.storage_key, artifact.sha256, artifact.byte_length)
                ok = True
            except ArtifactError:
                ok = False
        if not ok:
            job = _fresh_job(session, job_id)
            if job is not None:
                already = session.scalar(
                    select(JobEvent).where(
                        JobEvent.job_id == job_id, JobEvent.event_type == "receipt_integrity_failed"
                    )
                )
                if already is None and emit_event:
                    append_event(
                        session,
                        job,
                        "receipt_integrity_failed",
                        {"error_code": "RECEIPT_INTEGRITY", "result_artifact_id": str(job.result_artifact_id)},
                    )
                if job.error_code != "RECEIPT_INTEGRITY":
                    job.error_code = "RECEIPT_INTEGRITY"
                    job.updated_at = utcnow()
                session.commit()
        return ok
    finally:
        session.close()
        store.close()


def _settle_after_exception(
    settings: Settings,
    job_id: uuid.UUID,
    token: uuid.UUID,
    result_id: uuid.UUID,
    staged_key: str | None,
    error_code: str,
) -> None:
    """Re-establish state with a fresh session; never delete ambiguous commits."""
    factory = get_session_factory(settings)
    store = store_for(settings)
    session = factory()
    try:
        job = _fresh_job(session, job_id)
        if job is None:
            return
        stage = session.get(StageResult, (job_id, "receipt"))
        if (
            stage is not None
            and job.status == "succeeded"
            and job.result_artifact_id == stage.result_artifact_id
        ):
            # Acknowledged-loss/ambiguous success: committed receipt wins; keep bytes.
            artifact = session.get(Artifact, stage.result_artifact_id)
            if artifact is not None:
                try:
                    store.read_bytes(artifact.storage_key, artifact.sha256, artifact.byte_length)
                except ArtifactError:
                    append_event(session, job, "receipt_integrity_failed", {"error_code": "RECEIPT_INTEGRITY"})
            if staged_key and result_id != stage.result_artifact_id:
                store.delete(staged_key)
            staging = session.get(UploadStaging, result_id)
            if staging is not None:
                if result_id == stage.result_artifact_id:
                    staging.state = "finalized"
                else:
                    session.delete(staging)
            _finish_attempt(session, job_id, token, outcome="succeeded")
            session.commit()
            return
        # Proven uncommitted: no stage and no artifact row references our result.
        artifact = session.get(Artifact, result_id)
        if stage is None and artifact is None:
            if staged_key:
                store.delete(staged_key)
            staging = session.get(UploadStaging, result_id)
            if staging is not None:
                session.delete(staging)
            _retry_or_fail(session, job, token, error_code, settings)
            session.commit()
            return
        # Uncertain or partial: mark ambiguous and retain bytes for a human/review.
        staging = session.get(UploadStaging, result_id)
        if staging is not None and staging.state == "active":
            staging.state = "ambiguous"
        if job.status == "running" and job.current_attempt_token == token:
            _retry_or_fail(session, job, token, "AMBIGUOUS_COMMIT", settings)
        session.commit()
    except Exception:  # noqa: BLE001 - quarantine beats destructive guessing
        session.rollback()
    finally:
        session.close()
        store.close()


def execute(job_id: str) -> None:
    """RQ entry point with fenced commit, heartbeat and acknowledgement-loss safety."""
    settings = load_settings()
    store = store_for(settings)
    factory = get_session_factory(settings)
    job_uuid = uuid.UUID(job_id)
    session = factory()
    result_id = uuid.uuid4()
    staged_key: str | None = None
    token: uuid.UUID | None = None
    heartbeat_loop: _HeartbeatLoop | None = None
    failpoint = os.environ.get("W03_TEST_FAILPOINT", "") if settings.test_mode else ""
    try:
        claimed = claim_job(session, job_uuid, settings)
        if claimed is None:
            verify_receipt(settings, job_uuid)
            return
        job = claimed["job"]
        token = claimed["token"]
        heartbeat_loop = _HeartbeatLoop(settings, job_uuid, token)
        heartbeat_loop.start()
        project_id = job.project_id
        artifact_id = job.artifact_id

        artifact = session.get(Artifact, artifact_id)
        if artifact is None or artifact.project_id != project_id:
            raise ArtifactError("ARTIFACT_MISSING", "artifact row disappeared")
        data = store.read_bytes(artifact.storage_key, artifact.sha256, artifact.byte_length)
        digest = hashlib.sha256(data).hexdigest()
        _crash_if(failpoint, "crash_before_stage")

        receipt = {
            "schema_version": 1,
            "artifact_id": str(artifact.id),
            "sha256": digest,
            "byte_length": len(data),
            "job_id": str(job_uuid),
        }
        receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        session.add(
            UploadStaging(
                artifact_id=result_id,
                project_id=project_id,
                actor_id=job.actor_id,
                staging_key=store.staging_key(project_id, result_id),
                state="active",
                owner_kind="result",
                owner_job_id=job_uuid,
                owner_attempt_token=token,
                lease_until=utcnow() + timedelta(seconds=settings.lease_seconds),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        session.commit()
        upload = store.begin_staging(project_id, result_id)
        try:
            upload.write(receipt_bytes, settings.max_artifact_bytes)
            result_sha, result_length = upload.finish()
            staged_key = upload.promote()
        except Exception:
            upload.abort()
            raise
        if not store.verify_bytes(staged_key, result_sha, result_length):
            raise ArtifactError("ARTIFACT_INTEGRITY", "staged receipt bytes failed verification")
        _crash_if(failpoint, "crash_after_stage")
        if failpoint == "hold_after_stage":
            time.sleep(float(os.environ.get("W03_TEST_HOLD_SECONDS", "2")))

        job = _fence(session, job_uuid, token)
        if job is None:
            # Cancelled/stale/newer attempt: own bytes are not referenced.
            if staged_key:
                store.delete(staged_key)
                staged_key = None
            staging = session.get(UploadStaging, result_id)
            if staging is not None:
                session.delete(staging)
            session.commit()
            return

        staging = session.execute(
            select(UploadStaging)
            .where(UploadStaging.artifact_id == result_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        now = utcnow()
        if (
            staging is None
            or staging.state != "active"
            or staging.owner_kind != "result"
            or staging.owner_job_id != job_uuid
            or staging.owner_attempt_token != token
            or staging.lease_until <= now
        ):
            raise ArtifactError("STAGING_LEASE_LOST", "receipt staging ownership was lost")
        if not store.verify_bytes(staged_key, result_sha, result_length):
            raise ArtifactError("ARTIFACT_INTEGRITY", "receipt bytes changed before commit")

        existing_stage = session.get(StageResult, (job_uuid, "receipt"))
        if existing_stage is not None:
            if existing_stage.input_hash != artifact.sha256:
                raise ArtifactError("STAGE_INPUT_MISMATCH", "stage input hash does not match artifact")
            # Preserve the original committed receipt; discard this attempt's bytes.
            if staged_key:
                store.delete(staged_key)
                staged_key = None
            staging = session.get(UploadStaging, result_id)
            if staging is not None:
                session.delete(staging)
            job.status = "succeeded"
            job.result_artifact_id = existing_stage.result_artifact_id
            job.result_sha256 = existing_stage.result_sha256
            job.current_attempt_token = None
            job.lease_until = None
            job.updated_at = utcnow()
            append_event(session, job, "succeeded", {"result_artifact_id": str(existing_stage.result_artifact_id)})
            _finish_attempt(session, job_uuid, token, outcome="succeeded")
            session.commit()
            return

        session.add(
            Artifact(
                id=result_id,
                project_id=project_id,
                storage_key=staged_key,
                sha256=result_sha,
                byte_length=result_length,
                media_type="application/json",
                original_name=f"digest-{artifact.id}.json",
                state="ready",
                created_by=job.actor_id,
                created_at=utcnow(),
            )
        )
        session.flush()
        session.add(
            StageResult(
                project_id=project_id,
                job_id=job_uuid,
                stage_key="receipt",
                input_hash=artifact.sha256,
                result_artifact_id=result_id,
                result_sha256=result_sha,
                created_at=utcnow(),
            )
        )
        staging.state = "finalized"
        job.status = "succeeded"
        job.result_artifact_id = result_id
        job.result_sha256 = result_sha
        job.current_attempt_token = None
        job.lease_until = None
        job.updated_at = utcnow()
        append_event(
            session,
            job,
            "succeeded",
            {"result_artifact_id": str(result_id), "sha256": result_sha},
        )
        if not store.verify_bytes(staged_key, result_sha, result_length):
            raise ArtifactError("ARTIFACT_INTEGRITY", "receipt bytes changed before commit")
        _finish_attempt(session, job_uuid, token, outcome="succeeded")
        session.commit()
        staged_key = None
        if failpoint == "ack_loss_after_commit":
            raise RuntimeError("simulated acknowledgement loss after commit")
    except Exception as exc:  # noqa: BLE001 - settle durably
        try:
            session.rollback()
        except Exception:  # noqa: BLE001
            pass
        if token is not None:
            _settle_after_exception(
                settings,
                job_uuid,
                token,
                result_id,
                staged_key,
                getattr(exc, "code", None) or type(exc).__name__.upper(),
            )
    finally:
        if heartbeat_loop is not None:
            heartbeat_loop.stop()
        session.close()
        store.close()


# ---------------------------------------------------------------------------
# Dispatch and reconciliation
# ---------------------------------------------------------------------------
def dispatch_once(settings: Settings, limit: int = 20) -> dict:
    factory = get_session_factory(settings)
    dispatched = 0
    failed = 0
    with factory() as session:
        now = utcnow()
        rows = session.scalars(
            select(Outbox)
            .where(
                Outbox.sent_at.is_(None),
                Outbox.available_at <= now,
                (Outbox.claim_token.is_(None)) | (Outbox.lease_until < now),
            )
            .order_by(Outbox.available_at, Outbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        claims = []
        for row in rows:
            token = uuid.uuid4()
            row.claim_token = token
            row.lease_until = now + timedelta(seconds=30)
            claims.append((row.id, row.job_id, token))
        session.commit()
    for outbox_id, job_id, token in claims:
        try:
            enqueue_job(settings, job_id)
        except Exception:  # noqa: BLE001 - release claim for retry
            failed += 1
            with factory() as session:
                row = session.execute(
                    select(Outbox).where(Outbox.id == outbox_id).with_for_update()
                ).scalar_one_or_none()
                if row is not None and row.claim_token == token:
                    row.claim_token = None
                    row.lease_until = None
                    session.commit()
            continue
        with factory() as session:
            row = session.execute(
                select(Outbox)
                .where(Outbox.id == outbox_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalar_one_or_none()
            now = utcnow()
            if (
                row is not None
                and row.sent_at is None
                and row.claim_token == token
                and row.lease_until is not None
                and row.lease_until > now
            ):
                row.sent_at = now
                row.claim_token = None
                row.lease_until = None
                session.commit()
        dispatched += 1
    return {"claimed": len(claims), "dispatched": dispatched, "enqueue_failed": failed}


def reconcile_once(settings: Settings, limit: int = 50) -> dict:
    """Own the reconciliation store for exactly this pass."""
    store = store_for(settings)
    try:
        return _reconcile_once_with_store(settings, limit, store)
    finally:
        store.close()


def _reconcile_once_with_store(settings: Settings, limit: int, store: ArtifactStore) -> dict:
    factory = get_session_factory(settings)
    result = {
        "stale_requeued": 0,
        "stale_failed": 0,
        "queued_redispatched": 0,
        "terminal_outbox_closed": 0,
        "receipt_integrity_failed": 0,
        "orphans_removed": 0,
    }
    now = utcnow()
    with factory() as session:
        stale = session.scalars(
            select(Job)
            .where(Job.status == "running", Job.lease_until < now)
            .order_by(Job.lease_until)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for job in stale:
            token = job.current_attempt_token
            job.current_attempt_token = None
            job.lease_until = None
            job.updated_at = now
            if job.attempt_count < job.max_attempts:
                job.status = "queued"
                append_event(session, job, "lease_expired_requeue", {"attempt": job.attempt_count})
                _enqueue_outbox(session, job)
                result["stale_requeued"] += 1
            else:
                job.status = "failed"
                job.error_code = "LEASE_EXPIRED"
                append_event(session, job, "failed", {"error_code": "LEASE_EXPIRED"})
                result["stale_failed"] += 1
            if token is not None:
                _finish_attempt(session, job.id, token, outcome="failed", error_code="LEASE_EXPIRED")
        session.commit()

    with factory() as session:
        queued = session.scalars(
            select(Job)
            .where(Job.status == "queued", Job.updated_at <= now - timedelta(seconds=5))
            .order_by(Job.created_at, Job.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for job in queued:
            pending = session.scalar(
                select(func.count())
                .select_from(Outbox)
                .where(Outbox.job_id == job.id, Outbox.sent_at.is_(None))
            )
            if pending:
                continue
            outbox = _enqueue_outbox(session, job)
            append_event(session, job, "redispatched", {"generation": outbox.dispatch_generation})
            result["queued_redispatched"] += 1
        terminal = session.scalars(
            select(Outbox)
            .join(Job, Job.id == Outbox.job_id)
            .where(Job.status.in_(("succeeded", "failed", "cancelled")), Outbox.sent_at.is_(None))
            .limit(limit)
        ).all()
        for row in terminal:
            row.sent_at = now
            result["terminal_outbox_closed"] += 1
        session.commit()

    succeeded = []
    with factory() as session:
        succeeded = session.scalars(
            select(Job)
            .where(Job.status == "succeeded")
            .order_by(Job.updated_at)
            .limit(limit)
        ).all()
    for job in succeeded:
        if not verify_receipt(settings, job.id):
            result["receipt_integrity_failed"] += 1

    session = factory()
    try:
        orphan_result = reconcile_orphans(
            session,
            store,
            grace_seconds=settings.orphan_grace_seconds,
            database_identity=database_identity(settings.database_url),
        )
        session.commit()
        result["orphans_removed"] = orphan_result.get("removed_files", 0)
    finally:
        session.close()
    return result


def run_worker(settings: Settings) -> None:
    worker = Worker(
        [queue(settings)],
        connection=broker(settings),
        serializer=JSONSerializer,
    )
    worker.work(with_scheduler=False)


def run_dispatcher(settings: Settings) -> None:
    import signal

    stopping = {"value": False}

    def _stop(signum, frame):  # noqa: ANN001, ARG001
        stopping["value"] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while not stopping["value"]:
        try:
            dispatch_once(settings)
            reconcile_once(settings)
        except Exception:  # noqa: BLE001 - keep supervisor alive
            time.sleep(settings.dispatch_interval_seconds)
        time.sleep(settings.dispatch_interval_seconds)


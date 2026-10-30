"""Deterministic recovery helper used by infra/w03/recover.ps1.

Runs inside the W03 test container against the main local database and artifact
volume. Failpoints are only reachable through W03_TEST_MODE=1 and never via HTTP.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path

import httpx
from sqlalchemy import select, update

from erratascope_service import jobs, services
from erratascope_service.artifacts import ArtifactStore
from erratascope_service.config import load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.models import Artifact, Job, JobEvent, Outbox, StageResult

ACTOR = uuid.UUID(int=101)
SYNTHETIC = b"ErrataScope W03 recovery synthetic artifact\n"


def _settings():
    return load_settings()


def command_seed(args: argparse.Namespace) -> int:
    settings = _settings()
    session = get_session_factory(settings)()
    try:
        project = services.create_project(
            session, actor_id=ACTOR, name="recovery-synthetic", project_id=uuid.uuid4()
        )
        artifact_id = uuid.uuid4()
        store = ArtifactStore(settings.artifact_root)
        key, sha, length = store.put_bytes(
            project.id, artifact_id, SYNTHETIC, max_bytes=settings.max_artifact_bytes
        )
        services.create_artifact_record(
            session,
            project_id=project.id,
            actor_id=ACTOR,
            artifact_id=artifact_id,
            storage_key=key,
            sha256=sha,
            byte_length=length,
            media_type="text/plain",
            original_name="recovery.txt",
        )
        job = services.create_job(
            session, project_id=project.id, actor_id=ACTOR, artifact_id=artifact_id
        )
        session.commit()
        seed = {
            "project_id": str(project.id),
            "artifact_id": str(artifact_id),
            "job_id": str(job.id),
            "source_sha256": sha,
            "source_length": length,
        }
        Path(args.output).write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"seeded": True, "job_id": seed["job_id"]}))
        return 0
    finally:
        session.close()


def command_crash(args: argparse.Namespace) -> int:
    seed = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    jobs.execute(seed["job_id"])
    return 0


def command_recover(args: argparse.Namespace) -> int:
    settings = _settings()
    seed = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    session = get_session_factory(settings)()
    try:
        session.execute(
            update(Job)
            .where(Job.id == uuid.UUID(seed["job_id"]))
            .values(lease_until=services.utcnow() - timedelta(seconds=5))
        )
        session.commit()
    finally:
        session.close()
    reconciled = jobs.reconcile_once(settings)
    dispatched = jobs.dispatch_once(settings)
    print(json.dumps({"reconcile": reconciled, "dispatch": dispatched}))
    return 0


def _job_state(settings, seed) -> Job:
    session = get_session_factory(settings)()
    try:
        job = session.get(Job, uuid.UUID(seed["job_id"]))
        if job is None:
            raise SystemExit("seeded job missing")
        session.expunge(job)
        return job
    finally:
        session.close()


def command_verify(args: argparse.Namespace) -> int:
    settings = _settings()
    seed = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    deadline = time.time() + 120
    job = _job_state(settings, seed)
    while job.status not in ("succeeded", "failed", "cancelled") and time.time() < deadline:
        time.sleep(1)
        job = _job_state(settings, seed)
    checks = {
        "stage": "restart_after_crash",
        "job_status": job.status,
        "attempts": job.attempt_count,
        "job_succeeded": job.status == "succeeded",
        "attempt_count_at_least_2": job.attempt_count >= 2,
        "result_artifact_present": job.result_artifact_id is not None,
        "stage_result_committed": False,
        "events_ordered": False,
        "one_succeeded_event": False,
        "receipt_digest_matches": False,
    }
    if job.result_artifact_id is not None:
        session = get_session_factory(settings)()
        try:
            stage = session.get(StageResult, (job.id, "receipt"))
            receipt = session.get(Artifact, job.result_artifact_id)
            events = session.scalars(
                select(JobEvent)
                .where(JobEvent.job_id == job.id)
                .order_by(JobEvent.seq)
            ).all()
            checks["stage_result_committed"] = stage is not None
            checks["events_ordered"] = [event.seq for event in events] == list(
                range(1, len(events) + 1)
            )
            checks["one_succeeded_event"] = (
                [event.event_type for event in events].count("succeeded") == 1
            )
            if receipt is not None:
                store = ArtifactStore(settings.artifact_root)
                data = store.read_bytes(receipt.storage_key, receipt.sha256, receipt.byte_length)
                body = json.loads(data)
                checks["receipt_digest_matches"] = (
                    body["sha256"] == seed["source_sha256"]
                    and body["byte_length"] == seed["source_length"]
                )
        finally:
            session.close()
    passed = all(checks[name] for name in (
        "job_succeeded",
        "attempt_count_at_least_2",
        "result_artifact_present",
        "stage_result_committed",
        "events_ordered",
        "one_succeeded_event",
        "receipt_digest_matches",
    ))
    checks["passed"] = passed
    Path(args.output).write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "attempts": job.attempt_count}))
    return 0 if passed else 1


def command_http(args: argparse.Namespace) -> int:
    settings = _settings()
    seed = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    token = json.loads(Path("/local/dev-auth/tokens.json").read_text(encoding="utf-8"))["users"]["user-a"]["token"]
    base = settings.api_base_url
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, timeout=30.0, headers=headers) as client:
        ready = client.get("/health/ready")
        project = client.get(f"/api/v1/projects/{seed['project_id']}/artifacts")
        job = client.get(f"/api/v1/projects/{seed['project_id']}/jobs/{seed['job_id']}")
        artifact = client.get(
            f"/api/v1/projects/{seed['project_id']}/artifacts/{seed['artifact_id']}/content"
        )
        receipt = client.get(
            f"/api/v1/projects/{seed['project_id']}/artifacts/{job.json()['result_artifact_id']}/content"
        )
    receipt_body = json.loads(receipt.content)
    checks = {
        "stage": "api_restart_retrieval",
        "health_ready": ready.status_code == 200,
        "artifact_listing": project.status_code == 200,
        "job_retrieval": job.status_code == 200 and job.json()["status"] == "succeeded",
        "artifact_bytes_preserved": artifact.content == SYNTHETIC,
        "receipt_preserved": receipt.status_code == 200
        and receipt_body["sha256"] == seed["source_sha256"],
    }
    checks["passed"] = all(checks.values())
    Path(args.output).write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": checks["passed"]}))
    return 0 if checks["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed")
    seed.add_argument("--output", required=True)
    seed.set_defaults(func=command_seed)
    crash = sub.add_parser("crash")
    crash.add_argument("--seed", required=True)
    crash.set_defaults(func=command_crash)
    recover = sub.add_parser("recover")
    recover.add_argument("--seed", required=True)
    recover.set_defaults(func=command_recover)
    verify = sub.add_parser("verify")
    verify.add_argument("--seed", required=True)
    verify.add_argument("--output", required=True)
    verify.set_defaults(func=command_verify)
    http = sub.add_parser("http")
    http.add_argument("--seed", required=True)
    http.add_argument("--output", required=True)
    http.set_defaults(func=command_http)
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    raise SystemExit(arguments.func(arguments))


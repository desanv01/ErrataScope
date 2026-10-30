"""CLI for migrations, local auth bootstrap, workers, dispatch/reconcile and evidence."""

from __future__ import annotations

import argparse
import base64
from contextlib import closing
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from sqlalchemy import select

from . import services
from .artifacts import FINAL_RE, STAGING_RE, ArtifactStore
from .config import Settings, load_settings
from .db import database_ready, get_engine, get_session_factory, reset_engine
from .errors import ApiError, JobFailure
from .models import Artifact, UploadStaging
from .storage_identity import MARKER_NAME, database_identity, write_identity


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _alembic_config():
    from alembic.config import Config

    candidates = [
        Path("/app/alembic.ini"),
        Path(__file__).resolve().parent.parent / "alembic.ini",
    ]
    for candidate in candidates:
        if candidate.exists():
            return Config(str(candidate))
    raise SystemExit("alembic.ini not found")


def command_migrate(args: argparse.Namespace) -> int:
    from alembic import command

    settings = load_settings()
    if not settings.migrator_database_url:
        raise SystemExit("W03_MIGRATOR_DATABASE_URL is required for migrate")
    os.environ["W03_MIGRATOR_DATABASE_URL"] = settings.migrator_database_url
    command.upgrade(_alembic_config(), "head")
    print("migrations applied: head")
    return 0


def command_adopt_store(args: argparse.Namespace) -> int:
    """Explicit identity adoption for an existing store, validated against DB refs."""
    settings = load_settings()
    root = settings.artifact_root
    identity = database_identity(settings.database_url)
    marker = root / MARKER_NAME
    if marker.exists():
        data = json.loads(marker.read_text(encoding="utf-8"))
        if data.get("database_identity") != identity:
            print(
                json.dumps(
                    {
                        "adopted": False,
                        "reason": "STORE_IDENTITY_MISMATCH",
                        "existing_identity": data.get("database_identity"),
                        "requested_identity": identity,
                    }
                ),
                file=sys.stderr,
            )
            return 2
        print(json.dumps({"adopted": True, "already_bound": True, "database_identity": identity}))
        return 0
    with closing(ArtifactStore(root)) as store:
        session = get_session_factory(settings)()
        try:
            artifacts = set(session.scalars(select(Artifact.storage_key)))
            staging = session.scalars(select(UploadStaging)).all()
            references = set(artifacts)
            for row in staging:
                references.add(row.staging_key)
                references.add(store.final_key(row.project_id, row.artifact_id))
        finally:
            session.close()
        owned = store.iter_owned_files()
        unreferenced = sorted(key for _kind, key, _path in owned if key not in references)
        unknown_files = []
        for directory, dirnames, filenames in os.walk(root, followlinks=False):
            base = Path(directory)
            dirnames[:] = [name for name in dirnames if not (base / name).is_symlink()]
            for name in filenames:
                path = base / name
                if path.is_symlink():
                    continue
                key = path.relative_to(root).as_posix()
                if key == MARKER_NAME:
                    continue
                if not (FINAL_RE.match(key) or STAGING_RE.match(key)):
                    unknown_files.append(key)
        if unreferenced and not args.accept_unreferenced_generated:
            print(
                json.dumps(
                    {
                        "adopted": False,
                        "reason": "UNREFERENCED_GENERATED_FILES",
                        "count": len(unreferenced),
                        "sample": unreferenced[:20],
                    }
                ),
                file=sys.stderr,
            )
            return 2
        if unknown_files and not args.accept_unknown:
            print(
                json.dumps(
                    {
                        "adopted": False,
                        "reason": "UNKNOWN_FILES",
                        "count": len(unknown_files),
                        "sample": unknown_files[:20],
                    }
                ),
                file=sys.stderr,
            )
            return 2
        data = write_identity(root, identity)
        print(
            json.dumps(
                {
                    "adopted": True,
                    "database_identity": identity,
                    "store_id": data["store_id"],
                    "owned_files": len(owned),
                    "referenced_files": len(owned) - len(unreferenced),
                    "unreferenced_generated": len(unreferenced),
                    "unknown_files": len(unknown_files),
                },
                sort_keys=True,
            )
        )
        return 0

def command_bootstrap_local(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tokens_path = out / "tokens.json"
    jwks_path = out / "jwks.json"
    key_path = out / "private_key.pem"
    if tokens_path.exists() and not args.force:
        raise SystemExit(f"{tokens_path} already exists; refusing to overwrite without --force")
    settings = load_settings()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    kid = hashlib.sha256(public_der).hexdigest()[:16]
    numbers = key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": _b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                "e": _b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }
    users = {
        "user-a": uuid.UUID(int=101),
        "user-b": uuid.UUID(int=102),
        "user-c": uuid.UUID(int=103),
    }
    now = _utcnow()
    token_records = {}
    for name, subject in users.items():
        claims = {
            "sub": str(subject),
            "iss": settings.issuer,
            "aud": settings.audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=2)).timestamp()),
            "role": "authenticated",
        }
        token_records[name] = {
            "sub": str(subject),
            "token": jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid}),
        }
    key_path.write_bytes(private_pem)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    jwks_path.write_text(json.dumps(jwks, indent=2) + "\n", encoding="utf-8")
    tokens_path.write_text(
        json.dumps(
            {"issuer": settings.issuer, "audience": settings.audience, "users": token_records},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        tokens_path.chmod(0o600)
    except OSError:
        pass
    print(json.dumps({"jwks": str(jwks_path), "users": list(token_records), "kid": kid}, indent=2))
    return 0


def command_worker(args: argparse.Namespace) -> int:
    from .jobs import run_worker

    settings = load_settings()
    settings.ensure_startable()
    print("worker starting", flush=True)
    run_worker(settings)
    return 0


def command_dispatcher(args: argparse.Namespace) -> int:
    from .jobs import run_dispatcher

    settings = load_settings()
    settings.ensure_startable()
    run_dispatcher(settings)
    return 0


def command_dispatch(args: argparse.Namespace) -> int:
    from .jobs import dispatch_once

    settings = load_settings()
    settings.ensure_startable()
    print(json.dumps(dispatch_once(settings), sort_keys=True))
    return 0


def command_reconcile(args: argparse.Namespace) -> int:
    from .jobs import reconcile_once

    settings = load_settings()
    settings.ensure_startable()
    print(json.dumps(reconcile_once(settings), sort_keys=True))
    return 0


def command_health(args: argparse.Namespace) -> int:
    settings = load_settings()
    db_ok = database_ready(get_engine(settings))
    from .jobs import broker_ready

    broker_ok = broker_ready(settings)
    payload = {"database": db_ok, "broker": broker_ok, "mode": settings.mode}
    print(json.dumps(payload, sort_keys=True))
    return 0 if db_ok and broker_ok else 1


def command_export_openapi(args: argparse.Namespace) -> int:
    from .api import create_app

    app = create_app()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store = getattr(app.state, "store", None)
    if store is not None:
        store.close()
    print(f"wrote {output}")
    return 0


# ---------------------------------------------------------------------------
# Connected local verification (drives the real API, DB and worker)
# ---------------------------------------------------------------------------
class _Client:
    def __init__(self, base_url: str, token: str) -> None:
        import httpx

        self._httpx = httpx
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0, headers={"Authorization": f"Bearer {token}"})

    def close(self) -> None:
        self.client.close()

    def request(self, method: str, path: str, *, key: str | None = None, **kwargs):
        headers = kwargs.pop("headers", {})
        if key:
            headers["Idempotency-Key"] = key
        return self.client.request(method, path, headers=headers, **kwargs)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise JobFailure("VERIFY_FAILED", message)


def command_verify_foundation(args: argparse.Namespace) -> int:
    settings = load_settings()
    dev_dir = Path(args.auth_dir)
    tokens_raw = json.loads((dev_dir / "tokens.json").read_text(encoding="utf-8"))
    users = tokens_raw["users"]
    token_a = users["user-a"]["token"]
    token_b = users["user-b"]["token"]
    token_c = users["user-c"]["token"]
    base_url = args.api_url or settings.api_base_url
    observations: dict[str, object] = {
        "schema_version": 1,
        "generated_utc": _utcnow().isoformat().replace("+00:00", "Z"),
        "api_base_url": base_url,
        "checks": [],
        "secrets_recorded": False,
    }
    checks: list[dict[str, object]] = observations["checks"]  # type: ignore[assignment]

    def record(name: str, passed: bool, detail=None) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    client_a = _Client(base_url, token_a)
    client_b = _Client(base_url, token_b)
    client_c = _Client(base_url, token_c)
    try:
        ready = client_a.client.get("/health/ready")
        record("health_ready", ready.status_code == 200, {"status": ready.status_code})
        _require(ready.status_code == 200, "health/ready did not return 200")

        project_key = uuid.uuid4().hex
        project_body = {"name": f"synthetic-verify-{project_key[:8]}"}
        created = client_a.request("POST", "/api/v1/projects", key=project_key, json=project_body)
        _require(created.status_code == 201, f"project create returned {created.status_code}")
        project_id = created.json()["id"]
        replay = client_a.request("POST", "/api/v1/projects", key=project_key, json=project_body)
        record("idempotent_replay", replay.status_code == 201 and replay.json()["id"] == project_id)

        conflict = client_a.request(
            "POST", "/api/v1/projects", key=project_key, json={"name": "different"}
        )
        record("idempotency_conflict", conflict.status_code == 409, {"status": conflict.status_code})
        _require(conflict.status_code == 409, "changed idempotency body was not rejected")

        member = client_a.request(
            "POST",
            f"/api/v1/projects/{project_id}/members",
            key=uuid.uuid4().hex,
            json={"actor_id": users["user-b"]["sub"], "role": "viewer"},
        )
        _require(member.status_code == 201, f"membership create returned {member.status_code}")

        synthetic = b"ErrataScope W03 synthetic digest artifact\n"
        artifact = client_a.request(
            "POST",
            f"/api/v1/projects/{project_id}/artifacts",
            key=uuid.uuid4().hex,
            content=synthetic,
            headers={"Content-Type": "text/plain", "X-Filename": "synthetic-w03.txt"},
        )
        _require(artifact.status_code == 201, f"artifact upload returned {artifact.status_code}")
        artifact_body = artifact.json()
        _require(artifact_body["sha256"] == hashlib.sha256(synthetic).hexdigest(), "artifact hash mismatch")
        record("artifact_upload", True, {"byte_length": artifact_body["byte_length"]})
        content = client_a.client.get(
            f"/api/v1/projects/{project_id}/artifacts/{artifact_body['id']}/content"
        )
        record("artifact_roundtrip", content.status_code == 200 and content.content == synthetic)

        review = client_a.request(
            "POST",
            f"/api/v1/projects/{project_id}/review-items",
            key=uuid.uuid4().hex,
            json={
                "artifact_id": artifact_body["id"],
                "content_hash": artifact_body["sha256"],
                "annotation": "synthetic W03 review candidate",
            },
        )
        _require(review.status_code == 201, f"review item create returned {review.status_code}")
        review_id = review.json()["id"]
        decision_payload = {
            "decision": "accepted",
            "rationale": "synthetic local verification",
            "expected_revision": 0,
        }
        decision = client_a.request(
            "POST",
            f"/api/v1/projects/{project_id}/review-items/{review_id}/decisions",
            key=uuid.uuid4().hex,
            json=decision_payload,
        )
        _require(decision.status_code == 201, f"decision returned {decision.status_code}")
        stale = client_a.request(
            "POST",
            f"/api/v1/projects/{project_id}/review-items/{review_id}/decisions",
            key=uuid.uuid4().hex,
            json=decision_payload,
        )
        record("review_stale_denied", stale.status_code == 409, {"status": stale.status_code})
        _require(stale.status_code == 409, "stale review revision was not rejected")

        job = client_a.request(
            "POST",
            f"/api/v1/projects/{project_id}/jobs",
            key=uuid.uuid4().hex,
            json={"kind": "artifact_digest", "artifact_id": artifact_body["id"]},
        )
        _require(job.status_code == 202, f"job create returned {job.status_code}")
        job_id = job.json()["id"]
        deadline = time.time() + 90
        job_state = job.json()
        while time.time() < deadline:
            polled = client_a.client.get(f"/api/v1/projects/{project_id}/jobs/{job_id}")
            job_state = polled.json()
            if job_state["status"] in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(1)
        record(
            "job_completed",
            job_state["status"] == "succeeded",
            {"status": job_state["status"], "attempts": job_state["attempt_count"]},
        )
        _require(job_state["status"] == "succeeded", "job did not succeed")
        events = client_a.client.get(f"/api/v1/projects/{project_id}/jobs/{job_id}/events")
        event_list = events.json()["items"]
        event_types = [item["event_type"] for item in event_list]
        event_seqs = [item["seq"] for item in event_list]
        allowed_events = {"queued", "redispatched", "running", "succeeded"}
        event_order_ok = (
            event_types
            and event_types[0] == "queued"
            and event_types[-1] == "succeeded"
            and event_seqs == list(range(1, len(event_seqs) + 1))
            and set(event_types) <= allowed_events
        )
        record("event_order", bool(event_order_ok), event_types)
        _require(bool(event_order_ok), f"unexpected event sequence {event_types}")
        receipt = client_a.client.get(
            f"/api/v1/projects/{project_id}/artifacts/{job_state['result_artifact_id']}/content"
        )
        receipt_body = json.loads(receipt.content)
        record(
            "receipt_digest",
            receipt.status_code == 200
            and receipt_body["sha256"] == artifact_body["sha256"]
            and receipt_body["byte_length"] == artifact_body["byte_length"],
        )
        _require(receipt_body["sha256"] == artifact_body["sha256"], "receipt digest mismatch")

        foreign = client_c.client.get(f"/api/v1/projects/{project_id}/artifacts/{artifact_body['id']}")
        record("foreign_project_denied", foreign.status_code == 404, {"status": foreign.status_code})
        _require(foreign.status_code == 404, "foreign user was not denied")
        foreign_member_b = client_b.client.get(f"/api/v1/projects/{project_id}")
        record("viewer_membership_visible", foreign_member_b.status_code in (200, 404))
    finally:
        client_a.close()
        client_b.close()
        client_c.close()
    passed = all(item["passed"] for item in checks)
    observations["passed"] = passed
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(observations, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "checks": len(checks)}))
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="erratascope_service.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate").set_defaults(func=command_migrate)

    adopt = sub.add_parser("adopt-store")
    adopt.add_argument("--confirm", action="store_true", required=True)
    adopt.add_argument("--accept-unreferenced-generated", action="store_true")
    adopt.add_argument("--accept-unknown", action="store_true")
    adopt.set_defaults(func=command_adopt_store)

    bootstrap = sub.add_parser("bootstrap-local")
    bootstrap.add_argument("--out", required=True)
    bootstrap.add_argument("--force", action="store_true")
    bootstrap.set_defaults(func=command_bootstrap_local)

    sub.add_parser("worker").set_defaults(func=command_worker)
    sub.add_parser("dispatcher").set_defaults(func=command_dispatcher)

    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--once", action="store_true", required=True)
    dispatch.set_defaults(func=command_dispatch)

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--once", action="store_true", required=True)
    reconcile.set_defaults(func=command_reconcile)

    sub.add_parser("health").set_defaults(func=command_health)

    openapi = sub.add_parser("export-openapi")
    openapi.add_argument("--output", required=True)
    openapi.set_defaults(func=command_export_openapi)

    verify = sub.add_parser("verify-foundation")
    verify.add_argument("--output", required=True)
    verify.add_argument("--auth-dir", default="/local/dev-auth")
    verify.add_argument("--api-url", default=None)
    verify.set_defaults(func=command_verify_foundation)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ApiError, JobFailure) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


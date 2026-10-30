"""Shared helpers for W03 integration tests (real PostgreSQL/Valkey)."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from erratascope_service import services
from erratascope_service.api import create_app
from erratascope_service.config import Settings, load_settings
from erratascope_service.db import get_session_factory
from erratascope_service.services import NIL_PROJECT

DEV_AUTH = Path(os.environ.get("W03_DEV_AUTH_DIR", "/local/dev-auth"))
TOKEN_FILE = DEV_AUTH / "tokens.json"
JWKS_FILE = DEV_AUTH / "jwks.json"
PRIVATE_KEY = DEV_AUTH / "private_key.pem"


def tokens() -> dict:
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def token_for(user: str) -> str:
    return tokens()["users"][user]["token"]


def subject_for(user: str) -> uuid.UUID:
    return uuid.UUID(tokens()["users"][user]["sub"])


def settings() -> Settings:
    return load_settings()


def reset_database(target: str = "head") -> None:
    """Reset only the dedicated W03 test database/schema, preserving main data."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from erratascope_service.db import reset_engine

    current = load_settings()
    url = current.migrator_database_url
    if not url or "erratascope_test" not in url:
        raise RuntimeError("tests must target the dedicated erratascope_test database")
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS erratascope CASCADE"))
        connection.execute(
            text("CREATE SCHEMA erratascope AUTHORIZATION erratascope_migrator")
        )
    engine.dispose()
    os.environ["W03_MIGRATOR_DATABASE_URL"] = url
    command.upgrade(Config("/app/alembic.ini"), target)
    reset_engine()


def client() -> TestClient:
    return TestClient(create_app())


def auth(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}


def new_key() -> str:
    return uuid.uuid4().hex


def sign_claims(claims: dict) -> str:
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(PRIVATE_KEY.read_bytes(), password=None)
    kid = json.loads(JWKS_FILE.read_text(encoding="utf-8"))["keys"][0]["kid"]
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


def valid_claims(sub: str | None = None, **overrides) -> dict:
    base = {
        "sub": sub or str(subject_for("user-a")),
        "iss": tokens()["issuer"],
        "aud": tokens()["audience"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    base.update(overrides)
    return base


def ensure_project(project_id: uuid.UUID, actor_id: uuid.UUID, name: str = "synthetic-test") -> None:
    session = get_session_factory()()
    try:
        existing = session.get(services.Project, project_id)
        if existing is None:
            services.create_project(session, actor_id=actor_id, name=name, project_id=project_id)
            session.commit()
    finally:
        session.close()


def create_project(client: TestClient, user: str = "user-a", name: str | None = None) -> str:
    response = client.post(
        "/api/v1/projects",
        headers={**auth(user), "Idempotency-Key": new_key()},
        json={"name": name or f"synthetic-{uuid.uuid4().hex[:10]}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def upload_text(
    client: TestClient,
    project_id: str,
    body: bytes = b"synthetic W03 artifact\n",
    user: str = "user-a",
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/artifacts",
        headers={
            **auth(user),
            "Idempotency-Key": new_key(),
            "Content-Type": "text/plain",
            "X-Filename": "synthetic.txt",
        },
        content=body,
    )
    assert response.status_code == 201, response.text
    return response.json()


def body_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def error_code(response) -> str | None:
    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        return payload["error"].get("code")
    return payload.get("code") if isinstance(payload, dict) else None


def items(response) -> list:
    payload = response.json()
    if isinstance(payload, dict) and "items" in payload:
        return payload["items"]
    return payload

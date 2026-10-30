"""Environment configuration for the local W03 foundation service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError("INVALID_CONFIG", f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigError("INVALID_CONFIG", f"{name} must be between {minimum} and {maximum}")
    return value


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "1" if default else "0").strip().lower()
    if raw not in {"0", "1", "true", "false"}:
        raise ConfigError("INVALID_CONFIG", f"{name} must be 0/1/true/false")
    return raw in {"1", "true"}


@dataclass(frozen=True)
class Settings:
    mode: str
    database_url: str
    migrator_database_url: str | None
    broker_url: str
    artifact_root: Path
    jwks_path: Path | None
    jwks_url: str | None
    issuer: str
    audience: str
    algorithms: tuple[str, ...]
    max_artifact_bytes: int
    lease_seconds: int
    heartbeat_seconds: int
    max_attempts: int
    dispatch_interval_seconds: int
    reconcile_interval_seconds: int
    api_base_url: str
    test_mode: bool
    dev_auth_dir: Path | None
    queue_name: str
    staging_lease_seconds: int
    orphan_grace_seconds: int
    retry_delays_seconds: tuple[int, ...]
    w04_parse_timeout_seconds: int
    w04_parse_memory_mb: int
    w04_live_enabled: bool
    w04_secret_file: Path | None
    w04_provider_endpoint: str
    w04_provider_model: str
    w04_budget_id: str
    w04_prompt_version: str
    w04_provider_timeout_seconds: int
    w04_max_response_bytes: int
    w04_input_price_usd_per_million: float
    w04_output_price_usd_per_million: float
    w04_ledger_path: Path

    def ensure_startable(self) -> None:
        if self.mode == "hosted":
            raise ConfigError(
                "HOSTED_STORAGE_NOT_READY",
                "hosted mode requires managed private storage and hosted broker/auth binding, "
                "which are not implemented in W03; startup refuses to continue",
            )
        if self.mode != "local":
            raise ConfigError("INVALID_CONFIG", "W03_MODE must be local or hosted")
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ConfigError("INVALID_CONFIG", "W03_DATABASE_URL must use postgresql+psycopg")
        # JWKS existence is an API-only startup requirement: worker/dispatcher/
        # migrate processes never verify tokens and do not mount the public key.


def load_settings() -> Settings:
    mode = os.environ.get("W03_MODE", "local").strip().lower()
    database_url = os.environ.get("W03_DATABASE_URL", "").strip()
    if not database_url:
        raise ConfigError("INVALID_CONFIG", "W03_DATABASE_URL is required")
    artifact_root = Path(os.environ.get("W03_ARTIFACT_ROOT", "/var/lib/erratascope/artifacts"))
    jwks_path = os.environ.get("W03_JWKS_PATH")
    jwks_url = os.environ.get("W03_JWKS_URL")
    dev_dir = os.environ.get("W03_DEV_AUTH_DIR")
    algorithms_raw = os.environ.get("W03_JWT_ALGORITHMS", "RS256")
    algorithms = tuple(item.strip() for item in algorithms_raw.split(",") if item.strip())
    allowed = {"RS256", "ES256"}
    if not algorithms or any(item not in allowed for item in algorithms):
        raise ConfigError(
            "INVALID_CONFIG",
            "W03_JWT_ALGORITHMS must be a subset of RS256/ES256",
        )
    retry_raw = os.environ.get("W03_RETRY_DELAYS_SECONDS", "1,5")
    try:
        retry_delays = tuple(int(item.strip()) for item in retry_raw.split(",") if item.strip())
    except ValueError as exc:
        raise ConfigError("INVALID_CONFIG", "W03_RETRY_DELAYS_SECONDS must be comma-separated integers") from exc
    if not retry_delays or any(delay < 1 or delay > 300 for delay in retry_delays):
        raise ConfigError("INVALID_CONFIG", "retry delays must be between 1 and 300 seconds")
    issuer = os.environ.get("W03_ISSUER", "").strip()
    audience = os.environ.get("W03_AUDIENCE", "").strip()
    if not issuer or not audience:
        raise ConfigError("INVALID_CONFIG", "W03_ISSUER and W03_AUDIENCE are required")
    if mode == "hosted":
        if not jwks_url or not jwks_url.startswith("https://"):
            raise ConfigError("INVALID_CONFIG", "hosted mode requires an https W03_JWKS_URL")
        if not issuer.startswith("https://"):
            raise ConfigError("INVALID_CONFIG", "hosted mode requires an https issuer")
    return Settings(
        mode=mode,
        database_url=database_url,
        migrator_database_url=os.environ.get("W03_MIGRATOR_DATABASE_URL"),
        broker_url=os.environ.get("W03_BROKER_URL", "redis://broker:6379/0"),
        artifact_root=artifact_root,
        jwks_path=Path(jwks_path) if jwks_path else None,
        jwks_url=jwks_url,
        issuer=issuer,
        audience=audience,
        algorithms=algorithms,
        max_artifact_bytes=_int("W03_MAX_ARTIFACT_BYTES", 10 * 1024 * 1024, 1, 10 * 1024 * 1024),
        lease_seconds=_int("W03_LEASE_SECONDS", 60, 5, 3600),
        heartbeat_seconds=_int("W03_HEARTBEAT_SECONDS", 15, 1, 60),
        max_attempts=_int("W03_MAX_ATTEMPTS", 3, 1, 3),
        dispatch_interval_seconds=_int("W03_DISPATCH_INTERVAL_SECONDS", 2, 1, 60),
        reconcile_interval_seconds=_int("W03_RECONCILE_INTERVAL_SECONDS", 5, 1, 600),
        api_base_url=os.environ.get("W03_API_BASE_URL", "http://api:8000").rstrip("/"),
        test_mode=_bool("W03_TEST_MODE", False),
        dev_auth_dir=Path(dev_dir) if dev_dir else None,
        queue_name=os.environ.get("W03_QUEUE_NAME", "w03").strip() or "w03",
        staging_lease_seconds=_int("W03_STAGING_LEASE_SECONDS", 60, 5, 3600),
        orphan_grace_seconds=_int("W03_ORPHAN_GRACE_SECONDS", 30, 5, 3600),
        retry_delays_seconds=retry_delays,
        w04_parse_timeout_seconds=_int("W04_PARSE_TIMEOUT_SECONDS", 120, 10, 300),
        w04_parse_memory_mb=_int("W04_PARSE_MEMORY_MB", 512, 128, 1024),
        w04_live_enabled=_bool("W04_LIVE_ENABLED", False),
        w04_secret_file=(
            Path(os.environ["W04_SECRET_FILE"]) if os.environ.get("W04_SECRET_FILE") else None
        ),
        w04_provider_endpoint=os.environ.get(
            "W04_PROVIDER_ENDPOINT",
            "https://api.tokenfactory.nebius.com/v1/chat/completions",
        ).strip(),
        w04_provider_model=os.environ.get(
            "W04_PROVIDER_MODEL", "nvidia/Nemotron-3.5-Super-VL"
        ).strip(),
        w04_budget_id=os.environ.get("W04_BUDGET_ID", "W04-backend-v1").strip(),
        w04_prompt_version=os.environ.get(
            "W04_PROMPT_VERSION", "w04-draft-v5-grounded-no-thinking"
        ).strip(),
        w04_provider_timeout_seconds=_int("W04_PROVIDER_TIMEOUT_SECONDS", 180, 30, 300),
        w04_max_response_bytes=_int(
            "W04_MAX_RESPONSE_BYTES", 2 * 1024 * 1024, 1024, 2 * 1024 * 1024
        ),
        w04_input_price_usd_per_million=0.30,
        w04_output_price_usd_per_million=0.90,
        w04_ledger_path=Path(
            os.environ.get("W04_LEDGER_PATH", "/w04/provider/ledger.jsonl")
        ),
    )

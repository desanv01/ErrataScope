"""Nebius adapter with reservation-before-dispatch accounting and cache lookup."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import select

from ..config import Settings
from ..db import get_session_factory
from .models import (
    ModelDraft,
    ProviderAttemptEvent,
    ProviderBudget,
    ProviderReservation,
)
from .prompt import MAX_INPUT_TOKEN_BOUND, estimate_input_token_bound

MAX_OUTPUT_TOKENS = 8192
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
BUDGET_ID = "W04-backend-v1"
MAX_REQUESTS = 2
MAX_SPEND = Decimal("0.25")
INPUT_PRICE = Decimal("0.30")
OUTPUT_PRICE = Decimal("0.90")


class ProviderBlocked(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass
class ProviderResult:
    reservation_id: uuid.UUID
    status: str
    request_payload: dict
    wire_body: dict | None
    response_text: str | None
    response_hash: str | None
    provider_request_id: str | None
    usage: dict | None
    latency_ms: int | None
    error_code: str | None
    cached_draft: ModelDraft | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_api_key(settings: Settings) -> str | None:
    env_value = os.environ.get("NEBIUS_API_KEY")
    if env_value:
        return env_value.strip()
    path = settings.w04_secret_file
    if path is None:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "NEBIUS_API_KEY":
            return value.strip().strip('"').strip("'")
    return None


def key_presence(settings: Settings) -> str:
    return "CONFIGURED" if load_api_key(settings) is not None else "MISSING"


def _mirror(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _reserve(
    settings: Settings,
    *,
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    case_kind: str,
    source_sha256: str,
    extraction_id: uuid.UUID | None,
    context_hash: str,
    request_hash: str,
    prompt_version: str,
    endpoint: str,
    model: str,
    input_bound: int,
    output_bound: int,
) -> ProviderReservation:
    if input_bound > MAX_INPUT_TOKEN_BOUND:
        raise ProviderBlocked("INPUT_BOUND_EXCEEDED", "request exceeds the 16,000 input-token bound")
    if output_bound > MAX_OUTPUT_TOKENS:
        raise ProviderBlocked("OUTPUT_BOUND_EXCEEDED", "request exceeds the 8,192 output-token bound")
    cost = (
        Decimal(input_bound) / Decimal(1_000_000) * Decimal(str(settings.w04_input_price_usd_per_million))
        + Decimal(output_bound) / Decimal(1_000_000) * Decimal(str(settings.w04_output_price_usd_per_million))
    )
    factory = get_session_factory(settings)
    session = factory()
    try:
        budget = session.scalar(
            select(ProviderBudget).where(ProviderBudget.budget_id == BUDGET_ID).with_for_update()
        )
        if budget is None:
            raise ProviderBlocked("BUDGET_MISSING", "W04 provider budget row is missing")
        if budget.requests_reserved >= MAX_REQUESTS:
            raise ProviderBlocked("BUDGET_EXHAUSTED", "W04 paid reservation cap is exhausted")
        if Decimal(budget.spend_reserved_usd) + cost > MAX_SPEND:
            raise ProviderBlocked("BUDGET_CAP", "W04 reserved-estimate cap would be exceeded")
        reservation = ProviderReservation(
            id=uuid.uuid4(),
            budget_id=BUDGET_ID,
            attempt=budget.requests_reserved + 1,
            project_id=project_id,
            job_id=job_id,
            case_kind=case_kind,
            source_sha256=source_sha256,
            extraction_id=extraction_id,
            context_hash=context_hash,
            request_hash=request_hash,
            prompt_version=prompt_version,
            endpoint=endpoint,
            model=model,
            input_token_bound=input_bound,
            output_token_bound=output_bound,
            input_price_usd_per_million=settings.w04_input_price_usd_per_million,
            output_price_usd_per_million=settings.w04_output_price_usd_per_million,
            max_estimated_cost_usd=cost,
            status="reserved",
            reserved_utc=_utcnow(),
        )
        session.add(reservation)
        session.flush()
        session.add(
            ProviderAttemptEvent(
                id=uuid.uuid4(),
                reservation_id=reservation.id,
                event="reserved",
                detail={
                    "attempt": reservation.attempt,
                    "case": case_kind,
                    "input_token_bound": input_bound,
                    "output_token_bound": output_bound,
                    "max_estimated_cost_usd": str(cost),
                },
            )
        )
        budget.requests_reserved += 1
        budget.spend_reserved_usd = Decimal(budget.spend_reserved_usd) + cost
        budget.updated_at = _utcnow()
        session.commit()
        _mirror(
            settings.w04_ledger_path,
            {
                "event": "reserved",
                "utc": _utcnow().isoformat(),
                "reservation_id": str(reservation.id),
                "budget_id": BUDGET_ID,
                "attempt": reservation.attempt,
                "case": case_kind,
                "input_token_bound": input_bound,
                "output_token_bound": output_bound,
                "max_estimated_cost_usd": str(cost),
            },
        )
        return reservation
    finally:
        session.close()


def _settle(settings: Settings, reservation: ProviderReservation, *, status: str, **fields) -> None:
    factory = get_session_factory(settings)
    session = factory()
    try:
        row = session.get(ProviderReservation, reservation.id)
        if row is None:
            raise ProviderBlocked("RESERVATION_MISSING", "reservation disappeared")
        row.status = status
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)
        row.finalized_utc = _utcnow()
        session.add(
            ProviderAttemptEvent(
                id=uuid.uuid4(),
                reservation_id=row.id,
                event=status,
                detail={key: (str(value) if key == "usage" else value) for key, value in fields.items() if value is not None},
            )
        )
        session.commit()
        _mirror(
            settings.w04_ledger_path,
            {
                "event": status,
                "utc": _utcnow().isoformat(),
                "reservation_id": str(row.id),
                "budget_id": BUDGET_ID,
                "attempt": row.attempt,
                "response_hash": row.response_hash,
                "provider_request_id": row.provider_request_id,
                "usage": row.usage,
                "error_code": row.error_code,
            },
        )
        reservation.status = status
    finally:
        session.close()


def _cache_lookup(
    settings: Settings, *, extraction_id: uuid.UUID, source_id: uuid.UUID, request_hash: str, prompt_version: str
) -> ModelDraft | None:
    session = get_session_factory(settings)()
    try:
        return session.scalar(
            select(ModelDraft).where(
                ModelDraft.extraction_id == extraction_id,
                ModelDraft.source_id == source_id,
                ModelDraft.request_hash == request_hash,
                ModelDraft.prompt_version == prompt_version,
                ModelDraft.status == "validated",
                ModelDraft.provenance == "live",
            )
        )
    finally:
        session.close()


def run_case(
    settings: Settings,
    *,
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    extraction_id: uuid.UUID | None,
    source_id: uuid.UUID,
    source_sha256: str,
    case_kind: str,
    messages: list[dict],
    declared_identity: dict | None,
    context: dict,
) -> tuple[ProviderResult, bool]:
    """Return (result, cache_hit). Exactly zero or one paid HTTP request is issued."""
    if not settings.w04_live_enabled:
        raise ProviderBlocked("LIVE_DISABLED", "W04 live mode is not explicitly enabled")
    api_key = load_api_key(settings)
    if api_key is None:
        raise ProviderBlocked("KEY_MISSING", "NEBIUS_API_KEY is not configured")
    endpoint = settings.w04_provider_endpoint
    model = settings.w04_provider_model
    if endpoint != "https://api.tokenfactory.nebius.com/v1/chat/completions":
        raise ProviderBlocked("ENDPOINT_NOT_ALLOWED", "provider endpoint is not the fixed approved endpoint")
    if model != "nvidia/Nemotron-3.5-Super-VL":
        raise ProviderBlocked("MODEL_NOT_ALLOWED", "provider model is not the approved model")
    request_payload = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request_hash = hashlib.sha256(
        json.dumps(
            {
                "request": request_payload,
                "endpoint": endpoint,
                "prompt_version": settings.w04_prompt_version,
                "context_hash": context["context_hash"],
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if extraction_id is not None:
        cached = _cache_lookup(
            settings,
            extraction_id=extraction_id,
            source_id=source_id,
            request_hash=request_hash,
            prompt_version=settings.w04_prompt_version,
        )
        if cached is not None:
            return (
                ProviderResult(
                    reservation_id=uuid.uuid4(),
                    status="cached",
                    request_payload=request_payload,
                    wire_body=None,
                    response_text=None,
                    response_hash=cached.response_hash,
                    provider_request_id=cached.provider_request_id,
                    usage=cached.usage,
                    latency_ms=None,
                    error_code=None,
                    cached_draft=cached,
                ),
                True,
            )
    input_bound = estimate_input_token_bound(messages)
    reservation = _reserve(
        settings,
        project_id=project_id,
        job_id=job_id,
        case_kind=case_kind,
        source_sha256=source_sha256,
        extraction_id=extraction_id,
        context_hash=context["context_hash"],
        request_hash=request_hash,
        prompt_version=settings.w04_prompt_version,
        endpoint=endpoint,
        model=model,
        input_bound=input_bound,
        output_bound=MAX_OUTPUT_TOKENS,
    )
    wire_bytes = json.dumps(request_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(wire_bytes) > 256 * 1024:
        _settle(settings, reservation, status="failed", error_code="REQUEST_TOO_LARGE")
        raise ProviderBlocked("REQUEST_TOO_LARGE", "wire request exceeds bounded size")
    factory = get_session_factory(settings)
    session = factory()
    try:
        row = session.get(ProviderReservation, reservation.id)
        row.status = "dispatched"
        row.dispatch_utc = _utcnow()
        session.add(
            ProviderAttemptEvent(
                id=uuid.uuid4(),
                reservation_id=row.id,
                event="dispatched",
                detail={"endpoint": endpoint, "model": model, "request_hash": request_hash},
            )
        )
        session.commit()
        _mirror(
            settings.w04_ledger_path,
            {
                "event": "dispatched",
                "utc": _utcnow().isoformat(),
                "reservation_id": str(row.id),
                "budget_id": BUDGET_ID,
                "attempt": row.attempt,
                "request_hash": request_hash,
            },
        )
    finally:
        session.close()

    started = time.monotonic()
    try:
        with httpx.Client(timeout=settings.w04_provider_timeout_seconds, follow_redirects=False) as client:
            with client.stream(
                "POST",
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "ErrataScope-W04/1",
                },
                json=request_payload,
            ) as response:
                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        _settle(settings, reservation, status="failed", error_code="RESPONSE_TOO_LARGE")
                        raise ProviderBlocked("RESPONSE_TOO_LARGE", "provider response exceeded 2 MiB")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                status_code = response.status_code
                content_type = response.headers.get("content-type", "")
                request_id = response.headers.get("x-request-id") or response.headers.get("request-id")
    except ProviderBlocked:
        raise
    except httpx.ConnectError as exc:
        _settle(settings, reservation, status="failed", error_code="CONNECT_ERROR")
        raise ProviderBlocked("PROVIDER_CONNECT", f"provider connection failed: {type(exc).__name__}") from exc
    except Exception as exc:  # noqa: BLE001 - timeout/transport after dispatch is uncertain
        _settle(settings, reservation, status="uncertain", error_code="TRANSPORT_UNCERTAIN")
        raise ProviderBlocked(
            "PROVIDER_UNCERTAIN", f"provider outcome is uncertain: {type(exc).__name__}"
        ) from exc
    latency_ms = int((time.monotonic() - started) * 1000)
    response_hash = hashlib.sha256(raw).hexdigest()
    if status_code < 200 or status_code >= 300:
        _settle(
            settings,
            reservation,
            status="failed",
            provider_request_id=request_id,
            response_hash=response_hash,
            error_code=f"HTTP_{status_code}",
        )
        raise ProviderBlocked("PROVIDER_HTTP", f"provider returned HTTP {status_code}")
    if "application/json" not in content_type:
        _settle(
            settings,
            reservation,
            status="failed",
            provider_request_id=request_id,
            response_hash=response_hash,
            error_code="CONTENT_TYPE",
        )
        raise ProviderBlocked("PROVIDER_CONTENT_TYPE", "provider response is not JSON")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _settle(
            settings,
            reservation,
            status="failed",
            provider_request_id=request_id,
            response_hash=response_hash,
            error_code="RESPONSE_DECODE",
        )
        raise ProviderBlocked("PROVIDER_DECODE", "provider response JSON is invalid") from exc
    usage = body.get("usage") if isinstance(body, dict) else None
    returned_model = body.get("model") if isinstance(body, dict) else None
    choices = body.get("choices") if isinstance(body, dict) else None
    if not isinstance(choices, list) or not choices:
        _settle(
            settings,
            reservation,
            status="failed",
            provider_request_id=request_id,
            response_hash=response_hash,
            usage=usage,
            error_code="EMPTY_CHOICES",
        )
        raise ProviderBlocked("PROVIDER_EMPTY", "provider returned no choices")
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
    if returned_model and str(returned_model).strip().lower() != model.lower():
        _settle(
            settings,
            reservation,
            status="failed",
            provider_request_id=request_id,
            response_hash=response_hash,
            usage=usage,
            error_code="MODEL_MISMATCH",
        )
        raise ProviderBlocked("PROVIDER_MODEL", "provider returned a different model")
    if not isinstance(content, str) or not content.strip() or finish_reason != "stop":
        _settle(
            settings,
            reservation,
            status="failed",
            provider_request_id=request_id,
            response_hash=response_hash,
            usage=usage,
            error_code="INCOMPLETE_RESPONSE",
        )
        raise ProviderBlocked("PROVIDER_INCOMPLETE", "provider response is empty or truncated")
    _settle(
        settings,
        reservation,
        status="succeeded",
        provider_request_id=request_id,
        response_hash=response_hash,
        usage=usage,
    )
    return (
        ProviderResult(
            reservation_id=reservation.id,
            status="succeeded",
            request_payload=request_payload,
            wire_body=body,
            response_text=content,
            response_hash=response_hash,
            provider_request_id=request_id,
            usage=usage,
            latency_ms=latency_ms,
            error_code=None,
        ),
        False,
    )

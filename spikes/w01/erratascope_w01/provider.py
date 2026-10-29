"""Bounded Nebius probe adapter with reservation-first dispatch (repair R1/R2/R4).

Every paid call is reserved in the crash-safe ledger *before* the HTTP request.
Artifacts are written as explicit, hash-recorded wrappers bound to the case and
attempt; the shared :mod:`erratascope_w01.evidence` validator (used by both CLI
and report) is the only thing that can declare a live pass.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from . import config
from .cases import anchors_fingerprint
from .ledger import BudgetExhausted, Ledger, LedgerError, load_ledger
from .schemas import DraftInterpretation
from .util import rel, sha256_file, utc_now_iso, write_json
from .validate import validate_draft

ALLOWED_REQUEST_FIELDS = ("model", "messages", "max_tokens", "temperature", "stream", "chat_template_kwargs")
ARTIFACT_SCHEMA_VERSION = 2


class ProviderBlocked(RuntimeError):
    """Live probe cannot proceed; the message is the configured-variable gate."""


def send_request(payload: dict, api_key: str, client: httpx.Client | None = None) -> dict:
    """POST one chat-completions request. No retries at this layer."""
    url = config.PROVIDER["base_url"].rstrip("/") + "/" + config.PROVIDER["chat_path"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": config.USER_AGENT,
    }
    body = {key: payload[key] for key in ALLOWED_REQUEST_FIELDS if key in payload}
    owned = client is None
    client = client or httpx.Client(timeout=180.0, follow_redirects=False)
    try:
        started = time.perf_counter()
        response = client.post(url, json=body, headers=headers)
        latency_ms = int((time.perf_counter() - started) * 1000)
    finally:
        if owned:
            client.close()
    content_type = response.headers.get("content-type", "")
    body_json = None
    decode_error = None
    if "application/json" in content_type:
        try:
            body_json = response.json()
        except Exception as exc:  # noqa: BLE001 - malformed provider body is evidence
            decode_error = f"response JSON decode failed: {type(exc).__name__}: {exc}"
    else:
        decode_error = f"unexpected content-type {content_type!r}"
    return {
        "status_code": response.status_code,
        "latency_ms": latency_ms,
        "request_id": response.headers.get("x-request-id") or response.headers.get("request-id"),
        "content_type": content_type,
        "body": body_json,
        "decode_error": decode_error,
        "text_head": None if body_json is not None else response.text[:500],
    }


def model_matches(returned: str | None) -> bool:
    """Model binding check; aliases are accepted only when explicitly mapped."""
    if not returned:
        return False
    normalized = returned.strip().lower()
    if normalized == config.PROVIDER["model_id"].strip().lower():
        return True
    return normalized in {alias.lower() for alias in config.MODEL_ALIAS_MAP}


def _summarize_usage(body: dict | None) -> dict:
    if not body:
        return {"available": False}
    usage = body.get("usage") or {}
    if not usage:
        return {"available": False, "note": "provider returned no usage block; unknown, not zero"}
    return {
        "available": True,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def _case_dir(case: str) -> Path:
    return config.PROVIDER_DIR / "cases" / case


def _endpoint() -> str:
    return config.PROVIDER["base_url"].rstrip("/") + "/" + config.PROVIDER["chat_path"]


def _write_hashed(ledger: Ledger, attempt_no: int, path: Path, payload: dict, kind: str) -> str:
    write_json(path, payload)
    digest = sha256_file(path)
    ledger.record_artifact_hash(attempt_no, kind, digest)
    return digest


def run_case(
    *,
    case: str,
    payload: dict,
    anchors,
    expected_identity: dict,
    expected_document_sha256: str,
    pricing: dict,
    api_key: str,
    ledger: Ledger | None = None,
    client: httpx.Client | None = None,
    execution_mode: str = "live",
) -> dict:
    """Reserve, dispatch, evaluate, and finalize one case attempt.

    Raises BudgetExhausted before any HTTP call when a cap applies. Transport
    failures finalize as ``uncertain`` so the reservation and cost stay visible.
    """
    ledger = ledger or Ledger()
    config.PROVIDER_DIR.mkdir(parents=True, exist_ok=True)
    attempt_no = len(ledger.state.attempts) + 1
    case_dir = _case_dir(case)
    request_path = case_dir / f"attempt-{attempt_no:02d}.request.json"
    response_path = case_dir / f"attempt-{attempt_no:02d}.response.json"
    validation_path = case_dir / f"attempt-{attempt_no:02d}.validation.json"
    prompt_version = str(payload.get("prompt_metadata", {}).get("prompt_version", "unknown"))
    requested_model = config.PROVIDER["model_id"]
    endpoint = _endpoint()
    now = utc_now_iso()

    reservation = ledger.reserve(
        case=case,
        payload=payload,
        pricing=pricing,
        prompt_version=prompt_version,
        request_artifact=rel(request_path),
        execution_mode=execution_mode,
    )

    _write_hashed(
        ledger,
        reservation.attempt,
        request_path,
        {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_kind": "request",
            "case": case,
            "attempt": reservation.attempt,
            "created_utc": now,
            "provider": pricing["provider"],
            "endpoint": endpoint,
            "model_requested": requested_model,
            "prompt_version": prompt_version,
            "request": payload,
        },
        "request",
    )
    ledger.mark_dispatched(reservation.attempt)

    try:
        result = send_request(payload, api_key, client=client)
    except Exception as exc:  # noqa: BLE001 - timeout/transport keeps the reservation
        outcome = "timeout" if isinstance(exc, httpx.TimeoutException) else "transport_error"
        record = ledger.mark_uncertain(
            reservation.attempt,
            error=f"{type(exc).__name__}: {exc}",
            outcome=outcome,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    response_digest = _write_hashed(
        ledger,
        reservation.attempt,
        response_path,
        {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_kind": "response",
            "case": case,
            "attempt": reservation.attempt,
            "created_utc": utc_now_iso(),
            "endpoint": endpoint,
            "model_requested": requested_model,
            "prompt_version": prompt_version,
            "http_status": result["status_code"],
            "request_id": result["request_id"],
            "latency_ms": result["latency_ms"],
            "content_type": result["content_type"],
            "authorization_header_recorded": False,
            "decode_error": result["decode_error"],
            "body": result["body"],
            "text_head": result["text_head"],
        },
        "response",
    )

    common = {
        "http_status": result["status_code"],
        "response_artifact": rel(response_path),
        "response_sha256": response_digest,
        "usage": _summarize_usage(result["body"]),
    }

    if result["status_code"] != 200:
        record = ledger.finalize(
            reservation.attempt,
            outcome="http_error",
            validation={"status": "rejected", "reason": f"HTTP {result['status_code']}"},
            error=(result["text_head"] or "")[:300] or None,
            **common,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    body = result["body"]
    if result["decode_error"] or not isinstance(body, dict):
        record = ledger.finalize(
            reservation.attempt,
            outcome="invalid_json",
            validation={"status": "rejected", "reason": result["decode_error"] or "non-object body"},
            error=(result["decode_error"] or "non-object body")[:300],
            **common,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    choices = body.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    content = message.get("content")
    finish_reason = choice.get("finish_reason")
    model_returned = body.get("model")
    common.update({"model_returned": model_returned, "finish_reason": finish_reason})

    if not content or not str(content).strip():
        record = ledger.finalize(
            reservation.attempt,
            outcome="empty",
            validation={"status": "rejected", "reason": "empty completion content"},
            **common,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    # Repair 02: only a complete 'stop' completion can be usable. No alias
    # finish reasons are approved by Codex, so anything else is nonpassing.
    if finish_reason != "stop":
        record = ledger.finalize(
            reservation.attempt,
            outcome="truncated",
            validation={"status": "rejected", "reason": f"finish_reason={finish_reason!r}, not 'stop'"},
            **common,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    if not model_matches(model_returned):
        record = ledger.finalize(
            reservation.attempt,
            outcome="model_mismatch",
            validation={
                "status": "rejected",
                "reason": f"returned model {model_returned!r} does not match {requested_model!r}",
            },
            **common,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    try:
        draft_raw = json.loads(content)
    except json.JSONDecodeError as exc:
        record = ledger.finalize(
            reservation.attempt,
            outcome="invalid_json",
            validation={"status": "rejected", "reason": f"invalid JSON: {exc}"},
            error=str(exc)[:300],
            **common,
        )
        return _summary(record, case=case, execution_mode=execution_mode)

    validation = validate_draft(
        draft_raw, anchors, expected_document_sha256, expected_identity
    ).as_dict()

    expectation = None
    if case == "synthetic_missing_revision" and validation["status"] == "accepted":
        from .cases import evaluate_missing_information

        try:
            draft = DraftInterpretation(**draft_raw)
        except Exception as exc:  # noqa: BLE001 - schema error already reported by validation
            expectation = {"status": "fail", "problems": [f"schema: {exc}"]}
        else:
            expectation = evaluate_missing_information(draft)

    identity_snapshot = {
        "document_id": (expected_identity or {}).get("document_id"),
        "revision": (expected_identity or {}).get("revision"),
    }
    validation_digest = _write_hashed(
        ledger,
        reservation.attempt,
        validation_path,
        {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_kind": "validation",
            "case": case,
            "attempt": reservation.attempt,
            "created_utc": utc_now_iso(),
            "model_requested": requested_model,
            "prompt_version": prompt_version,
            "inputs": {
                "document_sha256": expected_document_sha256,
                "anchors_sha256": anchors_fingerprint(anchors),
                "identity": identity_snapshot,
            },
            "validation": validation,
            "case_expectation": expectation,
            "draft": draft_raw,
        },
        "validation",
    )

    if validation["status"] != "accepted":
        outcome = "schema_invalid"
    elif expectation is not None and expectation.get("status") != "pass":
        outcome = "expectation_failed"
    else:
        outcome = "success"

    record = ledger.finalize(
        reservation.attempt,
        outcome=outcome,
        validation=validation,
        case_expectation=expectation,
        validation_artifact=rel(validation_path),
        validation_sha256=validation_digest,
        **common,
    )
    return _summary(record, case=case, execution_mode=execution_mode)


def _summary(record, *, case: str, execution_mode: str) -> dict:
    data = record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)
    data["case"] = case
    data["execution_mode"] = execution_mode
    return data


def passes_live_gate(record: dict) -> bool:
    """Deprecated compatibility shim.

    A summary record alone is no longer accepted as evidence: only
    ``evidence.evaluate_case`` (used by CLI and report) can declare a live pass,
    because it validates the actual artifacts. This shim therefore always
    returns False; it exists so older diagnostic scripts fail closed instead of
    crashing or trusting ledger flags.
    """
    return False


def record_blocked(reason: str, ledger: Ledger | None = None, case: str | None = None) -> dict:
    """Record a blocked preflight without erasing prior dispatch history."""
    ledger = ledger or Ledger()
    return ledger.record_blocked(reason, case=case)


def current_ledger() -> tuple[dict | None, str | None]:
    return load_ledger()


__all__ = [
    "BudgetExhausted",
    "LedgerError",
    "ProviderBlocked",
    "current_ledger",
    "model_matches",
    "passes_live_gate",
    "record_blocked",
    "run_case",
    "send_request",
]

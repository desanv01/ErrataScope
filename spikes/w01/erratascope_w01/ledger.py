"""Crash-safe reservation ledger for paid W01 inference attempts (repair R1).

Invariants enforced here:

* an attempt is reserved *before* any HTTP call and the reservation is written
  with an atomic replace, so a timeout, crash, or malformed response cannot hide
  the dispatch or free the slot;
* reservations are never deleted, so attempt numbers are never reused and a
  restart cannot silently begin a new budget;
* the configured lifetime request cap applies across cases and restarts;
* prices, token bounds, and totals are validated as finite and non-negative;
* a later preflight block appends history and never rewrites prior dispatches.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from . import config
from .util import atomic_write_json, read_json, utc_now_iso

LEDGER_SCHEMA_VERSION = 2
CASES = ("real_source", "synthetic_missing_revision")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
OUTCOMES = (
    "pending",
    "success",
    "http_error",
    "invalid_json",
    "schema_invalid",
    "empty",
    "truncated",
    "model_mismatch",
    "expectation_failed",
    "timeout",
    "transport_error",
    "interrupted",
)


class LedgerError(RuntimeError):
    """The ledger file is corrupt or violates its invariants."""


class PricingError(ValueError):
    """Pricing configuration is missing, malformed, or mismatched."""


class BudgetExhausted(RuntimeError):
    """No attempt may be dispatched; the message states which cap applies."""


def _finite_nonnegative(value: float, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite, got {value!r}")
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative, got {value!r}")
    return number


class PricingEvidence(BaseModel):
    """Validated text pricing tied to provider, model, source, and date."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    model_id: str
    base_url: str
    currency: str
    input_usd_per_1m: float
    output_usd_per_1m: float
    source_url: str
    verified_date: str
    source_publication_date: str | None = None
    account_access_verified: bool = False
    modality_scope: str | None = None

    @field_validator("input_usd_per_1m")
    @classmethod
    def _input_price(cls, value: float) -> float:
        return _finite_nonnegative(value, "input_usd_per_1m")

    @field_validator("output_usd_per_1m")
    @classmethod
    def _output_price(cls, value: float) -> float:
        return _finite_nonnegative(value, "output_usd_per_1m")

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        if value.strip().upper() != "USD":
            raise ValueError(f"currency must be USD, got {value!r}")
        return "USD"

    @model_validator(mode="after")
    def _nonzero_price(self) -> PricingEvidence:
        if self.input_usd_per_1m == 0 and self.output_usd_per_1m == 0:
            raise ValueError("both prices are zero; cannot bound spend")
        if not self.source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an http(s) URL")
        if not DATE_RE.search(self.verified_date):
            raise ValueError("verified_date must contain an ISO date")
        return self


def load_pricing(path: Path | None = None) -> dict:
    """Validate pricing evidence and bind it to the configured provider/model."""
    path = path or config.PRICING_EVIDENCE_PATH
    try:
        raw = read_json(path)
    except FileNotFoundError as exc:
        raise PricingError(f"pricing evidence file not found: {path.name}") from exc
    except Exception as exc:
        raise PricingError(f"pricing evidence unreadable: {path.name}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PricingError("pricing evidence must be a JSON object")
    payload = dict(raw)
    if not payload.get("verified_date"):
        payload["verified_date"] = payload.get("verified_date_malaysia")
    try:
        evidence = PricingEvidence(**payload)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors()
        )
        raise PricingError(f"invalid pricing evidence: {details}") from exc

    if evidence.model_id != config.PROVIDER["model_id"]:
        raise PricingError(
            f"pricing model_id {evidence.model_id!r} does not match configured "
            f"model {config.PROVIDER['model_id']!r}"
        )
    if evidence.base_url.rstrip("/") != config.PROVIDER["base_url"].rstrip("/"):
        raise PricingError(
            f"pricing base_url {evidence.base_url!r} does not match configured "
            f"base_url {config.PROVIDER['base_url']!r}"
        )
    if "nebius" not in evidence.provider.lower():
        raise PricingError(f"pricing provider {evidence.provider!r} is not the configured provider")
    if not evidence.modality_scope or "text" not in evidence.modality_scope.lower():
        raise PricingError("pricing evidence must scope rates to text-only requests")

    return {
        "verified": True,
        "provider": evidence.provider,
        "model_id": evidence.model_id,
        "base_url": evidence.base_url,
        "currency": evidence.currency,
        "input_usd_per_1m": evidence.input_usd_per_1m,
        "output_usd_per_1m": evidence.output_usd_per_1m,
        "source_url": evidence.source_url,
        "verified_date": evidence.verified_date,
        "source_publication_date": evidence.source_publication_date,
        "account_access_verified": evidence.account_access_verified,
        "modality_scope": evidence.modality_scope,
        "pricing_file": path.name,
        "validated_utc": utc_now_iso(),
    }


def bound_input_tokens(payload: dict) -> dict:
    """Conservative input-token bound with a documented method.

    Byte-level BPE tokenizers emit at most one token per UTF-8 byte, so
    ``utf8_bytes`` is an upper bound for those tokenizers. JSON escaping and
    chat framing add bytes/tokens, so the bound multiplies the message bytes by
    1.1 and adds 8 tokens per message plus 64 for request framing.
    """
    total = 0.0
    per_message = []
    for message in payload.get("messages", []):
        encoded = len(str(message.get("content", "")).encode("utf-8"))
        per_message.append({"role": message.get("role"), "utf8_bytes": encoded})
        total += encoded + 8
    total = math.ceil(total * 1.1) + 64
    return {
        "tokens": total,
        "method": "utf8_bytes_plus_message_overhead_v1",
        "assumption": (
            "tokens <= UTF-8 bytes for byte-level BPE tokenizers; x1.1 for JSON escaping "
            "and +8 tokens/message +64 framing. Not a guarantee for other tokenizer families."
        ),
        "per_message": per_message,
    }


def estimate_cost_usd(input_tokens: int, max_output_tokens: int, pricing: dict) -> float:
    cost = (
        input_tokens / 1_000_000.0 * float(pricing["input_usd_per_1m"])
        + max_output_tokens / 1_000_000.0 * float(pricing["output_usd_per_1m"])
    )
    if not math.isfinite(cost) or cost < 0:
        raise PricingError("computed cost is not a finite non-negative number")
    return round(cost, 8)


class AttemptReservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt: int = Field(ge=1, le=config.BUDGET["max_requests"])
    case: Literal["real_source", "synthetic_missing_revision"]
    state: Literal["reserved", "dispatched", "finalized", "uncertain"] = "reserved"
    reserved_utc: str
    dispatched_utc: str | None = None
    finalized_utc: str | None = None
    provider: str
    base_url: str
    model_id: str
    prompt_version: str
    execution_mode: Literal["live", "mock"] = "live"
    max_output_tokens: int = Field(gt=0)
    input_token_bound: int = Field(ge=0)
    input_token_bound_method: str
    estimated_cost_usd: float = Field(ge=0)
    pricing: dict
    request_artifact: str | None = None
    response_artifact: str | None = None
    validation_artifact: str | None = None
    request_sha256: str | None = None
    response_sha256: str | None = None
    validation_sha256: str | None = None
    http_status: int | None = None
    model_returned: str | None = None
    finish_reason: str | None = None
    usage: dict | None = None
    outcome: Literal[OUTCOMES] = "pending"  # type: ignore[valid-type]
    validation: dict | None = None
    case_expectation: dict | None = None
    error: str | None = None

    @model_validator(mode="after")
    def _finite_cost(self) -> AttemptReservation:
        if not math.isfinite(self.estimated_cost_usd):
            raise ValueError("estimated_cost_usd must be finite")
        return self


class LedgerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = LEDGER_SCHEMA_VERSION
    created_utc: str
    updated_utc: str
    caps: dict
    pricing: dict | None = None
    attempts: list[AttemptReservation] = Field(default_factory=list)
    blocked_events: list[dict] = Field(default_factory=list)
    requests_reserved: int = 0
    spend_reserved_usd: float = 0.0

    @model_validator(mode="after")
    def _invariants(self) -> LedgerState:
        numbers = [attempt.attempt for attempt in self.attempts]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("attempt numbers must be sequential and never reused")
        if len(numbers) > config.BUDGET["max_requests"]:
            raise ValueError("ledger holds more attempts than the packet cap")
        if self.requests_reserved != len(self.attempts):
            raise ValueError("requests_reserved does not match stored attempts")
        total = sum(attempt.estimated_cost_usd for attempt in self.attempts)
        if abs(total - self.spend_reserved_usd) > 1e-6:
            raise ValueError("spend_reserved_usd does not match the sum of reservations")
        if not math.isfinite(self.spend_reserved_usd):
            raise ValueError("spend_reserved_usd must be finite")
        return self

    def dispatched(self) -> list[AttemptReservation]:
        return [a for a in self.attempts if a.state in {"dispatched", "finalized", "uncertain"}]

    def live_requests_made(self) -> bool:
        return bool(self.dispatched())


class Ledger:
    """Disk-backed reservation ledger; every mutation is written atomically."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config.PROVIDER_DIR / "ledger.json")
        if self.path.exists():
            try:
                payload = read_json(self.path)
                self.state = LedgerState(**payload)
            except (ValidationError, ValueError, TypeError) as exc:
                raise LedgerError(f"ledger at {self.path.name} is invalid: {exc}") from exc
        else:
            now = utc_now_iso()
            self.state = LedgerState(
                created_utc=now,
                updated_utc=now,
                caps=dict(config.BUDGET),
                pricing=None,
                attempts=[],
                blocked_events=[],
                requests_reserved=0,
                spend_reserved_usd=0.0,
            )

    # -- persistence ------------------------------------------------------
    def save(self) -> None:
        self.state.updated_utc = utc_now_iso()
        atomic_write_json(self.path, self.state.model_dump(mode="json"))

    def record_blocked(self, reason: str, case: str | None = None) -> dict:
        """Append a blocked preflight without altering prior dispatches."""
        self.state.blocked_events.append({"utc": utc_now_iso(), "reason": reason, "case": case})
        self.save()
        return {
            "blocked_events": len(self.state.blocked_events),
            "requests_reserved": self.state.requests_reserved,
            "live_requests_made": self.state.live_requests_made(),
        }

    # -- reservations -----------------------------------------------------
    def reserve(
        self,
        *,
        case: str,
        payload: dict,
        pricing: dict,
        prompt_version: str,
        request_artifact: str | None = None,
        execution_mode: str = "live",
    ) -> AttemptReservation:
        caps = config.BUDGET
        if case not in CASES:
            raise LedgerError(f"unknown case {case!r}")
        if self.state.requests_reserved >= caps["max_requests"]:
            raise BudgetExhausted(
                f"request cap reached: {self.state.requests_reserved}/{caps['max_requests']} attempts reserved"
            )
        bound = bound_input_tokens(payload)
        if bound["tokens"] > caps["max_input_tokens_per_request"]:
            raise BudgetExhausted(
                f"input token bound {bound['tokens']} exceeds cap "
                f"{caps['max_input_tokens_per_request']}; reduce input before dispatch"
            )
        max_output = int(payload.get("max_tokens") or 0)
        if max_output <= 0 or max_output > caps["max_output_tokens_per_request"]:
            raise BudgetExhausted(
                f"max_tokens {max_output} outside (0, {caps['max_output_tokens_per_request']}]"
            )
        cost = estimate_cost_usd(bound["tokens"], max_output, pricing)
        projected = self.state.spend_reserved_usd + cost
        if projected > caps["max_estimated_spend_usd"]:
            raise BudgetExhausted(
                f"projected spend ${projected:.4f} exceeds cap ${caps['max_estimated_spend_usd']}"
            )

        attempt_no = len(self.state.attempts) + 1
        reservation = AttemptReservation(
            attempt=attempt_no,
            case=case,
            state="reserved",
            reserved_utc=utc_now_iso(),
            provider=pricing["provider"],
            base_url=pricing["base_url"],
            model_id=pricing["model_id"],
            prompt_version=prompt_version,
            execution_mode=execution_mode if execution_mode in {"live", "mock"} else "live",
            max_output_tokens=max_output,
            input_token_bound=int(bound["tokens"]),
            input_token_bound_method=bound["method"],
            estimated_cost_usd=cost,
            pricing={
                "input_usd_per_1m": pricing["input_usd_per_1m"],
                "output_usd_per_1m": pricing["output_usd_per_1m"],
                "currency": pricing.get("currency", "USD"),
                "source_url": pricing["source_url"],
                "verified_date": pricing["verified_date"],
                "model_id": pricing["model_id"],
                "account_access_verified": pricing.get("account_access_verified", False),
            },
            request_artifact=request_artifact,
        )
        self.state.attempts.append(reservation)
        self.state.requests_reserved = len(self.state.attempts)
        self.state.spend_reserved_usd = round(projected, 8)
        self.state.pricing = pricing
        self.save()
        return reservation

    def _attempt(self, attempt_no: int) -> AttemptReservation:
        for attempt in self.state.attempts:
            if attempt.attempt == attempt_no:
                return attempt
        raise LedgerError(f"attempt {attempt_no} is not reserved")

    def mark_dispatched(self, attempt_no: int) -> None:
        attempt = self._attempt(attempt_no)
        attempt.state = "dispatched"
        attempt.dispatched_utc = utc_now_iso()
        self.save()

    def record_artifact_hash(self, attempt_no: int, kind: str, digest: str) -> None:
        """Persist an artifact hash at creation so later replacement is detectable."""
        if kind not in {"request", "response", "validation"}:
            raise LedgerError(f"unknown artifact kind {kind!r}")
        if not digest or len(digest) != 64:
            raise LedgerError(f"invalid SHA-256 for {kind} artifact")
        attempt = self._attempt(attempt_no)
        setattr(attempt, f"{kind}_sha256", digest)
        self.save()

    def finalize(self, attempt_no: int, *, outcome: str, **fields: Any) -> AttemptReservation:
        if outcome not in OUTCOMES or outcome == "pending":
            raise LedgerError(f"invalid final outcome {outcome!r}")
        attempt = self._attempt(attempt_no)
        attempt.state = "finalized"
        attempt.outcome = outcome  # type: ignore[assignment]
        attempt.finalized_utc = utc_now_iso()
        for key, value in fields.items():
            if key not in AttemptReservation.model_fields:
                raise LedgerError(f"unknown attempt field {key!r}")
            setattr(attempt, key, value)
        self.save()
        return attempt

    def mark_uncertain(self, attempt_no: int, *, error: str, outcome: str = "timeout") -> AttemptReservation:
        if outcome not in {"timeout", "transport_error", "interrupted"}:
            raise LedgerError(f"invalid uncertain outcome {outcome!r}")
        attempt = self._attempt(attempt_no)
        attempt.state = "uncertain"
        attempt.outcome = outcome  # type: ignore[assignment]
        attempt.error = error[:500]
        attempt.finalized_utc = utc_now_iso()
        self.save()
        return attempt


def load_ledger(path: Path | None = None) -> tuple[dict | None, str | None]:
    """Read the ledger for reporting; returns (data, error). No silent defaults."""
    path = path or (config.PROVIDER_DIR / "ledger.json")
    if not path.exists():
        return None, "ledger file not present"
    try:
        payload = read_json(path)
        state = LedgerState(**payload)
    except Exception as exc:  # noqa: BLE001 - reporting must not crash on bad evidence
        return None, f"invalid ledger: {type(exc).__name__}: {exc}"
    data = state.model_dump(mode="json")
    data["live_requests_made"] = state.live_requests_made()
    return data, None

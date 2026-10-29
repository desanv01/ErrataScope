"""Shared artifact-content evidence validation for CLI and report (repair R2).

A ledger record's summary flags are not evidence. This module reads the actual
request/response/validation artifacts, binds them to the same case, attempt,
model, endpoint, and completion, recomputes the draft validation against the
pinned case inputs, and rejects replaced or contradictory artifacts.

Every artifact is written by :mod:`erratascope_w01.provider` with an explicit
wrapper (case, attempt, kind, schema version) and its SHA-256 is recorded in the
ledger at creation, so replacement is detectable without a signature service.

Paths are confined to ``.local/w01/results/provider``: a path outside that tree,
an absolute path, a traversal, a directory, an empty object, or malformed JSON
is not evidence.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from . import config
from .cases import anchors_fingerprint, evaluate_missing_information
from .provider import model_matches
from .schemas import DraftInterpretation
from .util import sha256_file
from .validate import validate_draft

ARTIFACT_SCHEMA_VERSION = 2
ARTIFACT_KINDS = ("request", "response", "validation")

EvidenceStatus = Literal["PASS", "FAIL", "NOT_RUN", "MOCK_ONLY", "BLOCKED"]


@dataclass
class EvidenceResult:
    status: EvidenceStatus
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"status": self.status, "reasons": self.reasons, "details": self.details}


def artifacts_root() -> Path:
    return config.PROVIDER_DIR.resolve()


def expected_endpoint() -> str:
    return config.PROVIDER["base_url"].rstrip("/") + "/" + config.PROVIDER["chat_path"]


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _resolve_artifact(raw, project_root: Path) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "artifact path missing"
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.drive:
        return None, "absolute artifact path rejected"
    if ".." in candidate.parts:
        return None, "parent traversal in artifact path rejected"
    resolved = (project_root / candidate).resolve()
    allowed = artifacts_root()
    if resolved != allowed and allowed not in resolved.parents:
        return None, "artifact path outside the provider artifact directory"
    if not resolved.exists():
        return None, "artifact file missing"
    if not resolved.is_file():
        return None, "artifact path is not a regular file"
    if resolved.stat().st_size <= 2:
        return None, "artifact file is empty"
    return resolved, None


def _load_json_object(path: Path) -> tuple[dict | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"unreadable artifact: {exc}"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON: {exc.msg} at {exc.colno}"
    if not isinstance(value, dict):
        return None, f"unsupported artifact shape: {type(value).__name__}"
    if not value:
        return None, "empty artifact object is not evidence"
    return value, None


def _check_wrapper(artifact: dict, kind: str, case: str, attempt: int, reasons: list[str]) -> None:
    if artifact.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        reasons.append(f"{kind}: unsupported artifact schema_version {artifact.get('schema_version')!r}")
    if artifact.get("artifact_kind") != kind:
        reasons.append(f"{kind}: artifact_kind {artifact.get('artifact_kind')!r} does not match")
    if artifact.get("case") != case:
        reasons.append(f"{kind}: artifact case {artifact.get('case')!r} does not match expected {case!r}")
    if artifact.get("attempt") != attempt:
        reasons.append(f"{kind}: artifact attempt {artifact.get('attempt')!r} does not match record attempt {attempt!r}")


def evaluate_case(
    *,
    record,
    case: str,
    ledger,
    anchors: Iterable,
    expected_document_sha256: str,
    expected_identity: dict | None,
    project_root: Path | None = None,
) -> EvidenceResult:
    """Validate one executed case bundle. PASS is structural, not semantic acceptance."""
    root = project_root or config.PROJECT_ROOT
    reasons: list[str] = []
    details: dict = {}
    anchors = list(anchors)
    expected_model = config.PROVIDER["model_id"]

    if not isinstance(record, dict):
        return EvidenceResult("FAIL", ["no ledger record"])
    if record.get("case") != case:
        return EvidenceResult(
            "FAIL", [f"ledger record case {record.get('case')!r} does not match requested case {case!r}"]
        )
    if record.get("execution_mode") != "live":
        return EvidenceResult(
            "MOCK_ONLY", ["execution_mode is not live; mock/cache output cannot pass a live gate"]
        )
    if not isinstance(ledger, dict):
        return EvidenceResult("FAIL", ["intended ledger unavailable"])

    attempt_no = record.get("attempt")
    attempts = ledger.get("attempts") or []
    ledger_attempt = next((item for item in attempts if item.get("attempt") == attempt_no), None)
    if ledger_attempt is None:
        return EvidenceResult("FAIL", [f"attempt {attempt_no!r} is not reserved in the intended ledger"])
    if ledger_attempt.get("case") != case:
        reasons.append(f"ledger attempt case {ledger_attempt.get('case')!r} does not match {case!r}")
    if ledger.get("requests_reserved") != len(attempts):
        reasons.append("ledger requests_reserved does not match stored attempts")
    for key in (
        "state",
        "outcome",
        "http_status",
        "model_returned",
        "finish_reason",
        "request_artifact",
        "response_artifact",
        "validation_artifact",
    ):
        if record.get(key) != ledger_attempt.get(key):
            reasons.append(f"record field '{key}' differs from the intended ledger")

    state = record.get("state")
    if state != "finalized":
        reasons.append(f"attempt state is {state!r}, not finalized (incomplete evidence)")
    if record.get("outcome") != "success":
        reasons.append(f"attempt outcome is {record.get('outcome')!r}, not success")

    # -- artifacts: confinement, replacement detection, wrapper metadata ----
    artifacts: dict[str, dict] = {}
    for kind in ARTIFACT_KINDS:
        path, error = _resolve_artifact(record.get(f"{kind}_artifact"), root)
        if error:
            reasons.append(f"{kind}: {error}")
            continue
        recorded_hash = record.get(f"{kind}_sha256")
        actual_hash = sha256_file(path)
        details[f"{kind}_sha256"] = actual_hash
        details[f"{kind}_bytes"] = path.stat().st_size
        if not recorded_hash:
            reasons.append(f"{kind}: artifact hash was not recorded at creation")
        elif recorded_hash != actual_hash:
            reasons.append(f"{kind}: artifact content was replaced or corrupted after recording")
        artifact, error = _load_json_object(path)
        if error:
            reasons.append(f"{kind}: {error}")
            continue
        _check_wrapper(artifact, kind, case, attempt_no, reasons)
        artifacts[kind] = artifact
    if len(artifacts) != len(ARTIFACT_KINDS):
        return EvidenceResult("FAIL", reasons, details)

    # -- request: model/provider/endpoint binding ---------------------------
    request = artifacts["request"]
    request_body = request.get("request")
    if request.get("model_requested") != expected_model:
        reasons.append(f"request model_requested {request.get('model_requested')!r} is not the configured model")
    if request.get("endpoint") != expected_endpoint():
        reasons.append("request endpoint does not match the documented endpoint")
    if not isinstance(request_body, dict):
        reasons.append("request body is not a JSON object")
    else:
        if request_body.get("model") != expected_model:
            reasons.append("request body model does not match the configured model")
        messages = request_body.get("messages")
        if not isinstance(messages, list) or not messages:
            reasons.append("request body has no messages")
        elif not any(str(message.get("content", "")).strip() for message in messages if isinstance(message, dict)):
            reasons.append("request body messages contain no content")
    if record.get("model_id") != expected_model:
        reasons.append(f"ledger model_id {record.get('model_id')!r} is not the configured model")
    if str(record.get("base_url", "")).rstrip("/") != config.PROVIDER["base_url"].rstrip("/"):
        reasons.append("ledger base_url does not match the configured endpoint")

    # -- response: status, model, completion -------------------------------
    response = artifacts["response"]
    body = response.get("body")
    if response.get("http_status") != 200:
        reasons.append(f"response HTTP status is {response.get('http_status')!r}, not 200")
    if response.get("http_status") != record.get("http_status"):
        reasons.append("response HTTP status disagrees with the ledger record")
    if response.get("model_requested") != expected_model:
        reasons.append("response artifact does not record the requested model")
    if response.get("endpoint") != expected_endpoint():
        reasons.append("response endpoint does not match the documented endpoint")
    if response.get("decode_error"):
        reasons.append(f"response decode_error recorded: {response.get('decode_error')}")
    if not isinstance(body, dict):
        reasons.append("response body is not a JSON object")
        body = {}
    returned_model = body.get("model")
    if not model_matches(returned_model):
        reasons.append(f"returned model {returned_model!r} is not the configured model")
    if returned_model != record.get("model_returned"):
        reasons.append("returned model disagrees with the ledger record")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        reasons.append("response choices must be a nonempty list of completion objects")
        choice = {}
    else:
        choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        reasons.append("completion message is not a JSON object")
        message = {}
    content = message.get("content")
    finish_reason = choice.get("finish_reason")
    if not isinstance(content, str) or not content.strip():
        reasons.append("completion content is missing or empty")
        content = None
    if finish_reason != "stop":
        reasons.append(f"finish_reason is {finish_reason!r}, not 'stop'")
    if record.get("finish_reason") != "stop":
        reasons.append(f"ledger finish_reason is {record.get('finish_reason')!r}, not 'stop'")

    # -- validation: recompute from response content against pinned inputs --
    validation_artifact = artifacts["validation"]
    stored_draft = validation_artifact.get("draft")
    if not isinstance(stored_draft, dict):
        reasons.append("saved draft must be a JSON object")
    stored_validation = validation_artifact.get("validation")
    if not isinstance(stored_validation, dict):
        reasons.append("stored validation must be a JSON object")
        stored_validation = {}
    inputs = validation_artifact.get("inputs")
    if not isinstance(inputs, dict):
        reasons.append("validation inputs must be a JSON object")
        inputs = {}
    if inputs.get("document_sha256") != expected_document_sha256:
        reasons.append("validation inputs document hash does not match the pinned case input")
    if inputs.get("anchors_sha256") != anchors_fingerprint(anchors):
        reasons.append("validation inputs anchor fingerprint does not match the pinned case inputs")
    identity = inputs.get("identity")
    if not isinstance(identity, dict):
        reasons.append("validation input identity must be a JSON object")
        identity = {}
    expected = expected_identity or {}
    if identity.get("document_id") != expected.get("document_id"):
        reasons.append("validation inputs document identity does not match the pinned identity")
    if identity.get("revision") != expected.get("revision"):
        reasons.append("validation inputs document revision does not match the pinned identity")
    if validation_artifact.get("model_requested") != expected_model:
        reasons.append("validation artifact does not record the requested model")
    if validation_artifact.get("prompt_version") != record.get("prompt_version"):
        reasons.append("validation artifact prompt version disagrees with the ledger")

    parsed = None
    if content is not None:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            reasons.append(f"response content is not valid JSON: {exc}")
    if not isinstance(parsed, dict):
        reasons.append("response draft must be a JSON object")
    if isinstance(parsed, dict) and isinstance(stored_draft, dict):
        if _canonical(parsed) != _canonical(stored_draft):
            reasons.append("saved draft disagrees with the response content")

    if parsed is not None and isinstance(parsed, dict):
        recomputed = validate_draft(
            parsed, anchors, expected_document_sha256, expected_identity
        ).as_dict()
        details["recomputed_validation"] = recomputed["status"]
        if recomputed["status"] != "accepted":
            reasons.append(f"recomputed validation rejected the response draft: {recomputed['errors']}")
        if stored_validation.get("status") != recomputed["status"]:
            reasons.append("stored validation status contradicts recomputation")
        if stored_validation.get("errors"):
            reasons.append("stored validation recorded errors despite a pass claim")
        if (record.get("validation") or {}).get("status") != "accepted":
            reasons.append("ledger validation flag is not accepted")

    # -- synthetic case: independent omission expectation -------------------
    if case == "synthetic_missing_revision":
        if not isinstance(parsed, dict):
            reasons.append("synthetic case has no parsed draft to evaluate")
        else:
            try:
                draft = DraftInterpretation(**parsed)
            except Exception as exc:  # noqa: BLE001 - reported as evidence failure
                reasons.append(f"synthetic case draft does not satisfy the schema: {exc}")
            else:
                expectation = evaluate_missing_information(draft)
                details["recomputed_expectation"] = expectation["status"]
                if expectation["status"] != "pass":
                    reasons.append(
                        "recomputed omission expectation failed: " + "; ".join(expectation["problems"])
                    )
                stored_expectation = validation_artifact.get("case_expectation") or {}
                if stored_expectation.get("status") != "pass":
                    reasons.append("stored omission expectation is not pass")
                if (record.get("case_expectation") or {}).get("status") != "pass":
                    reasons.append("ledger omission expectation flag is not pass")
    else:
        if validation_artifact.get("case_expectation") is not None:
            reasons.append("real-source validation artifact carries an unexpected omission expectation")

    if reasons:
        return EvidenceResult("FAIL", reasons, details)
    return EvidenceResult(
        "PASS",
        [
            "artifacts bound to case/attempt/model/endpoint; hashes match; completion stop; "
            "recomputed validation accepted"
            + ("; omission expectation reproduced" if case == "synthetic_missing_revision" else "")
        ],
        details,
    )

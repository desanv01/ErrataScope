"""Local regression suite: no network, no credentials, no paid calls.

Covers the attempt-01 defects and the repair requirements:

* R1 reservation-first dispatch: timeouts stop at the configured lifetime cap, restart reads
  reservations, malformed responses consume an attempt, history survives a later
  blocked preflight, invalid/NaN/negative pricing is rejected.
* R2 evidence-derived gates: 401/500, wrong model, truncated/empty, malformed or
  invalid JSON, missing artifacts, unexecuted negative case, failing local test,
  and missing baseline records all stay nonpassing; mocks never pass a live gate.
* R3 identity: correct sealed identity accepted with evidence; unrelated document
  ID, wrong revision, and silicon/document revision conflation rejected; missing
  revision stays unresolved; context anchors exist with real geometry.
"""

from __future__ import annotations

import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from . import cases, config, provider, report
from . import ledger as ledger_module
from .schemas import AnchorDocument, DraftInterpretation
from .util import read_json, sha256_bytes, sha256_file, utc_now_iso, write_json
from .validate import parse_json_file, validate_draft, verify_document_bytes

FIXTURES = config.FIXTURE_DIR
TMP_ROOT = config.LOCAL_DIR / "tmp" / "selftest"
RESULTS: list[dict] = []


def check(test_id: str, fn) -> None:
    try:
        detail = fn()
        status = "SKIP" if str(detail).startswith("SKIP:") else "PASS"
        RESULTS.append({"id": test_id, "status": status, "detail": detail})
    except AssertionError as exc:
        RESULTS.append({"id": test_id, "status": "FAIL", "detail": str(exc)})
    except Exception as exc:  # noqa: BLE001 - a crashing check is a failed check
        RESULTS.append({"id": test_id, "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})


def _fresh_dir(name: str) -> Path:
    path = TMP_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fake_pricing(**overrides) -> dict:
    pricing = {
        "verified": True,
        "provider": "Nebius Token Factory",
        "model_id": config.PROVIDER["model_id"],
        "base_url": config.PROVIDER["base_url"],
        "currency": "USD",
        "input_usd_per_1m": 0.30,
        "output_usd_per_1m": 0.90,
        "source_url": "https://example.invalid/pricing-evidence",
        "verified_date": "2026-10-29",
        "source_publication_date": "2026-10-16",
        "account_access_verified": False,
        "modality_scope": "Text-only W01 probe; do not infer image billing",
    }
    pricing.update(overrides)
    return pricing


def _small_payload() -> dict:
    return {
        "model": config.PROVIDER["model_id"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 64,
        "temperature": 0,
        "case": "real_source",
        "prompt_metadata": {"prompt_version": "selftest", "case": "real_source"},
    }


def load_anchor_fixture(name: str = "anchors_fixture.json") -> AnchorDocument:
    return AnchorDocument(**read_json(FIXTURES / name))


def _draft(name: str) -> dict:
    return read_json(FIXTURES / name)


# ---------------------------------------------------------------------------
# Core schema/anchor checks (attempt 01, retained)
# ---------------------------------------------------------------------------
def test_valid_anchor_fixture() -> str:
    document = load_anchor_fixture()
    assert len(document.anchors) == 2
    return f"{len(document.anchors)} anchors validated"


def test_valid_draft_accepted() -> str:
    document = load_anchor_fixture()
    result = validate_draft(_draft("draft_valid.json"), document.anchors, document.document_sha256)
    assert result.status == "accepted", result.errors
    return f"accepted with {result.anchor_references} anchor references"


def test_missing_revision_unresolved() -> str:
    document = load_anchor_fixture()
    result = validate_draft(_draft("draft_missing_revision.json"), document.anchors, document.document_sha256)
    assert result.status == "accepted", result.errors
    draft = DraftInterpretation(**_draft("draft_missing_revision.json"))
    assert draft.source_revision is None
    assert "source_revision" in draft.unresolved_fields
    return "revision None and listed unresolved"


def test_invented_revision_rejected() -> str:
    document = load_anchor_fixture()
    result = validate_draft(_draft("draft_invented_revision.json"), document.anchors, document.document_sha256)
    assert result.status == "rejected" and any("not grounded" in error for error in result.errors), result.errors
    return "rejected: revision not grounded"


def test_nonexistent_anchor_rejected() -> str:
    document = load_anchor_fixture()
    result = validate_draft(_draft("draft_nonexistent_anchor.json"), document.anchors, document.document_sha256)
    assert result.status == "rejected" and any("nonexistent anchor" in e for e in result.errors), result.errors
    return "rejected: nonexistent anchor"


def test_malformed_json_rejected() -> str:
    payload, error = parse_json_file(FIXTURES / "draft_malformed.json")
    assert payload is None and error
    return error or "rejected"


def test_schema_violation_rejected() -> str:
    document = load_anchor_fixture()
    result = validate_draft(_draft("draft_schema_invalid.json"), document.anchors, document.document_sha256)
    assert result.status == "rejected" and any("schema:" in e for e in result.errors), result.errors
    return "rejected: missing claims"


def test_bbox_out_of_range_rejected() -> str:
    try:
        AnchorDocument(**read_json(FIXTURES / "anchors_invalid_bbox.json"))
    except ValidationError as exc:
        messages = [str(error["msg"]) for error in exc.errors()]
        assert any("outside" in message for message in messages), messages
        return "rejected: normalized bbox outside [0,1]"
    raise AssertionError("out-of-range bbox was accepted")


def test_page_out_of_range_rejected() -> str:
    try:
        AnchorDocument(**read_json(FIXTURES / "anchors_page_out_of_range.json"))
    except ValidationError as exc:
        messages = [str(error["msg"]) for error in exc.errors()]
        assert any("page_index" in message or "outside page_count" in message for message in messages), messages
        return "rejected: page_index outside page_count"
    raise AssertionError("out-of-range page index was accepted")


def test_synthetic_fixtures_labeled() -> str:
    files = sorted((FIXTURES / "synthetic").glob("*.md"))
    assert len(files) == 3, f"expected 3 synthetic fixtures, found {len(files)}"
    for path in files:
        head = path.read_text(encoding="utf-8").splitlines()[:2]
        assert any("SYNTHETIC" in line.upper() for line in head), f"{path.name} lacks SYNTHETIC banner"
    manifest = read_json(config.MANIFEST_PATH)
    synthetic = [source for source in manifest["sources"] if source.get("kind") == "synthetic_fixture"]
    assert len(synthetic) == 3 and all(source.get("synthetic") for source in synthetic)
    return f"3 files labeled; {len(synthetic)} manifest records synthetic=true"


def test_hash_mismatch_detected() -> str:
    target = TMP_ROOT / "hash-check.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"original bytes")
    expected = sha256_bytes(target.read_bytes())
    ok, _ = verify_document_bytes(target, expected)
    assert ok
    target.write_bytes(b"tampered bytes")
    ok, actual = verify_document_bytes(target, expected)
    assert not ok and actual != expected
    return "mismatch detected after byte change"


# ---------------------------------------------------------------------------
# R1: reservation ledger
# ---------------------------------------------------------------------------
def test_token_bound_documented() -> str:
    payload = _small_payload()
    bound = ledger_module.bound_input_tokens(payload)
    encoded = sum(len(message["content"].encode("utf-8")) for message in payload["messages"])
    assert bound["method"] == "utf8_bytes_plus_message_overhead_v1"
    assert "assumption" in bound and "byte-level BPE" in bound["assumption"]
    assert bound["tokens"] >= encoded, "bound must not undercut raw UTF-8 bytes"
    bigger = {"messages": [{"role": "user", "content": "x" * 1000}], "max_tokens": 64}
    assert ledger_module.bound_input_tokens(bigger)["tokens"] > bound["tokens"]
    return f"bound={bound['tokens']} tokens >= {encoded} utf8 bytes ({bound['method']})"


def test_atomic_ledger_write() -> str:
    directory = _fresh_dir("atomic")
    ledger = ledger_module.Ledger(directory / "ledger.json")
    ledger.reserve(case="real_source", payload=_small_payload(), pricing=_fake_pricing(), prompt_version="t")
    assert ledger.path.exists()
    leftovers = list(directory.glob(".*.tmp"))
    assert not leftovers, f"temporary files left behind: {leftovers}"
    reloaded = ledger_module.Ledger(ledger.path)
    assert reloaded.state.requests_reserved == 1
    return "atomic replace, no temp residue, reload valid"


def test_timeouts_stop_at_request_cap() -> str:
    cap = config.BUDGET["max_requests"]
    directory = _fresh_dir("timeouts")
    ledger = ledger_module.Ledger(directory / "ledger.json")
    calls = {"n": 0}

    def timeout(*_args, **_kwargs):
        calls["n"] += 1
        raise httpx.ReadTimeout("simulated timeout; no network used")

    blocked = 0
    with patch.object(provider, "send_request", side_effect=timeout), patch.object(
        config, "PROVIDER_DIR", directory
    ):
        for _ in range(cap + 1):
            try:
                provider.run_case(
                    case="real_source",
                    payload=_small_payload(),
                    anchors=[],
                    expected_identity=None,
                    expected_document_sha256="0" * 64,
                    pricing=_fake_pricing(),
                    api_key="selftest-not-a-credential",
                    ledger=ledger,
                )
            except ledger_module.BudgetExhausted:
                blocked += 1
    assert calls["n"] == cap, f"expected {cap} dispatches, got {calls['n']}"
    assert blocked == 1, f"expected one guard refusal, got {blocked}"
    assert ledger.state.requests_reserved == cap
    assert all(attempt.state == "uncertain" for attempt in ledger.state.attempts)
    assert ledger.state.spend_reserved_usd > 0
    return f"{cap + 1} simulated timeouts -> {cap} dispatches, {cap} uncertain reservations, 1 guard refusal"


def test_restart_reads_reservations() -> str:
    cap = config.BUDGET["max_requests"]
    directory = _fresh_dir("restart")
    path = directory / "ledger.json"
    ledger = ledger_module.Ledger(path)
    for _ in range(cap):
        ledger.reserve(case="real_source", payload=_small_payload(), pricing=_fake_pricing(), prompt_version="t")
    restarted = ledger_module.Ledger(path)
    assert restarted.state.requests_reserved == cap
    try:
        restarted.reserve(case="real_source", payload=_small_payload(), pricing=_fake_pricing(), prompt_version="t")
    except ledger_module.BudgetExhausted:
        return f"restart sees {cap}/{cap} reserved and refuses another attempt"
    raise AssertionError("restarted ledger allowed an extra reservation")


def test_malformed_response_consumes_attempt() -> str:
    directory = _fresh_dir("malformed-response")
    ledger = ledger_module.Ledger(directory / "ledger.json")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, text="{not-json")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, patch.object(config, "PROVIDER_DIR", directory):
        record = provider.run_case(
            case="real_source",
            payload=_small_payload(),
            anchors=[],
            expected_identity=None,
            expected_document_sha256="0" * 64,
            pricing=_fake_pricing(),
            api_key="selftest-not-a-credential",
            ledger=ledger,
            client=client,
            execution_mode="mock",
        )
    assert record["outcome"] == "invalid_json", record["outcome"]
    assert ledger.state.requests_reserved == 1
    assert ledger.state.attempts[0].state == "finalized"
    assert ledger.state.attempts[0].response_sha256, "response artifact hash must be recorded"
    return "malformed provider body finalized as invalid_json and consumed attempt 1"


def test_history_survives_blocked_preflight() -> str:
    directory = _fresh_dir("history")
    ledger = ledger_module.Ledger(directory / "ledger.json")
    reservation = ledger.reserve(case="real_source", payload=_small_payload(), pricing=_fake_pricing(), prompt_version="t")
    ledger.mark_dispatched(reservation.attempt)
    ledger.finalize(reservation.attempt, outcome="http_error", http_status=500)
    before = ledger.state.model_dump(mode="json")
    provider.record_blocked("NEBIUS_API_KEY is not configured for this process.", ledger=ledger)
    after = ledger.state.model_dump(mode="json")
    assert after["requests_reserved"] == before["requests_reserved"] == 1
    assert after["attempts"] == before["attempts"], "blocked preflight must not rewrite attempts"
    assert len(after["blocked_events"]) == 1
    assert ledger.state.live_requests_made() is True
    return "blocked preflight appended history without erasing the prior dispatch"


def test_invalid_pricing_rejected() -> str:
    directory = _fresh_dir("pricing-invalid")
    base = {
        "schema_version": 1,
        "provider": "Nebius Token Factory",
        "model_id": config.PROVIDER["model_id"],
        "base_url": config.PROVIDER["base_url"],
        "currency": "USD",
        "input_usd_per_1m": 0.30,
        "output_usd_per_1m": 0.90,
        "source_url": "https://example.invalid/pricing",
        "verified_date_malaysia": "2026-10-29",
        "modality_scope": "Text-only W01 probe",
    }
    cases_to_try = {
        "nan": {**base, "input_usd_per_1m": float("nan")},
        "negative": {**base, "output_usd_per_1m": -1.0},
        "infinite": {**base, "input_usd_per_1m": float("inf")},
        "wrong-model": {**base, "model_id": "nvidia/some-other-model"},
        "wrong-base": {**base, "base_url": "https://api.example.invalid/v1/"},
        "missing-source": {k: v for k, v in base.items() if k != "source_url"},
    }
    rejected = []
    for name, payload in cases_to_try.items():
        path = directory / f"{name}.json"
        write_json(path, payload)
        try:
            ledger_module.load_pricing(path)
        except ledger_module.PricingError:
            rejected.append(name)
    assert len(rejected) == len(cases_to_try), f"accepted invalid pricing: {set(cases_to_try) - set(rejected)}"
    return f"rejected {len(rejected)} invalid pricing configurations"


def test_pricing_evidence_accepted() -> str:
    assert config.PRICING_EVIDENCE_PATH.exists(), "Codex pricing evidence file missing"
    pricing = ledger_module.load_pricing(config.PRICING_EVIDENCE_PATH)
    assert pricing["model_id"] == config.PROVIDER["model_id"]
    assert pricing["verified"] is True
    assert pricing["input_usd_per_1m"] >= 0 and pricing["output_usd_per_1m"] >= 0
    assert pricing["source_url"].startswith("https://")
    return (
        f"accepted model={pricing['model_id']} input=${pricing['input_usd_per_1m']}/1M "
        f"output=${pricing['output_usd_per_1m']}/1M verified {pricing['verified_date']}"
    )


# ---------------------------------------------------------------------------
# R2: artifact-content evidence bundles (repair 02)
# ---------------------------------------------------------------------------
def _case_materials(case: str) -> dict:
    if case == "real_source":
        sealed = _sealed()
        return {
            "anchors": sealed["document"].anchors,
            "sha": sealed["document"].document_sha256,
            "identity": {
                "document_id": sealed["source"]["document_id"],
                "revision": sealed["source"]["revision"],
                "sha256": sealed["document"].document_sha256,
            },
            "draft": _real_draft(sealed),
            "expectation": None,
        }
    document, anchors = cases.build_synthetic_anchors()
    draft = {
        "schema_version": 1,
        "source_document_id": None,
        "source_revision": None,
        "claims": [
            {
                "field": "unresolved_field",
                "statement": "The excerpt states neither a document ID nor a revision.",
                "anchor_ids": [anchors[0].anchor_id],
                "status": "unresolved",
            }
        ],
        "unresolved_fields": ["source_revision", "source_document_id"],
    }
    return {
        "anchors": anchors,
        "sha": document["document_sha256"],
        "identity": {"document_id": None, "revision": None, "sha256": document["document_sha256"]},
        "draft": draft,
        "expectation": cases.evaluate_missing_information(DraftInterpretation(**draft)),
    }


@contextmanager
def _bundle(name: str, case: str = "real_source"):
    """Build an internally consistent, hash-recorded evidence bundle in a temp dir."""
    directory = _fresh_dir(name) / "provider"
    directory.mkdir(parents=True, exist_ok=True)
    with patch.object(config, "PROVIDER_DIR", directory):
        materials = _case_materials(case)
        attempt = 1
        case_dir = directory / "cases" / case
        case_dir.mkdir(parents=True, exist_ok=True)
        paths = {kind: case_dir / f"attempt-01.{kind}.json" for kind in ("request", "response", "validation")}
        content = json.dumps(materials["draft"])
        content_type = json.dumps(materials["identity"])
        request = {
            "schema_version": 2,
            "artifact_kind": "request",
            "case": case,
            "attempt": attempt,
            "created_utc": utc_now_iso(),
            "provider": "Nebius Token Factory",
            "endpoint": config.PROVIDER["base_url"].rstrip("/") + "/" + config.PROVIDER["chat_path"],
            "model_requested": config.PROVIDER["model_id"],
            "prompt_version": "draft-v2",
            "request": {
                "model": config.PROVIDER["model_id"],
                "messages": [
                    {"role": "system", "content": "selftest system prompt"},
                    {"role": "user", "content": "selftest user prompt"},
                ],
                "max_tokens": 64,
                "temperature": 0,
            },
        }
        response = {
            "schema_version": 2,
            "artifact_kind": "response",
            "case": case,
            "attempt": attempt,
            "created_utc": utc_now_iso(),
            "endpoint": request["endpoint"],
            "model_requested": config.PROVIDER["model_id"],
            "prompt_version": "draft-v2",
            "http_status": 200,
            "request_id": "selftest-fixture",
            "latency_ms": 1,
            "content_type": "application/json",
            "authorization_header_recorded": False,
            "decode_error": None,
            "body": {
                "id": "selftest-fixture",
                "model": config.PROVIDER["model_id"],
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            "text_head": None,
        }
        validation = {
            "schema_version": 2,
            "artifact_kind": "validation",
            "case": case,
            "attempt": attempt,
            "created_utc": utc_now_iso(),
            "model_requested": config.PROVIDER["model_id"],
            "prompt_version": "draft-v2",
            "inputs": {
                "document_sha256": materials["sha"],
                "anchors_sha256": cases.anchors_fingerprint(materials["anchors"]),
                "identity": {
                    "document_id": materials["identity"]["document_id"],
                    "revision": materials["identity"]["revision"],
                },
            },
            "validation": validate_draft(
                materials["draft"], materials["anchors"], materials["sha"], materials["identity"]
            ).as_dict(),
            "case_expectation": materials["expectation"],
            "draft": materials["draft"],
        }
        write_json(paths["request"], request)
        write_json(paths["response"], response)
        write_json(paths["validation"], validation)
        record = {
            "attempt": attempt,
            "case": case,
            "state": "finalized",
            "outcome": "success",
            "execution_mode": "live",
            "http_status": 200,
            "model_returned": config.PROVIDER["model_id"],
            "finish_reason": "stop",
            "model_id": config.PROVIDER["model_id"],
            "base_url": config.PROVIDER["base_url"],
            "prompt_version": "draft-v2",
            "validation": {"status": "accepted", "errors": []},
            "case_expectation": materials["expectation"],
            "request_artifact": paths["request"].relative_to(config.PROJECT_ROOT).as_posix(),
            "response_artifact": paths["response"].relative_to(config.PROJECT_ROOT).as_posix(),
            "validation_artifact": paths["validation"].relative_to(config.PROJECT_ROOT).as_posix(),
            "request_sha256": sha256_file(paths["request"]),
            "response_sha256": sha256_file(paths["response"]),
            "validation_sha256": sha256_file(paths["validation"]),
        }
        ledger = {
            "schema_version": 2,
            "attempts": [record],
            "requests_reserved": 1,
            "spend_reserved_usd": 0.0,
            "blocked_events": [],
            "live_requests_made": True,
        }
        yield {
            "case": case,
            "record": record,
            "ledger": ledger,
            "materials": materials,
            "dir": directory,
            "paths": paths,
            "content_type": content_type,
        }


def _rewrite(bundle: dict, kind: str, obj: dict | None = None, raw: str | None = None, rehash: bool = True) -> None:
    path = config.PROJECT_ROOT / bundle["record"][f"{kind}_artifact"]
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    else:
        write_json(path, obj)
    if rehash:
        bundle["record"][f"{kind}_sha256"] = sha256_file(path)


def _evaluate(bundle: dict):
    from erratascope_w01 import evidence

    return evidence.evaluate_case(
        record=bundle["record"],
        case=bundle["case"],
        ledger=bundle["ledger"],
        anchors=bundle["materials"]["anchors"],
        expected_document_sha256=bundle["materials"]["sha"],
        expected_identity=bundle["materials"]["identity"],
    )


def _gate(bundle: dict) -> dict:
    case_inputs = {
        "anchors": bundle["materials"]["anchors"],
        "expected_document_sha256": bundle["materials"]["sha"],
        "expected_identity": bundle["materials"]["identity"],
        "ledger": bundle["ledger"],
    }
    return report.derive_case_gate(
        bundle["record"], gate_id="G4", case=bundle["case"], blocked_reason=None, case_inputs=case_inputs
    )


def _assert_fail(bundle: dict, label: str) -> str:
    result = _evaluate(bundle)
    gate = _gate(bundle)
    assert result.status == "FAIL", f"{label}: evidence {result.status}: {result.reasons}"
    assert gate["status"] == "FAIL", f"{label}: report gate {gate['status']}: {gate['reason']}"
    return f"{label}: evidence FAIL and report FAIL ({result.reasons[0]})"


def test_gate_well_formed_record_passes() -> str:
    with _bundle("well-formed") as bundle:
        result = _evaluate(bundle)
        gate = _gate(bundle)
    assert result.status == "PASS", result.reasons
    assert gate["status"] == "PASS", gate
    return "consistent hash-bound bundle passes evidence and report structurally"


def test_gate_401_not_pass() -> str:
    with _bundle("http-401") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["http_status"] = 401
        _rewrite(bundle, "response", response)
        return _assert_fail(bundle, "HTTP 401 in actual response despite 200 ledger flag")


def test_gate_500_not_pass() -> str:
    with _bundle("http-500") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["http_status"] = 500
        _rewrite(bundle, "response", response)
        return _assert_fail(bundle, "HTTP 500 in actual response")


def test_gate_wrong_model_not_pass() -> str:
    with _bundle("wrong-model") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["body"]["model"] = "nvidia/other-model"
        _rewrite(bundle, "response", response)
        return _assert_fail(bundle, "wrong returned model despite optimistic ledger")


def test_gate_truncated_not_pass() -> str:
    with _bundle("finish-length") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["body"]["choices"][0]["finish_reason"] = "length"
        _rewrite(bundle, "response", response)
        _assert_fail(bundle, "finish_reason=length")
    with _bundle("finish-tool-calls") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["body"]["choices"][0]["finish_reason"] = "tool_calls"
        _rewrite(bundle, "response", response)
        return _assert_fail(bundle, "finish_reason=tool_calls (no approved equivalence)")


def test_gate_empty_not_pass() -> str:
    with _bundle("empty-content") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["body"]["choices"][0]["message"]["content"] = ""
        _rewrite(bundle, "response", response)
        return _assert_fail(bundle, "empty completion content")


def test_gate_malformed_json_not_pass() -> str:
    with _bundle("malformed-artifact") as bundle:
        _rewrite(bundle, "response", raw="{not-json")
        return _assert_fail(bundle, "malformed response artifact JSON")


def test_gate_invalid_draft_not_pass() -> str:
    with _bundle("invalid-draft") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["body"]["choices"][0]["message"]["content"] = json.dumps({"schema_version": 1})
        _rewrite(bundle, "response", response)
        validation = read_json(bundle["paths"]["validation"])
        validation["draft"] = {"schema_version": 1}
        _rewrite(bundle, "validation", validation)
        return _assert_fail(bundle, "draft missing required schema fields")


def test_gate_empty_artifact_not_pass() -> str:
    with _bundle("empty-object") as bundle:
        _rewrite(bundle, "request", raw="{}")
        return _assert_fail(bundle, "empty {} request artifact")


def test_gate_directory_artifact_not_pass() -> str:
    with _bundle("directory-artifact") as bundle:
        target = bundle["dir"] / "cases" / bundle["case"] / "attempt-01.request.json"
        target.unlink()
        target.mkdir()
        bundle["record"]["request_sha256"] = None
        return _assert_fail(bundle, "artifact path is a directory")


def test_gate_missing_artifacts_not_pass() -> str:
    with _bundle("missing-artifact") as bundle:
        (config.PROJECT_ROOT / bundle["record"]["response_artifact"]).unlink()
        return _assert_fail(bundle, "response artifact missing")


def test_gate_wrong_case_not_pass() -> str:
    with _bundle("wrong-case") as bundle:
        request = read_json(bundle["paths"]["request"])
        request["case"] = "synthetic_missing_revision"
        _rewrite(bundle, "request", request)
        return _assert_fail(bundle, "request artifact bound to a different case")


def test_gate_wrong_attempt_not_pass() -> str:
    with _bundle("wrong-attempt") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["attempt"] = 99
        _rewrite(bundle, "response", response)
        return _assert_fail(bundle, "response artifact bound to a different attempt")


def test_gate_replaced_artifact_not_pass() -> str:
    with _bundle("replaced-artifact") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["request_id"] = "replaced-after-recording"
        _rewrite(bundle, "response", response, rehash=False)
        assert sha256_file(bundle["paths"]["response"]) != bundle["record"]["response_sha256"]
        return _assert_fail(bundle, "artifact replaced after its hash was recorded")


def test_gate_draft_disagreement_not_pass() -> str:
    with _bundle("draft-disagreement") as bundle:
        validation = read_json(bundle["paths"]["validation"])
        validation["draft"] = {**bundle["materials"]["draft"], "source_document_id": "DIFFERENT-DOC"}
        _rewrite(bundle, "validation", validation)
        return _assert_fail(bundle, "saved draft disagrees with response content")


def test_gate_synthetic_bundle_passes() -> str:
    with _bundle("synthetic-pass", case="synthetic_missing_revision") as bundle:
        result = _evaluate(bundle)
        gate = _gate(bundle)
    assert result.status == "PASS", result.reasons
    assert gate["status"] == "PASS", gate
    return "synthetic omission bundle passes only with its own recomputed expectation"


def test_gate_synthetic_expectation_required() -> str:
    with _bundle("synthetic-no-expectation", case="synthetic_missing_revision") as bundle:
        validation = read_json(bundle["paths"]["validation"])
        validation["case_expectation"] = None
        _rewrite(bundle, "validation", validation)
        bundle["record"]["case_expectation"] = None
        return _assert_fail(bundle, "synthetic bundle without a passing omission expectation")


def test_gate_mock_not_live() -> str:
    with _bundle("mock-record") as bundle:
        bundle["record"]["execution_mode"] = "mock"
        result = _evaluate(bundle)
        gate = _gate(bundle)
    assert result.status == "MOCK_ONLY", result.reasons
    assert gate["status"] == "NOT_RUN", gate
    return "mock execution record -> evidence MOCK_ONLY, report NOT_RUN"


def test_legacy_summary_flags_not_evidence() -> str:
    """The review-02 defect calls: optimistic flags + {} artifacts + non-stop finish."""
    directory = _fresh_dir("legacy-flags") / "provider"
    directory.mkdir(parents=True, exist_ok=True)
    with patch.object(config, "PROVIDER_DIR", directory):
        record = {
            "attempt": 1,
            "case": "real_source",
            "state": "finalized",
            "outcome": "success",
            "execution_mode": "live",
            "http_status": 200,
            "model_returned": config.PROVIDER["model_id"],
            "finish_reason": "stop",
            "validation": {"status": "accepted"},
            "case_expectation": None,
        }
        for kind in ("request", "response", "validation"):
            path = directory / f"{kind}.json"
            path.write_text("{}", encoding="utf-8")
            record[f"{kind}_artifact"] = path.relative_to(config.PROJECT_ROOT).as_posix()
        without_inputs = report.derive_case_gate(
            record, gate_id="G4", case="real_source", blocked_reason=None
        )
        wrong_case = dict(record, case="synthetic_missing_revision")
        wrong_case_gate = report.derive_case_gate(
            wrong_case, gate_id="G4", case="real_source", blocked_reason=None
        )
    assert without_inputs["status"] != "PASS", without_inputs
    assert wrong_case_gate["status"] != "PASS", wrong_case_gate
    assert provider.passes_live_gate({"finish_reason": "tool_calls"}) is False
    assert provider.passes_live_gate(record) is False
    return "legacy summary-flag path fails closed; non-stop finish rejected"


def test_cli_report_gate_consistency() -> str:
    checks = []
    with _bundle("consistency-pass") as bundle:
        checks.append((_evaluate(bundle).status, _gate(bundle)["status"]))
    with _bundle("consistency-401") as bundle:
        response = read_json(bundle["paths"]["response"])
        response["http_status"] = 401
        _rewrite(bundle, "response", response)
        checks.append((_evaluate(bundle).status, _gate(bundle)["status"]))
    with _bundle("consistency-replaced") as bundle:
        _rewrite(bundle, "request", raw="{bad", rehash=False)
        checks.append((_evaluate(bundle).status, _gate(bundle)["status"]))
    mapping = {"PASS": "PASS", "FAIL": "FAIL", "MOCK_ONLY": "NOT_RUN", "NOT_RUN": "NOT_RUN", "BLOCKED": "BLOCKED"}
    for evidence_status, gate_status in checks:
        assert mapping[evidence_status] == gate_status, (evidence_status, gate_status)
    return f"CLI/report statuses agree for {len(checks)} bundles"


def _selftest_record(failed: bool = False) -> dict:
    results = [
        {"id": test_id, "status": "FAIL" if failed and test_id == REQUIRED[0] else "PASS", "detail": "synthetic"}
        for test_id in REQUIRED
    ]
    return {
        "generated_utc": utc_now_iso(),
        "checks_total": len(results),
        "checks_passed": len([r for r in results if r["status"] == "PASS"]),
        "checks_failed": len([r for r in results if r["status"] == "FAIL"]),
        "checks_skipped": 0,
        "results": results,
    }


REQUIRED = report.REQUIRED_LOCAL_CHECKS


def test_gate_no_negative_case_partial() -> str:
    ledger = {"attempts": [], "blocked_events": [], "requests_reserved": 0, "spend_reserved_usd": 0.0}
    state = {
        "manifest": read_json(config.MANIFEST_PATH),
        "anchors": read_json(config.RESULT_DIR / "anchors.json"),
        "coverage": read_json(config.RESULT_DIR / "coverage.json"),
        "selftest": _selftest_record(),
        "renders": {"pages": [{"page_index": 0}]},
        "baseline": {"exit_code": 0, "result": {"status": "PASS", "protected_hashes_checked": 1, "local_links_checked": 1}},
        "ledger": ledger,
        "environment": {"python": {"version": "3.11"}},
        "pricing": None,
    }
    gates = {gate["gate"]: gate for gate in report.compute_gates(state)}
    assert gates["W01-G5"]["status"] == "PARTIAL", gates["W01-G5"]
    assert gates["W01-G5"]["status"] != "PASS"
    return "local pass + no omission case -> G5 PARTIAL"


def test_gate_failing_local_check_not_pass() -> str:
    ledger = {"attempts": [], "blocked_events": [], "requests_reserved": 0, "spend_reserved_usd": 0.0}
    state = {
        "manifest": read_json(config.MANIFEST_PATH),
        "anchors": read_json(config.RESULT_DIR / "anchors.json"),
        "coverage": read_json(config.RESULT_DIR / "coverage.json"),
        "selftest": _selftest_record(failed=True),
        "renders": {"pages": [{"page_index": 0}]},
        "baseline": {"exit_code": 0, "result": {"status": "PASS", "protected_hashes_checked": 1, "local_links_checked": 1}},
        "ledger": ledger,
        "environment": {"python": {"version": "3.11"}},
        "pricing": None,
    }
    gates = {gate["gate"]: gate for gate in report.compute_gates(state)}
    assert gates["W01-G5"]["status"] == "FAIL", gates["W01-G5"]
    return "failing local check -> G5 FAIL"


def test_baseline_missing_record_not_pass() -> str:
    gates = {gate["gate"]: gate for gate in report.compute_gates({"baseline": None})}
    assert gates["W01-G1"]["status"] == "NOT_RUN", gates["W01-G1"]
    return "missing baseline record -> G1 NOT_RUN"


# ---------------------------------------------------------------------------
# R3: identity and context
# ---------------------------------------------------------------------------
def _sealed() -> dict:
    manifest = read_json(config.MANIFEST_PATH)
    source = next(s for s in manifest["sources"] if s["source_key"] == "st-es0620")
    anchors_document = AnchorDocument(**read_json(config.RESULT_DIR / "anchors.json"))
    identity = next(a for a in anchors_document.anchors if a.context_kind == "source_identity")
    row = next(
        a
        for a in anchors_document.anchors
        if a.section == config.SELECTED_SECTIONS[0] and a.block_role == "table_row"
    )
    header = next(a for a in anchors_document.anchors if a.context_kind == "revision_header")
    return {
        "source": source,
        "document": anchors_document,
        "identity_anchor": identity,
        "row_anchor": row,
        "header_anchor": header,
    }


def _real_draft(sealed) -> dict:
    source = sealed["source"]
    return {
        "schema_version": 1,
        "source_document_id": source["document_id"],
        "source_revision": source["revision"],
        "claims": [
            {
                "field": "source_identity",
                "statement": f"{source['document_id']} {source['revision']} identity as printed.",
                "anchor_ids": [sealed["identity_anchor"].anchor_id],
                "status": "supported",
            },
            {
                "field": "affected_revision",
                "statement": "Revision Z is applicable to the selected reset entry.",
                "anchor_ids": [sealed["row_anchor"].anchor_id, sealed["header_anchor"].anchor_id],
                "status": "supported",
            },
            {
                "field": "trigger_condition",
                "statement": "Using the NRST pin may prevent a correct reset.",
                "anchor_ids": [
                    next(
                        a.anchor_id
                        for a in sealed["document"].anchors
                        if a.section == config.SELECTED_SECTIONS[0] and a.block_role == "body"
                    )
                ],
                "status": "supported",
            },
        ],
        "unresolved_fields": [],
    }


def test_identity_correct_accepted() -> str:
    sealed = _sealed()
    draft = _real_draft(sealed)
    expected = {
        "document_id": sealed["source"]["document_id"],
        "revision": sealed["source"]["revision"],
        "sha256": sealed["document"].document_sha256,
    }
    result = validate_draft(draft, sealed["document"].anchors, sealed["document"].document_sha256, expected)
    assert result.status == "accepted", result.errors
    return f"identity {draft['source_document_id']} {draft['source_revision']} accepted with cited identity anchor"


def test_identity_unrelated_document_rejected() -> str:
    sealed = _sealed()
    draft = _real_draft(sealed)
    draft["source_document_id"] = "COMPLETELY-DIFFERENT-DOCUMENT"
    expected = {
        "document_id": sealed["source"]["document_id"],
        "revision": sealed["source"]["revision"],
        "sha256": sealed["document"].document_sha256,
    }
    result = validate_draft(draft, sealed["document"].anchors, sealed["document"].document_sha256, expected)
    assert result.status == "rejected" and any("source_document_id" in e for e in result.errors), result.errors
    return "unrelated document ID rejected"


def test_identity_wrong_revision_rejected() -> str:
    sealed = _sealed()
    draft = _real_draft(sealed)
    draft["source_revision"] = "Rev 6"
    expected = {
        "document_id": sealed["source"]["document_id"],
        "revision": sealed["source"]["revision"],
        "sha256": sealed["document"].document_sha256,
    }
    result = validate_draft(draft, sealed["document"].anchors, sealed["document"].document_sha256, expected)
    assert result.status == "rejected" and any("source_revision" in e for e in result.errors), result.errors
    return "wrong document revision rejected"


def test_identity_missing_revision_unresolved() -> str:
    document, anchors = cases.build_synthetic_anchors()
    draft = {
        "schema_version": 1,
        "source_document_id": None,
        "source_revision": None,
        "claims": [
            {
                "field": "unresolved_field",
                "statement": "The excerpt states neither a document ID nor a revision.",
                "anchor_ids": [anchors[0].anchor_id],
                "status": "unresolved",
            }
        ],
        "unresolved_fields": ["source_revision", "source_document_id"],
    }
    expected = {"document_id": None, "revision": None, "sha256": document["document_sha256"], "enforce_missing": True}
    result = validate_draft(draft, anchors, document["document_sha256"], expected)
    assert result.status == "accepted", result.errors
    return "missing identity/revision stays null and unresolved"


def test_identity_silicon_revision_not_from_document() -> str:
    sealed = _sealed()
    draft = _real_draft(sealed)
    draft["claims"] = [
        claim for claim in draft["claims"] if claim["field"] != "affected_revision"
    ] + [
        {
            "field": "affected_revision",
            "statement": "Applies to revision as printed on the document.",
            "anchor_ids": [sealed["identity_anchor"].anchor_id],
            "status": "supported",
        }
    ]
    expected = {
        "document_id": sealed["source"]["document_id"],
        "revision": sealed["source"]["revision"],
        "sha256": sealed["document"].document_sha256,
    }
    result = validate_draft(draft, sealed["document"].anchors, sealed["document"].document_sha256, expected)
    assert result.status == "rejected" and any("affected_revision" in e for e in result.errors), result.errors
    return "silicon revision cannot be sourced from the document identity anchor"


def test_context_anchors_present() -> str:
    document = AnchorDocument(**read_json(config.RESULT_DIR / "anchors.json"))
    identity = [a for a in document.anchors if a.context_kind == "source_identity"]
    headers = [a for a in document.anchors if a.context_kind == "revision_header"]
    legends = [a for a in document.anchors if a.context_kind == "status_legend"]
    footnotes = [a for a in document.anchors if a.context_kind == "footnote"]
    assert identity and headers and legends and footnotes, (len(identity), len(headers), len(legends), len(footnotes))
    assert len(headers) == 3, len(headers)
    assert all(0 <= a.bbox.left < a.bbox.right <= 1 for a in identity + headers + legends + footnotes)
    assert all(a.geometry_kind == "located" for a in identity + headers + legends + footnotes)
    revision = "rev" in identity[0].text.lower()
    assert revision, identity[0].text
    return f"identity + {len(headers)} headers + {len(legends)} legend entries + {len(footnotes)} footnotes, located geometry"


# ---------------------------------------------------------------------------
# Mock / usage / secrets
# ---------------------------------------------------------------------------
def test_mock_response_execution_recorded() -> str:
    sealed = _sealed()
    draft = _real_draft(sealed)
    directory = _fresh_dir("mock-live-gate")
    ledger = ledger_module.Ledger(directory / "ledger.json")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "id": "mock-1",
                "model": config.PROVIDER["model_id"],
                "choices": [{"message": {"content": json.dumps(draft)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    expected = {
        "document_id": sealed["source"]["document_id"],
        "revision": sealed["source"]["revision"],
        "sha256": sealed["document"].document_sha256,
    }
    from erratascope_w01 import evidence

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, patch.object(config, "PROVIDER_DIR", directory):
        record = provider.run_case(
            case="real_source",
            payload=_small_payload(),
            anchors=sealed["document"].anchors,
            expected_identity=expected,
            expected_document_sha256=sealed["document"].document_sha256,
            pricing=_fake_pricing(),
            api_key="selftest-not-a-credential",
            ledger=ledger,
            client=client,
            execution_mode="mock",
        )
        ledger_snapshot = ledger.state.model_dump(mode="json")
        verdict = evidence.evaluate_case(
            record=record,
            case="real_source",
            ledger=ledger_snapshot,
            anchors=sealed["document"].anchors,
            expected_document_sha256=sealed["document"].document_sha256,
            expected_identity=expected,
        )
        gate = report.derive_case_gate(
            record,
            gate_id="G4",
            case="real_source",
            blocked_reason=None,
            case_inputs={
                "anchors": sealed["document"].anchors,
                "expected_document_sha256": sealed["document"].document_sha256,
                "expected_identity": expected,
                "ledger": ledger_snapshot,
            },
        )
    assert record["execution_mode"] == "mock"
    assert (record.get("validation") or {}).get("status") == "accepted", record.get("validation")
    assert verdict.status == "MOCK_ONLY", verdict.reasons
    assert gate["status"] == "NOT_RUN", gate
    assert ledger.state.requests_reserved == 1
    return "valid mock validated, evidence MOCK_ONLY, report NOT_RUN, execution_mode=mock recorded"


def test_missing_usage_unknown_not_zero() -> str:
    summary = provider._summarize_usage({"choices": []})
    assert summary["available"] is False and "prompt_tokens" not in summary
    return "usage reported unavailable"


def test_no_secret_values_in_public_evidence() -> str:
    key = os.environ.get(config.PROVIDER["api_key_env"])
    if not key:
        return "SKIP: NEBIUS_API_KEY not configured; no secret value to scan for"
    scanned = 0
    for root in (config.EVIDENCE_DIR, config.MANIFEST_DIR, config.SPIKE_DIR):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {".png", ".pdf"}:
                continue
            if key in path.read_text(encoding="utf-8", errors="ignore"):
                raise AssertionError(f"secret value found in {path}")
            scanned += 1
    return f"scanned {scanned} text artifacts; no secret value present"


CHECKS = [
    ("anchors_fixture_valid", test_valid_anchor_fixture),
    ("valid_draft_accepted", test_valid_draft_accepted),
    ("malformed_json_rejected", test_malformed_json_rejected),
    ("schema_violation_rejected", test_schema_violation_rejected),
    ("nonexistent_anchor_rejected", test_nonexistent_anchor_rejected),
    ("bbox_out_of_range_rejected", test_bbox_out_of_range_rejected),
    ("page_out_of_range_rejected", test_page_out_of_range_rejected),
    ("missing_revision_unresolved", test_missing_revision_unresolved),
    ("invented_revision_rejected", test_invented_revision_rejected),
    ("synthetic_fixtures_labeled", test_synthetic_fixtures_labeled),
    ("source_hash_mismatch_detected", test_hash_mismatch_detected),
    ("token_bound_documented", test_token_bound_documented),
    ("atomic_ledger_write", test_atomic_ledger_write),
    ("timeouts_stop_at_request_cap", test_timeouts_stop_at_request_cap),
    ("restart_reads_reservations", test_restart_reads_reservations),
    ("malformed_response_consumes_attempt", test_malformed_response_consumes_attempt),
    ("history_survives_blocked_preflight", test_history_survives_blocked_preflight),
    ("invalid_pricing_rejected", test_invalid_pricing_rejected),
    ("pricing_evidence_accepted", test_pricing_evidence_accepted),
    ("gate_401_not_pass", test_gate_401_not_pass),
    ("gate_500_not_pass", test_gate_500_not_pass),
    ("gate_wrong_model_not_pass", test_gate_wrong_model_not_pass),
    ("gate_truncated_not_pass", test_gate_truncated_not_pass),
    ("gate_empty_not_pass", test_gate_empty_not_pass),
    ("gate_malformed_json_not_pass", test_gate_malformed_json_not_pass),
    ("gate_invalid_draft_not_pass", test_gate_invalid_draft_not_pass),
    ("gate_empty_artifact_not_pass", test_gate_empty_artifact_not_pass),
    ("gate_directory_artifact_not_pass", test_gate_directory_artifact_not_pass),
    ("gate_wrong_case_not_pass", test_gate_wrong_case_not_pass),
    ("gate_wrong_attempt_not_pass", test_gate_wrong_attempt_not_pass),
    ("gate_replaced_artifact_not_pass", test_gate_replaced_artifact_not_pass),
    ("gate_draft_disagreement_not_pass", test_gate_draft_disagreement_not_pass),
    ("gate_synthetic_bundle_passes", test_gate_synthetic_bundle_passes),
    ("gate_synthetic_expectation_required", test_gate_synthetic_expectation_required),
    ("gate_mock_not_live", test_gate_mock_not_live),
    ("gate_missing_artifacts_not_pass", test_gate_missing_artifacts_not_pass),
    ("gate_well_formed_record_passes", test_gate_well_formed_record_passes),
    ("cli_report_gate_consistency", test_cli_report_gate_consistency),
    ("legacy_summary_flags_not_evidence", test_legacy_summary_flags_not_evidence),
    ("gate_no_negative_case_partial", test_gate_no_negative_case_partial),
    ("gate_failing_local_check_not_pass", test_gate_failing_local_check_not_pass),
    ("baseline_missing_record_not_pass", test_baseline_missing_record_not_pass),
    ("identity_correct_accepted", test_identity_correct_accepted),
    ("identity_unrelated_document_rejected", test_identity_unrelated_document_rejected),
    ("identity_wrong_revision_rejected", test_identity_wrong_revision_rejected),
    ("identity_missing_revision_unresolved", test_identity_missing_revision_unresolved),
    ("identity_silicon_revision_not_from_document", test_identity_silicon_revision_not_from_document),
    ("context_anchors_present", test_context_anchors_present),
    ("mock_response_execution_recorded", test_mock_response_execution_recorded),
    ("missing_usage_unknown_not_zero", test_missing_usage_unknown_not_zero),
    ("no_secret_values_in_public_evidence", test_no_secret_values_in_public_evidence),
]


def run_self_test() -> dict:
    RESULTS.clear()
    for test_id, fn in CHECKS:
        check(test_id, fn)
    failed = [result for result in RESULTS if result["status"] == "FAIL"]
    skipped = [result for result in RESULTS if result["status"] == "SKIP"]
    summary = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "network_used": False,
        "credentials_required": False,
        "checks_total": len(RESULTS),
        "checks_passed": len([r for r in RESULTS if r["status"] == "PASS"]),
        "checks_failed": len(failed),
        "checks_skipped": len(skipped),
        "results": RESULTS,
    }
    write_json(config.RESULT_DIR / "selftest.json", summary)
    return summary

"""Evidence-derived feasibility report (repair R2).

Gate results are computed from records actually written by this attempt:
the protected-baseline record, the local self-test record, the sealed source and
anchor artifacts, and the per-case ledger. A missing record is NOT_RUN, never
PASS. A mock execution can never satisfy a live gate.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config
from .ledger import load_ledger
from .util import read_json, rel, utc_now_iso, write_json, write_text

REQUIRED_LOCAL_CHECKS = (
    "anchors_fixture_valid",
    "valid_draft_accepted",
    "malformed_json_rejected",
    "schema_violation_rejected",
    "nonexistent_anchor_rejected",
    "bbox_out_of_range_rejected",
    "page_out_of_range_rejected",
    "missing_revision_unresolved",
    "invented_revision_rejected",
    "synthetic_fixtures_labeled",
    "source_hash_mismatch_detected",
    "token_bound_documented",
    "atomic_ledger_write",
    "timeouts_stop_at_request_cap",
    "restart_reads_reservations",
    "malformed_response_consumes_attempt",
    "history_survives_blocked_preflight",
    "invalid_pricing_rejected",
    "pricing_evidence_accepted",
    "gate_401_not_pass",
    "gate_500_not_pass",
    "gate_wrong_model_not_pass",
    "gate_truncated_not_pass",
    "gate_empty_not_pass",
    "gate_malformed_json_not_pass",
    "gate_invalid_draft_not_pass",
    "gate_empty_artifact_not_pass",
    "gate_directory_artifact_not_pass",
    "gate_wrong_case_not_pass",
    "gate_wrong_attempt_not_pass",
    "gate_replaced_artifact_not_pass",
    "gate_draft_disagreement_not_pass",
    "gate_synthetic_bundle_passes",
    "gate_synthetic_expectation_required",
    "gate_mock_not_live",
    "gate_missing_artifacts_not_pass",
    "gate_well_formed_record_passes",
    "cli_report_gate_consistency",
    "legacy_summary_flags_not_evidence",
    "gate_no_negative_case_partial",
    "gate_failing_local_check_not_pass",
    "baseline_missing_record_not_pass",
    "identity_correct_accepted",
    "identity_unrelated_document_rejected",
    "identity_wrong_revision_rejected",
    "identity_missing_revision_unresolved",
    "identity_silicon_revision_not_from_document",
    "context_anchors_present",
)


def _load(path: Path, default=None):
    try:
        return read_json(path)
    except Exception:
        return default


def _exists(relative_path: str | None) -> bool:
    if not relative_path:
        return False
    return (config.PROJECT_ROOT / relative_path).exists()


def _is_current(timestamp: str | None) -> bool:
    """True only for records written during this worker attempt."""
    return bool(timestamp) and str(timestamp) >= config.WORKER_ATTEMPT_START_UTC


def _blocked_reason(ledger: dict | None, case: str | None = None) -> str | None:
    if not ledger:
        return None
    events = [event for event in ledger.get("blocked_events") or [] if _is_current(event.get("utc"))]
    if case:
        events = [event for event in events if event.get("case") == case]
    return events[-1].get("reason") if events else None


def _last_case_attempt(ledger: dict | None, case: str) -> dict | None:
    if not ledger:
        return None
    attempts = [a for a in ledger.get("attempts", []) if a.get("case") == case]
    return max(attempts, key=lambda a: a.get("attempt", 0)) if attempts else None


def derive_case_gate(
    record: dict | None,
    *,
    gate_id: str,
    case: str,
    blocked_reason: str | None,
    case_inputs: dict | None = None,
) -> dict:
    """Per-case gate derived by the same evidence validator the CLI uses."""
    if record is None:
        return {
            "gate": gate_id,
            "status": "NOT_RUN",
            "reason": f"no '{case}' attempt recorded" + (f"; blocked: {blocked_reason}" if blocked_reason else ""),
        }
    if case_inputs is None:
        return {
            "gate": gate_id,
            "status": "FAIL",
            "reason": "pinned case inputs unavailable; artifact contents cannot be validated",
        }
    from .evidence import evaluate_case

    result = evaluate_case(
        record=record,
        case=case,
        ledger=case_inputs["ledger"],
        anchors=case_inputs["anchors"],
        expected_document_sha256=case_inputs["expected_document_sha256"],
        expected_identity=case_inputs["expected_identity"],
    )
    status = {
        "PASS": "PASS",
        "FAIL": "FAIL",
        "MOCK_ONLY": "NOT_RUN",
        "NOT_RUN": "NOT_RUN",
        "BLOCKED": "BLOCKED",
    }.get(result.status, "FAIL")
    return {
        "gate": gate_id,
        "status": status,
        "reason": (
            f"attempt {record.get('attempt')} evidence PASS: " + "; ".join(result.reasons)
            if status == "PASS"
            else "; ".join(result.reasons)
        ),
    }


def derive_local_gate(selftest: dict | None) -> dict:
    if not selftest:
        return {"status": "NOT_RUN", "reason": "no self-test record for this attempt"}
    if not _is_current(selftest.get("generated_utc")):
        return {
            "status": "NOT_RUN",
            "reason": "self-test record predates this attempt; historical results do not count",
        }
    results = {result["id"]: result for result in selftest.get("results", [])}
    failed = [test_id for test_id, result in results.items() if result.get("status") == "FAIL"]
    missing = [test_id for test_id in REQUIRED_LOCAL_CHECKS if test_id not in results]
    if failed:
        return {"status": "FAIL", "reason": f"failing local checks: {', '.join(sorted(failed))}"}
    if missing:
        return {"status": "FAIL", "reason": f"required local checks missing: {', '.join(missing)}"}
    not_passed = [
        test_id
        for test_id in REQUIRED_LOCAL_CHECKS
        if results[test_id].get("status") != "PASS"
    ]
    if not_passed:
        return {"status": "FAIL", "reason": f"required local checks not passing: {', '.join(not_passed)}"}
    return {
        "status": "PASS",
        "reason": f"{selftest.get('checks_passed')}/{selftest.get('checks_total')} local checks passed, required set present",
    }


def derive_baseline_gate(record: dict | None) -> dict:
    if not record:
        return {"status": "NOT_RUN", "reason": "no protected-baseline record for this attempt"}
    if not _is_current(record.get("recorded_utc")):
        return {
            "status": "NOT_RUN",
            "reason": "baseline record predates this attempt; historical results do not count",
        }
    if record.get("exit_code") != 0:
        return {"status": "FAIL", "reason": f"verifier exit {record.get('exit_code')}"}
    result = record.get("result") or {}
    if result.get("status") != "PASS":
        return {"status": "FAIL", "reason": f"verifier status {result.get('status')}"}
    return {
        "status": "PASS",
        "reason": (
            f"{result.get('protected_hashes_checked')} protected hashes / "
            f"{result.get('local_links_checked')} links checked at {record.get('recorded_utc')}"
        ),
    }


def compute_gates(state: dict, case_inputs: dict | None = None) -> list[dict]:
    """Pure gate computation; tests inject synthetic state dictionaries."""
    case_inputs = case_inputs or {}
    manifest = state.get("manifest") or {}
    anchors_doc = state.get("anchors") or {}
    coverage = state.get("coverage") or {}
    selftest = state.get("selftest")
    ledger = state.get("ledger")
    counts = coverage.get("counts") or {}

    baseline = derive_baseline_gate(state.get("baseline"))
    source = next((s for s in manifest.get("sources", []) if s.get("source_key") == "st-es0620"), {})
    source_ok = bool(
        source.get("sha256")
        and anchors_doc.get("document_sha256") == source.get("sha256")
        and anchors_doc.get("page_count") == source.get("page_count")
        and counts.get("anchored_sections") == len(config.SELECTED_SECTIONS)
    )
    g2 = {
        "status": "PASS" if source_ok else ("NOT_RUN" if not source else "FAIL"),
        "reason": (
            f"source hash bound to anchors; {counts.get('anchored_sections')} selected sections anchored"
            if source_ok
            else "source/anchor binding or selected coverage is missing or inconsistent"
        ),
    }
    selected_anchors = [
        a
        for a in anchors_doc.get("anchors", [])
        if a.get("section") in config.SELECTED_SECTIONS and a.get("block_role") in {"heading", "body", "code"}
    ]
    renders = state.get("renders") or {}
    g3 = {
        "status": "PASS" if selected_anchors and renders.get("pages") else "NOT_RUN",
        "reason": (
            f"{len(selected_anchors)} selected-section anchors with bbox and {len(renders.get('pages', []))} rendered pages"
            if selected_anchors and renders.get("pages")
            else "selected-section anchors or page renders missing"
        ),
    }

    real_record = _last_case_attempt(ledger, "real_source")
    synthetic_record = _last_case_attempt(ledger, "synthetic_missing_revision")
    g4 = derive_case_gate(
        real_record,
        gate_id="W01-G4",
        case="real_source",
        blocked_reason=_blocked_reason(ledger, "real_source"),
        case_inputs=_with_ledger(case_inputs.get("real_source"), ledger),
    )
    live_negative = derive_case_gate(
        synthetic_record,
        gate_id="W01-G5-live",
        case="synthetic_missing_revision",
        blocked_reason=_blocked_reason(ledger, "synthetic_missing_revision"),
        case_inputs=_with_ledger(case_inputs.get("synthetic_missing_revision"), ledger),
    )
    local = derive_local_gate(selftest)
    if local["status"] == "FAIL":
        g5_status, g5_reason = "FAIL", f"local checks failed: {local['reason']}"
    elif local["status"] == "NOT_RUN":
        g5_status, g5_reason = "NOT_RUN", local["reason"]
    elif live_negative["status"] == "PASS":
        g5_status, g5_reason = "PASS", "local checks pass and the live omission case evidence passed"
    elif live_negative["status"] == "FAIL":
        g5_status, g5_reason = "FAIL", f"local checks pass; live omission evidence failed: {live_negative['reason']}"
    else:
        g5_status, g5_reason = "PARTIAL", f"local checks pass; live omission case not run: {live_negative['reason']}"

    synthetic_sources = [s for s in manifest.get("sources", []) if s.get("kind") == "synthetic_fixture"]
    fixtures_present = all(
        (config.PROJECT_ROOT / source.get("artifact_path", "")).exists()
        for source in synthetic_sources
        if source.get("artifact_path")
    )
    g6 = {
        "status": "PASS" if len(synthetic_sources) >= 2 and fixtures_present else "FAIL",
        "reason": (
            f"{len(synthetic_sources)} labeled synthetic fixtures with hashes; no manufacturer pair claimed"
            if len(synthetic_sources) >= 2 and fixtures_present
            else "synthetic fallback fixtures or manifest records missing"
        ),
    }
    env = state.get("environment") or {}
    g7_ready = (
        _is_current(env.get("generated_utc"))
        and _is_current((state.get("baseline") or {}).get("recorded_utc"))
        and _is_current((selftest or {}).get("generated_utc"))
    )
    g7 = {
        "status": "PASS" if g7_ready else "PARTIAL",
        "reason": (
            "environment, baseline, and local-check records are current for this attempt; "
            "provider/account gaps listed below"
            if g7_ready
            else "environment, baseline, or local-check record missing or predates this attempt"
        ),
    }

    def row(gate: str, result: dict, evidence: str) -> dict:
        return {
            "gate": gate,
            "status": result["status"],
            "reason": result["reason"],
            "evidence": evidence,
        }

    return [
        row("W01-G1", baseline, "protected baseline record from this attempt"),
        row("W01-G2", g2, "sealed source + anchor bundle + coverage"),
        row("W01-G3", g3, "selected anchors with bbox + page renders"),
        row("W01-G4", g4, "real_source case artifacts in the ledger"),
        row("W01-G5", {"status": g5_status, "reason": g5_reason}, "local self-test + synthetic_missing_revision case"),
        row("W01-G6", g6, "synthetic fixtures + manifest records"),
        row("W01-G7", g7, "environment/baseline/self-test records; uncertainties below"),
    ]


def _with_ledger(inputs: dict | None, ledger: dict | None) -> dict | None:
    if not inputs:
        return None
    return {**inputs, "ledger": ledger}


def _build_case_inputs(manifest: dict, anchors_doc: dict) -> dict:
    """Pinned inputs used to recompute evidence for each case."""
    inputs: dict = {}
    source = next(
        (item for item in manifest.get("sources", []) if item.get("source_key") == "st-es0620"),
        None,
    )
    if source is not None and anchors_doc:
        from .schemas import AnchorDocument

        document = AnchorDocument(**anchors_doc)
        inputs["real_source"] = {
            "anchors": document.anchors,
            "expected_document_sha256": document.document_sha256,
            "expected_identity": {
                "document_id": source.get("document_id"),
                "revision": source.get("revision"),
                "sha256": document.document_sha256,
            },
        }
    try:
        from .cases import build_synthetic_anchors

        synthetic_document, synthetic_anchors = build_synthetic_anchors()
        inputs["synthetic_missing_revision"] = {
            "anchors": synthetic_anchors,
            "expected_document_sha256": synthetic_document["document_sha256"],
            "expected_identity": {
                "document_id": None,
                "revision": None,
                "sha256": synthetic_document["document_sha256"],
            },
        }
    except Exception:  # noqa: BLE001, S110 - missing synthetic fixture leaves that gate NOT_RUN
        pass
    return inputs


def build_report() -> dict:
    environment = _load(config.ENVIRONMENT_PATH, {})
    manifest = _load(config.MANIFEST_PATH, {})
    anchors_doc = _load(config.RESULT_DIR / "anchors.json", {})
    coverage = _load(config.RESULT_DIR / "coverage.json", {})
    matrix = _load(config.RESULT_DIR / "revision_matrix.json", {})
    selftest = _load(config.RESULT_DIR / "selftest.json")
    renders = _load(config.RESULT_DIR / "renders.json", {})
    baseline_record = _load(config.RESULT_DIR / "baseline_check.json")
    commands = _load(config.RESULT_DIR / "command_log.json", [])
    ledger, ledger_error = load_ledger()
    pricing, pricing_error = None, None
    try:
        from .ledger import load_pricing

        pricing = load_pricing()
    except Exception as exc:  # noqa: BLE001 - invalid pricing is report evidence
        pricing_error = f"{type(exc).__name__}: {exc}"

    state = {
        "environment": environment,
        "manifest": manifest,
        "anchors": anchors_doc,
        "coverage": coverage,
        "selftest": selftest,
        "renders": renders,
        "baseline": baseline_record,
        "ledger": ledger,
        "pricing": pricing,
    }
    case_inputs = _build_case_inputs(manifest, anchors_doc)
    gates = compute_gates(state, case_inputs)

    st_source = next(
        (source for source in manifest.get("sources", []) if source.get("source_key") == "st-es0620"),
        {},
    )
    anchors = anchors_doc.get("anchors", [])
    parsers = anchors_doc.get("parsers", [])
    counts = coverage.get("counts", {})
    entries = coverage.get("entries", [])
    context_anchors = [anchor for anchor in anchors if anchor.get("context_kind")]

    lines: list[str] = []
    add = lines.append
    add(f"# W01 feasibility report — worker repair draft ({config.WORKER_ATTEMPT})")
    add("")
    add(
        "Status: **worker draft for Codex review**. Gate values below are computed from records "
        "written by this attempt; this file does not accept a gate or change canonical status."
    )
    add("")
    add(f"- Generated: {utc_now_iso()}")
    add(f"- Packet: W01-feasibility revision 1; evidence attempt: {config.WORKER_ATTEMPT}")
    add(f"- Configured worker baseline: {config.REPAIR_BASELINE_PATH.name}; see recorded baseline below for the actual verification target")
    add(f"- Source document: {st_source.get('document_id')} {st_source.get('revision')} "
        f"({st_source.get('publication_date')}), {st_source.get('page_count')} pages")
    add(f"- Source SHA-256: `{st_source.get('sha256')}`")
    add(f"- Selected sections: {', '.join(coverage.get('selected_sections') or [])}")
    add("")

    add("## Gate table (computed from this attempt's records)")
    add("")
    add("| Gate | Status | Reason | Evidence |")
    add("|---|---|---|---|")
    for gate in gates:
        add(f"| {gate['gate']} | **{gate['status']}** | {gate['reason']} | {gate['evidence']} |")
    add("")
    add(
        "A live gate requires a real dispatched request, the configured model binding, a complete "
        "non-truncated completion, accepted schema/citation validation, and case-bound artifacts. "
        "Mocks, caches, failed requests, unexecuted cases, and missing records are nonpassing."
    )
    add("")

    add("## Repair dispositions (R1–R4)")
    add("")
    add("| Repair | Disposition | Evidence | Limit |")
    add("|---|---|---|---|")
    add(
        "| R1 reservation/uncertainty | Implemented and regression-tested offline | "
        "`spikes/w01/erratascope_w01/ledger.py` (atomic reservation before dispatch, never reused); "
        "checks `timeouts_stop_at_request_cap`, `restart_reads_reservations`, "
        "`malformed_response_consumes_attempt`, `history_survives_blocked_preflight`, "
        "`atomic_ledger_write`, `token_bound_documented`, `invalid_pricing_rejected` | "
        "See the provider ledger below for actual dispatch and reservation evidence; offline tests alone do not prove live behavior |"
    )
    add(
        "| R2 evidence-derived gates | Implemented with a shared artifact-content validator; "
        "gate values computed from records | `report.compute_gates` calls `evidence.evaluate_case` "
        "(same path as the CLI) for G4/live G5: case/attempt binding, artifact JSON contents, recorded "
        "SHA-256 replacement checks, HTTP status, returned model, `finish_reason=stop`, response/draft "
        "agreement, recomputed schema/citation/identity validation against pinned inputs, and the "
        "synthetic omission expectation; checks `gate_401_not_pass`, `gate_500_not_pass`, "
        "`gate_wrong_model_not_pass`, `gate_truncated_not_pass`, `gate_empty_not_pass`, "
        "`gate_malformed_json_not_pass`, `gate_invalid_draft_not_pass`, `gate_empty_artifact_not_pass`, "
        "`gate_directory_artifact_not_pass`, `gate_wrong_case_not_pass`, `gate_wrong_attempt_not_pass`, "
        "`gate_replaced_artifact_not_pass`, `gate_draft_disagreement_not_pass`, "
        "`gate_synthetic_bundle_passes`, `gate_synthetic_expectation_required`, `gate_mock_not_live`, "
        "`gate_missing_artifacts_not_pass`, `gate_well_formed_record_passes`, "
        "`cli_report_gate_consistency`, `gate_no_negative_case_partial`, "
        "`baseline_missing_record_not_pass` | See current gate table: historical credential failures do not override executed evidence |"
    )
    add(
        "| R3 source identity/context | Implemented; identity read from the sealed manifest and citable | "
        "`cases.py` payload identity; `context.py` identity/revision-header/legend/footnote anchors; "
        "`validate.py` identity + silicon-vs-document revision checks; checks `identity_correct_accepted`, "
        "`identity_unrelated_document_rejected`, `identity_wrong_revision_rejected`, "
        "`identity_missing_revision_unresolved`, `identity_silicon_revision_not_from_document`, "
        "`context_anchors_present` | Identity consistency is structural, not semantic proof |"
    )
    add(
        "| R4 runnable cases/pricing | Implemented; explicit per-case selection and validated pricing input | "
        "`run.py probe-provider --case ... --pricing-file ...`; `ledger.load_pricing` against the protected "
        "Codex pricing evidence; checks `pricing_evidence_accepted`, `invalid_pricing_rejected` | "
        "Live cases blocked: `NEBIUS_API_KEY` absent from the worker process |"
    )
    add("")

    add("## R2 evidence binding (repair 02)")
    add("")
    add(
        "Both `probe-provider` and this report now call one validator, "
        "`evidence.evaluate_case`. It does not trust ledger summary flags or artifact existence:"
    )
    add("")
    add("1. The ledger record case must equal the expected gate case, and the attempt must be the "
        "finalized attempt reserved in the intended ledger (mock/uncertain/failed records cannot pass).")
    add("2. The request, response, and validation JSON files are read and parsed; empty objects, "
        "directories, missing files, malformed JSON, and paths outside the provider artifact tree "
        "are rejected.")
    add("3. Each artifact carries its own case, attempt, kind, and schema version, and its SHA-256 "
        "recorded in the ledger at creation; a later replacement is detectable and fails.")
    add("4. The response must be HTTP 200 with the configured model returned, nonempty content, and "
        "`finish_reason=stop`; the same conditions are enforced in execution, CLI, and report.")
    add("5. The saved draft must equal the response content, and schema/citation/identity validation "
        "is recomputed against pinned document hash, anchor fingerprint, and identity; a stored "
        "`accepted` string cannot overrule the recomputation.")
    add("6. The synthetic case must independently reproduce its missing-information expectation; a "
        "real-source result cannot substitute for it.")
    add("")
    add(
        "Attempt-02 behavior was: gate PASS if `live_requests_made`/`validation.status` were optimistic "
        "and the artifact paths existed; its positive test used `{}` files. Attempt-03 replaces that "
        "with the content-bound validator and a genuine consistent fixture bundle, and maps missing "
        "cases to NOT_RUN, mocks to NOT_RUN, incomplete/contradictory executed evidence to FAIL, and "
        "missing credentials to a recorded BLOCKED preflight. A structural PASS remains provisional "
        "pending Codex semantic review."
    )
    add("")

    add("## Protected baseline record")
    add("")
    if baseline_record:
        result = baseline_record.get("result") or {}
        add(f"- Command: `{baseline_record.get('command')}`")
        add(f"- Exit code: {baseline_record.get('exit_code')}")
        add(f"- Recorded: {baseline_record.get('recorded_utc')}")
        add(
            f"- Result: {result.get('status')}; protected hashes {result.get('protected_hashes_checked')}; "
            f"links {result.get('local_links_checked')}; errors {result.get('errors')}"
        )
    else:
        add("- **No baseline record exists for this attempt.** G1 is NOT_RUN, not PASS.")
    add("")

    add("## Environment (measured)")
    add("")
    python_info = environment.get("python", {})
    add(f"- Python {python_info.get('version')} ({python_info.get('implementation')}) in "
        f"`{python_info.get('executable')}`")
    add(f"- Platform: {(environment.get('platform') or {}).get('platform')}")
    add("")
    add("| Package | Version |")
    add("|---|---|")
    for name, info in (environment.get("packages") or {}).items():
        add(f"| {name} | {info.get('version') or 'not installed'} |")
    add("")
    capabilities = environment.get("capabilities", {})
    docker_client = capabilities.get("docker_client", {})
    docker_daemon = capabilities.get("docker_daemon", {})
    daemon_text = (
        "reachable"
        if docker_daemon.get("exit_code") == 0
        else f"not reachable (exit {docker_daemon.get('exit_code')})"
    )
    add(f"- Docker client: {docker_client.get('first_line') or 'not found'}; daemon: {daemon_text}")
    add(
        f"- WSL: exit {capabilities.get('wsl', {}).get('exit_code')} "
        f"({capabilities.get('wsl', {}).get('first_line') or 'no output'})"
    )
    add("")

    add("## Source provenance")
    add("")
    add("| Field | Value |")
    add("|---|---|")
    for key in (
        "source_key",
        "manufacturer",
        "document_id",
        "revision",
        "publication_date",
        "http_status",
        "byte_size",
        "page_count",
        "sha256",
        "final_url",
        "redistribution",
    ):
        add(f"| {key} | {st_source.get(key)} |")
    add("")

    add("## Identity and context anchors (R3)")
    add("")
    add("| Context | Anchor | Page | Text |")
    add("|---|---|---|---|")
    for anchor in context_anchors:
        text = (anchor.get("text") or "").replace("\n", " ")[:110]
        add(f"| {anchor.get('context_kind')} | `{anchor.get('anchor_id')}` | {anchor.get('page_index')} | {text} |")
    add("")
    add(
        "The derived revision matrix below is not authority: each value is checked against the "
        "row anchor and the governing `Rev. Z / Rev. B / Rev. X` header anchors listed above, and "
        "the status letters require their legend anchors."
    )
    add("")
    add("| Section | Status | Title | Pages | Revision matrix | Row anchor |")
    add("|---|---|---|---|---|---|")
    for entry in entries:
        row = (matrix.get("rows") or {}).get(entry.get("section")) or {}
        statuses = row.get("status_by_revision") or {}
        matrix_text = ", ".join(
            f"Rev. {letter}={statuses[letter]}" for letter in ("Z", "B", "X") if letter in statuses
        ) or "unresolved"
        row_anchor = f"`st-es0620:p{row.get('page_index', 0):02d}:row-{entry.get('section', '').replace('.', '-')}`"
        add(
            f"| {entry.get('section')} | {entry.get('status')} | {entry.get('section_title')} | "
            f"{entry.get('page_indexes')} | {matrix_text} | {row_anchor} |"
        )
    add("")

    add("## Parsing and coverage")
    add("")
    add("| Parser | Version | Mode |")
    add("|---|---|---|")
    for parser in parsers:
        add(f"| {parser.get('name')} | {parser.get('version')} | {parser.get('mode')} |")
    add("")
    add(f"- Anchors persisted: **{len(anchors)}** (context anchors: {len(context_anchors)})")
    add(f"- Coverage counts: `{json.dumps(counts)}`")
    add(f"- Page renders: `{rel(config.PAGE_DIR)}` ({len(renders.get('pages', []))} pages)")
    add("- Printed page labels remain separate from physical zero-based page indexes.")
    add("")

    add("## Provider cases, ledger, and pricing (R1/R4)")
    add("")
    if pricing:
        add(
            f"- Validated pricing: model `{pricing['model_id']}`, input ${pricing['input_usd_per_1m']}/1M, "
            f"output ${pricing['output_usd_per_1m']}/1M, verified {pricing['verified_date']}, "
            f"source {pricing['source_url']}, account_access_verified={pricing['account_access_verified']}."
        )
    else:
        add(f"- **Pricing configuration invalid or missing:** {pricing_error}")
    if ledger_error:
        add(f"- **Ledger unavailable:** {ledger_error}")
    if ledger:
        add(
            f"- Ledger: {ledger.get('requests_reserved')} attempt(s) reserved, "
            f"${ledger.get('spend_reserved_usd'):.6f} reserved, "
            f"live_requests_made={ledger.get('live_requests_made')}."
        )
        add("")
        add("| Attempt | Case | State | Outcome | HTTP | Model returned | Validation | Cost USD |")
        add("|---|---|---|---|---|---|---|---|")
        for attempt in ledger.get("attempts", []):
            validation = (attempt.get("validation") or {}).get("status", "n/a")
            add(
                f"| {attempt.get('attempt')} | {attempt.get('case')} | {attempt.get('state')} | "
                f"{attempt.get('outcome')} | {attempt.get('http_status')} | {attempt.get('model_returned')} | "
                f"{validation} | {attempt.get('estimated_cost_usd')} |"
            )
        add("")
        if ledger.get("blocked_events"):
            add("Blocked preflight events (history preserved, prior attempts untouched):")
            add("")
            for event in ledger["blocked_events"]:
                add(f"- {event.get('utc')}: {event.get('reason')}")
            add("")
    else:
        add("- No ledger exists; no case has been dispatched.")
        add("")
    add("**Live / mock distinction:** every ledger attempt records `execution_mode`. Mock executions "
        "are labelled and cannot satisfy G4 or the live part of G5.")
    add("")

    add("## Local regression checks")
    add("")
    if selftest:
        add(
            f"- {selftest.get('checks_passed')} passed, {selftest.get('checks_failed')} failed, "
            f"{selftest.get('checks_skipped')} skipped ({selftest.get('checks_total')} total); "
            f"generated {selftest.get('generated_utc')}; network_used={selftest.get('network_used')}."
        )
        add(f"- Raw results: `{rel(config.RESULT_DIR / 'selftest.json')}`")
        add("")
        add("| Check | Status | Detail |")
        add("|---|---|---|")
        for result in selftest.get("results", []):
            add(f"| {result['id']} | {result['status']} | {result['detail']} |")
        add("")
    else:
        add("- **No self-test record for this attempt.** G5 local evidence is NOT_RUN.")
        add("")

    add("## Commands actually run")
    add("")
    current_commands: list[dict] = []
    historical_commands: list[dict] = []
    for record in commands:
        is_current = record.get("attempt") == config.WORKER_ATTEMPT or (
            record.get("attempt") is None
            and str(record.get("started_utc", "")) >= config.WORKER_ATTEMPT_START_UTC
        )
        (current_commands if is_current else historical_commands).append(record)
    add(f"### This attempt ({config.WORKER_ATTEMPT})")
    add("")
    if current_commands:
        add("| Command | Exit code | Finished (UTC) |")
        add("|---|---|---|")
        for record in current_commands:
            add(f"| `{record.get('command')}` | {record.get('exit_code')} | {record.get('finished_utc')} |")
    else:
        add("No command records tagged for this attempt.")
    add("")
    add(
        f"### Historical records preserved ({len(historical_commands)} attempt-01 command records)"
    )
    add("")
    add(
        "Attempt-01 command history remains in `.local/w01/results/command_log.json` and its evidence "
        "snapshot in `.local/reviews/W01-review-01/`; it is not counted as this attempt's evidence."
    )
    add("")

    add("## Hosting feasibility (read-only)")
    add("")
    add(
        "- No container, registry, cluster, or cloud resource was created; Docker/WSL status is in "
        "`docs/evidence/W01/ENVIRONMENT.json`."
    )
    add(
        "- Proposed route for Codex to freeze: Python 3.11 Linux container with pinned wheels, Docling "
        "models baked at image build, provider keys injected as runtime secrets. Account/region "
        "verification remains a Codex/human decision."
    )
    add("")

    add("## Unresolved decisions for Codex")
    add("")
    add("1. Live provider evidence: `NEBIUS_API_KEY` is required in the worker process. Published "
        "pricing is now recorded in the protected pricing evidence; account/model access is still "
        "unverified until a real call, and HTTP 401 alone proves neither the model nor full endpoint behavior.")
    add("2. Whether selected-section evidence (2.2.18, 2.2.5) is sufficient for P0's parser/source exit gate.")
    add("3. Anchor identity for W02: document hash + parser version + extraction configuration; "
        "anchor IDs are page-scoped ordinals and are not stable across parser upgrades.")
    add("4. Redistribution rights for ES0620 remain unknown; the public bundle keeps metadata and short quotations only.")
    add("")

    add("## Reproduction")
    add("")
    add("```powershell")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py verify-baseline")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py inspect-env")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py fetch-source")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py parse-source")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py self-test")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py probe-provider --case real-source")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py probe-provider --case synthetic-missing-revision")
    add(f"{python_info.get('executable', '.local/w01/venv/Scripts/python.exe')} spikes/w01/run.py report")
    add("```")
    add("")
    add("`probe-provider` requires `NEBIUS_API_KEY` and validated pricing evidence; without them it "
        "records a blocked preflight and exits 2 without dispatching.")
    add("")

    write_text(config.REPORT_PATH, "\n".join(lines) + "\n")
    summary = {
        "report_path": rel(config.REPORT_PATH),
        "gates": [{"gate": gate["gate"], "status": gate["status"], "reason": gate["reason"]} for gate in gates],
    }
    write_json(config.RESULT_DIR / "report_summary.json", summary)
    return summary

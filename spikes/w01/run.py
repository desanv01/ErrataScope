"""W01 feasibility spike command-line entry point.

Subcommands: inspect-env, fetch-source, parse-source, probe-provider,
self-test, report, verify-baseline. See spikes/w01/README.md.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
if str(SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(SPIKE_DIR))

# Keep model/temporary artifacts inside the project (the sandbox denies the
# platform temp root) and avoid 0700 temp dirs that this sandbox cannot access.
os.environ.setdefault("HF_HOME", str(SPIKE_DIR.parent.parent / ".local" / "w01" / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ["TEMP"] = str(SPIKE_DIR.parent.parent / ".local" / "w01" / "tmp")
os.environ["TMP"] = os.environ["TEMP"]

from erratascope_w01 import config
from erratascope_w01.util import read_json, utc_now_iso, write_json

CASE_NAMES = {
    "real-source": "real_source",
    "synthetic-missing-revision": "synthetic_missing_revision",
}


def _log_command(command: str, argv: list[str], started: str, exit_code: int, notes: str = "") -> None:
    path = config.RESULT_DIR / "command_log.json"
    try:
        log = read_json(path) if path.exists() else []
    except Exception:
        log = []
    log.append(
        {
            "command": command,
            "argv": argv,
            "attempt": config.WORKER_ATTEMPT,
            "started_utc": started,
            "finished_utc": utc_now_iso(),
            "exit_code": exit_code,
            "notes": notes,
        }
    )
    write_json(path, log)


def cmd_inspect_env(_args: argparse.Namespace) -> int:
    from erratascope_w01.envprobe import inspect_environment

    environment = inspect_environment()
    python_info = environment["python"]
    print(f"python           {python_info['version']} ({python_info['implementation']})")
    print(f"executable       {python_info['executable']}")
    print(f"venv             {python_info['in_virtualenv']}")
    for name, info in environment["packages"].items():
        print(f"package          {name:<12} {info['version'] or 'not installed'}")
    print(f"docker client    {environment['capabilities']['docker_client']}")
    print(f"wsl              {environment['capabilities']['wsl']}")
    for name, info in environment["configured_secret_variables"].items():
        print(f"secret variable  {name}: {'configured' if info['configured'] else 'not configured'}")
    print(f"environment file {config.ENVIRONMENT_PATH.relative_to(config.PROJECT_ROOT)}")
    return 0


def cmd_fetch_source(_args: argparse.Namespace) -> int:
    from erratascope_w01.fetch import fetch_sources

    payload = fetch_sources()
    for source in payload["sources"]:
        if source.get("kind") == "synthetic_fixture":
            continue
        print(
            f"{source['source_key']:<32} http={source.get('http_status')} "
            f"bytes={source.get('byte_size')} sha256={source.get('sha256')}"
        )
    st = next(
        (source for source in payload["sources"] if source["source_key"] == config.ST_ERRATA["source_key"]),
        None,
    )
    if st:
        print(f"document         {st.get('document_id')} {st.get('revision')} {st.get('publication_date')}")
        print(f"pages            {st.get('page_count')}")
    synthetic = [s for s in payload["sources"] if s.get("kind") == "synthetic_fixture"]
    print(f"synthetic        {len(synthetic)} fixture(s) registered and labeled")
    print(f"manifest         {config.MANIFEST_PATH.relative_to(config.PROJECT_ROOT)}")
    if payload["failures"]:
        for failure in payload["failures"]:
            print(f"MANDATORY FAILURE {failure}", file=sys.stderr)
        return 1
    return 0


def cmd_parse_source(_args: argparse.Namespace) -> int:
    from erratascope_w01.anchors import ParseError, parse_source, render_selected_pages

    try:
        parsed = parse_source()
    except ParseError as exc:
        print(f"PARSE FAILED: {exc}", file=sys.stderr)
        return 1
    renders = render_selected_pages(parsed)
    document = parsed["document"]
    coverage = parsed["coverage"]
    print(f"anchors          {len(document.anchors)}")
    context = [anchor for anchor in document.anchors if anchor.context_kind]
    print(
        "context anchors  "
        + ", ".join(sorted({anchor.context_kind for anchor in context}))  # type: ignore[arg-type]
    )
    print(f"pages parsed     {sorted({anchor.page_index for anchor in document.anchors})}")
    for entry in coverage.entries:
        print(f"section {entry.section:<8} status={entry.status:<9} anchors={len(entry.anchor_ids)}")
    for row_section, row in parsed["rows"].items():
        statuses = row["status_by_revision"]
        print(f"revision matrix  {row_section}: " + ", ".join(f"Rev. {k}={v}" for k, v in statuses.items()))
    print(f"anchors file     {(config.RESULT_DIR / 'anchors.json').relative_to(config.PROJECT_ROOT)}")
    print(f"coverage file    {(config.RESULT_DIR / 'coverage.json').relative_to(config.PROJECT_ROOT)}")
    print(f"renders          {len(renders)} page(s) in {config.PAGE_DIR.relative_to(config.PROJECT_ROOT)}")
    if any(entry.status != "anchored" for entry in coverage.entries):
        print("one or more selected sections are not anchored", file=sys.stderr)
        return 1
    return 0


def _load_real_source_case():
    from erratascope_w01.cases import (
        build_real_source_payload,
        expected_identity_for,
        source_identity_from_manifest,
    )
    from erratascope_w01.schemas import AnchorDocument, SourceManifest

    manifest = SourceManifest(**read_json(config.MANIFEST_PATH))
    anchors_document = AnchorDocument(**read_json(config.RESULT_DIR / "anchors.json"))
    matrix = read_json(config.RESULT_DIR / "revision_matrix.json").get("rows", {})
    identity = source_identity_from_manifest(manifest.model_dump(mode="json"))
    payload = build_real_source_payload(anchors_document, {}, matrix, identity)
    expected = expected_identity_for("real_source", identity, None)
    return {
        "payload": payload,
        "anchors": anchors_document.anchors,
        "document_sha256": anchors_document.document_sha256,
        "expected_identity": expected,
        "identity": identity,
        "case": "real_source",
    }


def _load_synthetic_case():
    from erratascope_w01.cases import (
        build_synthetic_anchors,
        build_synthetic_payload,
        expected_identity_for,
    )

    document, anchors = build_synthetic_anchors()
    payload = build_synthetic_payload([anchor.model_dump(mode="json") for anchor in anchors])
    expected = expected_identity_for("synthetic_missing_revision", None, document["document_sha256"])
    return {
        "payload": payload,
        "anchors": anchors,
        "document_sha256": document["document_sha256"],
        "expected_identity": expected,
        "identity": None,
        "case": "synthetic_missing_revision",
    }


def cmd_probe_provider(args: argparse.Namespace) -> int:
    from erratascope_w01.cases import CaseError
    from erratascope_w01.ledger import (
        BudgetExhausted,
        LedgerError,
        PricingError,
        load_pricing,
    )
    from erratascope_w01.provider import record_blocked, run_case

    case_name = CASE_NAMES[args.case]
    key_name = config.PROVIDER["api_key_env"]
    api_key = os.environ.get(key_name)

    try:
        pricing = load_pricing(Path(args.pricing_file) if args.pricing_file else None)
    except PricingError as exc:
        record_blocked(f"pricing configuration rejected: {exc}", case=case_name)
        print(f"PRICING CONFIGURATION REJECTED: {exc}", file=sys.stderr)
        print("No request was made.", file=sys.stderr)
        return 2

    # Persist the validated pricing metadata even when preflight is blocked, so
    # the ledger records which configuration was checked (never a counter edit).
    from erratascope_w01.ledger import Ledger

    ledger = Ledger()
    if ledger.state.pricing != pricing:
        ledger.state.pricing = pricing
        ledger.save()

    if not api_key:
        reason = (
            f"{key_name} is not configured for this process. Live provider case "
            f"'{case_name}' blocked; no request was made and no fixture output is reported as live."
        )
        record_blocked(reason, case=case_name)
        print(f"PROVIDER CASE BLOCKED: {reason}", file=sys.stderr)
        return 2

    try:
        case = _load_real_source_case() if case_name == "real_source" else _load_synthetic_case()
    except CaseError as exc:
        print(f"CASE INPUT INVALID: {exc}", file=sys.stderr)
        return 1

    print(f"case             {case_name}")
    print(f"model            {pricing['model_id']}")
    print(f"pricing source   {pricing['source_url']} (verified {pricing['verified_date']})")
    print(f"pricing rates    input ${pricing['input_usd_per_1m']}/1M, output ${pricing['output_usd_per_1m']}/1M")

    try:
        record = run_case(
            case=case["case"],
            payload=case["payload"],
            anchors=case["anchors"],
            expected_identity=case["expected_identity"],
            expected_document_sha256=case["document_sha256"],
            pricing=pricing,
            api_key=api_key,
            ledger=ledger,
        )
    except BudgetExhausted as exc:
        record_blocked(f"budget guard refused dispatch: {exc}", ledger=ledger, case=case_name)
        print(f"BUDGET GUARD: {exc}", file=sys.stderr)
        return 2
    except LedgerError as exc:
        print(f"LEDGER ERROR: {exc}", file=sys.stderr)
        return 1

    # CLI and report share exactly one verification path.
    from erratascope_w01.evidence import evaluate_case

    verdict = evaluate_case(
        record=record,
        case=case["case"],
        ledger=ledger.state.model_dump(mode="json"),
        anchors=case["anchors"],
        expected_document_sha256=case["document_sha256"],
        expected_identity=case["expected_identity"],
    )

    print(f"attempt          {record.get('attempt')} ({record.get('state')}/{record.get('outcome')})")
    print(f"http status      {record.get('http_status')}")
    print(f"model returned   {record.get('model_returned')}")
    print(f"request id       {record.get('request_id')}")
    print(f"latency ms       {record.get('latency_ms')}")
    print(f"usage            {record.get('usage')}")
    print(f"validation       {(record.get('validation') or {}).get('status')}")
    print(f"case expectation {(record.get('case_expectation') or {}).get('status', 'n/a')}")
    print(f"evidence gate    {verdict.status}")
    for reason in verdict.reasons:
        print(f"  - {reason}")
    return 0 if verdict.status == "PASS" else 1


def cmd_verify_baseline(args: argparse.Namespace) -> int:
    """Run the protected verifier and persist its actual result for the report."""
    baseline = Path(args.baseline).resolve()
    script = config.PROJECT_ROOT / "scripts" / "verify_execution_framework.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--baseline", str(baseline)],
        capture_output=True,
        check=False,
        text=True,
        cwd=str(config.PROJECT_ROOT),
    )
    parsed = None
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = None
    record = {
        "baseline_file": baseline.name,
        "command": f"verify_execution_framework.py --baseline {baseline.name}",
        "exit_code": completed.returncode,
        "recorded_utc": utc_now_iso(),
        "result": parsed,
        "stdout_tail": (completed.stdout or "")[-2000:],
        "stderr_tail": (completed.stderr or "")[-2000:],
    }
    write_json(config.RESULT_DIR / "baseline_check.json", record)
    print(completed.stdout.strip())
    if parsed is None:
        print(completed.stderr.strip(), file=sys.stderr)
    print(f"baseline record  {(config.RESULT_DIR / 'baseline_check.json').relative_to(config.PROJECT_ROOT)}")
    return completed.returncode


def cmd_self_test(_args: argparse.Namespace) -> int:
    from erratascope_w01.selftest import run_self_test

    summary = run_self_test()
    for result in summary["results"]:
        print(f"{result['status']:<5} {result['id']:<50} {result['detail']}")
    print(
        f"TOTAL {summary['checks_total']} passed={summary['checks_passed']} "
        f"failed={summary['checks_failed']} skipped={summary['checks_skipped']}"
    )
    print(f"results {config.RESULT_DIR / 'selftest.json'}")
    return 0 if summary["checks_failed"] == 0 else 1


def cmd_report(_args: argparse.Namespace) -> int:
    from erratascope_w01.report import build_report

    result = build_report()
    for gate in result["gates"]:
        print(f"{gate['gate']:<8} {gate['status']:<10} {gate.get('reason', '')}")
    print(f"report {result['report_path']}")
    return 0


def cmd_check_key(_args: argparse.Namespace) -> int:
    configured = bool(os.environ.get("NEBIUS_API_KEY", "").strip())
    print("NEBIUS_API_KEY: CONFIGURED" if configured else "NEBIUS_API_KEY: MISSING")
    return 0 if configured else 2


COMMANDS = {
    "check-key": cmd_check_key,
    "inspect-env": cmd_inspect_env,
    "fetch-source": cmd_fetch_source,
    "parse-source": cmd_parse_source,
    "probe-provider": cmd_probe_provider,
    "self-test": cmd_self_test,
    "report": cmd_report,
    "verify-baseline": cmd_verify_baseline,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="ErrataScope W01 feasibility spike (narrow source/parser/provider proof).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, function in COMMANDS.items():
        subparser = subparsers.add_parser(name)
        subparser.set_defaults(handler=function)
        if name == "probe-provider":
            subparser.add_argument(
                "--case",
                required=True,
                choices=sorted(CASE_NAMES),
                help="Explicit case; one case per invocation, never both.",
            )
            subparser.add_argument(
                "--pricing-file",
                default=None,
                help="Validated pricing evidence JSON (default: Codex W01 pricing evidence).",
            )
        if name == "verify-baseline":
            subparser.add_argument(
                "--baseline",
                default=str(config.REPAIR_BASELINE_PATH.relative_to(config.PROJECT_ROOT)),
                help="Protected baseline manifest to verify.",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {"check-key", "probe-provider", "inspect-env", "self-test"}:
        from erratascope_w01.localenv import LocalEnvError, load_nebius_key
        try:
            load_nebius_key()
        except LocalEnvError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "check-key":
        # Presence only: no request, ledger entry, or command log containing secrets.
        return args.handler(args)
    started = utc_now_iso()
    exit_code = 1
    try:
        exit_code = int(args.handler(args))
    except Exception:  # noqa: BLE001 - surface failures with a nonzero exit
        traceback.print_exc()
        exit_code = 1
    finally:
        _log_command(args.command, list(argv or sys.argv[1:]), started, exit_code)
    print(f"exit_code={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

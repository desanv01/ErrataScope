"""W04 CLI: key presence, connected ingestion verification, evidence checks, OpenAPI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..config import load_settings
from .fixture import SYNTHETIC_TEXT
from .provider import key_presence

API_PREFIX = "/api/v1"


def _token() -> str:
    dev = Path(os.environ.get("W03_DEV_AUTH_DIR", "/local/dev-auth"))
    data = json.loads((dev / "tokens.json").read_text(encoding="utf-8"))
    return data["users"]["user-a"]["token"]


def _client() -> httpx.Client:
    settings = load_settings()
    return httpx.Client(
        base_url=settings.api_base_url,
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=30.0,
        follow_redirects=False,
    )


def _write(path: str, payload: dict) -> int:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload.get("status"), "output": str(output)}))
    return 0 if payload.get("status") == "pass" else 2


def _create_project(client: httpx.Client, name: str) -> str:
    response = client.post(
        f"{API_PREFIX}/projects",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json={"name": name},
    )
    response.raise_for_status()
    return response.json()["id"]


def _upload(client: httpx.Client, project_id: str, data: bytes, media_type: str, name: str) -> dict:
    response = client.post(
        f"{API_PREFIX}/projects/{project_id}/artifacts",
        headers={
            "Idempotency-Key": uuid.uuid4().hex,
            "Content-Type": media_type,
            "X-Filename": name,
        },
        content=data,
    )
    response.raise_for_status()
    return response.json()


def _create_source(client: httpx.Client, project_id: str, payload: dict) -> dict:
    response = client.post(
        f"{API_PREFIX}/projects/{project_id}/sources",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def _create_extraction(
    client: httpx.Client, project_id: str, source_id: str, payload: dict
) -> dict:
    response = client.post(
        f"{API_PREFIX}/projects/{project_id}/sources/{source_id}/extractions",
        headers={"Idempotency-Key": uuid.uuid4().hex},
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def _wait_job(client: httpx.Client, project_id: str, job_id: str, timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        response = client.get(f"{API_PREFIX}/projects/{project_id}/jobs/{job_id}")
        if response.status_code != 200:
            raise RuntimeError(f"job read failed: {response.status_code}")
        last = response.json()
        if last["status"] in ("succeeded", "failed", "cancelled"):
            return last
        time.sleep(1.0)
    raise TimeoutError(f"job did not finish: {last}")


def verify_ingestion(mode: str, case: str, output: str) -> int:
    settings = load_settings()
    if mode == "live" and not settings.w04_live_enabled:
        payload = {
            "status": "blocked",
            "code": "LIVE_DISABLED",
            "mode": mode,
            "case": case,
            "message": "W04 live mode is not enabled in this runtime",
        }
        return _write(output, payload)
    if case not in ("real_source", "synthetic_missing_revision"):
        raise SystemExit("invalid case")
    with _client() as client:
        project_id = _create_project(client, f"w04-{mode}-{case}-{uuid.uuid4().hex[:8]}")
        if case == "real_source":
            pdf_path = Path("/w04/st-es0620.pdf")
            data = pdf_path.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            if sha != "dcabef6a6f7554b8ae83b9718b3924d1f76003448de3ba94b5f0a195da70d3fd":
                raise SystemExit("pinned source hash mismatch")
            artifact = _upload(client, project_id, data, "application/pdf", "st-es0620.pdf")
            source = _create_source(
                client,
                project_id,
                {
                    "artifact_id": artifact["id"],
                    "document_id": "ES0620",
                    "revision": "Rev 5",
                    "manufacturer": "STMicroelectronics",
                    "authority": "manufacturer",
                    "synthetic": False,
                    "source_url": "https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf",
                },
            )
            selected = ["2.2.18", "2.2.5"]
        else:
            data = SYNTHETIC_TEXT.encode("utf-8")
            artifact = _upload(client, project_id, data, "text/plain", "synthetic-missing-revision.txt")
            source = _create_source(
                client,
                project_id,
                {
                    "artifact_id": artifact["id"],
                    "document_id": None,
                    "revision": None,
                    "manufacturer": None,
                    "authority": "synthetic",
                    "synthetic": True,
                },
            )
            selected = ["2.9.99"]
        extraction = _create_extraction(
            client,
            project_id,
            source["id"],
            {"selected_entries": selected, "mode": mode, "case_kind": case},
        )
        try:
            job = _wait_job(client, project_id, extraction["job_id"], 30 if mode == "offline" else 300)
        except TimeoutError as exc:
            return _write(
                output,
                {"status": "partial", "code": "JOB_TIMEOUT", "message": str(exc), "mode": mode, "case": case},
            )
        detail = client.get(f"{API_PREFIX}/extractions/{extraction['id']}").json()
        anchors = client.get(f"{API_PREFIX}/extractions/{extraction['id']}/anchors").json()["items"]
        coverage = client.get(f"{API_PREFIX}/extractions/{extraction['id']}/coverage").json()["items"]
        drafts = client.get(f"{API_PREFIX}/extractions/{extraction['id']}/drafts").json()["items"]
        draft = drafts[0] if drafts else None
        checks = {
            "job_succeeded": job["status"] == "succeeded",
            "extraction_succeeded": detail["status"] == "succeeded",
            "anchors_present": len(anchors) >= 1,
            "coverage_present": len(coverage) >= 1,
            "selected_supported": all(
                entry["status"] == "supported" for entry in coverage if entry["section"] in selected
            ),
            "draft_present": draft is not None,
            "draft_validated": bool(draft and draft["status"] == "validated"),
            "identity_rule": (
                draft is not None
                and (
                    (draft["draft"].get("source_document_id") is None and draft["draft"].get("source_revision") is None)
                    if case == "synthetic_missing_revision"
                    else (draft["draft"].get("source_document_id") is not None)
                )
            ),
            "provenance_expected": bool(
                draft
                and (
                    (mode == "live" and draft["provenance"] in ("live", "cached"))
                    or (mode == "offline" and draft["provenance"] == "mock")
                )
            ),
        }
        payload = {
            "schema_version": 1,
            "status": "pass" if all(checks.values()) else "fail",
            "mode": mode,
            "case": case,
            "project_id": project_id,
            "source_id": source["id"],
            "source_sha256": source["sha256"],
            "extraction_id": extraction["id"],
            "job_id": extraction["job_id"],
            "job_status": job["status"],
            "anchors": len(anchors),
            "coverage": len(coverage),
            "coverage_summary": detail.get("coverage_summary"),
            "draft": (
                {
                    "id": draft["id"],
                    "status": draft["status"],
                    "provenance": draft["provenance"],
                    "validation": draft["validation"],
                    "provider_request_id": draft["provider_request_id"],
                    "usage": draft["usage"],
                    "draft": draft["draft"],
                }
                if draft
                else None
            ),
            "checks": checks,
            "checked_utc": datetime.now(timezone.utc).isoformat(),
        }
        return _write(output, payload)


def verify_evidence(path: str) -> int:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = []
    gates = manifest.get("gates")
    if not isinstance(gates, dict) or not gates:
        errors.append("manifest has no gates")
    if manifest.get("status") not in ("pass", "partial", "blocked"):
        errors.append("manifest status is not pass/partial/blocked")
    for item in manifest.get("files", []):
        try:
            actual = hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()
        except OSError:
            errors.append(f"missing file {item['path']}")
            continue
        if actual != item.get("sha256"):
            errors.append(f"hash mismatch {item['path']}")
    payload = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "gates": gates,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 2


def export_openapi(output: str) -> int:
    from ..api import create_app

    app = create_app()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store = getattr(app.state, "store", None)
    if store is not None:
        store.close()
    print(f"wrote {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m erratascope_service.ingestion.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-key")
    verify = sub.add_parser("verify-ingestion")
    verify.add_argument("--mode", choices=["offline", "live"], required=True)
    verify.add_argument("--case", choices=["real_source", "synthetic_missing_revision"], required=True)
    verify.add_argument("--output", required=True)
    evidence = sub.add_parser("verify-evidence")
    evidence.add_argument("--manifest", required=True)
    openapi = sub.add_parser("export-openapi")
    openapi.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "check-key":
        settings = load_settings()
        presence = key_presence(settings)
        print(presence)
        return 0 if presence == "CONFIGURED" else 2
    if args.command == "verify-ingestion":
        return verify_ingestion(args.mode, args.case, args.output)
    if args.command == "verify-evidence":
        return verify_evidence(args.manifest)
    if args.command == "export-openapi":
        return export_openapi(args.output)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


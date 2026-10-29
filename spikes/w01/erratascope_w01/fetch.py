"""Source retrieval with byte hashing, provenance, and public-safe manifests."""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pymupdf

from . import config
from .util import redact_url, rel, sha256_bytes, utc_now_iso, write_json

REVISION_RE = re.compile(r"(ES\d{4})\s*-\s*(Rev\s*\d+)\s*-\s*([A-Z][a-z]+\s+\d{4})")


def _get(url: str) -> tuple[httpx.Response | None, str | None]:
    headers = {"User-Agent": config.USER_AGENT, "Accept": "*/*"}
    try:
        with httpx.Client(
            timeout=config.HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=headers,
        ) as client:
            return client.get(url), None
    except Exception as exc:  # network failure is data for the manifest
        return None, f"{type(exc).__name__}: {exc}"


def _pdf_page_count(path: Path) -> int | None:
    try:
        with pymupdf.open(path) as document:
            return document.page_count
    except Exception:
        return None


def _pdf_metadata(path: Path) -> dict:
    try:
        with pymupdf.open(path) as document:
            raw = document.metadata or {}
            return {k: v for k, v in raw.items() if v}
    except Exception:
        return {}


def _document_identity(first_page_text: str) -> dict:
    match = REVISION_RE.search(first_page_text)
    if not match:
        return {"document_id": None, "revision": None, "publication_date": None}
    return {
        "document_id": match.group(1),
        "revision": match.group(2).replace("  ", " ").strip(),
        "publication_date": match.group(3).strip(),
    }


def synthetic_fixture_records() -> list[dict]:
    """Register the original synthetic fixtures with hashes and labels.

    These are authored fixtures, not manufacturer material. Every record is
    marked synthetic and every file starts with a SYNTHETIC banner.
    """
    records: list[dict] = []
    fixture_dir = config.FIXTURE_DIR / "synthetic"
    if not fixture_dir.exists():
        return records
    for path in sorted(fixture_dir.glob("*.md")):
        data = path.read_bytes()
        first_lines = data.decode("utf-8", errors="replace").splitlines()[:3]
        has_banner = any("SYNTHETIC" in line.upper() for line in first_lines)
        records.append(
            {
                "schema_version": config.MANIFEST_SCHEMA_VERSION,
                "source_key": f"synthetic-{path.stem.lower().replace('synthetic_', '')}",
                "kind": "synthetic_fixture",
                "title": first_lines[0].strip() if first_lines else path.stem,
                "manufacturer": None,
                "document_id": path.stem,
                "authority": "Synthetic fixture authored for W01 testing; no manufacturer authority",
                "redistribution": "permitted",
                "redistribution_reference": "Authored for ErrataScope W01; contains no manufacturer content",
                "retrieval_utc": None,
                "request_url": None,
                "final_url": None,
                "http_status": None,
                "content_type": "text/markdown",
                "byte_size": len(data),
                "sha256": sha256_bytes(data),
                "page_count": None,
                "artifact_path": rel(path),
                "synthetic": True,
                "notes": [
                    "Every object in this file is SYNTHETIC; it does not describe a real product.",
                    "Fixture availability only; it does not prove the change engine.",
                ]
                + ([] if has_banner else ["WARNING: SYNTHETIC banner missing from file head."]),
            }
        )
    return records


def fetch_sources(write_public_manifest: bool = True) -> dict:
    """Attempt every registered source once and return a provenance payload."""
    config.SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    attempts: list[dict] = []
    failures: list[str] = []

    for spec in config.SOURCE_SPECS:
        retrieved_utc = utc_now_iso()
        response, error = _get(spec["url"])
        attempt = {
            "source_key": spec["source_key"],
            "request_url": redact_url(spec["url"]),
            "retrieval_utc": retrieved_utc,
            "http_status": None if response is None else response.status_code,
            "error": error,
            "type": "retrieval",
        }
        attempts.append(attempt)

        record = {
            "schema_version": config.MANIFEST_SCHEMA_VERSION,
            "source_key": spec["source_key"],
            "kind": spec["kind"],
            "title": spec["document_id"],
            "manufacturer": spec["manufacturer"],
            "document_id": spec["document_id"],
            "authority": spec["authority"],
            "redistribution": "unknown",
            "redistribution_reference": (
                "docs/execution/contracts/provider-and-sources.md: public document URLs "
                "do not authorize redistributing full documents"
            ),
            "retrieval_utc": retrieved_utc,
            "request_url": redact_url(spec["url"]),
            "synthetic": False,
            "notes": [],
        }

        if response is None or response.status_code != 200:
            status = "no response" if response is None else f"HTTP {response.status_code}"
            record["notes"].append(f"Retrieval failed: {status} ({error or 'no error detail'})")
            if spec["mandatory"]:
                failures.append(f"{spec['source_key']}: {status}")
            records.append(record)
            continue

        data = response.content
        target = config.SOURCE_DIR / spec["local_filename"]
        target.write_bytes(data)
        digest = sha256_bytes(data)
        record.update(
            {
                "final_url": redact_url(str(response.url)),
                "http_status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "byte_size": len(data),
                "sha256": digest,
                "artifact_path": rel(target),
            }
        )

        if spec["source_key"] == config.ST_ERRATA["source_key"]:
            pages = _pdf_page_count(target)
            record["page_count"] = pages
            metadata = _pdf_metadata(target)
            with pymupdf.open(target) as document:
                first_page = document[0].get_text()
            identity = _document_identity(first_page)
            record["document_id"] = identity["document_id"] or spec["document_id"]
            record["revision"] = identity["revision"]
            record["publication_date"] = identity["publication_date"]
            record["title"] = (
                metadata.get("title") or "STM32N6xxxx device errata - Errata sheet"
            )
            if pages is None:
                failures.append("st-es0620: downloaded bytes are not a readable PDF")
            if identity["revision"] is None:
                record["notes"].append(
                    "Revision string not found on page 1; revision remains unknown."
                )
        else:
            record["notes"].append(
                "Non-PDF metadata page retrieved for provenance only; not parsed for errata content."
            )

        records.append(record)

    records.extend(synthetic_fixture_records())

    payload = {
        "generated_utc": utc_now_iso(),
        "sources": records,
        "retrieval_attempts": attempts,
        "selection": {
            "selected_sections": list(config.SELECTED_SECTIONS),
            "selected_source_key": config.ST_ERRATA["source_key"],
            "scope_note": (
                "Selected-section coverage only. The full document was inventoried for "
                "headings but not interpreted."
            ),
            "inventory_complete": None,
        },
        "failures": failures,
    }

    if write_public_manifest:
        from .schemas import SourceManifest

        manifest = SourceManifest(
            schema_version=config.MANIFEST_SCHEMA_VERSION,
            generated_utc=payload["generated_utc"],
            sources=payload["sources"],
            retrieval_attempts=payload["retrieval_attempts"],
            selection=payload["selection"],
        )
        config.MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        write_json(config.MANIFEST_PATH, manifest.model_dump(mode="json"))

    write_json(config.RESULT_DIR / "fetch.json", payload)
    return payload

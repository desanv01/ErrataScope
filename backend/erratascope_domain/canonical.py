"""Canonical JSON, content sealing and deterministic hashing.

Rules: UTF-8, sorted object keys, no whitespace separators, ensure_ascii=False,
allow_nan=False, model defaults/null fields materialized. Unordered collections
are sorted by stable keys before hashing; AST child order and other semantic
sequences are preserved. UUIDs are lowercase strings via Pydantic JSON mode.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from pydantic import BaseModel

CONTENT_HASH_FIELD = "content_hash"
RESULT_HASH_FIELD = "result_hash"


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def dump_model(model: BaseModel) -> dict:
    return model.model_dump(mode="json", exclude_none=False)


def _sorted(items: list, key) -> list:
    return sorted(items, key=key)


def normalize_snapshot_dump(dump: dict) -> dict:
    data = copy.deepcopy(dump)
    data["component_instances"] = _sorted(
        data.get("component_instances", []), key=lambda item: item["id"]
    )
    return data


def normalize_fact_set_dump(dump: dict) -> dict:
    data = copy.deepcopy(dump)
    data["fact_versions"] = _sorted(data.get("fact_versions", []), key=lambda item: item["id"])
    return data


def _entry_key(item: dict) -> tuple[str, str]:
    return (item["document_version_id"], item["entry_id"])


def _normalize_entry_list(values) -> list:
    return _sorted(list(values or []), key=_entry_key)


def normalize_coverage_dump(dump: dict) -> dict:
    data = copy.deepcopy(dump)
    for field in (
        "discovered",
        "supported",
        "reviewed",
        "assessed",
        "failed",
        "unsupported",
        "selected",
    ):
        data[field] = _normalize_entry_list(data.get(field, []))
    data["document_version_ids"] = sorted(data.get("document_version_ids", []))
    return data


def normalize_bundle_dump(dump: dict) -> dict:
    data = copy.deepcopy(dump)
    data["snapshot"] = normalize_snapshot_dump(data["snapshot"])
    data["fact_set"] = normalize_fact_set_dump(data["fact_set"])
    data["documents"] = _sorted(data.get("documents", []), key=lambda item: item["id"])
    data["anchors"] = _sorted(data.get("anchors", []), key=lambda item: item["anchor_id"])
    data["rules"] = _sorted(
        data.get("rules", []),
        key=lambda item: (item["document_version_id"], item["entry_id"], item["id"]),
    )
    data["coverage"] = normalize_coverage_dump(data["coverage"])
    baseline = copy.deepcopy(data["source_baseline"])
    baseline["document_version_ids"] = sorted(baseline.get("document_version_ids", []))
    baseline["rule_version_ids"] = sorted(baseline.get("rule_version_ids", []))
    data["source_baseline"] = baseline
    return data


def normalize_result_dump(dump: dict) -> dict:
    data = copy.deepcopy(dump)
    data["rules"] = _sorted(
        data.get("rules", []),
        key=lambda item: (
            item["document_version_id"],
            item["entry_id"],
            item["rule_version_id"],
        ),
    )
    data["selector_dependencies"] = _sorted(
        data.get("selector_dependencies", []),
        key=lambda item: (
            item["scope"]["project_id"],
            item["scope"]["snapshot_id"],
            item["scope"]["subject_id"],
            item["scope"]["firmware_build_id"],
            item["scope"]["operating_profile_id"],
            item["selector"],
        ),
    )
    data["missing_selectors"] = sorted(set(data.get("missing_selectors", [])))
    data["rule_version_ids"] = sorted(data.get("rule_version_ids", []))
    data["contradictions"] = _sorted(
        data.get("contradictions", []),
        key=lambda item: (item["selector"], tuple(item.get("fact_ids", []))),
    )
    data["warnings"] = _sorted(
        data.get("warnings", []),
        key=lambda item: (
            item["code"],
            item.get("selector") or "",
            item.get("rule_version_id") or "",
            tuple(item.get("fact_ids", [])),
        ),
    )
    summary = copy.deepcopy(data["coverage_summary"])
    summary["selected_entries"] = _normalize_entry_list(summary.get("selected_entries", []))
    summary["unsupported_entries"] = _normalize_entry_list(summary.get("unsupported_entries", []))
    data["coverage_summary"] = summary
    return data


def snapshot_content_hash(dump: dict) -> str:
    payload = normalize_snapshot_dump(dump)
    payload.pop(CONTENT_HASH_FIELD, None)
    return sha256_hex(payload)


def fact_set_content_hash(dump: dict) -> str:
    payload = normalize_fact_set_dump(dump)
    payload.pop(CONTENT_HASH_FIELD, None)
    return sha256_hex(payload)


def seal_snapshot(snapshot: BaseModel) -> BaseModel:
    dump = dump_model(snapshot)
    digest = snapshot_content_hash(dump)
    return snapshot.model_copy(update={CONTENT_HASH_FIELD: digest})


def seal_fact_set(fact_set: BaseModel) -> BaseModel:
    dump = dump_model(fact_set)
    digest = fact_set_content_hash(dump)
    return fact_set.model_copy(update={CONTENT_HASH_FIELD: digest})


def bundle_input_hash(bundle: BaseModel) -> str:
    return sha256_hex(normalize_bundle_dump(dump_model(bundle)))


def result_hash(result_dump: dict) -> str:
    payload = normalize_result_dump(copy.deepcopy(result_dump))
    payload.pop(RESULT_HASH_FIELD, None)
    return sha256_hex(payload)


def normalized_result_bytes(result_dump: dict) -> bytes:
    normalized = normalize_result_dump(copy.deepcopy(result_dump))
    return canonical_bytes(normalized) + b"\n"

"""Adapter between persistence/API and the accepted pure domain package."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from erratascope_domain import canonical, evaluate, parse_bundle
from erratascope_domain.errors import Diagnostic, DomainValidationError
from erratascope_domain.models import AssessmentInputBundle

ALLOWED_KINDS = (
    "snapshot",
    "component_instance",
    "fact_set",
    "fact_version",
    "document_version",
    "anchor",
    "rule",
    "coverage",
    "source_baseline",
)


def canonical_bundle(raw: dict[str, Any]) -> tuple[AssessmentInputBundle, dict[str, Any], str]:
    """Validate a W02 bundle and produce normalized storage payload + input hash."""
    if not isinstance(raw, dict):
        raise DomainValidationError(
            [Diagnostic("SCHEMA_INVALID", "<root>", "bundle must be a JSON object")]
        )
    bundle = parse_bundle(raw)
    payload = canonical.normalize_bundle_dump(canonical.dump_model(bundle))
    input_hash = canonical.bundle_input_hash(bundle)
    return bundle, payload, input_hash


def payload_bytes(payload: dict[str, Any]) -> bytes:
    return canonical.canonical_bytes(payload)


def load_bundle(payload: dict[str, Any], expected_input_hash: str) -> AssessmentInputBundle:
    """Reconstruct and revalidate a persisted bundle; verify the normalized hash."""
    bundle = parse_bundle(payload)
    if canonical.bundle_input_hash(bundle) != expected_input_hash:
        raise DomainValidationError(
            [
                {
                    "code": "HASH_MISMATCH",
                    "path": "input_hash",
                    "message": "persisted bundle does not reproduce its input hash",
                }
            ]
        )
    return bundle


def evaluate_bundle(bundle: AssessmentInputBundle):
    return evaluate(bundle)


def _normalized_payload(kind: str, model) -> dict[str, Any]:
    if kind == "snapshot":
        return canonical.normalize_snapshot_dump(canonical.dump_model(model))
    if kind == "fact_set":
        return canonical.normalize_fact_set_dump(canonical.dump_model(model))
    if kind == "coverage":
        return canonical.normalize_coverage_dump(canonical.dump_model(model))
    return canonical.dump_model(model)


def _version_id(value: Any) -> str:
    return str(value)


def extract_versions(bundle: AssessmentInputBundle) -> list[dict[str, Any]]:
    """Flatten every persisted domain entity into an immutable version record."""
    entries: list[tuple[str, str, Any]] = []
    entries.append(("snapshot", _version_id(bundle.snapshot.id), bundle.snapshot))
    for instance in bundle.snapshot.component_instances:
        entries.append(("component_instance", _version_id(instance.id), instance))
    entries.append(("fact_set", _version_id(bundle.fact_set.id), bundle.fact_set))
    for fact in bundle.fact_set.fact_versions:
        entries.append(("fact_version", _version_id(fact.id), fact))
    for document in bundle.documents:
        entries.append(("document_version", _version_id(document.id), document))
    for anchor in bundle.anchors:
        entries.append(("anchor", anchor.anchor_id, anchor))
    for rule in bundle.rules:
        entries.append(("rule", _version_id(rule.id), rule))
    entries.append(("coverage", _version_id(bundle.coverage.id), bundle.coverage))
    entries.append(("source_baseline", _version_id(bundle.source_baseline.id), bundle.source_baseline))
    records = []
    for kind, version_id, model in entries:
        payload = _normalized_payload(kind, model)
        payload_hash = hashlib.sha256(canonical.canonical_bytes(payload)).hexdigest()
        records.append(
            {
                "kind": kind,
                "version_id": version_id,
                "payload": payload,
                "payload_hash": payload_hash,
            }
        )
    return records


__all__ = [
    "ALLOWED_KINDS",
    "canonical_bundle",
    "evaluate_bundle",
    "extract_versions",
    "load_bundle",
    "payload_bytes",
]

"""Strict source-bounded draft validation (model output is untrusted data)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from .schemas import DraftInterpretation

SAFETY_RE = re.compile(r"\b(is|are|deemed|considered)\s+(safe|certified|defect[- ]free)\b", re.I)
PLACEHOLDER_RE = re.compile(r"<[A-Z_]{3,}>")
REVISION_TOKEN_RE = re.compile(r"\bRev(?:ision)?\.?\s*[A-Z0-9]\b")
UNCERTAINTY_RE = re.compile(r"\b(may|might|could|unknown|not stated|unclear|uncertain|no workaround|not documented)\b", re.I)
EXCEPTION_RE = re.compile(r"\b(not apply|does not apply|unaffected|not affected|no exception)\b", re.I)
ACTION_RE = re.compile(r"^(use|set|configure|enable|disable|insert|add|apply|perform|generate|write)\b", re.I)
FIELDS = {
    "source_document_id",
    "source_revision",
    "source_identity",
    "affected_device",
    "affected_revision",
    "trigger_condition",
    "exception",
    "consequence",
    "workaround_documented",
    "workaround_restriction",
    "unresolved_field",
}
IDENTITY_FIELDS = {"source_identity", "affected_revision"}


def _norm(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.strip()).strip(".").lower()


def validate_draft(
    raw: Any,
    *,
    anchors: list[dict],
    selected_entries: list[str],
    expected_document_id: str | None,
    expected_revision: str | None,
    enforce_missing_identity: bool = False,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(raw, dict):
        return _result("rejected", ["draft must be a JSON object"], warnings, 0, 0, False)
    try:
        draft = DraftInterpretation.model_validate(raw)
    except ValidationError as exc:
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"]) or "<root>"
            errors.append(f"schema: {location}: {error['msg']}")
        return _result("rejected", errors, warnings, 0, 0, False)
    by_key = {anchor["anchor_key"]: anchor for anchor in anchors}
    if len(by_key) != len(anchors):
        return _result("rejected", ["duplicate supplied anchor keys"], warnings, 0, 0, False)
    references = 0
    supported = 0
    asserted_fields: set[str] = set()
    for index, claim in enumerate(draft.claims):
        label = f"claims[{index}]"
        if not claim.citations:
            errors.append(f"{label}: citation list is empty")
            continue
        if claim.status == "supported":
            supported += 1
            asserted_fields.add(claim.field)
        for key in claim.citations:
            anchor = by_key.get(key)
            references += 1
            if anchor is None:
                errors.append(f"{label}: citation {key!r} was not supplied")
            elif claim.field == "source_identity" and anchor.get("context_kind") != "source_identity":
                errors.append(f"{label}: source_identity must cite the source-identity anchor")
            elif claim.field in {"affected_device", "trigger_condition", "consequence", "workaround_documented", "workaround_restriction"} and (
                anchor.get("context_kind") in {"source_identity", "revision_header", "status_legend"}
            ):
                errors.append(f"{label}: {claim.field} is not supported by context anchor {key!r}")
        if claim.field == "affected_revision":
            kinds = {by_key[key].get("context_kind") for key in claim.citations if key in by_key}
            roles = {by_key[key].get("block_role") for key in claim.citations if key in by_key}
            if "table_row" not in roles:
                errors.append(f"{label}: affected_revision requires the summary-table row anchor")
            if not ({"revision_header", "status_legend"} & kinds):
                errors.append(f"{label}: affected_revision requires governing header/legend anchors")
        if claim.field == "unresolved_field":
            if claim.status != "unresolved":
                errors.append(f"{label}: unresolved_field claims must use unresolved status")
            if not any(UNCERTAINTY_RE.search(by_key[key]["text"]) for key in claim.citations if key in by_key):
                errors.append(f"{label}: cited text does not explicitly state uncertainty")
        if claim.field == "exception":
            if ACTION_RE.search(claim.value.strip()) or not EXCEPTION_RE.search(claim.value):
                errors.append(f"{label}: a workaround/action is not an exception")
        if SAFETY_RE.search(claim.value):
            errors.append(f"{label}: unsafe certification language is not allowed")
        if PLACEHOLDER_RE.search(claim.value):
            errors.append(f"{label}: unresolved placeholder text is not allowed")
        if enforce_missing_identity and REVISION_TOKEN_RE.search(claim.value):
            errors.append(f"{label}: synthetic missing-revision case must not assert a revision")
    known = set(FIELDS)
    for field in draft.unresolved_fields:
        if field not in known:
            errors.append(f"unresolved_fields: unknown field {field!r}")
    duplicates = {field for field in draft.unresolved_fields if draft.unresolved_fields.count(field) > 1}
    if duplicates:
        errors.append(f"unresolved_fields: duplicate fields {sorted(duplicates)}")
    for field in asserted_fields & set(draft.unresolved_fields):
        errors.append(f"unresolved_fields: {field} is both asserted and unresolved")
    identity_checked = False
    if enforce_missing_identity:
        identity_checked = True
        if draft.source_document_id is not None or draft.source_revision is not None:
            errors.append("synthetic missing-revision case must leave document identity ambiguous")
        for field in ("source_document_id", "source_revision"):
            if field not in draft.unresolved_fields:
                errors.append(f"{field} must be listed in unresolved_fields")
    else:
        identity_checked = True
        for field, expected in (("source_document_id", expected_document_id), ("source_revision", expected_revision)):
            asserted = getattr(draft, field)
            if expected is None:
                if asserted is not None:
                    errors.append(f"{field} is asserted but the sealed source does not state it")
                if field not in draft.unresolved_fields:
                    errors.append(f"{field} must be listed in unresolved_fields")
            else:
                if asserted is None or _norm(asserted) != _norm(expected):
                    errors.append(f"{field} does not match the sealed source identity")
                if field in draft.unresolved_fields:
                    errors.append(f"{field} is listed unresolved but the source states it")
        if draft.source_document_id and REVISION_TOKEN_RE.search(draft.source_document_id):
            errors.append("source_document_id incorrectly contains a revision token")
    if supported == 0:
        errors.append("draft contains no supported claim")
    if draft.limitations and SAFETY_RE.search(draft.limitations):
        errors.append("limitations contains unsafe certification language")
    if errors:
        return _result("rejected", errors, warnings, references, len(draft.claims), identity_checked)
    return _result("validated", [], warnings, references, len(draft.claims), identity_checked)


def _result(status: str, errors: list[str], warnings: list[str], references: int, claims: int, identity: bool) -> dict:
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "anchor_references": references,
        "checked_claims": claims,
        "identity_checked": identity,
    }

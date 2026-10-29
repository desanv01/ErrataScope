"""Draft validation: schema, anchor binding, identity, and citation evidence.

A schema-valid draft is not a semantically accepted interpretation. These checks
reject structurally or evidentially impossible drafts, including identity
mismatches and conflating document revision with silicon revision (repair R3).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .util import sha256_file

SAFETY_VERDICT_RE = re.compile(
    r"\b(is|are|deemed|considered)\s+(safe|certified|defect[- ]free)\b", re.IGNORECASE
)
PLACEHOLDER_RE = re.compile(r"<[A-Z_]{3,}>")
UNRESOLVED_SAFE_VALUES = {"", "unknown", "n/a", "na", "tbd", "none", "not stated"}
SILICON_ANCHOR_ROLES = {"table_row"}
SILICON_CONTEXT_KINDS = {"revision_header", "status_legend"}


def _norm(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.strip()).strip(".").strip().lower()


@dataclass
class IdentityExpectation:
    """Sealed source identity a draft must be consistent with."""

    document_id: str | None
    revision: str | None
    sha256: str | None = None
    enforce_missing: bool = False

    @classmethod
    def from_value(cls, value: Any) -> IdentityExpectation | None:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(
                document_id=value.get("document_id"),
                revision=value.get("revision"),
                sha256=value.get("sha256"),
                enforce_missing=bool(value.get("enforce_missing", value.get("document_id") is None)),
            )
        raise TypeError(f"unsupported identity expectation type: {type(value).__name__}")


@dataclass
class ValidationResult:
    status: str = "accepted"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    anchor_references: int = 0
    checked_claims: int = 0
    identity_checked: bool = False

    def reject(self, message: str) -> None:
        self.status = "rejected"
        self.errors.append(message)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "anchor_references": self.anchor_references,
            "checked_claims": self.checked_claims,
            "identity_checked": self.identity_checked,
        }


def validate_draft(
    raw: Any,
    anchors: Iterable,
    expected_document_sha256: str,
    expected_identity: Any = None,
) -> ValidationResult:
    """Validate a draft interpretation object against sealed anchors."""
    from .schemas import DraftInterpretation

    result = ValidationResult()
    expectation = IdentityExpectation.from_value(expected_identity)
    if not isinstance(raw, dict):
        result.reject(f"draft must be a JSON object, got {type(raw).__name__}")
        return result

    try:
        draft = DraftInterpretation(**raw)
    except ValidationError as exc:
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"]) or "<root>"
            result.reject(f"schema: {location}: {error['msg']}")
        return result

    anchor_list = list(anchors)
    index = {anchor.anchor_id: anchor for anchor in anchor_list}
    cited: list = []
    has_identity_context = any(
        getattr(anchor, "context_kind", None) == "source_identity" for anchor in anchor_list
    )

    for claim in draft.claims:
        result.checked_claims += 1
        claim_anchors = []
        for anchor_id in claim.anchor_ids:
            result.anchor_references += 1
            anchor = index.get(anchor_id)
            if anchor is None:
                result.reject(f"claim '{claim.field}' cites nonexistent anchor {anchor_id}")
                continue
            if anchor.document_sha256 != expected_document_sha256:
                result.reject(
                    f"claim '{claim.field}' cites anchor {anchor_id} from a different document"
                )
            claim_anchors.append(anchor)
            cited.append(anchor)

        if claim.field == "unresolved_field" and claim.status != "unresolved":
            result.reject(f"claim '{claim.field}' must be marked unresolved, got '{claim.status}'")
        if SAFETY_VERDICT_RE.search(claim.statement):
            result.reject(f"claim '{claim.field}' asserts an unsupported safety/certification verdict")
        if PLACEHOLDER_RE.search(claim.statement):
            result.reject(f"claim '{claim.field}' contains an unresolved placeholder token")

        if (
            claim.field == "source_identity"
            and claim_anchors
            and has_identity_context
            and not any(
                getattr(a, "context_kind", None) == "source_identity" for a in claim_anchors
            )
        ):
            result.reject("source_identity claim does not cite a source-identity anchor")

        if claim.field == "affected_revision" and claim.status == "supported" and claim_anchors:
            has_silicon_evidence = any(
                getattr(a, "block_role", None) in SILICON_ANCHOR_ROLES
                or getattr(a, "context_kind", None) in SILICON_CONTEXT_KINDS
                for a in claim_anchors
            )
            if not has_silicon_evidence:
                result.reject(
                    "affected_revision claim cites no revision-matrix row, revision header, "
                    "or status-legend anchor; document revision cannot stand in for silicon revision"
                )

    # Generic grounding: any asserted document revision must appear in cited text.
    if draft.source_revision and _norm(draft.source_revision) not in UNRESOLVED_SAFE_VALUES:
        cited_text = _norm(" ".join(anchor.text for anchor in cited))
        if _norm(draft.source_revision) not in cited_text:
            result.reject(
                f"asserted source_revision '{draft.source_revision}' is not grounded in any "
                "cited anchor text"
            )

    # Identity consistency against the sealed expectation.
    if expectation is not None:
        result.identity_checked = True
        expected_doc = _norm(expectation.document_id)
        actual_doc = _norm(draft.source_document_id)
        if expected_doc:
            if not actual_doc:
                result.reject("draft omits the sealed source_document_id")
            elif actual_doc != expected_doc:
                result.reject(
                    f"draft source_document_id '{draft.source_document_id}' does not match sealed "
                    f"identity '{expectation.document_id}'"
                )
        elif expectation.enforce_missing and actual_doc:
            result.reject(
                f"draft asserts source_document_id '{draft.source_document_id}' but the sealed "
                "source identity has no document ID"
            )

        expected_rev = _norm(expectation.revision)
        actual_rev = _norm(draft.source_revision)
        if expected_rev:
            if not actual_rev:
                result.reject("draft omits the sealed source_revision")
            elif actual_rev != expected_rev:
                result.reject(
                    f"draft source_revision '{draft.source_revision}' does not match sealed "
                    f"identity '{expectation.revision}'"
                )
            identity_cited = [
                anchor
                for anchor in cited
                if getattr(anchor, "context_kind", None) == "source_identity"
            ]
            if not identity_cited:
                result.reject(
                    "asserted source_revision requires citing a source-identity anchor; "
                    "the derived revision matrix is not identity evidence"
                )
            elif expected_rev not in _norm(" ".join(anchor.text for anchor in identity_cited)):
                result.reject(
                    "cited source-identity anchor text does not contain the asserted document revision"
                )
        elif expectation.enforce_missing and actual_rev:
            result.reject(
                f"draft asserts source_revision '{draft.source_revision}' but the sealed source "
                "has no document revision"
            )

    if "source_revision" in draft.unresolved_fields and draft.source_revision:
        result.reject("source_revision is both asserted and listed as unresolved")

    return result


def verify_document_bytes(path: Path, expected_sha256: str) -> tuple[bool, str]:
    actual = sha256_file(path)
    return actual == expected_sha256, actual


def parse_json_file(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}"
    except OSError as exc:
        return None, f"unreadable file: {exc}"

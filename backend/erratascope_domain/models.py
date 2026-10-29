"""Strict immutable domain models and bundle-level invariant validation.

Every model is frozen and forbids extra fields. IDs are UUIDs, content hashes are
lowercase SHA-256 hex. `parse_bundle` checks limits and AST depth before Pydantic
conversion, then validates cross-references, activation, coverage, identity
consistency, and supplied content hashes.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from . import canonical
from .errors import Diagnostic, DomainValidationError
from .rules import (
    MAX_AST_NODES,
    RuleExpr,
    preflight_ast,
    validate_ast,
)
from .selectors import (
    SelectorError,
    TypedValue,
    get_selector,
    validate_value_for_selector,
)

MAX_RULES = 100
MAX_FACTS = 5000
MAX_ANCHORS = 10000
MAX_DIAGNOSTICS = 60
SHA256_PATTERN = r"^[0-9a-f]{64}$"
Sha256Hex = Annotated[StrictStr, Field(pattern=SHA256_PATTERN)]
NonEmptyText = Annotated[StrictStr, Field(min_length=1)]
Truth = Literal["true", "false", "unknown"]

_FROZEN = ConfigDict(frozen=True, extra="forbid")


def _nonblank(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _finite_float(value, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


class ComponentIdentity(BaseModel):
    model_config = _FROZEN
    manufacturer: StrictStr | None
    exact_part: StrictStr | None
    family: StrictStr | None
    package: StrictStr | None
    silicon_revision: StrictStr | None
    evidence_refs: tuple[StrictStr, ...] = ()

    @field_validator("manufacturer", "exact_part", "family", "package", "silicon_revision")
    @classmethod
    def _known_identity_nonblank(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return _nonblank(value, info.field_name)


class ComponentInstance(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    identity: ComponentIdentity


class ProductSnapshot(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    product_name: NonEmptyText
    board_revision: StrictStr | None = None
    firmware_build_id: UUID
    operating_profile_id: UUID
    component_instances: tuple[ComponentInstance, ...] = Field(min_length=1)
    predecessor_id: UUID | None = None
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def _unique_instances(self) -> ProductSnapshot:
        ids = [item.id for item in self.component_instances]
        if len(ids) != len(set(ids)):
            raise ValueError("component instance ids must be unique")
        return self


class EvaluationScope(BaseModel):
    model_config = _FROZEN
    project_id: UUID
    snapshot_id: UUID
    subject_id: UUID
    firmware_build_id: UUID
    operating_profile_id: UUID


class DocumentVersion(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    document_id: StrictStr | None = None
    revision: StrictStr | None = None
    manufacturer: StrictStr | None = None
    source_url: StrictStr | None = None
    document_sha256: Sha256Hex
    authority: Literal["manufacturer", "forum", "synthetic"]
    synthetic: StrictBool
    predecessor_id: UUID | None = None


class SourceAnchor(BaseModel):
    model_config = _FROZEN
    anchor_id: NonEmptyText
    document_version_id: UUID
    document_sha256: Sha256Hex
    page_index: Annotated[StrictInt, Field(ge=0)]
    printed_page_label: StrictStr | None = None
    section: StrictStr | None = None
    text: NonEmptyText
    bbox: tuple[float, float, float, float] | None = None
    page_width_pt: float | None = None
    page_height_pt: float | None = None
    page_rotation: Annotated[StrictInt, Field(ge=0, le=359)]
    parser_name: NonEmptyText
    parser_version: NonEmptyText
    geometry_kind: Literal["located", "synthetic_not_located"]

    @field_validator("bbox", mode="before")
    @classmethod
    def _bbox_floats(cls, value):
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            raise ValueError("bbox must be a four-item sequence")
        return tuple(_finite_float(item, "bbox") for item in value)

    @field_validator("page_width_pt", "page_height_pt", mode="before")
    @classmethod
    def _dimension_floats(cls, value, info):
        return _finite_float(value, info.field_name)

    @field_validator("page_rotation")
    @classmethod
    def _rotation(cls, value: int) -> int:
        if value not in (0, 90, 180, 270):
            raise ValueError("page_rotation must be one of 0, 90, 180, 270")
        return value

    @model_validator(mode="after")
    def _geometry_rules(self) -> SourceAnchor:
        has_bbox = self.bbox is not None
        has_dims = self.page_width_pt is not None and self.page_height_pt is not None
        if has_bbox:
            left, top, right, bottom = self.bbox
            if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
                raise ValueError("bbox must be ordered inside [0,1]")
        if has_dims:
            if self.page_width_pt <= 0 or self.page_height_pt <= 0:
                raise ValueError("page dimensions must be positive")
        if self.geometry_kind == "located" and not (has_bbox and has_dims):
            raise ValueError("located geometry requires bbox and page dimensions")
        return self


class FactVersion(BaseModel):
    model_config = _FROZEN
    id: UUID
    scope: EvaluationScope
    selector: NonEmptyText
    value: TypedValue | None
    origin: Literal["declared", "extracted", "measured", "external"]
    evidence_refs: tuple[StrictStr, ...] = ()
    review_state: Literal["draft", "accepted", "rejected"]
    predecessor_id: UUID | None = None


class FactSet(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    fact_versions: tuple[FactVersion, ...]
    content_hash: Sha256Hex

    @model_validator(mode="after")
    def _unique_facts(self) -> FactSet:
        ids = [item.id for item in self.fact_versions]
        if len(ids) != len(set(ids)):
            raise ValueError("fact version ids must be unique")
        return self


class RuleVersion(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    document_version_id: UUID
    entry_id: NonEmptyText
    review_state: Literal["draft", "accepted", "rejected"]
    reviewer_id: StrictStr | None = None
    target: RuleExpr
    trigger: RuleExpr
    exceptions: tuple[RuleExpr, ...]
    consequence: StrictStr
    workaround_documentation: StrictStr | None = None
    workaround_restrictions: StrictStr | None = None
    anchors: tuple[StrictStr, ...]
    predecessor_id: UUID | None = None


class EntryKey(BaseModel):
    model_config = _FROZEN
    document_version_id: UUID
    entry_id: NonEmptyText

    def sort_key(self) -> tuple[str, str]:
        return (str(self.document_version_id), self.entry_id)


class CoverageManifest(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    document_version_ids: tuple[UUID, ...]
    inventory_complete: StrictBool
    discovered: tuple[EntryKey, ...]
    supported: tuple[EntryKey, ...]
    reviewed: tuple[EntryKey, ...]
    assessed: tuple[EntryKey, ...]
    failed: tuple[EntryKey, ...]
    unsupported: tuple[EntryKey, ...]
    selected: tuple[EntryKey, ...]
    notes: tuple[StrictStr, ...] = ()

    def key_set(self, field: str) -> set[tuple[str, str]]:
        return {
            item.sort_key()
            for item in getattr(self, field)
        }


class SourceBaseline(BaseModel):
    model_config = _FROZEN
    id: UUID
    project_id: UUID
    document_version_ids: tuple[UUID, ...]
    rule_version_ids: tuple[UUID, ...]
    coverage_manifest_id: UUID


class AssessmentInputBundle(BaseModel):
    model_config = _FROZEN
    schema_version: Literal[1] = 1
    project_id: UUID
    scope: EvaluationScope
    snapshot: ProductSnapshot
    fact_set: FactSet
    source_baseline: SourceBaseline
    documents: tuple[DocumentVersion, ...]
    anchors: tuple[SourceAnchor, ...]
    rules: tuple[RuleVersion, ...]
    coverage: CoverageManifest
    evaluator_version: Literal["domain-v1"] = "domain-v1"


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------
class NodeTrace(BaseModel):
    model_config = _FROZEN
    path: NonEmptyText
    op: NonEmptyText
    result: Truth
    selector: StrictStr | None = None
    value: TypedValue | None = None
    values: tuple[TypedValue, ...] | None = None
    constant_value: StrictBool | None = None
    children: tuple[NodeTrace, ...] = ()
    fact_ids: tuple[UUID, ...] = ()
    anchor_ids: tuple[StrictStr, ...] = ()
    resolved_value: TypedValue | None = None
    missing: StrictBool = False
    conflict: StrictBool = False
    warning_codes: tuple[StrictStr, ...] = ()


NodeTrace.model_rebuild()


class RuleResult(BaseModel):
    model_config = _FROZEN
    rule_version_id: UUID
    document_version_id: UUID
    entry_id: NonEmptyText
    target: Truth
    trigger: Truth
    exception: Truth
    overall: Truth
    applicability: Literal["applicable", "not_applicable", "unknown"]
    target_trace: NodeTrace
    trigger_trace: NodeTrace
    exception_traces: tuple[NodeTrace, ...]


class Dependency(BaseModel):
    model_config = _FROZEN
    scope: EvaluationScope
    selector: NonEmptyText


class Contradiction(BaseModel):
    model_config = _FROZEN
    selector: NonEmptyText
    fact_ids: tuple[UUID, ...]
    value_reprs: tuple[StrictStr, ...]


class Warning(BaseModel):
    model_config = _FROZEN
    code: NonEmptyText
    message: NonEmptyText
    rule_version_id: UUID | None = None
    selector: StrictStr | None = None
    fact_ids: tuple[UUID, ...] = ()
    anchor_ids: tuple[StrictStr, ...] = ()


class CoverageSummary(BaseModel):
    model_config = _FROZEN
    inventory_complete: StrictBool
    selected_entries: tuple[EntryKey, ...]
    unsupported_entries: tuple[EntryKey, ...]
    discovered_count: Annotated[StrictInt, Field(ge=0)]
    supported_count: Annotated[StrictInt, Field(ge=0)]
    reviewed_count: Annotated[StrictInt, Field(ge=0)]
    assessed_count: Annotated[StrictInt, Field(ge=0)]
    failed_count: Annotated[StrictInt, Field(ge=0)]
    unsupported_count: Annotated[StrictInt, Field(ge=0)]
    notes: tuple[StrictStr, ...] = ()


class AssessmentResult(BaseModel):
    model_config = _FROZEN
    schema_version: Literal[1] = 1
    evaluator_version: Literal["domain-v1"] = "domain-v1"
    project_id: UUID
    scope: EvaluationScope
    snapshot_id: UUID
    fact_set_id: UUID
    source_baseline_id: UUID
    coverage_manifest_id: UUID
    rule_version_ids: tuple[UUID, ...]
    input_hash: Sha256Hex
    result_hash: Sha256Hex
    rules: tuple[RuleResult, ...]
    selector_dependencies: tuple[Dependency, ...]
    missing_selectors: tuple[StrictStr, ...]
    contradictions: tuple[Contradiction, ...]
    warnings: tuple[Warning, ...]
    coverage_summary: CoverageSummary


# ---------------------------------------------------------------------------
# Bundle parsing and validation
# ---------------------------------------------------------------------------
def _validation_diagnostics(exc: ValidationError, prefix: str = "") -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for error in exc.errors()[:MAX_DIAGNOSTICS]:
        location = "/".join(str(part) for part in error["loc"])
        path = f"{prefix}{location}" if prefix else (location or "<root>")
        diagnostics.append(Diagnostic("SCHEMA_INVALID", path, str(error["msg"])))
    return diagnostics


def _preflight_raw_limits(raw: dict) -> None:
    if not isinstance(raw, dict):
        raise DomainValidationError([Diagnostic("SCHEMA_INVALID", "<root>", "bundle must be a JSON object")])
    rules = raw.get("rules")
    if rules is not None and not isinstance(rules, list):
        raise DomainValidationError(
            [Diagnostic("SCHEMA_INVALID", "rules", "rules must be a JSON array")]
        )
    if isinstance(rules, list):
        if len(rules) > MAX_RULES:
            raise DomainValidationError(
                [Diagnostic("RULE_LIMIT_EXCEEDED", "rules", f"bundle holds more than {MAX_RULES} rules")]
            )
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            aggregate_nodes = 0
            if "target" in rule:
                _depth, nodes = preflight_ast(rule["target"], f"rules/{index}/target")
                aggregate_nodes += nodes
            if "trigger" in rule:
                _depth, nodes = preflight_ast(rule["trigger"], f"rules/{index}/trigger")
                aggregate_nodes += nodes
            exceptions = rule.get("exceptions")
            if exceptions is not None and not isinstance(exceptions, list):
                raise DomainValidationError(
                    [Diagnostic("SCHEMA_INVALID", f"rules/{index}/exceptions", "exceptions must be a JSON array")]
                )
            if isinstance(exceptions, list):
                for position, exception in enumerate(exceptions):
                    _depth, nodes = preflight_ast(
                        exception, f"rules/{index}/exceptions/{position}"
                    )
                    aggregate_nodes += nodes
            if aggregate_nodes > MAX_AST_NODES:
                raise DomainValidationError(
                    [
                        Diagnostic(
                            "AST_NODE_LIMIT_EXCEEDED",
                            f"rules/{index}",
                            (
                                "rule expression tree exceeds the aggregate limit of "
                                f"{MAX_AST_NODES} nodes (target+trigger+exceptions={aggregate_nodes})"
                            ),
                        )
                    ]
                )
    anchors = raw.get("anchors")
    if isinstance(anchors, list) and len(anchors) > MAX_ANCHORS:
        raise DomainValidationError(
            [Diagnostic("ANCHOR_LIMIT_EXCEEDED", "anchors", f"bundle holds more than {MAX_ANCHORS} anchors")]
        )
    fact_set = raw.get("fact_set")
    if isinstance(fact_set, dict):
        facts = fact_set.get("fact_versions")
        if isinstance(facts, list) and len(facts) > MAX_FACTS:
            raise DomainValidationError(
                [Diagnostic("FACT_LIMIT_EXCEEDED", "fact_set/fact_versions", f"bundle holds more than {MAX_FACTS} facts")]
            )


def parse_bundle(raw: dict) -> AssessmentInputBundle:
    """Validate, seal-check and return a typed bundle or raise DomainValidationError."""
    _preflight_raw_limits(raw)
    try:
        bundle = AssessmentInputBundle.model_validate(raw)
    except ValidationError as exc:
        raise DomainValidationError(_validation_diagnostics(exc)) from None
    validate_bundle(bundle)
    return bundle


def _add(diagnostics: list[Diagnostic], code: str, path: str, message: str) -> None:
    diagnostics.append(Diagnostic(code, path, message))


def validate_bundle(bundle: AssessmentInputBundle) -> None:
    """Re-run every cross-reference/invariant check (evaluate calls this too)."""
    diagnostics: list[Diagnostic] = []
    project = bundle.project_id
    scope = bundle.scope
    snapshot = bundle.snapshot

    # Project and scope coherence.
    if scope.project_id != project:
        _add(diagnostics, "PROJECT_MISMATCH", "scope/project_id", "scope project does not match bundle project")
    if snapshot.project_id != project:
        _add(diagnostics, "PROJECT_MISMATCH", "snapshot/project_id", "snapshot project does not match bundle project")
    if scope.snapshot_id != snapshot.id:
        _add(diagnostics, "SCOPE_MISMATCH", "scope/snapshot_id", "scope does not reference the bundle snapshot")
    if scope.firmware_build_id != snapshot.firmware_build_id:
        _add(diagnostics, "SCOPE_MISMATCH", "scope/firmware_build_id", "scope firmware build differs from snapshot")
    if scope.operating_profile_id != snapshot.operating_profile_id:
        _add(diagnostics, "SCOPE_MISMATCH", "scope/operating_profile_id", "scope operating profile differs from snapshot")
    instances = {instance.id: instance for instance in snapshot.component_instances}
    if scope.subject_id not in instances:
        _add(diagnostics, "SCOPE_MISMATCH", "scope/subject_id", "scope subject is not a snapshot component instance")

    # Content hashes seal immutable snapshot/fact-set content.
    snapshot_dump = canonical.dump_model(snapshot)
    if canonical.snapshot_content_hash(snapshot_dump) != snapshot.content_hash:
        _add(diagnostics, "HASH_MISMATCH", "snapshot/content_hash", "snapshot content hash does not match its content")
    facts = bundle.fact_set.fact_versions
    fact_dump = canonical.dump_model(bundle.fact_set)
    if canonical.fact_set_content_hash(fact_dump) != bundle.fact_set.content_hash:
        _add(diagnostics, "HASH_MISMATCH", "fact_set/content_hash", "fact set content hash does not match its content")
    if bundle.fact_set.project_id != project:
        _add(diagnostics, "PROJECT_MISMATCH", "fact_set/project_id", "fact set project does not match bundle project")

    # Documents.
    documents = {document.id: document for document in bundle.documents}
    if len(documents) != len(bundle.documents):
        _add(diagnostics, "DUPLICATE_ID", "documents", "document version ids must be unique")
    for index, document in enumerate(bundle.documents):
        if document.project_id != project:
            _add(diagnostics, "PROJECT_MISMATCH", f"documents/{index}/project_id", "document project mismatch")
        if document.synthetic and document.authority != "synthetic":
            _add(diagnostics, "AUTHORITY_CONFLICT", f"documents/{index}/authority", "synthetic document must use synthetic authority")

    # Anchors.
    anchors_by_id = {}
    for index, anchor in enumerate(bundle.anchors):
        if anchor.anchor_id in anchors_by_id:
            _add(diagnostics, "DUPLICATE_ID", f"anchors/{index}/anchor_id", "duplicate anchor id")
        anchors_by_id[anchor.anchor_id] = anchor
        document = documents.get(anchor.document_version_id)
        if document is None:
            _add(diagnostics, "UNRESOLVED_REF", f"anchors/{index}/document_version_id", "anchor document does not resolve")
            continue
        if anchor.document_sha256 != document.document_sha256:
            _add(diagnostics, "HASH_MISMATCH", f"anchors/{index}/document_sha256", "anchor hash disagrees with its document")
        if anchor.geometry_kind == "synthetic_not_located" and not document.synthetic:
            _add(diagnostics, "INVALID_GEOMETRY", f"anchors/{index}/geometry_kind", "synthetic geometry requires a synthetic document")
    if len(anchors_by_id) > MAX_ANCHORS:
        _add(diagnostics, "ANCHOR_LIMIT_EXCEEDED", "anchors", "too many anchors")

    # Component instances: project isolation and identity evidence references.
    for index, component in enumerate(snapshot.component_instances):
        path = f"snapshot/component_instances/{index}"
        if component.project_id != project:
            _add(diagnostics, "PROJECT_MISMATCH", f"{path}/project_id", "component instance project mismatch")
        for anchor_id in component.identity.evidence_refs:
            if anchor_id not in anchors_by_id:
                _add(
                    diagnostics,
                    "UNRESOLVED_ANCHOR",
                    f"{path}/identity/evidence_refs",
                    f"identity evidence anchor {anchor_id!r} does not resolve",
                )

    # Rules: activation, references, AST semantics, selector/value compatibility.
    rules_by_id = {}
    seen_entries: set[tuple[str, str]] = set()
    for index, rule in enumerate(bundle.rules):
        path = f"rules/{index}"
        if rule.id in rules_by_id:
            _add(diagnostics, "DUPLICATE_ID", f"{path}/id", "duplicate rule version id")
        rules_by_id[rule.id] = rule
        if rule.project_id != project:
            _add(diagnostics, "PROJECT_MISMATCH", f"{path}/project_id", "rule project mismatch")
        document = documents.get(rule.document_version_id)
        if document is None:
            _add(diagnostics, "UNRESOLVED_REF", f"{path}/document_version_id", "rule document does not resolve")
        if rule.review_state != "accepted":
            _add(diagnostics, "UNREVIEWED_RULE", f"{path}/review_state", "only accepted rules may be assessed")
        if not (rule.reviewer_id or "").strip():
            _add(diagnostics, "UNREVIEWED_RULE", f"{path}/reviewer_id", "accepted rule requires a reviewer id")
        if not rule.consequence.strip():
            _add(diagnostics, "MISSING_CONSEQUENCE", f"{path}/consequence", "accepted rule requires a consequence")
        if not rule.anchors:
            _add(diagnostics, "MISSING_ANCHORS", f"{path}/anchors", "accepted rule requires source anchors")
        for anchor_id in rule.anchors:
            anchor = anchors_by_id.get(anchor_id)
            if anchor is None:
                _add(diagnostics, "UNRESOLVED_ANCHOR", f"{path}/anchors", f"rule anchor {anchor_id!r} does not resolve")
            elif anchor.document_version_id != rule.document_version_id:
                _add(diagnostics, "ANCHOR_DOCUMENT_MISMATCH", f"{path}/anchors", f"rule anchor {anchor_id!r} belongs to another document")
        key = (str(rule.document_version_id), rule.entry_id)
        if key in seen_entries:
            _add(diagnostics, "DUPLICATE_ENTRY", f"{path}/entry_id", "duplicate (document, entry) key")
        seen_entries.add(key)
        try:
            for target_name, expr in (
                ("target", rule.target),
                ("trigger", rule.trigger),
            ):
                diagnostics.extend(
                    validate_ast(
                        expr,
                        document_version_id=rule.document_version_id,
                        anchors_by_id=anchors_by_id,
                        path=f"{path}/{target_name}",
                    )
                )
            for position, exception in enumerate(rule.exceptions):
                diagnostics.extend(
                    validate_ast(
                        exception,
                        document_version_id=rule.document_version_id,
                        anchors_by_id=anchors_by_id,
                        path=f"{path}/exceptions/{position}",
                    )
                )
        except DomainValidationError as exc:
            diagnostics.extend(exc.diagnostics)
    if len(rules_by_id) > MAX_RULES:
        _add(diagnostics, "RULE_LIMIT_EXCEEDED", "rules", "too many rules")

    # Facts.
    if len(facts) > MAX_FACTS:
        _add(diagnostics, "FACT_LIMIT_EXCEEDED", "fact_set/fact_versions", "too many facts")
    subject_identity = instances.get(scope.subject_id).identity if scope.subject_id in instances else None
    identity_fields = {
        "component.manufacturer": "manufacturer",
        "component.exact_part": "exact_part",
        "component.family": "family",
        "component.package": "package",
        "component.silicon_revision": "silicon_revision",
    }
    for index, fact in enumerate(facts):
        path = f"fact_set/fact_versions/{index}"
        if fact.scope.project_id != project:
            _add(diagnostics, "PROJECT_MISMATCH", f"{path}/scope/project_id", "fact project mismatch")
        if fact.scope.snapshot_id != snapshot.id:
            _add(diagnostics, "UNRESOLVED_REF", f"{path}/scope/snapshot_id", "facts from another snapshot are not supported in v1")
        if fact.scope.subject_id not in instances:
            _add(diagnostics, "UNRESOLVED_REF", f"{path}/scope/subject_id", "fact subject is not a snapshot component instance")
        # Every supplied evidence reference must resolve, regardless of selector,
        # review state or whether the observed value is null.
        for anchor_id in fact.evidence_refs:
            if anchor_id not in anchors_by_id:
                _add(
                    diagnostics,
                    "UNRESOLVED_ANCHOR",
                    f"{path}/evidence_refs",
                    f"evidence anchor {anchor_id!r} does not resolve",
                )
        try:
            get_selector(fact.selector)
        except SelectorError as exc:
            _add(diagnostics, exc.code, f"{path}/selector", exc.message)
            continue
        if fact.value is not None:
            try:
                validate_value_for_selector(fact.selector, fact.value)
            except SelectorError as exc:
                _add(diagnostics, exc.code, f"{path}/value", exc.message)
        if fact.review_state == "accepted" and fact.value is not None and fact.selector in identity_fields:
            if not fact.evidence_refs:
                _add(diagnostics, "MISSING_EVIDENCE", f"{path}/evidence_refs", "accepted identity fact requires evidence anchors")
        # Snapshot identity is a consistency constraint, not a hidden fact channel.
        if (
            fact.review_state == "accepted"
            and fact.value is not None
            and fact.selector in identity_fields
            and fact.scope == scope
            and subject_identity is not None
        ):
            attribute = identity_fields[fact.selector]
            snapshot_value = getattr(subject_identity, attribute)
            fact_value = getattr(fact.value, "value", None)
            if snapshot_value is not None and fact_value is not None and snapshot_value != fact_value:
                _add(
                    diagnostics,
                    "IDENTITY_MISMATCH",
                    f"{path}/value",
                    f"accepted identity fact for {fact.selector!r} disagrees with the snapshot identity",
                )

    # Coverage.
    coverage = bundle.coverage
    if coverage.project_id != project:
        _add(diagnostics, "PROJECT_MISMATCH", "coverage/project_id", "coverage project mismatch")
    coverage_documents = set(coverage.document_version_ids)
    if not coverage_documents <= set(documents):
        _add(diagnostics, "UNRESOLVED_REF", "coverage/document_version_ids", "coverage references an unknown document")
    lists = {
        "discovered": coverage.discovered,
        "supported": coverage.supported,
        "reviewed": coverage.reviewed,
        "assessed": coverage.assessed,
        "failed": coverage.failed,
        "unsupported": coverage.unsupported,
        "selected": coverage.selected,
    }
    sets: dict[str, set[tuple[str, str]]] = {}
    for name, values in lists.items():
        keys = coverage.key_set(name)
        if len(keys) != len(values):
            _add(diagnostics, "DUPLICATE_COVERAGE_ENTRY", f"coverage/{name}", "duplicate entry keys in coverage set")
        sets[name] = keys
        for key in keys:
            if key[0] not in {str(item) for item in coverage_documents}:
                _add(diagnostics, "UNRESOLVED_REF", f"coverage/{name}", f"entry document {key[0]!r} is not in coverage documents")
    if not sets["supported"] <= sets["discovered"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/supported", "supported entries must be discovered")
    if not sets["reviewed"] <= sets["supported"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/reviewed", "reviewed entries must be supported")
    if not sets["assessed"] <= sets["reviewed"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/assessed", "assessed entries must be reviewed")
    if not sets["failed"] <= sets["discovered"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/failed", "failed entries must be discovered")
    if not sets["unsupported"] <= sets["discovered"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/unsupported", "unsupported entries must be discovered")
    if sets["failed"] & sets["supported"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/failed", "failed entries cannot be supported")
    if sets["unsupported"] & sets["supported"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/unsupported", "unsupported entries cannot be supported")
    if not sets["selected"] <= sets["discovered"]:
        _add(diagnostics, "COVERAGE_INCONSISTENT", "coverage/selected", "selected entries must be discovered")
    for index, rule in enumerate(bundle.rules):
        key = (str(rule.document_version_id), rule.entry_id)
        for name in ("selected", "reviewed", "assessed"):
            if key not in sets[name]:
                _add(diagnostics, "UNSELECTED_ENTRY", f"rules/{index}", f"rule entry is not {name} in coverage")

    # Source baseline pins.
    baseline = bundle.source_baseline
    if baseline.project_id != project:
        _add(diagnostics, "PROJECT_MISMATCH", "source_baseline/project_id", "baseline project mismatch")
    if set(baseline.document_version_ids) != set(documents):
        _add(diagnostics, "UNRESOLVED_REF", "source_baseline/document_version_ids", "baseline document set differs from bundle documents")
    if set(baseline.rule_version_ids) != set(rules_by_id):
        _add(diagnostics, "UNRESOLVED_REF", "source_baseline/rule_version_ids", "baseline rule set differs from bundle rules")
    if baseline.coverage_manifest_id != coverage.id:
        _add(diagnostics, "UNRESOLVED_REF", "source_baseline/coverage_manifest_id", "baseline coverage id does not match")

    if diagnostics:
        raise DomainValidationError(diagnostics)


__all__ = [
    "AssessmentInputBundle",
    "AssessmentResult",
    "ComponentIdentity",
    "ComponentInstance",
    "Contradiction",
    "CoverageManifest",
    "CoverageSummary",
    "Dependency",
    "DocumentVersion",
    "EntryKey",
    "EvaluationScope",
    "FactSet",
    "FactVersion",
    "NodeTrace",
    "ProductSnapshot",
    "RuleResult",
    "RuleVersion",
    "SourceAnchor",
    "SourceBaseline",
    "Warning",
    "parse_bundle",
    "validate_bundle",
]

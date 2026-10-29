"""Deterministic scoped three-valued evaluation (domain v1).

Applicability = target AND trigger AND NOT(any exception). Every branch is
evaluated; warnings/conflicts from irrelevant branches are retained. Selector
resolution uses accepted facts in the exact five-field scope only. No latest-wins,
scope inheritance, unit conversion, or inference beyond the source-bounded facts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TypeVar

from . import canonical
from .errors import Diagnostic, DomainValidationError
from .models import (
    AssessmentInputBundle,
    AssessmentResult,
    Contradiction,
    CoverageSummary,
    Dependency,
    FactVersion,
    NodeTrace,
    RuleResult,
    RuleVersion,
    Warning,
    parse_bundle,
)
from .rules import All, Any, Constant, Eq, Gt, Gte, In, Lt, Lte, Not, RuleExpr
from .selectors import (
    SelectorError,
    TypedValue,
    compare_order,
    typed_value_key,
)

TRUE = "true"
FALSE = "false"
UNKNOWN = "unknown"


def truth_not(value: str) -> str:
    if value == TRUE:
        return FALSE
    if value == FALSE:
        return TRUE
    return UNKNOWN


def truth_and(values: Iterable[str]) -> str:
    items = list(values)
    if any(value == FALSE for value in items):
        return FALSE
    if all(value == TRUE for value in items):
        return TRUE
    return UNKNOWN


def truth_or(values: Iterable[str]) -> str:
    items = list(values)
    if any(value == TRUE for value in items):
        return TRUE
    if all(value == FALSE for value in items):
        return FALSE
    return UNKNOWN


@dataclass
class Resolution:
    selector: str
    status: str  # known | missing | conflict
    values: list[TypedValue] = field(default_factory=list)
    groups: dict[tuple, list] = field(default_factory=dict)
    null_fact_ids: list = field(default_factory=list)
    out_of_scope_fact_ids: list = field(default_factory=list)

    @property
    def known_fact_ids(self) -> list:
        return [fact_id for ids in self.groups.values() for fact_id in ids]

    @property
    def all_fact_ids(self) -> list:
        seen = []
        for fact_id in self.known_fact_ids + self.null_fact_ids:
            if fact_id not in seen:
                seen.append(fact_id)
        return seen

    @property
    def resolved(self) -> TypedValue | None:
        if self.status != "known":
            return None
        return self.values[0]

    @property
    def value_reprs(self) -> list[str]:
        return [str(typed_value_key(value)) for value in self.values]


def _is_scope_equal(fact: FactVersion, bundle: AssessmentInputBundle) -> bool:
    return fact.scope == bundle.scope


def resolve_selector(bundle: AssessmentInputBundle, selector: str) -> Resolution:
    resolution = Resolution(selector=selector, status="missing")
    groups: dict[tuple, list] = {}
    values: dict[tuple, TypedValue] = {}
    for fact in bundle.fact_set.fact_versions:
        if fact.review_state != "accepted" or fact.selector != selector:
            continue
        if not _is_scope_equal(fact, bundle):
            resolution.out_of_scope_fact_ids.append(fact.id)
            continue
        if fact.value is None:
            resolution.null_fact_ids.append(fact.id)
            continue
        key = typed_value_key(fact.value)
        groups.setdefault(key, []).append(fact.id)
        values.setdefault(key, fact.value)
    resolution.groups = groups
    resolution.values = [values[key] for key in sorted(groups, key=str)]
    if not groups:
        resolution.status = "missing"
    elif len(groups) == 1:
        resolution.status = "known"
    else:
        resolution.status = "conflict"
    return resolution


def _leaf_truth(leaf, resolution: Resolution) -> str:
    if resolution.status == "missing":
        return UNKNOWN
    if resolution.status == "conflict":
        return UNKNOWN
    resolved = resolution.resolved
    assert resolved is not None
    if isinstance(leaf, Eq):
        return TRUE if typed_value_key(resolved) == typed_value_key(leaf.value) else FALSE
    if isinstance(leaf, In):
        keys = {typed_value_key(value) for value in leaf.values}
        return TRUE if typed_value_key(resolved) in keys else FALSE
    if isinstance(leaf, (Lt, Lte, Gt, Gte)):
        try:
            return TRUE if compare_order(leaf.op, resolved, leaf.value) else FALSE
        except SelectorError:
            return UNKNOWN
    raise TypeError(f"unsupported leaf {type(leaf).__name__}")


def _leaf_warnings(leaf, resolution: Resolution, rule_id) -> list[Warning]:
    warnings: list[Warning] = []
    fact_ids = tuple(resolution.all_fact_ids)
    anchor_ids = tuple(leaf.anchor_ids)
    if resolution.status == "missing":
        warnings.append(
            Warning(
                code="MISSING_SELECTOR",
                message=f"no accepted known value for {leaf.selector!r} in the exact scope",
                rule_version_id=rule_id,
                selector=leaf.selector,
                fact_ids=fact_ids,
                anchor_ids=anchor_ids,
            )
        )
    elif resolution.status == "conflict":
        warnings.append(
            Warning(
                code="CONTRADICTORY_FACTS",
                message=f"multiple different accepted values for {leaf.selector!r} in the same scope",
                rule_version_id=rule_id,
                selector=leaf.selector,
                fact_ids=fact_ids,
                anchor_ids=anchor_ids,
            )
        )
    elif resolution.null_fact_ids:
        warnings.append(
            Warning(
                code="NULL_OBSERVATION_RETAINED",
                message=f"explicit null observation retained alongside a known value for {leaf.selector!r}",
                rule_version_id=rule_id,
                selector=leaf.selector,
                fact_ids=fact_ids,
                anchor_ids=anchor_ids,
            )
        )
    if resolution.out_of_scope_fact_ids:
        warnings.append(
            Warning(
                code="OUT_OF_SCOPE_FACT_IGNORED",
                message=(
                    f"accepted {leaf.selector!r} facts exist outside the exact scope and were not selected"
                ),
                rule_version_id=rule_id,
                selector=leaf.selector,
                fact_ids=tuple(resolution.out_of_scope_fact_ids),
                anchor_ids=anchor_ids,
            )
        )
    return warnings


def _evaluate(expr: RuleExpr, bundle: AssessmentInputBundle, path: str, rule_id):
    warnings: list[Warning] = []
    dependencies: set[str] = set()
    missing: set[str] = set()
    contradictions: list[Contradiction] = []

    if isinstance(expr, (All, Any)):
        children = []
        truths = []
        for index, child in enumerate(expr.children):
            trace, child_warnings, child_deps, child_missing, child_conflicts = _evaluate(
                child, bundle, f"{path}/children/{index}", rule_id
            )
            children.append(trace)
            truths.append(trace.result)
            warnings.extend(child_warnings)
            dependencies |= child_deps
            missing |= child_missing
            contradictions.extend(child_conflicts)
        result = truth_and(truths) if isinstance(expr, All) else truth_or(truths)
        return (
            NodeTrace(
                path=path,
                op=expr.op,
                result=result,
                children=tuple(children),
                warning_codes=tuple(sorted({warning.code for warning in warnings})),
            ),
            warnings,
            dependencies,
            missing,
            contradictions,
        )
    if isinstance(expr, Not):
        child_trace, child_warnings, child_deps, child_missing, child_conflicts = _evaluate(
            expr.child, bundle, f"{path}/child", rule_id
        )
        return (
            NodeTrace(
                path=path,
                op="not",
                result=truth_not(child_trace.result),
                children=(child_trace,),
                warning_codes=tuple(sorted({warning.code for warning in child_warnings})),
            ),
            child_warnings,
            child_deps,
            child_missing,
            child_conflicts,
        )
    if isinstance(expr, Constant):
        return (
            NodeTrace(
                path=path,
                op="constant",
                result=TRUE if expr.value else FALSE,
                constant_value=expr.value,
                anchor_ids=tuple(expr.anchor_ids),
            ),
            warnings,
            dependencies,
            missing,
            contradictions,
        )

    resolution = resolve_selector(bundle, expr.selector)
    dependencies.add(expr.selector)
    leaf_warnings = _leaf_warnings(expr, resolution, rule_id)
    warnings.extend(leaf_warnings)
    if resolution.status in ("missing", "conflict"):
        missing.add(expr.selector)
    if resolution.status == "conflict":
        contradictions.append(
            Contradiction(
                selector=expr.selector,
                fact_ids=tuple(sorted(resolution.all_fact_ids, key=str)),
                value_reprs=tuple(sorted(set(resolution.value_reprs))),
            )
        )
    trace = NodeTrace(
        path=path,
        op=expr.op,
        selector=expr.selector,
        result=_leaf_truth(expr, resolution),
        value=expr.value if isinstance(expr, (Eq, Lt, Lte, Gt, Gte)) else None,
        values=expr.values if isinstance(expr, In) else None,
        fact_ids=tuple(sorted(resolution.all_fact_ids, key=str)),
        anchor_ids=tuple(expr.anchor_ids),
        resolved_value=resolution.resolved,
        missing=resolution.status == "missing",
        conflict=resolution.status == "conflict",
        warning_codes=tuple(sorted({warning.code for warning in leaf_warnings})),
    )
    return trace, warnings, dependencies, missing, contradictions


def _applicability(overall: str) -> str:
    if overall == TRUE:
        return "applicable"
    if overall == FALSE:
        return "not_applicable"
    return "unknown"


def _evaluate_rule(rule: RuleVersion, bundle: AssessmentInputBundle):
    rule_id = rule.id
    target_trace, target_warnings, target_deps, target_missing, target_conflicts = _evaluate(
        rule.target, bundle, f"rules/{rule_id}/target", rule_id
    )
    trigger_trace, trigger_warnings, trigger_deps, trigger_missing, trigger_conflicts = _evaluate(
        rule.trigger, bundle, f"rules/{rule_id}/trigger", rule_id
    )
    exception_traces = []
    exception_warnings: list[Warning] = []
    exception_deps: set[str] = set()
    exception_missing: set[str] = set()
    exception_conflicts: list[Contradiction] = []
    for index, exception in enumerate(rule.exceptions):
        trace, warnings, deps, missing, conflicts = _evaluate(
            exception, bundle, f"rules/{rule_id}/exceptions/{index}", rule_id
        )
        exception_traces.append(trace)
        exception_warnings.extend(warnings)
        exception_deps |= deps
        exception_missing |= missing
        exception_conflicts.extend(conflicts)
    if exception_traces:
        exception_truth = truth_or(trace.result for trace in exception_traces)
    else:
        exception_truth = FALSE
    overall = truth_and([target_trace.result, trigger_trace.result, truth_not(exception_truth)])
    result = RuleResult(
        rule_version_id=rule.id,
        document_version_id=rule.document_version_id,
        entry_id=rule.entry_id,
        target=target_trace.result,
        trigger=trigger_trace.result,
        exception=exception_truth,
        overall=overall,
        applicability=_applicability(overall),
        target_trace=target_trace,
        trigger_trace=trigger_trace,
        exception_traces=tuple(exception_traces),
    )
    return (
        result,
        target_warnings + trigger_warnings + exception_warnings,
        target_deps | trigger_deps | exception_deps,
        target_missing | trigger_missing | exception_missing,
        target_conflicts + trigger_conflicts + exception_conflicts,
    )


T = TypeVar("T")


def _dedupe(items: list[T], key) -> list[T]:
    seen = set()
    output = []
    for item in items:
        marker = key(item)
        if marker in seen:
            continue
        seen.add(marker)
        output.append(item)
    return output


def _coverage_warnings(bundle: AssessmentInputBundle) -> list[Warning]:
    coverage = bundle.coverage
    warnings: list[Warning] = []
    if not coverage.inventory_complete:
        warnings.append(
            Warning(
                code="INVENTORY_INCOMPLETE",
                message="the source inventory is explicitly incomplete; assessment scope is selected entries only",
            )
        )
    if coverage.unsupported:
        warnings.append(
            Warning(
                code="UNSUPPORTED_ENTRIES",
                message=f"{len(coverage.unsupported)} discovered entries are unsupported and were not assessed",
            )
        )
    if coverage.failed:
        warnings.append(
            Warning(
                code="FAILED_ENTRIES",
                message=f"{len(coverage.failed)} discovered entries failed extraction and were not assessed",
            )
        )
    return warnings


def _revalidated_bundle(bundle: AssessmentInputBundle) -> AssessmentInputBundle:
    """Strictly revalidate a caller-supplied bundle through its JSON form.

    Pydantic's default instance revalidation can trust already-constructed
    models; dumping to JSON primitives and re-running the public parser catches
    model_copy/model_construct bypasses, strict typing violations, schema-version
    tampering, aggregate AST-limit breaches and content-hash mismatches without
    mutating the caller's sealed value.
    """
    if not isinstance(bundle, AssessmentInputBundle):
        raise DomainValidationError(
            [Diagnostic("SCHEMA_INVALID", "<root>", "evaluate requires an AssessmentInputBundle")]
        )
    try:
        # Treat serializer type mismatches as invalid input. Ignoring them can
        # convert an invalid bytes operand to text before strict revalidation.
        raw = bundle.model_dump(mode="json", exclude_none=False, warnings="error")
    except RecursionError:
        raise DomainValidationError(
            [
                Diagnostic(
                    "AST_DEPTH_EXCEEDED",
                    "<root>",
                    "expression nesting exceeds the supported recursion depth",
                )
            ]
        ) from None
    except Exception as exc:  # noqa: BLE001 - structured diagnostic, no incidental leak
        raise DomainValidationError(
            [
                Diagnostic(
                    "SCHEMA_INVALID",
                    "<root>",
                    f"bundle cannot be serialized for strict revalidation: {type(exc).__name__}",
                )
            ]
        ) from None
    return parse_bundle(raw)


def evaluate(bundle: AssessmentInputBundle) -> AssessmentResult:
    """Validate and evaluate a bundle; returns a canonical-hashed result."""
    bundle = _revalidated_bundle(bundle)
    rule_results = []
    warnings: list[Warning] = []
    dependencies: set[str] = set()
    missing_selectors: set[str] = set()
    contradictions: list[Contradiction] = []
    for rule in bundle.rules:
        result, rule_warnings, deps, missing, conflicts = _evaluate_rule(rule, bundle)
        rule_results.append(result)
        warnings.extend(rule_warnings)
        dependencies |= deps
        missing_selectors |= missing
        contradictions.extend(conflicts)
    warnings.extend(_coverage_warnings(bundle))
    warnings = _dedupe(
        warnings,
        key=lambda item: (
            item.code,
            item.selector,
            item.rule_version_id,
            tuple(str(value) for value in item.fact_ids),
            item.anchor_ids,
        ),
    )
    contradictions = _dedupe(
        contradictions,
        key=lambda item: (item.selector, tuple(str(value) for value in item.fact_ids)),
    )
    coverage = bundle.coverage
    coverage_summary = CoverageSummary(
        inventory_complete=coverage.inventory_complete,
        selected_entries=tuple(sorted(coverage.selected, key=lambda item: item.sort_key())),
        unsupported_entries=tuple(sorted(coverage.unsupported, key=lambda item: item.sort_key())),
        discovered_count=len(coverage.discovered),
        supported_count=len(coverage.supported),
        reviewed_count=len(coverage.reviewed),
        assessed_count=len(coverage.assessed),
        failed_count=len(coverage.failed),
        unsupported_count=len(coverage.unsupported),
        notes=coverage.notes,
    )
    dependency_models = tuple(
        sorted(
            (Dependency(scope=bundle.scope, selector=selector) for selector in dependencies),
            key=lambda item: item.selector,
        )
    )
    result_payload = AssessmentResult(
        project_id=bundle.project_id,
        scope=bundle.scope,
        snapshot_id=bundle.snapshot.id,
        fact_set_id=bundle.fact_set.id,
        source_baseline_id=bundle.source_baseline.id,
        coverage_manifest_id=bundle.coverage.id,
        rule_version_ids=tuple(sorted((rule.id for rule in bundle.rules), key=str)),
        input_hash=canonical.bundle_input_hash(bundle),
        result_hash="0" * 64,
        rules=tuple(rule_results),
        selector_dependencies=dependency_models,
        missing_selectors=tuple(sorted(missing_selectors)),
        contradictions=tuple(contradictions),
        warnings=tuple(warnings),
        coverage_summary=coverage_summary,
    )
    digest = canonical.result_hash(canonical.dump_model(result_payload))
    return result_payload.model_copy(update={"result_hash": digest})


__all__ = [
    "evaluate",
    "resolve_selector",
    "truth_and",
    "truth_not",
    "truth_or",
]

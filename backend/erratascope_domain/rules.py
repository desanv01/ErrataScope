"""Approved rule AST for deterministic domain v1.

Only the bound operators exist: typed eq/in, quantity/integer ordering,
all/any/not and a reviewed explicit constant. No expressions, truthiness,
string-to-number guessing, or dynamic evaluation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    field_validator,
)

from .errors import Diagnostic, DomainValidationError, raise_diagnostic
from .selectors import (
    SelectorError,
    TypedValue,
    get_selector,
    validate_value_for_selector,
    values_are_homogeneous,
)

MAX_AST_DEPTH = 32
MAX_AST_NODES = 512

LEAF_OPS = ("eq", "in", "lt", "lte", "gt", "gte", "constant")
COMPOSITE_OPS = ("all", "any", "not")
ALL_OPS = LEAF_OPS + COMPOSITE_OPS

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class _Leaf(BaseModel):
    model_config = _FROZEN
    anchor_ids: tuple[StrictStr, ...]

    @field_validator("anchor_ids")
    @classmethod
    def _nonempty_anchors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("technical predicates require at least one anchor id")
        return value


class Eq(_Leaf):
    op: Literal["eq"] = "eq"
    selector: StrictStr
    value: TypedValue


class In(_Leaf):
    op: Literal["in"] = "in"
    selector: StrictStr
    values: tuple[TypedValue, ...]

    @field_validator("values")
    @classmethod
    def _nonempty_values(cls, value: tuple[TypedValue, ...]) -> tuple[TypedValue, ...]:
        if not value:
            raise ValueError("'in' requires a nonempty tuple of values")
        if not values_are_homogeneous(value):
            raise ValueError("'in' values must share one type (and quantity unit)")
        return value


class Lt(_Leaf):
    op: Literal["lt"] = "lt"
    selector: StrictStr
    value: TypedValue


class Lte(_Leaf):
    op: Literal["lte"] = "lte"
    selector: StrictStr
    value: TypedValue


class Gt(_Leaf):
    op: Literal["gt"] = "gt"
    selector: StrictStr
    value: TypedValue


class Gte(_Leaf):
    op: Literal["gte"] = "gte"
    selector: StrictStr
    value: TypedValue


class Constant(BaseModel):
    model_config = _FROZEN
    op: Literal["constant"] = "constant"
    value: StrictBool
    anchor_ids: tuple[StrictStr, ...]
    review_rationale: StrictStr

    @field_validator("anchor_ids")
    @classmethod
    def _nonempty_anchors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("'constant' requires at least one anchor id")
        return value

    @field_validator("review_rationale")
    @classmethod
    def _nonempty_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("'constant' requires a nonempty review_rationale")
        return value


class All(BaseModel):
    model_config = _FROZEN
    op: Literal["all"] = "all"
    children: tuple[RuleExpr, ...]

    @field_validator("children")
    @classmethod
    def _nonempty_children(cls, value):
        if not value:
            raise ValueError("'all' requires at least one child")
        return value


class Any(BaseModel):
    model_config = _FROZEN
    op: Literal["any"] = "any"
    children: tuple[RuleExpr, ...]

    @field_validator("children")
    @classmethod
    def _nonempty_children(cls, value):
        if not value:
            raise ValueError("'any' requires at least one child")
        return value


class Not(BaseModel):
    model_config = _FROZEN
    op: Literal["not"] = "not"
    child: RuleExpr


RuleExpr = Annotated[
    Eq | In | Lt | Lte | Gt | Gte | All | Any | Not | Constant,
    Field(discriminator="op"),
]

for _model in (All, Any, Not):
    _model.model_rebuild()


def preflight_ast(raw, path: str) -> tuple[int, int]:
    """Validate raw AST shape, depth and node count before Pydantic recursion."""
    if not isinstance(raw, dict):
        raise_diagnostic("INVALID_AST", path, "expression must be a JSON object")
    stack: list[tuple[object, int, str]] = [(raw, 1, path)]
    nodes = 0
    deepest = 0
    while stack:
        node, depth, node_path = stack.pop()
        if not isinstance(node, dict):
            raise_diagnostic("INVALID_AST", node_path, "expression must be a JSON object")
        if depth > MAX_AST_DEPTH:
            raise_diagnostic(
                "AST_DEPTH_EXCEEDED", node_path, f"expression depth exceeds {MAX_AST_DEPTH}"
            )
        deepest = max(deepest, depth)
        nodes += 1
        if nodes > MAX_AST_NODES:
            raise_diagnostic(
                "AST_NODE_LIMIT_EXCEEDED", node_path, f"expression exceeds {MAX_AST_NODES} nodes"
            )
        op = node.get("op")
        if op not in ALL_OPS:
            raise_diagnostic("UNSUPPORTED_OPERATOR", node_path, f"unsupported operator {op!r}")
        if op in ("all", "any"):
            children = node.get("children")
            if not isinstance(children, list) or not children:
                raise_diagnostic("INVALID_AST", node_path, f"{op!r} requires a nonempty children array")
            for index, child in enumerate(children):
                stack.append((child, depth + 1, f"{node_path}/children/{index}"))
        elif op == "not":
            stack.append((node.get("child"), depth + 1, f"{node_path}/child"))
    return deepest, nodes


def node_count(expr: RuleExpr) -> int:
    total = 1
    if isinstance(expr, (All, Any)):
        total += sum(node_count(child) for child in expr.children)
    elif isinstance(expr, Not):
        total += node_count(expr.child)
    return total


def iter_leaves(expr: RuleExpr, path: str = "expr"):
    """Yield (path, leaf) for every technical/constant leaf, recursively."""
    if isinstance(expr, (All, Any)):
        for index, child in enumerate(expr.children):
            yield from iter_leaves(child, f"{path}/children/{index}")
    elif isinstance(expr, Not):
        yield from iter_leaves(expr.child, f"{path}/child")
    else:
        yield path, expr


def collect_selectors(expr: RuleExpr) -> set[str]:
    names: set[str] = set()
    for _path, leaf in iter_leaves(expr):
        if isinstance(leaf, Constant):
            continue
        names.add(leaf.selector)
    return names


def validate_ast(
    expr: RuleExpr,
    *,
    document_version_id,
    anchors_by_id: dict,
    path: str,
) -> list[Diagnostic]:
    """Validate operator/selector/value/anchor compatibility for one expression."""
    diagnostics: list[Diagnostic] = []
    preflight_ast(expr.model_dump(mode="json"), path)
    for leaf_path, leaf in iter_leaves(expr, path):
        for anchor_id in leaf.anchor_ids:
            anchor = anchors_by_id.get(anchor_id)
            if anchor is None:
                diagnostics.append(
                    Diagnostic("UNRESOLVED_ANCHOR", f"{leaf_path}/anchor_ids", f"anchor {anchor_id!r} does not resolve")
                )
            elif anchor.document_version_id != document_version_id:
                diagnostics.append(
                    Diagnostic(
                        "ANCHOR_DOCUMENT_MISMATCH",
                        f"{leaf_path}/anchor_ids",
                        f"anchor {anchor_id!r} belongs to a different document version",
                    )
                )
        if isinstance(leaf, Constant):
            continue
        try:
            spec = get_selector(leaf.selector)
        except SelectorError as exc:
            diagnostics.append(Diagnostic(exc.code, f"{leaf_path}/selector", exc.message))
            continue
        if leaf.op == "eq":
            try:
                validate_value_for_selector(leaf.selector, leaf.value)
            except SelectorError as exc:
                diagnostics.append(Diagnostic(exc.code, f"{leaf_path}/value", exc.message))
        elif leaf.op == "in":
            if spec.kind not in ("text", "integer"):
                diagnostics.append(
                    Diagnostic(
                        "UNSUPPORTED_OPERATOR",
                        f"{leaf_path}/op",
                        f"'in' is only supported for text/integer selectors, not {spec.kind}",
                    )
                )
            for index, value in enumerate(leaf.values):
                try:
                    validate_value_for_selector(leaf.selector, value)
                except SelectorError as exc:
                    diagnostics.append(Diagnostic(exc.code, f"{leaf_path}/values/{index}", exc.message))
        else:  # ordering
            if spec.kind not in ("quantity", "integer"):
                diagnostics.append(
                    Diagnostic(
                        "UNSUPPORTED_OPERATOR",
                        f"{leaf_path}/op",
                        f"ordered comparison is only supported for quantity/integer selectors, not {spec.kind}",
                    )
                )
            else:
                try:
                    validate_value_for_selector(leaf.selector, leaf.value)
                except SelectorError as exc:
                    diagnostics.append(Diagnostic(exc.code, f"{leaf_path}/value", exc.message))
    return diagnostics


def raise_if(diagnostics: list[Diagnostic]) -> None:
    if diagnostics:
        raise DomainValidationError(diagnostics)

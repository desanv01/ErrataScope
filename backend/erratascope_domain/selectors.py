"""Selector registry and typed fact values (binding: deterministic domain v1).

Values are discriminated objects. Text is compared exactly (case-sensitive, no
trimming); integers exclude booleans; quantities are canonicalized decimal
strings with an exact registry unit and no unit conversion in v1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
)

QUANTITY_RE = re.compile(r"^-?[0-9]{1,18}(?:\.[0-9]{1,9})?\Z")
VALUE_KINDS = ("text", "boolean", "integer", "quantity")


class TextValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["text"] = "text"
    value: StrictStr


class BooleanValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["boolean"] = "boolean"
    value: StrictBool


class IntegerValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["integer"] = "integer"
    value: StrictInt


class QuantityValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["quantity"] = "quantity"
    value: StrictStr
    unit: StrictStr

    @field_validator("value")
    @classmethod
    def _decimal_string(cls, raw: str) -> str:
        if not isinstance(raw, str):
            raise ValueError("quantity value must be a decimal string, not a JSON number")
        if QUANTITY_RE.fullmatch(raw) is None:
            raise ValueError(
                "quantity must match -?digits[.digits] exactly (ASCII, at most 18 integral "
                "and 9 fractional digits, no whitespace or exponent)"
            )
        return normalize_decimal_string(raw)


TypedValue = Annotated[
    TextValue | BooleanValue | IntegerValue | QuantityValue,
    Field(discriminator="kind"),
]


def normalize_decimal_string(raw: str) -> str:
    """Canonicalize a bounded decimal string without changing its value."""
    sign = ""
    body = raw
    if body.startswith("-"):
        sign = "-"
        body = body[1:]
    if "." in body:
        integral, fraction = body.split(".", 1)
    else:
        integral, fraction = body, ""
    integral = integral.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    if integral == "0" and fraction == "":
        return "0"
    text = integral + (f".{fraction}" if fraction else "")
    return sign + text


def quantity_decimal(value: str) -> Decimal:
    return Decimal(value)


@dataclass(frozen=True, slots=True)
class SelectorSpec:
    name: str
    kind: str
    unit: str | None
    description: str
    supports_ordering: bool

    @property
    def operators(self) -> tuple[str, ...]:
        """Operators exactly as permitted by the bound AST for this type."""
        if self.kind == "text":
            return ("eq", "in")
        if self.kind == "boolean":
            return ("eq",)
        if self.kind == "integer":
            return ("eq", "in", "lt", "lte", "gt", "gte")
        if self.kind == "quantity":
            return ("eq", "lt", "lte", "gt", "gte")
        raise ValueError(f"unsupported selector kind {self.kind!r}")


_SELECTORS = (
    SelectorSpec("component.manufacturer", "text", None, "Component manufacturer identity.", False),
    SelectorSpec("component.exact_part", "text", None, "Exact manufacturer part number.", False),
    SelectorSpec("component.family", "text", None, "Component family identity.", False),
    SelectorSpec("component.package", "text", None, "Package identity.", False),
    SelectorSpec("component.silicon_revision", "text", None, "Silicon revision identity.", False),
    SelectorSpec("operating.external_reset_used", "boolean", None, "External reset input used.", False),
    SelectorSpec("operating.reset_pulse_ns", "quantity", "ns", "Reset pulse width in nanoseconds.", True),
    SelectorSpec("operating.clock_hz", "quantity", "Hz", "Operating clock rate in hertz.", True),
    SelectorSpec("operating.supply_voltage_v", "quantity", "V", "Supply voltage in volts.", True),
    SelectorSpec("operating.temperature_c", "quantity", "degC", "Operating temperature in degrees Celsius.", True),
    SelectorSpec("firmware.initial_software_reset", "boolean", None, "Initial software reset performed.", False),
    SelectorSpec("firmware.revision_id_value", "integer", None, "Revision identifier register value.", True),
)

SELECTORS: dict[str, SelectorSpec] = {spec.name: spec for spec in _SELECTORS}

NONNEGATIVE_SELECTORS = {
    "operating.reset_pulse_ns",
    "operating.clock_hz",
    "operating.supply_voltage_v",
}
IDENTITY_SELECTORS = {
    "component.manufacturer",
    "component.exact_part",
    "component.family",
    "component.package",
    "component.silicon_revision",
}


class SelectorError(ValueError):
    """Selector/value mismatch with a stable diagnostic code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def get_selector(name: str) -> SelectorSpec:
    spec = SELECTORS.get(name)
    if spec is None:
        raise SelectorError("UNSUPPORTED_SELECTOR", f"selector {name!r} is not registered")
    return spec


def kind_of(value: BaseModel) -> str:
    return value.kind


def validate_value_for_selector(name: str, value: TypedValue) -> TypedValue:
    spec = get_selector(name)
    if value.kind != spec.kind:
        raise SelectorError(
            "TYPE_MISMATCH",
            f"selector {name!r} requires {spec.kind}, got {value.kind}",
        )
    if spec.kind == "text":
        assert isinstance(value, TextValue)
        if spec.name in IDENTITY_SELECTORS and not value.value.strip():
            raise SelectorError("BLANK_IDENTITY", f"selector {name!r} rejects blank identity text")
    if spec.kind == "quantity":
        assert isinstance(value, QuantityValue)
        if value.unit != spec.unit:
            raise SelectorError(
                "UNIT_MISMATCH",
                f"selector {name!r} requires unit {spec.unit!r}, got {value.unit!r}",
            )
        if spec.name in NONNEGATIVE_SELECTORS and quantity_decimal(value.value) < 0:
            raise SelectorError("NEGATIVE_QUANTITY", f"selector {name!r} rejects negative values")
    return value


def typed_value_key(value: TypedValue) -> tuple:
    if isinstance(value, QuantityValue):
        return ("quantity", value.value, value.unit)
    if isinstance(value, IntegerValue):
        return ("integer", value.value)
    if isinstance(value, BooleanValue):
        return ("boolean", value.value)
    return ("text", value.value)  # type: ignore[union-attr]


def typed_value_json(value: TypedValue) -> dict:
    return value.model_dump(mode="json")


def compare_order(op: str, left: TypedValue, right: TypedValue) -> bool:
    if isinstance(left, QuantityValue) and isinstance(right, QuantityValue):
        if left.unit != right.unit:
            raise SelectorError("UNIT_MISMATCH", "ordered comparison requires identical units")
        a, b = quantity_decimal(left.value), quantity_decimal(right.value)
    elif isinstance(left, IntegerValue) and isinstance(right, IntegerValue):
        a, b = left.value, right.value
    else:
        raise SelectorError("TYPE_MISMATCH", "ordered comparison requires quantity or integer values")
    if op == "lt":
        return a < b
    if op == "lte":
        return a <= b
    if op == "gt":
        return a > b
    if op == "gte":
        return a >= b
    raise SelectorError("UNSUPPORTED_OPERATOR", f"operator {op!r} is not an ordering operator")


def values_are_homogeneous(values: tuple[TypedValue, ...]) -> bool:
    if not values:
        return False
    kinds = {value.kind for value in values}
    if len(kinds) != 1:
        return False
    if kinds == {"quantity"}:
        units = {value.unit for value in values}  # type: ignore[union-attr]
        return len(units) == 1
    return True

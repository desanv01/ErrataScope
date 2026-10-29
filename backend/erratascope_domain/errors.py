"""Structured validation diagnostics for the ErrataScope domain package."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One stable, machine-readable validation finding."""

    code: str
    path: str
    message: str

    def as_dict(self) -> dict:
        return {"code": self.code, "path": self.path, "message": self.message}


class DomainValidationError(ValueError):
    """Raised when a bundle violates the bound domain contract.

    Carries every diagnostic collected for the failure so callers (CLI, tests)
    can report field paths instead of an opaque exception.
    """

    def __init__(self, diagnostics) -> None:
        self.diagnostics: tuple[Diagnostic, ...] = tuple(diagnostics)
        detail = "; ".join(
            f"{item.code} at {item.path}: {item.message}" for item in self.diagnostics
        )
        super().__init__(detail or "domain validation failed")

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.diagnostics)

    def as_list(self) -> list[dict]:
        return [item.as_dict() for item in self.diagnostics]


def raise_diagnostic(code: str, path: str, message: str) -> None:
    raise DomainValidationError([Diagnostic(code, path, message)])

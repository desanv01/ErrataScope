"""ErrataScope deterministic domain package (W02 domain v1).

Public API: ``parse_bundle`` validates a raw bundle into a sealed typed value,
and ``evaluate`` returns a canonical-hashed three-valued assessment result.
Importing this package never reads credentials, touches the network, or imports
the W01 parser/provider spike.
"""

from .evaluate import evaluate, resolve_selector, truth_and, truth_not, truth_or
from .models import (
    AssessmentInputBundle,
    AssessmentResult,
    ComponentIdentity,
    ComponentInstance,
    Contradiction,
    CoverageManifest,
    CoverageSummary,
    Dependency,
    DocumentVersion,
    EntryKey,
    EvaluationScope,
    FactSet,
    FactVersion,
    NodeTrace,
    ProductSnapshot,
    RuleResult,
    RuleVersion,
    SourceAnchor,
    SourceBaseline,
    Warning,
    parse_bundle,
    validate_bundle,
)
from .selectors import SELECTORS, SelectorSpec, get_selector

__all__ = [
    "SELECTORS",
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
    "SelectorSpec",
    "SourceAnchor",
    "SourceBaseline",
    "Warning",
    "evaluate",
    "get_selector",
    "parse_bundle",
    "resolve_selector",
    "truth_and",
    "truth_not",
    "truth_or",
    "validate_bundle",
]

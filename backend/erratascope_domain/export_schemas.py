"""Export JSON schemas and the selector registry for review evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import models
from .selectors import SELECTORS

SCHEMA_MODELS = (
    models.AssessmentInputBundle,
    models.AssessmentResult,
    models.ProductSnapshot,
    models.ComponentIdentity,
    models.ComponentInstance,
    models.EvaluationScope,
    models.DocumentVersion,
    models.SourceAnchor,
    models.FactVersion,
    models.FactSet,
    models.RuleVersion,
    models.CoverageManifest,
    models.EntryKey,
    models.SourceBaseline,
    models.NodeTrace,
    models.RuleResult,
    models.Dependency,
    models.Contradiction,
    models.Warning,
    models.CoverageSummary,
)


def _snake(name: str) -> str:
    output = []
    for index, char in enumerate(name):
        if char.isupper() and index and (not name[index - 1].isupper()):
            output.append("_")
        output.append(char.lower())
    return "".join(output)


def export(out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for model in SCHEMA_MODELS:
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        path = out_dir / f"{_snake(model.__name__)}.schema.json"
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path.name)
    registry = {
        name: {
            "kind": spec.kind,
            "unit": spec.unit,
            "supports_ordering": spec.supports_ordering,
            "operators": list(spec.operators),
            "description": spec.description,
        }
        for name, spec in sorted(SELECTORS.items())
    }
    (out_dir / "selector_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append("selector_registry.json")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="erratascope_domain.export_schemas")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    written = export(Path(args.out))
    print(f"wrote {len(written)} schema files to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

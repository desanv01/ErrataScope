"""Offline replay CLI: parse one JSON bundle, evaluate, write atomically.

Exit codes: 0 valid evaluation (including unknown results), 2 invalid input,
1 IO/runtime failure. A validation failure never replaces an existing output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from . import canonical
from .errors import DomainValidationError
from .evaluate import evaluate
from .models import parse_bundle


def _atomic_write(path: Path, payload: bytes) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with open(temp, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="erratascope_domain.replay")
    parser.add_argument("--input", required=True, help="bundle JSON path")
    parser.add_argument("--output", required=True, help="result JSON path")
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"IO error: input not found: {input_path}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"IO error reading input: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"invalid input JSON: {exc}", file=sys.stderr)
        return 2

    try:
        bundle = parse_bundle(raw)
        result = evaluate(bundle)
    except DomainValidationError as exc:
        for item in exc.diagnostics:
            print(f"{item.code} at {item.path}: {item.message}", file=sys.stderr)
        return 2

    payload = canonical.normalized_result_bytes(canonical.dump_model(result))
    try:
        _atomic_write(output_path, payload)
    except OSError as exc:
        print(f"IO error writing output: {exc}", file=sys.stderr)
        return 1

    applicable = sum(1 for rule in result.rules if rule.applicability == "applicable")
    unknown = sum(1 for rule in result.rules if rule.applicability == "unknown")
    not_applicable = len(result.rules) - applicable - unknown
    print(
        f"result_hash={result.result_hash} rules={len(result.rules)} "
        f"applicable={applicable} unknown={unknown} not_applicable={not_applicable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

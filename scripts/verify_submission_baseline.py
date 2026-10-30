"""Verify the S01 submission assignment without rewriting historical W baselines."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/submission/S01-baseline.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--starting", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("assignment") != "S01-revision-1" or manifest.get("schema_version") != 1:
            raise ValueError("unsupported submission baseline")
        records = list(manifest["protected_files"])
        if args.starting:
            records += manifest["starting_inventory"]
        if not records or not manifest["protected_files"] or not manifest["starting_inventory"]:
            raise ValueError("empty inventory")
        errors = []
        seen = set()
        for row in records:
            rel = Path(row["path"])
            if rel.is_absolute() or ".." in rel.parts or row["path"] in seen:
                raise ValueError("unsafe or duplicate inventory path")
            seen.add(row["path"])
            path = ROOT / rel
            if not path.is_file() or path.is_symlink():
                errors.append(row["path"] + ": missing/nonregular")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                errors.append(row["path"] + ": changed")
        approval = json.loads((ROOT / "docs/submission/ui/approval.json").read_text(encoding="utf-8"))
        if approval["decision"] != "Approve this direction":
            errors.append("visual approval missing")
        print(json.dumps({"status": "FAIL" if errors else "PASS", "assignment": manifest["assignment"],
                          "mode": "starting" if args.starting else "protected", "checked": len(records),
                          "errors": errors}, indent=2))
        return 2 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

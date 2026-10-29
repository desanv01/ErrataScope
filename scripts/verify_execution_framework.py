"""Read-only framework/link/hash checks. Standard library only; no application tests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="docs/execution/baselines/W01-baseline.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    framework = root / "docs" / "execution"
    errors: list[str] = []
    manifest_path = root / args.baseline
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "errors": [f"Cannot read baseline: {type(exc).__name__}"]}))
        return 1
    phases = sorted((framework / "phases").glob("P*.md"))
    packets = sorted((framework / "packets").glob("W*.md"))
    contracts = sorted((framework / "contracts").glob("*.md"))
    expected_phases = {f"P{i}" for i in range(11)}
    expected_packets = {f"W{i:02d}" for i in range(1, 11)}
    if {p.name.split("-")[0] for p in phases} != expected_phases:
        errors.append("Phase set differs from P0-P10")
    if {p.name.split("-")[0] for p in packets} != expected_packets:
        errors.append("Packet set differs from W01-W10")
    if len(contracts) != 8:
        errors.append(f"Expected 8 shared contracts; found {len(contracts)}")

    markdown_files = sorted(framework.rglob("*.md"))
    checked_links = 0
    for path in markdown_files:
        content = path.read_text(encoding="utf-8")
        if content.count("```") % 2:
            errors.append(f"Unbalanced code fences: {path.relative_to(root)}")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            clean = unquote(target.split("#", 1)[0].strip("<>"))
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                errors.append(f"Broken local link: {path.relative_to(root)} -> {target}")
            checked_links += 1

    for path in packets:
        content = path.read_text(encoding="utf-8")
        packet_id = path.name.split("-")[0]
        legacy = "READY_TO_DISPATCH" if packet_id == "W01" else "PLANNED_NOT_DISPATCHABLE"
        expected = manifest.get("dispatch_states", {}).get(packet_id, legacy)
        if f"Dispatch state: **{expected}**" not in content:
            errors.append(f"Unexpected initial dispatch state: {path.name}")
    ui_gate = (framework / "UI_APPROVAL_GATE.md").read_text(encoding="utf-8")
    if "PENDING" not in ui_gate or "imagegen" not in ui_gate:
        errors.append("Initial human UI/imagegen approval gate is missing")

    checked_hashes = 0
    try:
        if manifest.get("schema_version") not in {1, 2} or manifest.get("packet") not in expected_packets:
            errors.append("Unsupported baseline manifest")
        if manifest.get("schema_version") == 2:
            states = manifest.get("dispatch_states", {})
            allowed_states = {"READY_TO_DISPATCH", "PLANNED_NOT_DISPATCHABLE", "DEFERRED_LIVE", "ACCEPTED"}
            if set(states) != expected_packets or any(value not in allowed_states for value in states.values()):
                errors.append("Version 2 baseline must bind every packet's supported dispatch state")
        for record in manifest["files"]:
            relative = Path(record["path"])
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(root):
                errors.append("Baseline contains a path outside the project")
                continue
            if not path.is_file():
                errors.append(f"Missing protected file: {relative}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != record["sha256"]:
                errors.append(f"Protected file changed: {relative}")
            checked_hashes += 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Cannot validate baseline: {type(exc).__name__}: {exc}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "scope": "Execution framework and protected hashes; not application or provider acceptance",
        "phases": len(phases),
        "packets": len(packets),
        "contracts": len(contracts),
        "markdown_files": len(markdown_files),
        "local_links_checked": checked_links,
        "protected_hashes_checked": checked_hashes,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

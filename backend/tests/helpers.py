"""Shared builders for W02 tests and synthetic fixtures.

All data is original SYNTHETIC fixture material: no manufacturer documents,
geometry, or claims are reproduced. Expected truth values in tests/fixtures are
explicit literals, never computed by the evaluator under test.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from erratascope_domain import evaluate, parse_bundle
from erratascope_domain.canonical import seal_fact_set, seal_snapshot
from erratascope_domain.models import (
    AssessmentInputBundle,
    ComponentIdentity,
    ComponentInstance,
    CoverageManifest,
    DocumentVersion,
    EntryKey,
    EvaluationScope,
    FactSet,
    FactVersion,
    ProductSnapshot,
    RuleVersion,
    SourceAnchor,
    SourceBaseline,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FIXTURE_DIR = BACKEND_ROOT / "fixtures" / "w02"
SYNTHETIC_SOURCE = FIXTURE_DIR / "synthetic_sources" / "synthetic-errata.txt"
SYNTHETIC_TEXT = (
    "SYNTHETIC FIXTURE — NOT A MANUFACTURER DOCUMENT\n"
    "Original text authored for W02 deterministic-domain tests.\n"
    "Entry 1.1: a synthetic condition applies when external reset is used and the\n"
    "reset pulse is shorter than 20 ns on silicon revision B, unless an initial\n"
    "software reset has been performed.\n"
)
DOC_SHA256 = hashlib.sha256(SYNTHETIC_TEXT.encode("utf-8")).hexdigest()

PROJECT = uuid.UUID(int=1)
DOCUMENT = uuid.UUID(int=2)
RULE = uuid.UUID(int=3)
FACT_SET = uuid.UUID(int=4)
COVERAGE = uuid.UUID(int=5)
BASELINE = uuid.UUID(int=6)
SNAPSHOT = uuid.UUID(int=8)
FIRMWARE_BUILD = uuid.UUID(int=9)
OPERATING_PROFILE = uuid.UUID(int=10)
SUBJECT = uuid.UUID(int=7)
OTHER_COMPONENT = uuid.UUID(int=17)
OTHER_BUILD = uuid.UUID(int=18)
OTHER_PROFILE = uuid.UUID(int=19)
ANCHOR = "synth-erratum:p00:000"
ANCHOR_2 = "synth-erratum:p00:001"


def uuid_for(index: int) -> uuid.UUID:
    return uuid.UUID(int=1000 + index)


def document(
    document_id: uuid.UUID = DOCUMENT,
    *,
    project: uuid.UUID = PROJECT,
    synthetic: bool = True,
    authority: str = "synthetic",
    sha256: str = DOC_SHA256,
) -> DocumentVersion:
    return DocumentVersion(
        id=document_id,
        project_id=project,
        document_id="SYNTH-ERRATA-1",
        revision="Rev A",
        manufacturer=None,
        source_url=None,
        document_sha256=sha256,
        authority=authority,
        synthetic=synthetic,
    )


def anchor(
    anchor_id: str = ANCHOR,
    *,
    document_version_id: uuid.UUID = DOCUMENT,
    sha256: str = DOC_SHA256,
    geometry_kind: str = "synthetic_not_located",
    text: str = "Synthetic anchor text for a bounded errata condition.",
    bbox=None,
    dimensions=None,
    rotation: int = 0,
) -> SourceAnchor:
    width, height = dimensions if dimensions else (None, None)
    return SourceAnchor(
        anchor_id=anchor_id,
        document_version_id=document_version_id,
        document_sha256=sha256,
        page_index=0,
        printed_page_label=None,
        section="1",
        text=text,
        bbox=bbox,
        page_width_pt=width,
        page_height_pt=height,
        page_rotation=rotation,
        parser_name="synthetic-fixture",
        parser_version="1",
        geometry_kind=geometry_kind,
    )


def identity(
    manufacturer: str | None = "SYNTH",
    exact_part: str | None = "SYNTH-1",
    family: str | None = "SYNTH-FAMILY",
    package: str | None = "SYNTH-PKG",
    silicon_revision: str | None = "B",
    evidence_refs=(ANCHOR,),
) -> ComponentIdentity:
    return ComponentIdentity(
        manufacturer=manufacturer,
        exact_part=exact_part,
        family=family,
        package=package,
        silicon_revision=silicon_revision,
        evidence_refs=tuple(evidence_refs),
    )


def instance(
    component_id: uuid.UUID = SUBJECT,
    component_identity: ComponentIdentity | None = None,
    *,
    project_id: uuid.UUID = PROJECT,
) -> ComponentInstance:
    return ComponentInstance(
        id=component_id,
        project_id=project_id,
        identity=component_identity or identity(),
    )


def scope(
    *,
    subject: uuid.UUID = SUBJECT,
    firmware_build: uuid.UUID = FIRMWARE_BUILD,
    operating_profile: uuid.UUID = OPERATING_PROFILE,
    snapshot: uuid.UUID = SNAPSHOT,
) -> EvaluationScope:
    return EvaluationScope(
        project_id=PROJECT,
        snapshot_id=snapshot,
        subject_id=subject,
        firmware_build_id=firmware_build,
        operating_profile_id=operating_profile,
    )


def snapshot(instances=None, *, snap_id: uuid.UUID = SNAPSHOT) -> ProductSnapshot:
    if instances is None:
        instances = (instance(), instance(OTHER_COMPONENT, identity(silicon_revision="A")))
    raw = ProductSnapshot(
        id=snap_id,
        project_id=PROJECT,
        product_name="Synthetic W02 board",
        board_revision="A",
        firmware_build_id=FIRMWARE_BUILD,
        operating_profile_id=OPERATING_PROFILE,
        component_instances=tuple(instances),
        predecessor_id=None,
        content_hash="0" * 64,
    )
    return seal_snapshot(raw)


def fact(
    selector: str,
    value,
    *,
    fact_scope: EvaluationScope | None = None,
    review_state: str = "accepted",
    evidence_refs=(ANCHOR,),
    fact_id: uuid.UUID | None = None,
    origin: str = "declared",
) -> FactVersion:
    resolved_scope = fact_scope or scope()
    if fact_id is None:
        marker = f"{selector}|{json.dumps(value, sort_keys=True)}|{resolved_scope.model_dump_json()}"
        fact_id = uuid.uuid5(uuid.NAMESPACE_URL, marker)
    return FactVersion(
        id=fact_id,
        scope=resolved_scope,
        selector=selector,
        value=value,
        origin=origin,
        evidence_refs=tuple(evidence_refs),
        review_state=review_state,
    )


def fact_set(facts) -> FactSet:
    raw = FactSet(
        id=FACT_SET,
        project_id=PROJECT,
        fact_versions=tuple(facts),
        content_hash="0" * 64,
    )
    return seal_fact_set(raw)


def eq(selector: str, value: dict, anchors=(ANCHOR,)) -> dict:
    return {"op": "eq", "selector": selector, "value": value, "anchor_ids": list(anchors)}


def in_(selector: str, values, anchors=(ANCHOR,)) -> dict:
    return {"op": "in", "selector": selector, "values": list(values), "anchor_ids": list(anchors)}


def lt(selector: str, value: dict, anchors=(ANCHOR,)) -> dict:
    return {"op": "lt", "selector": selector, "value": value, "anchor_ids": list(anchors)}


def lte(selector: str, value: dict, anchors=(ANCHOR,)) -> dict:
    return {"op": "lte", "selector": selector, "value": value, "anchor_ids": list(anchors)}


def gt(selector: str, value: dict, anchors=(ANCHOR,)) -> dict:
    return {"op": "gt", "selector": selector, "value": value, "anchor_ids": list(anchors)}


def gte(selector: str, value: dict, anchors=(ANCHOR,)) -> dict:
    return {"op": "gte", "selector": selector, "value": value, "anchor_ids": list(anchors)}


def all_(*children) -> dict:
    return {"op": "all", "children": list(children)}


def any_(*children) -> dict:
    return {"op": "any", "children": list(children)}


def not_(child: dict) -> dict:
    return {"op": "not", "child": child}


def constant(value: bool, anchors=(ANCHOR,), rationale="Synthetic reviewed unconditional test constant.") -> dict:
    return {
        "op": "constant",
        "value": value,
        "anchor_ids": list(anchors),
        "review_rationale": rationale,
    }


def boolean(value: bool) -> dict:
    return {"kind": "boolean", "value": value}


def text(value: str) -> dict:
    return {"kind": "text", "value": value}


def quantity(value: str, unit: str = "ns") -> dict:
    return {"kind": "quantity", "value": value, "unit": unit}


def integer(value: int) -> dict:
    return {"kind": "integer", "value": value}


def rule(
    *,
    rule_id: uuid.UUID = RULE,
    entry_id: str = "1.1",
    target=None,
    trigger=None,
    exceptions=None,
    document_version_id: uuid.UUID = DOCUMENT,
    anchors=(ANCHOR,),
    review_state: str = "accepted",
    reviewer_id: str | None = "synthetic-reviewer",
    consequence: str = "Synthetic condition consequence for test purposes.",
) -> RuleVersion:
    exception_tuple = (
        tuple(exceptions)
        if exceptions is not None
        else (eq("firmware.initial_software_reset", boolean(True)),)
    )
    return RuleVersion(
        id=rule_id,
        project_id=PROJECT,
        document_version_id=document_version_id,
        entry_id=entry_id,
        review_state=review_state,
        reviewer_id=reviewer_id,
        target=target or eq("component.silicon_revision", text("B")),
        trigger=trigger
        or all_(
            eq("operating.external_reset_used", boolean(True)),
            lt("operating.reset_pulse_ns", quantity("20", "ns")),
        ),
        exceptions=exception_tuple,
        consequence=consequence,
        workaround_documentation=None,
        workaround_restrictions=None,
        anchors=tuple(anchors),
    )


def coverage(
    entries=None,
    *,
    inventory_complete: bool = True,
    unsupported=(),
    failed=(),
    doc_ids=(DOCUMENT,),
) -> CoverageManifest:
    if entries is None:
        entries = (EntryKey(document_version_id=DOCUMENT, entry_id="1.1"),)
    entries = tuple(entries)
    return CoverageManifest(
        id=COVERAGE,
        project_id=PROJECT,
        document_version_ids=tuple(doc_ids),
        inventory_complete=inventory_complete,
        discovered=entries + tuple(unsupported),
        supported=entries,
        reviewed=entries,
        assessed=entries,
        failed=tuple(failed),
        unsupported=tuple(unsupported),
        selected=entries,
    )


def baseline(rule_ids=(RULE,), doc_ids=(DOCUMENT,)) -> SourceBaseline:
    return SourceBaseline(
        id=BASELINE,
        project_id=PROJECT,
        document_version_ids=tuple(doc_ids),
        rule_version_ids=tuple(rule_ids),
        coverage_manifest_id=COVERAGE,
    )


def build_raw(
    *,
    facts=None,
    rules=None,
    documents=None,
    anchors=None,
    coverage_manifest=None,
    snapshot_model=None,
    scope_model=None,
    baseline_model=None,
) -> dict:
    docs = tuple(documents) if documents is not None else (document(),)
    anchors_tuple = tuple(anchors) if anchors is not None else (anchor(), anchor(ANCHOR_2, text="Second synthetic anchor."))
    facts_tuple = tuple(facts) if facts is not None else (
        fact("component.silicon_revision", text("B")),
        fact("operating.external_reset_used", boolean(True)),
        fact("operating.reset_pulse_ns", quantity("10", "ns")),
        fact("firmware.initial_software_reset", boolean(False)),
    )
    rules_tuple = tuple(rules) if rules is not None else (rule(),)
    bundle = AssessmentInputBundle(
        project_id=PROJECT,
        scope=scope_model or scope(),
        snapshot=snapshot_model or snapshot(),
        fact_set=fact_set(facts_tuple),
        source_baseline=baseline_model or baseline(tuple(item.id for item in rules_tuple)),
        documents=docs,
        anchors=anchors_tuple,
        rules=rules_tuple,
        coverage=coverage_manifest or coverage(),
    )
    return json.loads(bundle.model_dump_json())


def evaluate_raw(raw: dict):
    return evaluate(parse_bundle(raw))


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@contextmanager
def temp_dir(prefix: str = "tmp"):
    """Workspace-local scratch directory with default (accessible) permissions.

    The Windows sandbox denies access to directories created with POSIX mode
    0700 (the tempfile.mkdtemp default), so tests create their own 0777 dirs.
    """
    base = PROJECT_ROOT / ".local" / "w02"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{prefix}-{uuid.uuid4().hex[:10]}"
    path.mkdir(parents=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def write_fixture(name: str, raw: dict) -> Path:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / name
    path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return path


def run_replay(input_path: Path, output_path: Path) -> subprocess.CompletedProcess:
    env = {
        "PYTHONPATH": str(BACKEND_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": "",
    }
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "erratascope_domain.replay",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        check=False,
        text=True,
        env={**env, "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")},
        cwd=str(PROJECT_ROOT),
    )

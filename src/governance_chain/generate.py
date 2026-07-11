#!/usr/bin/env python3
"""
Orchestrator: build the entire Full Spectrum governance object chain from a
single raw business input, then validate each artifact against the vendored
protocol schemas and render a Markdown report.
"""
import json
import os
from typing import Any, Dict, Tuple

from .adapters import get_adapter, DEFAULT_TIMESTAMP, _split_raw_id
from .engine import run
from . import validator
from .render import render

ARTIFACT_KINDS = (
    "governance-event",
    "canonical-context",
    "cell-manifest",
    "output-envelope",
    "enterprise-writeback",
)


def build_chain(raw_doc: Dict[str, Any], timestamp: str = None) -> Tuple[Dict[str, Any], str, str]:
    adapter = get_adapter(raw_doc.get("adapter_id"))
    ts = timestamp or DEFAULT_TIMESTAMP

    ge = adapter.build_governance_event(raw_doc, timestamp=ts)
    event_id = ge["event_id"]
    cc = adapter.build_canonical_context(raw_doc, event_id, timestamp=ts)
    cell = adapter.build_cell_manifest(raw_doc)

    stem, num = _split_raw_id(raw_doc["raw_input"]["raw_input_id"])
    run_id = f"run_{stem}_{num}"
    audit_id = f"audit_{stem}_{num}"

    envelope, ew = run(cc, cell, adapter, run_id, audit_id)

    artifacts = {
        "governance-event": ge,
        "canonical-context": cc,
        "cell-manifest": cell,
        "output-envelope": envelope,
        "enterprise-writeback": ew,
    }

    # validate every artifact and record the result in the output envelope
    all_ok = True
    for kind in ARTIFACT_KINDS:
        schema_file = validator.map_schema_for_filename(kind + ".json")
        schema = validator.load_schema(schema_file)
        ok, _ = validator.validate_instance(artifacts[kind], schema)
        if not ok:
            all_ok = False
    artifacts["output-envelope"]["conformance"]["schema_valid"] = all_ok

    return artifacts, run_id, audit_id


def write_chain(out_dir: str, raw_doc: Dict[str, Any], timestamp: str = None) -> Tuple[Dict[str, str], Dict[str, Any]]:
    artifacts, run_id, audit_id = build_chain(raw_doc, timestamp=timestamp)
    os.makedirs(out_dir, exist_ok=True)
    suffix = raw_doc["adapter_id"]
    writes = {}
    for kind in ARTIFACT_KINDS:
        fname = f"{kind}.{suffix}.json"
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(artifacts[kind], f, ensure_ascii=False, indent=2)
            f.write("\n")
        writes[kind] = path
    report = render(raw_doc, artifacts, run_id, audit_id)
    report_path = os.path.join(out_dir, f"report.{suffix}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    writes["report"] = report_path
    return writes, artifacts

#!/usr/bin/env python3
"""
Generate deterministic local API sample artifacts for public inspection.

This script is intentionally local-first:
- starts the FastAPI app in-process via TestClient
- writes machine-readable JSON samples into examples/api-samples/
- avoids any external network or production dependency
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.server import create_app  # noqa: E402


OUT_DIR = PROJECT_ROOT / "examples" / "api-samples"
SCENARIO_PATH = PROJECT_ROOT / "examples" / "scenario_refund_conflict.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="fse_api_samples_"))
    db_path = temp_root / "sample.db"

    try:
        app = create_app(db_path=str(db_path))
        client = TestClient(app)
        scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

        evaluate_resp = client.post("/api/v1/evaluate", json={"scenario": scenario, "seed": 42})
        evaluate_resp.raise_for_status()
        evaluate_body = evaluate_resp.json()

        decision_id = evaluate_resp.headers["x-decision-id"]
        runestone_id = evaluate_body["runestone"]["runestone_id"]

        decision_resp = client.get(f"/api/v1/decisions/{decision_id}")
        decision_resp.raise_for_status()

        runestone_resp = client.get(f"/api/v1/audit/runestones/{runestone_id}")
        runestone_resp.raise_for_status()

        decision_list_resp = client.get("/api/v1/audit/decisions?limit=5&offset=0")
        decision_list_resp.raise_for_status()

        runestone_list_resp = client.get("/api/v1/audit/runestones?limit=5&offset=0")
        runestone_list_resp.raise_for_status()

        risk_alert_equivalent = {
            "sample_type": "engine-risk-vector-preview",
            "note": "The engine currently exposes RiskVector as the machine-readable local risk object. Protocol-layer RiskAlert remains a higher-level profile.",
            "simulation_id": evaluate_body["simulation_id"],
            "decision_id": decision_id,
            "runestone_id": runestone_id,
            "risk_level": evaluate_body["fshi"]["risk_level"],
            "risk_vector": evaluate_body["risk_vector"],
            "validation": evaluate_body["validation"],
        }

        audit_trace_equivalent = {
            "sample_type": "engine-audit-trace-preview",
            "note": "The engine currently persists local audit records as decision/runestone storage artifacts. This preview bundles the decision identity, the persisted runestone identity, and the evaluation outcome.",
            "decision_id": decision_id,
            "runestone_id": runestone_id,
            "created_from": "POST /api/v1/evaluate",
            "decision_record": decision_resp.json(),
        }

        _write_json(OUT_DIR / "evaluate-response-refund-seed42.json", evaluate_body)
        _write_json(OUT_DIR / "risk-vector-preview-refund-seed42.json", risk_alert_equivalent)
        _write_json(OUT_DIR / "runestone-refund-seed42.json", runestone_resp.json())
        _write_json(OUT_DIR / "audit-trace-preview-refund-seed42.json", audit_trace_equivalent)
        _write_json(OUT_DIR / "audit-decision-list-sample.json", decision_list_resp.json())
        _write_json(OUT_DIR / "audit-runestone-list-sample.json", runestone_list_resp.json())

        readme = """# API Sample Pack

This directory stores deterministic local API artifacts generated from:

- `POST /api/v1/evaluate`
- `GET /api/v1/decisions/{decision_id}`
- `GET /api/v1/audit/runestones/{runestone_id}`
- `GET /api/v1/audit/decisions`
- `GET /api/v1/audit/runestones`

Files:

- `evaluate-response-refund-seed42.json`
- `risk-vector-preview-refund-seed42.json`
- `runestone-refund-seed42.json`
- `audit-trace-preview-refund-seed42.json`
- `audit-decision-list-sample.json`
- `audit-runestone-list-sample.json`

Notes:

- `risk-vector-preview-*` is the current engine-layer equivalent of a future protocol-level `RiskAlert`.
- `audit-trace-preview-*` is the current engine-layer equivalent of a local `AuditTrace` preview.
- These artifacts are generated locally and do not imply network governance completeness.

Regenerate:

```bash
python scripts/generate_api_samples.py
```
"""
        (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
        return 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

# API Sample Pack

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

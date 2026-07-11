# OpenAPI Export

This directory stores the machine-readable API contract for `full-spectrum-engine`.

Current contract files:

- `full-spectrum-engine-openapi-0.9.0a1.json`
- `latest.json`

These files are exported from the actual FastAPI app, not hand-written.

## Why this exists

The repository now has three parallel API entry surfaces:

1. runtime Swagger UI at `/docs`
2. human-readable docs such as `docs/api-reference-v0.9.md`
3. machine-readable OpenAPI export in this folder

This third surface allows:

- API review without starting the server
- contract diffing between versions
- future schema / SDK generation
- external verification that docs and runtime agree

## How to regenerate

```bash
pip install -e ".[api]"
python scripts/export_openapi.py
```

## Current boundary

This OpenAPI file reflects the **local-first development API** only.

It does not mean:

- production authentication exists
- network governance is complete
- Cell Manifest is integrated
- protocol-network interoperability is live

It means the current engine-side HTTP contract is explicit and can be reviewed.

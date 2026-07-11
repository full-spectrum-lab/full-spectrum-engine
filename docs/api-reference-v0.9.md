# API Quick Reference (`v0.9.0a1`)

This page documents the local REST API exposed by `full-spectrum-engine`.

The API is for:

- local development
- internal validation
- sample inspection
- protocol-facing experimentation

It is **not** a production-hardened deployment interface.

## Start the API

```bash
pip install -e ".[api]"
python -m src.api.server
```

Default URL:

```text
http://127.0.0.1:8000
```

Interactive docs:

```text
http://127.0.0.1:8000/docs
```

Machine-readable spec:

```text
docs/openapi/latest.json
```

## Version and surface

Current API version:

```text
0.9.0a1
```

Current engine version:

```text
0.9.0-alpha
```

Publicly visible endpoints:

- `GET /api/v1/health`
- `POST /api/v1/evaluate`
- `POST /api/v1/runestone`
- `GET /api/v1/decisions/{decision_id}`
- `GET /api/v1/audit/decisions`
- `GET /api/v1/audit/runestones`
- `GET /api/v1/audit/runestones/{runestone_id}`
- `DELETE /api/v1/audit/decisions`

## Common response headers

Most responses include:

- `X-Storage-Mode: sqlite-persistent`
- `X-Full-Spectrum-Notice: local-dev-only`
- `X-Production-Ready: false`

Some responses may also include:

- `X-Decision-Id`
- `X-Input-Metrics-Persisted`

See [API fields and error codes](api-fields-and-errors-v0.9.md) for interpretation details.

## 1. Health

### Request

```http
GET /api/v1/health
```

### Purpose

Returns API version, engine version, registered adapters, storage mode, DB metadata, and network exposure level.

### Typical response fields

- `status`
- `version`
- `engine_version`
- `registered_adapters`
- `storage_mode`
- `network_exposure`
- `db_path`
- `db_size_bytes`
- `decision_count`
- `runestone_count`
- `ttl_days`
- `max_records`

## 2. Evaluate

### Request

```http
POST /api/v1/evaluate
Content-Type: application/json
```

This endpoint supports two mutually exclusive request modes.

### Mode A: direct scenario

```json
{
  "scenario": {
    "simulation_id": "CASE001_REFUND_CONFLICT",
    "input_query": "User requests a refund after merchant refusal.",
    "sensitivity_level": "high",
    "enterprise_id": "ecommerce-platform",
    "rule_version": "v0.3",
    "initial_state": {
      "survival": 0.72,
      "coordination": 0.45,
      "meaning": 0.55
    },
    "agents": [
      {"type": "AI", "weight": 0.40},
      {"type": "Human", "weight": 0.20},
      {"type": "Regulator", "weight": 0.25},
      {"type": "Enterprise", "weight": 0.15}
    ],
    "weights": {
      "survival": 0.40,
      "coordination": 0.35,
      "meaning": 0.25
    },
    "ess_horizon": 5,
    "ess_candidates": 10,
    "conflict_density": 0.6,
    "reversibility": 0.4,
    "diffusivity": 0.5
  },
  "seed": 42
}
```

### Mode B: adapter mode

```json
{
  "industry": "ecommerce_customer_service",
  "metrics": {
    "dispute_rate": 0.62,
    "user_sentiment_drop": 0.70,
    "promise_mismatch": 0.55
  },
  "seed": 42,
  "simulation_id": "CASE_ECOM_001",
  "input_query": "Customer service quality inspection sample",
  "sensitivity_level": "medium",
  "enterprise_id": "demo-enterprise",
  "rule_version": "v0.4",
  "include_input_metrics": false
}
```

### Rules

- direct mode and adapter mode cannot be used together
- one of them must be complete
- adapter mode requires `industry` and `metrics`

### Typical response body

The response body stays close to CLI output. Typical top-level keys:

- `simulation_id`
- `timestamp`
- `input_query`
- `sensitivity_level`
- `initial_state`
- `final_state`
- `fshi`
- `ess`
- `validation`
- `risk_vector`
- `runestone`
- `causal_chain`

### Typical status codes

- `200` success
- `422` malformed request or invalid adapter input
- `500` internal simulation / storage failure

## 3. Runestone

### Request

```http
POST /api/v1/runestone
Content-Type: application/json
```

### Purpose

Generates a standalone `Runestone` audit token without running the full simulation pipeline.

### Typical status codes

- `200` success
- `422` invalid or incomplete `risk_vector`
- `500` persistence failure

## 4. Decision detail

### Request

```http
GET /api/v1/decisions/{decision_id}
```

### Purpose

Returns a previously stored decision body.

## 5. Decision audit list

### Request

```http
GET /api/v1/audit/decisions?limit=20&offset=0
```

### Query parameters

- `limit`
- `offset`
- `adapter`
- `since`

## 6. Runestone audit list

### Request

```http
GET /api/v1/audit/runestones?limit=20&offset=0
```

### Query parameters

- `limit`
- `offset`
- `since`

## 7. Single runestone lookup

### Request

```http
GET /api/v1/audit/runestones/{runestone_id}
```

## 8. Data cleanup

### Request

```http
DELETE /api/v1/audit/decisions?confirm=true&before=2026-01-01T00:00:00Z
```

or

```http
DELETE /api/v1/audit/decisions?confirm=true&all=true
```

### Safety rules

- local bind only
- requires `confirm=true`
- requires either `before=...` or `all=true`

## Related docs

- [OpenAPI export](openapi/README.md)
- [API fields and error codes](api-fields-and-errors-v0.9.md)
- [Explainability walkthrough](explainability-walkthrough-v0.9.md)
- [Troubleshooting](troubleshooting.md)

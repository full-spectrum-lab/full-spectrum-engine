# API Quick Reference (`v0.8.0-beta`)

This page documents the local REST API exposed by `full-spectrum-engine`.

The API is for:

- local development
- internal validation
- sample inspection
- protocol-facing experimentation

It is **not** a production-hardened deployment interface.

---

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

---

## Version and surface

Current API version:

```text
0.7.2a1
```

Current engine version:

```text
0.7.2-alpha
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

---

## Common response headers

Most responses include:

- `X-Storage-Mode: sqlite-persistent`
- `X-Full-Spectrum-Notice: local-dev-only`
- `X-Production-Ready: false`

Some responses may also include:

- `X-Decision-Id`
- `X-Input-Metrics-Persisted`

---

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

---

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

---

## 3. Runestone

### Request

```http
POST /api/v1/runestone
Content-Type: application/json
```

### Example

```json
{
  "decision": "W3",
  "reason": {
    "enterprise_id": "demo-enterprise",
    "rule_version": "v0.4"
  },
  "risk_vector": {
    "survival_impact": 0.42,
    "trust_impact": 0.68,
    "meaning_impact": 0.31,
    "reversibility": 0.55,
    "explainability": 0.73,
    "diffusivity": 0.48,
    "urgency": 0.61,
    "uncertainty": 0.29
  },
  "seed": 42
}
```

### Purpose

Generates a standalone `Runestone` audit token without running the full simulation pipeline.

### Typical status codes

- `200` success
- `422` invalid or incomplete `risk_vector`
- `500` persistence failure

---

## 4. Decision detail

### Request

```http
GET /api/v1/decisions/{decision_id}
```

### Purpose

Returns a previously stored decision body.

### Typical status codes

- `200` found
- `404` not found

---

## 5. Decision audit list

### Request

```http
GET /api/v1/audit/decisions?limit=20&offset=0
```

### Optional filters

- `limit`
- `offset`
- `adapter`
- `since`

### Purpose

Returns paginated decision audit metadata.

### Typical response shape

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

---

## 6. Runestone audit list

### Request

```http
GET /api/v1/audit/runestones?limit=20&offset=0
```

### Optional filters

- `limit`
- `offset`
- `decision_id`
- `since`

---

## 7. Runestone detail

### Request

```http
GET /api/v1/audit/runestones/{runestone_id}
```

### Typical status codes

- `200` found
- `404` not found

---

## 8. Audit cleanup

### Request

```http
DELETE /api/v1/audit/decisions
```

### Guard rails

This endpoint is intentionally restricted.

It requires:

- local bind only
- `confirm=true`
- either `before=...` or `all=true`

### Why

This is a local maintenance path, not a casual destructive endpoint.

### Typical failure codes

- `403` not running on local bind
- `422` missing confirmation or range selector

---

## Error model summary

### `422 Unprocessable Content`

Means the request structure or payload is wrong.

Common causes:

- request mode collision in `/evaluate`
- missing adapter metrics
- missing `risk_vector` fields in `/runestone`

### `404 Not Found`

Means the requested decision or runestone ID does not exist.

### `500 Internal Server Error`

Means the engine runtime or persistence layer failed unexpectedly.

Use [troubleshooting.md](troubleshooting.md) for first-pass diagnosis.

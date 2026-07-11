# API Quick Contract (`v1.0.0`)

This page is the shortest public contract for `full-spectrum-engine v1.0.0`.

If a new developer reads only one API page before integrating the engine, it should be this one.

---

## What v1.0.0 guarantees

`full-spectrum-engine v1.0.0` guarantees a stable local-first contract for:

- deterministic seeded simulation
- structured REST output
- stable audit record lookup
- structured error responses
- documented non-goals

It does **not** guarantee:

- enterprise production orchestration
- protocol network interoperability
- final legal or compliance judgement
- direct business action execution

---

## API base

Default local server:

```text
http://127.0.0.1:8000
```

API prefix:

```text
/api/v1
```

Docs:

- Swagger UI: `/docs`
- ReDoc: `/redoc`

---

## Stable endpoints in v1.0.0

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Service health, adapter list, local exposure status |
| `POST` | `/api/v1/evaluate` | Run a deterministic simulation in direct mode or adapter mode |
| `POST` | `/api/v1/runestone` | Generate a standalone `Runestone` audit token |
| `GET` | `/api/v1/decisions/{id}` | Read a persisted decision record |
| `GET` | `/api/v1/audit/decisions` | List persisted decision records |
| `GET` | `/api/v1/audit/runestones` | List persisted runestones |
| `GET` | `/api/v1/audit/runestones/{id}` | Read a persisted runestone |
| `DELETE` | `/api/v1/audit/decisions` | Cleanup persisted decision data with safety valves |

---

## Request modes

`POST /api/v1/evaluate` supports two stable modes:

### 1. Direct mode

You submit a fully assembled synthetic scenario.

Use this when:

- you already have a scenario object
- you want exact reproducibility against a known sample

### 2. Adapter mode

You submit:

- `industry`
- `metrics`
- optional `include_input_metrics`

Use this when:

- you want the engine to map structured business metrics into a scenario first
- you are testing an industry adapter such as e-commerce or logistics

Do **not** send both direct mode and adapter mode fields in the same request.

---

## Output objects you can rely on

The public contract centers on four output families:

1. **simulation result**
2. **RiskVector**
3. **Runestone**
4. **audit records**

### Simulation result

Contains the core engine output, including:

- FSHI / state information
- risk vector fields
- treatment path suggestion
- structured explanation fields

### RiskVector

The stable governance-risk dimensions are:

- `survival_impact`
- `trust_impact`
- `meaning_impact`
- `reversibility`
- `explainability`
- `diffusivity`
- `urgency`
- `uncertainty`

### Runestone

A `Runestone` is an audit token, not a final business action.

It records:

- risk summary
- reasoning fields
- audit-oriented traceability metadata

### Audit records

Persisted audit records are local SQLite records for:

- decision outputs
- generated runestones

They are for inspection and traceability, not for automatic external enforcement.

---

## Stable error contract

All public error responses in `v1.0.0` follow:

```json
{
  "message": "human readable explanation",
  "error_code": "STRUCTURED_ERROR_CODE"
}
```

Current public error codes:

- `VALIDATION_ERROR`
- `ADAPTER_NOT_FOUND`
- `SIMULATION_ERROR`
- `INTERNAL_ERROR`
- `STORAGE_ERROR`
- `NOT_FOUND`
- `FORBIDDEN`

---

## Safety boundary

`full-spectrum-engine v1.0.0` is a **stable local-first contract release**, not a production governance platform.

Interpretation rule:

- the engine may surface risk
- the engine may recommend a path
- the engine does **not** itself perform the final business act

That boundary is part of the release contract.

---

## Read next

1. [REST examples (curl / PowerShell / Python)](rest-examples-v1.0.md)
2. [API quick reference](api-reference-v1.0.md)
3. [API fields and error codes](api-fields-and-errors-v1.0.md)
4. [Explainability walkthrough](explainability-walkthrough-v1.0.md)
5. [v1.0 release checklist](v1.0-release-checklist.md)

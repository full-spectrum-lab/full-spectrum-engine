# REST Examples (`v1.0.0`)

This page gives a single practical entry for calling `full-spectrum-engine` from:

- `curl`
- PowerShell
- Python `requests`

Base URL:

```text
http://127.0.0.1:8000
```

---

## 1. Health check

### curl

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### PowerShell

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"
```

### Python

```python
import requests

resp = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=30)
print(resp.json())
```

---

## 2. Evaluate - direct mode

### Request body

```json
{
  "scenario": {
    "event": "refund_conflict",
    "context": {
      "user_emotion": "angry",
      "merchant_commitment": "ambiguous"
    }
  },
  "seed": 42
}
```

### curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/evaluate" ^
  -H "Content-Type: application/json" ^
  -d @examples/api-samples/evaluate-request-direct-refund.json
```

### PowerShell

```powershell
$body = Get-Content "examples/api-samples/evaluate-request-direct-refund.json" -Raw
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/evaluate" `
  -ContentType "application/json" `
  -Body $body
```

### Python

```python
import json
import requests

with open("examples/api-samples/evaluate-request-direct-refund.json", "r", encoding="utf-8") as f:
    body = json.load(f)

resp = requests.post(
    "http://127.0.0.1:8000/api/v1/evaluate",
    json=body,
    timeout=30,
)
print(resp.status_code)
print(resp.json())
```

---

## 3. Evaluate - adapter mode

### Request body

```json
{
  "industry": "ecommerce_customer_service",
  "metrics": {
    "promise_conflict_rate": 0.72,
    "customer_emotion_escalation": 0.81,
    "policy_boundary_blur": 0.66
  },
  "include_input_metrics": true,
  "seed": 42,
  "simulation_id": "SIM_ECOM_001",
  "input_query": "Customer asks whether a coupon can still be applied after the order is locked."
}
```

### curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/evaluate" ^
  -H "Content-Type: application/json" ^
  -d @examples/api-samples/evaluate-request-adapter-ecommerce.json
```

### PowerShell

```powershell
$body = Get-Content "examples/api-samples/evaluate-request-adapter-ecommerce.json" -Raw
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/evaluate" `
  -ContentType "application/json" `
  -Body $body
```

### Python

```python
import json
import requests

with open("examples/api-samples/evaluate-request-adapter-ecommerce.json", "r", encoding="utf-8") as f:
    body = json.load(f)

resp = requests.post(
    "http://127.0.0.1:8000/api/v1/evaluate",
    json=body,
    timeout=30,
)
print(resp.status_code)
print(resp.headers.get("X-Decision-Id"))
print(resp.json())
```

---

## 4. Generate a standalone Runestone

### curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/runestone" ^
  -H "Content-Type: application/json" ^
  -d @examples/api-samples/runestone-request-refund.json
```

### PowerShell

```powershell
$body = Get-Content "examples/api-samples/runestone-request-refund.json" -Raw
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/runestone" `
  -ContentType "application/json" `
  -Body $body
```

### Python

```python
import json
import requests

with open("examples/api-samples/runestone-request-refund.json", "r", encoding="utf-8") as f:
    body = json.load(f)

resp = requests.post(
    "http://127.0.0.1:8000/api/v1/runestone",
    json=body,
    timeout=30,
)
print(resp.status_code)
print(resp.json())
```

---

## 5. Read persisted decisions

### curl

```bash
curl "http://127.0.0.1:8000/api/v1/audit/decisions?limit=10&offset=0"
```

### PowerShell

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/audit/decisions?limit=10&offset=0"
```

### Python

```python
import requests

resp = requests.get(
    "http://127.0.0.1:8000/api/v1/audit/decisions",
    params={"limit": 10, "offset": 0},
    timeout=30,
)
print(resp.json())
```

---

## 6. Structured error example

If you send both direct mode and adapter mode fields to `/evaluate`, the response shape is:

```json
{
  "message": "exactly one evaluation mode must be selected",
  "error_code": "VALIDATION_ERROR"
}
```

This error format is stable in `v1.0.0`.

---

## Sample files used on this page

Recommended local sample files:

- `examples/api-samples/evaluate-request-direct-refund.json`
- `examples/api-samples/evaluate-request-adapter-ecommerce.json`
- `examples/api-samples/runestone-request-refund.json`

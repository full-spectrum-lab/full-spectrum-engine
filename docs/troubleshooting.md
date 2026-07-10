# Troubleshooting

This page covers the most common first-run problems for `full-spectrum-engine v0.8.0-beta`.

---

## 1. `python` command not found

### Symptom

```text
'python' is not recognized as an internal or external command
```

### Fix

- install Python 3.10 or later
- verify with:

```bash
python --version
```

- if Windows still cannot find Python, reopen the terminal after installation

---

## 2. Dependency install fails

### Symptom

`pip install -r requirements.txt` fails because of network or resolver issues.

### Fix

- upgrade pip first:

```bash
python -m pip install --upgrade pip
```

- retry:

```bash
pip install -r requirements.txt
```

- if the API extras are needed:

```bash
pip install -e ".[api]"
```

---

## 3. Scenario file cannot be loaded

### Symptom

```text
Simulation error: ...
```

or a file-not-found / JSON parse failure.

### Fix

- make sure the config file path exists
- start from the repository root
- validate the JSON syntax

Known good commands:

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42
```

---

## 4. Deterministic output does not match the golden sample

### Symptom

`scripts/validate-public-beta.ps1` reports golden sample drift.

### What it usually means

One of the public output contracts changed:

- simulation logic
- stable ID generation
- timestamp handling
- seeded ESS-lite behavior

### Fix

1. re-run the deterministic tests:

```bash
python -m unittest tests.test_simulate_determinism -v
python -m unittest tests.test_golden_samples -v
```

2. if the output change was intentional, regenerate the golden samples and review the diff before committing
3. if the output change was not intentional, revert the change and re-run validation

---

## 5. API server starts but `/docs` does not open

### Symptom

The server starts but the browser cannot reach `http://127.0.0.1:8000/docs`.

### Fix

- confirm the server is still running in the terminal
- confirm the port is not occupied by another process
- try a different port:

```bash
python -m src.api.server --port 8001
```

- then open:

```text
http://127.0.0.1:8001/docs
```

---

## 6. API returns 422

### Symptom

The request reaches the API, but the response is `422 Unprocessable Content`.

### What it usually means

The request shape is structurally wrong. Common causes:

- both `scenario` and `industry + metrics` were provided to `/api/v1/evaluate`
- neither direct mode nor adapter mode was fully provided
- required metrics for an adapter are missing
- `risk_vector` is missing required fields in `/api/v1/runestone`

### Fix

Use one request mode at a time:

- direct mode: provide `scenario`
- adapter mode: provide `industry` and `metrics`

See [API quick reference](api-reference-v0.8.md).

---

## 7. API returns 500

### Symptom

The request reaches the API, but the response is `500 Internal Server Error`.

### What it usually means

One of these failed:

- simulation runtime
- SQLite write path
- audit persistence
- unexpected internal exception

### Fix

- check the terminal output where the API is running
- verify the database path is writable
- try a clean DB path:

```bash
python -m src.api.server --db-path ./data/fse-clean.db
```

- retry the same request

---

## 8. SQLite file cannot be created

### Symptom

The server fails on startup or first write because the DB file cannot be created.

### Fix

- make sure the target directory exists and is writable
- avoid protected system directories
- use a local relative path such as:

```bash
python -m src.api.server --db-path ./data/fse.db
```

---

## 9. Delete endpoint refuses to run

### Symptom

`DELETE /api/v1/audit/decisions` returns `403` or `422`.

### Why

This endpoint is deliberately guarded. It requires:

- local bind only (`127.0.0.1` / `localhost`)
- `confirm=true`
- either `before=...` or `all=true`

### Meaning

This is expected behavior, not a bug.

---

## 10. Test suite passes with one warning

### Symptom

`pytest` passes, but one warning remains.

### Current status

For `v0.8.0-beta`, one FastAPI / Starlette related warning is currently accepted and is not treated as a beta blocker.

If the warning count grows, that becomes a v0.9 hardening issue.

---

## 11. Recommended recovery path

If you are stuck, use this minimum recovery order:

1. `pip install -r requirements.txt`
2. `python simulate.py --config examples/scenario_refund_conflict.json --seed 42`
3. `powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1`
4. `pip install -e ".[api]"`
5. `python -m src.api.server`

If step 2 fails, fix the local runtime first.  
If step 3 fails, fix reproducibility first.  
If step 5 fails, fix API/storage setup next.

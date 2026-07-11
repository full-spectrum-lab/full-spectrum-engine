# Warning Governance (`v0.9.0a1`)

This page defines which warnings are currently accepted, which warnings are boundary signals, and which warnings should block further release claims.

## 1. Why warning governance matters

At this stage the engine is still moving toward a `v1.0` contract.

That means the project needs a stable rule for answering:

- which warnings are known and tolerated
- which warnings signal public-contract weakness
- which warnings must stop release progression

## 2. Current accepted warning class

At `v0.9.0a1`, the currently accepted warning is:

- one FastAPI / Starlette dependency-level warning in the local test run

Why it is tolerated for now:

- it does not invalidate runtime behavior
- it does not change API contract shape
- it does not create nondeterministic output
- it is upstream dependency behavior, not an engine logic failure

## 3. Warnings that are not blockers right now

### A. dependency deprecation warning

Current example:

- FastAPI / Starlette `TestClient` dependency warning

Required handling:

- keep test count green
- mention it in release notes
- mention it in troubleshooting
- do not silently let the warning count grow

### B. non-local bind warning

When starting:

```bash
python -m src.api.server --host 0.0.0.0 --port 8000
```

the server prints a warning.

That is intentional:

> the current API is local-development oriented and not production-hardened.

## 4. Warnings that should block release progression

These should be treated as blockers for moving toward `v1.0`:

- warning count increases without explanation
- deterministic tests start warning about drift
- API contract generation emits schema/runtime mismatch warnings
- storage behavior emits warnings that affect persistence trust
- release docs disagree with runtime behavior

## 5. Current rule of thumb

### Allowed

```text
pytest green
one known dependency warning
warning explicitly documented
```

### Not allowed

```text
new warning appears
warning source unknown
warning changes runtime meaning
warning count silently grows
```

## 6. Relationship to troubleshooting

Use [troubleshooting.md](troubleshooting.md) for:

- how to recover
- how to diagnose first-run failures
- what to do when API or DB startup fails

Use this page for:

- whether a warning is currently acceptable
- whether the project should stay in `v0.9.x`
- whether a warning blocks the path to `v1.0`

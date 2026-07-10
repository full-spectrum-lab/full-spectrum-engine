# Release Notes: v0.7.2-alpha

> Status: release-quality cleanup  
> Date: 2026-07-07  
> Scope: no new architecture layer, no protocol-network features

## Purpose

v0.7.2-alpha is a cleanup release after the v0.7 industry CASE pack and v0.7.1 hotfix work. It prepares the engine for clearer internal use, later GitHub mirroring, and the upcoming v1.0-beta planning cycle.

## What Changed

- Unified package/API metadata to `0.7.2a1` / `0.7.2-alpha`.
- Replaced deprecated FastAPI status constant usage in project code:
  - from `HTTP_422_UNPROCESSABLE_ENTITY`
  - to `HTTP_422_UNPROCESSABLE_CONTENT`
- Reduced local test warnings from 15 to 1.
- Added `.wiki/` to `.gitignore` to avoid committing local Wiki clones.
- Updated README status, test count, and release boundary notes.
- Clarified that v0.7.2-alpha is still an L2 / organ-level alpha engine.

## Test Result

```text
125 passed, 1 warning
```

Remaining warning:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

This warning originates from FastAPI / Starlette TestClient dependency behavior in the local Python environment. It is not caused by Full Spectrum Engine project code and is not treated as a release blocker for v0.7.2-alpha.

## Compatibility Note: `reversibility`

The current engine still preserves the `reversibility` field name in several RiskVector / Runestone outputs for historical compatibility with earlier protocol drafts and sample records.

In the current engine implementation, this field should be interpreted as **irreversibility / rollback difficulty**:

```text
higher value = harder to reverse = stronger irreversible-risk signal
```

This release does not rename the field in order to avoid breaking existing tests and samples. A future v1.0-beta migration may introduce an explicit alias or a clearer field name such as `rollback_difficulty`.

## Explicit Non-Goals

v0.7.2-alpha does not implement:

- Cell Manifest
- full four-layer recursive architecture
- organization-level aggregation
- protocol-network interoperability
- complete DreamBrain
- Frequency Economy settlement
- production authentication / authorization
- enterprise final action execution

## Next Recommended Work

1. Keep v0.7.x focused on release-quality cleanup.
2. Prepare v1.0-beta as an L2 / organ-level public trial.
3. Introduce minimal `canonical_context.schema.json`.
4. Introduce minimal `layer_profile.schema.json`.
5. Start Cell Manifest design after v1.0-beta boundary is stable.

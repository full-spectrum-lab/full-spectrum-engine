# Release Notes: v1.0.0

> Status: stable local-first contract  
> Date: 2026-07-11  
> Scope: first sealed `v1.0` release for the standalone engine layer

## Purpose

`v1.0.0` means the current local-first engine contract is stable enough for outside developers and reviewers to rely on without private handoff knowledge.

This is a narrow `v1.0`.

It seals the current engine layer. It does not claim that the wider Full Spectrum protocol network, Cell Manifest, DreamBrain, or four-layer recursive architecture are complete.

## What changed since the public beta line

- stabilized seeded reproducibility and committed golden samples
- standardized API error output into `{message, error_code}`
- documented public API fields and failure cases
- exported formal OpenAPI JSON
- added explainability walkthrough
- added warning governance and release-boundary documentation
- completed a hardening cycle after the public beta entry

## What v1.0.0 means

This release now guarantees a stable local-first contract for:

- running synthetic scenario inspection locally
- reproducing output with a fixed seed
- generating structured `RiskVector` and `Runestone` outputs
- persisting local audit records
- calling the engine through a documented REST interface

## What v1.0.0 does not mean

`v1.0.0` does **not** mean:

- production enterprise governance is complete
- protocol-network interoperability is complete
- final legal, compliance, or business action can be delegated to the engine
- four-layer recursive architecture is fully implemented
- Cell Manifest is complete
- DreamBrain is complete
- Frequency Economy settlement is active

## Verification baseline

Release baseline:

```text
141 passed, 1 warning
```

Accepted warning:

- FastAPI / Starlette dependency deprecation warning in the local test environment

This warning is documented and is not treated as a release blocker for `v1.0.0`.

## Recommended use

Recommended:

- local AI inspection experiments
- internal governance validation
- synthetic-case replay
- adapter development
- audit-visibility prototyping

Not recommended:

- final enterprise action execution
- live compliance adjudication
- production cross-organization orchestration

## Read next

1. `docs/api-quick-contract-v1.0.md`
2. `docs/rest-examples-v1.0.md`
3. `docs/api-reference-v1.0.md`
4. `docs/openapi/README.md`
5. `docs/v1.0-release-checklist.md`

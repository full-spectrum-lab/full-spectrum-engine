# Release Notes: v0.8.0-beta

> Status: public beta  
> Date: 2026-07-10  
> Scope: public-facing closure over the v0.7.x alpha line

## Purpose

v0.8.0-beta is the first release intended to present `full-spectrum-engine` as a credible public beta package rather than only an internal alpha cleanup line.

This release focuses on the surface that outside developers and reviewers experience first:

- can it run?
- can it reproduce the same output?
- can it explain what it produced?
- does it state its boundaries honestly?

## What Changed

- promoted version framing from `v0.7.2-alpha` to `v0.8.0-beta`
- updated package metadata in `pyproject.toml`
- refreshed README around the public beta promise:
  - runnable
  - reproducible
  - explainable
  - bounded
- aligned public links to the `full-spectrum-lab` GitHub structure
- added `docs/v0.8-public-beta-gap-list.md`
- added public beta validation script:
  - `scripts/validate-public-beta.ps1`
- added committed golden samples for seeded scenarios:
  - `test-records/v0.8-public-beta/golden_refund_seed42.json`
  - `test-records/v0.8-public-beta/golden_knowledge_seed42.json`
- added tests that compare seeded runtime output against golden samples
- refreshed examples and test-record documentation for the public beta workflow

## Test Result

Expected local baseline after closure:

```text
127 passed
```

The exact count depends on the local environment and new tests included in this release line.

## What Public Beta Means Here

Public beta does **not** mean production-ready enterprise governance.

It means:

- external developers can run it locally
- seeded outputs are stable enough for golden-sample validation
- core outputs are understandable enough for audit-style review
- architecture boundaries are no longer hidden

## Explicit Non-Goals

v0.8.0-beta does not implement:

- full four-layer recursive architecture
- Cell Manifest
- organization-level aggregation
- protocol-network interoperability
- complete DreamBrain
- Frequency Economy settlement
- production authentication / authorization
- enterprise final action execution

## Recommended Use

Recommended:

- local scenario simulation
- synthetic-case validation
- internal research review
- early integration experiments
- public demonstration of local-first governance ideas

Not recommended:

- direct production business execution
- legal / compliance final ruling
- live enterprise action routing
- public claims of enterprise deployment based only on sample runs

## Recommended Next Work

1. gather feedback from the first public beta readers
2. stabilize the REST/API contract surface further
3. keep building explainable examples and golden samples
4. decide whether the next step is `v0.9` hardening or `v1.0-beta` public trial

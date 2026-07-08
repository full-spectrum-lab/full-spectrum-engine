# Test Records

This directory keeps local verification evidence for `full-spectrum-engine`.

It is not a replacement for the automated test suite. It exists to preserve reproducible artifacts, sample outputs, and version-to-version comparison evidence during the early collaboration stage.

## Current archived folders

- `test-records/2026-07-04-v0.3-candidate/`
- `test-records/v0.4-adapter/`

## Why this directory exists

The project does not only say “it runs”. It also tries to preserve:

- how it was run;
- what it produced;
- what was used as the reference sample;
- what later versions should not silently break.

## Reproducible sample baseline

Important baseline samples include seeded outputs such as:

- `golden_refund_seed42.json`
- `golden_knowledge_seed42.json`

These are useful for deterministic regression checks.

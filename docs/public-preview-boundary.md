# Public Preview Boundary

## Current status

`full-spectrum-engine` is currently positioned as a local-first public beta engine preview.

The right expectation is:

```text
Runnable locally
Reproducible with seeds and golden samples
Auditable at sample level
Useful for synthetic scenario validation
Not a production governance platform
```

## What this engine does

- runs local simulations
- produces structured risk outputs
- generates runestone-style audit records
- supports reproducible sample runs with seeds
- preserves golden samples for regression comparison
- exposes a local REST API for development and testing
- supports industry adaptation experiments

## What this engine does not do

- does not execute final enterprise actions
- does not replace legal, compliance, or business review
- does not implement the full four-layer recursive architecture
- does not implement protocol-network interoperability
- does not implement Cell Manifest
- does not implement complete DreamBrain
- does not implement Frequency Economy settlement

## Data boundary

By default, the engine is intended for:

- local use
- synthetic samples
- internal testing
- offline scenario validation

Public examples should not imply real enterprise deployment or real user data usage.

## Reading order

If you are new to the project, read in this order:

1. `README.md`
2. `docs/getting-started-5min.md`
3. `docs/local-first-engine.md`
4. `docs/api-reference-v0.8.md`
5. `docs/troubleshooting.md`
6. `docs/v0.8-public-beta-gap-list.md`
7. `docs/release-v0.8.0-beta.md`
8. protocol-side materials in `full-spectrum-protocol`

## 中文说明

当前 public beta 的边界很明确：这是一个可以本地运行、可以通过固定种子复现输出、可以验证样例、可以产出结构化风险与审计记录的实验性引擎，但它还不是完整协议网络，也不是生产级企业治理平台。

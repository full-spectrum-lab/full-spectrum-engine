# Public Preview Boundary

## Current status

`full-spectrum-engine` is currently a **local-first experimental engine preview**.

The correct expectation is:

```text
Runnable locally
Testable
Auditable at sample level
Useful for synthetic scenario validation
Not a production governance platform
```

## What this engine does

- runs local simulations;
- produces structured risk outputs;
- generates `Runestone` audit tokens;
- writes local `AuditTrace`-style outputs;
- supports reproducible sample runs with `--seed`;
- exposes a local REST API for development and testing;
- supports industry adaptation experiments.

## What this engine does not do

- does not execute final enterprise actions;
- does not replace legal, compliance, or business review;
- does not implement the full four-layer recursive architecture yet;
- does not implement protocol-network interoperability yet;
- does not implement Cell Manifest yet;
- does not implement complete DreamBrain yet;
- does not implement Frequency Economy settlement yet.

## Data boundary

By default, the engine is intended for:

- local use;
- synthetic samples;
- internal testing;
- offline scenario validation.

Public examples must not imply real enterprise deployment or real user data usage.

## 中文说明

当前 GitHub 公开版只把它定位为“企业内部引擎层”的可运行预览：

- 可以本地运行；
- 可以做样例验证；
- 可以输出结构化风险和审计记录；
- 但还不是完整协议网络；
- 也不是生产级企业治理平台。

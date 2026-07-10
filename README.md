# Full Spectrum Engine

[![public intro](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/public-intro/from-ethical-appeal-to-engineering-compilation.png?raw=1)](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/public-intro/from-ethical-appeal-to-engineering-compilation.png)

> Local-first governance runtime for reproducible AI inspection, risk visibility, audit trace, and explainable simulation.

[![License](https://img.shields.io/badge/License-Mulan%20PSL%20v2%20%2F%20Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-v0.8.0--beta-blue)](#)
[![Tests](https://img.shields.io/badge/Tests-127%20passed-brightgreen)](#)

Full Spectrum Engine is the runnable engine layer in the Full Spectrum ecosystem. It turns AI behavior, knowledge-source conflicts, structured metrics, and synthetic scenarios into reproducible outputs such as `RiskVector`, `Runestone`, `AuditTrace`, and optional ESS-lite path suggestions.

This repository is for **local internal validation first**:

- runnable on a local machine
- reproducible with fixed seeds
- auditable at sample level
- explainable through structured outputs
- usable without joining an external protocol network

It does **not** upload enterprise data by default, does **not** execute final business actions on behalf of an enterprise, and does **not** claim production governance completeness.

## 中文一句话

这是全频谱体系里的“企业内部引擎层” public beta：先让单个主体在本地边界内看见风险、留下审计记录、完成可复现验证，再决定是否进入更重的细胞协议层或协议网络层。

---

## Public beta at a glance

`v0.8.0-beta` is the first version intended to be publicly inspected as a coherent package:

- **Runnable**: a reviewer can clone and run it locally in minutes
- **Reproducible**: fixed seeds and golden samples make output comparison stable
- **Explainable**: results are exported as structured governance artifacts instead of opaque scores only
- **Bounded**: non-goals and release boundary are explicit

---

## Fast visual entry

If you want the fastest possible overview before reading code, start here:

- [From Ethical Appeal to Engineering Compilation](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/public-intro/from-ethical-appeal-to-engineering-compilation.png)
- [Why AI Needs a Relationship Protocol](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/protocol-system/why-ai-needs-relationship-protocol.png)
- [Four-Layer Architecture](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/architecture/four-layer-architecture-v01.png)
- [Visual Index](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/docs/visual-index.md)

---

## What this engine does

- models a three-dimensional governance state `S(t) = [Survival, Coordination, Meaning]`
- computes FSHI (Full Spectrum Health Index)
- generates structured `RiskVector` and `Runestone` outputs
- records local `AuditTrace` results
- supports deterministic simulation with `--seed`
- provides industry-adapter experiments, including e-commerce customer service
- exposes a local REST API for development and testing
- stores local audit records in SQLite
- supports optional ESS-lite path simulation for non-binding treatment suggestions

## What this engine does not do

- does not replace legal, compliance, or business review
- does not execute refunds, penalties, bans, or final rulings
- does not implement the full four-layer recursive architecture yet
- does not implement protocol-network interoperability yet
- does not implement the full Cell Manifest yet
- does not implement the full DreamBrain yet
- does not implement Frequency Economy settlement yet

---

## Repository role in the ecosystem

| Repository | Role |
| --- | --- |
| [`full-spectrum-protocol`](https://github.com/full-spectrum-lab/full-spectrum-protocol) | Public protocol specification, RFCs, schemas, mappings, and examples |
| [`full-spectrum-engine`](https://github.com/full-spectrum-lab/full-spectrum-engine) | Runnable local-first engine (this repository) |
| [`full-spectrum-enterprise-governance`](https://github.com/full-spectrum-lab/full-spectrum-enterprise-governance) | Enterprise deployment package, industry adapters, dashboards, and internal governance workflows |
| [`full-spectrum-commons`](https://github.com/full-spectrum-lab/full-spectrum-commons) | Shared diagrams, ecosystem descriptions, and public-facing common materials |

A practical adoption path is:

1. run the **engine layer** locally inside one organization
2. add **cell protocol declarations** when identity, permission, and responsibility need to be formalized
3. add the **protocol network layer** only when multiple subjects need cross-node audit or coordination

---

## Quick start

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt

# Run a simulation
python simulate.py --config examples/scenario_refund_conflict.json

# Reproducible output
python simulate.py --config examples/scenario_refund_conflict.json --seed 42

# Validate public beta surface
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1

# Run full test suite
python -m pytest tests -v

# Start local API
pip install -e ".[api]"
python -m src.api.server
```

Local API docs:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Recommended reading order

1. [Public preview boundary](docs/public-preview-boundary.md)
2. [5-minute quick start](docs/getting-started-5min.md)
3. [Local-first engine note](docs/local-first-engine.md)
4. [API quick reference](docs/api-reference-v0.8.md)
5. [Troubleshooting](docs/troubleshooting.md)
6. [Examples overview](examples/README.md)
7. [Test records and golden samples](test-records/README.md)
8. [v0.8 public beta gap list](docs/v0.8-public-beta-gap-list.md)
9. [v0.8 release notes](docs/release-v0.8.0-beta.md)
10. [GitHub release body draft](docs/github-release-v0.8.0-beta.md)
11. [v0.9 hardening checklist](docs/v0.9-hardening-checklist.md)
12. [v1.0 gate criteria](docs/v1.0-gate-criteria.md)

---

## Current release boundary

Current public target:

```text
Runnable locally
Reproducible with fixed seeds
Auditable at sample level
Useful for synthetic scenario validation
Not yet a production governance platform
```

This repository is suitable today for:

- AI governance research
- enterprise-side internal validation
- customer-service quality inspection experiments
- local audit trail prototyping
- protocol-compatible simulation tests

This repository is not yet suitable for:

- direct production business execution
- automatic legal or compliance rulings
- cross-organization live governance orchestration
- claims of mature network governance interoperability

---

## Test status

Current local baseline:

```text
127 passed, 1 warning
```

The remaining warning comes from FastAPI / Starlette dependency behavior and is not currently treated as a blocker for this beta.

---

## License

Dual license:

- Mulan PSL v2
- Apache License 2.0

See [LICENSE](LICENSE).

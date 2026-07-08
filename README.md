# Full Spectrum Engine

> Local-first governance engine for Full Spectrum-compatible simulation, risk visibility, audit trace, and reproducible enterprise-side validation.

[![License](https://img.shields.io/badge/License-Mulan%20PSL%20v2%20%2F%20Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-v0.7.2--alpha-orange)](#)
[![Tests](https://img.shields.io/badge/Tests-125%20passed-brightgreen)](#)

Full Spectrum Engine is the runnable local-first engine layer in the Full Spectrum ecosystem. It turns AI behavior, knowledge-source conflicts, structured metrics, and synthetic scenarios into reproducible simulation outputs, `RiskVector`, `Runestone`, `AuditTrace`, and optional ESS-lite path suggestions.

It is designed for internal validation first:

- local execution;
- offline-capable testing;
- desensitized or synthetic samples;
- auditable records;
- non-invasive governance experiments.

It does **not** upload enterprise data by default, does **not** require joining a protocol network before use, and does **not** execute final business actions on behalf of an enterprise.

## 中文一句话

这是全频谱体系里“企业内部引擎层”的最小可运行版本：先让单个主体在自己的边界内看见风险、留下审计记录、完成本地验证，再决定是否进入更重的细胞协议层或协议网络层。

---

## What this engine does

- models a three-dimensional governance state `S(t) = [Survival, Coordination, Meaning]`;
- computes FSHI (Full Spectrum Health Index);
- generates structured `RiskVector` and `Runestone` outputs;
- records local `AuditTrace` results;
- supports deterministic simulation with `--seed`;
- provides industry-adapter experiments, including e-commerce customer service;
- exposes a local REST API for development and testing;
- stores local audit records in SQLite;
- supports optional ESS-lite path simulation for non-binding treatment suggestions.

## What this engine does not do

- does not replace legal, compliance, or business review;
- does not execute refunds, penalties, bans, or final rulings;
- does not implement the full four-layer recursive architecture yet;
- does not implement protocol-network interoperability yet;
- does not implement full Cell Manifest yet;
- does not implement full DreamBrain yet;
- does not implement Frequency Economy settlement yet.

---

## Repository role in the ecosystem

| Repository | Role |
| --- | --- |
| [`full-spectrum-protocol`](https://github.com/full-spectrum-lab/full-spectrum-protocol) | Public protocol specification, RFCs, schemas, mappings, and examples |
| [`full-spectrum-engine`](https://github.com/full-spectrum-lab/full-spectrum-engine) | Runnable local-first engine (this repository) |
| [`full-spectrum-enterprise-governance`](https://github.com/full-spectrum-lab/full-spectrum-enterprise-governance) | Enterprise deployment package, industry adapters, dashboards, and internal governance workflows |
| [`full-spectrum-commons`](https://github.com/full-spectrum-lab/full-spectrum-commons) | Shared diagrams, ecosystem descriptions, and public-facing common materials |

A practical adoption path is:

1. run the **engine layer** locally inside one organization;
2. add **cell protocol declarations** when identity, permission, and responsibility need to be formalized;
3. add the **protocol network layer** only when multiple subjects need cross-node audit or coordination.

---

## Quick start

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt

# run a simulation
python simulate.py --config examples/scenario_refund_conflict.json

# reproducible output
python simulate.py --config examples/scenario_refund_conflict.json --seed 42

# run tests
python -m pytest tests -v

# start local API
pip install -e ".[api]"
python -m src.api.server
```

API docs (local only):

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Recommended reading order

1. [docs/public-preview-boundary.md](docs/public-preview-boundary.md)
2. [docs/getting-started-5min.md](docs/getting-started-5min.md)
3. [docs/local-first-engine.md](docs/local-first-engine.md)
4. [docs/release-v0.7.2-alpha.md](docs/release-v0.7.2-alpha.md)
5. [examples/README.md](examples/README.md)
6. [test-records/README.md](test-records/README.md)
7. protocol-side materials in [`full-spectrum-protocol`](https://github.com/full-spectrum-lab/full-spectrum-protocol)

---

## Current release boundary

Current public preview target:

```text
Runnable locally
Testable and reproducible
Auditable at sample level
Useful for synthetic scenario validation
Not yet a production governance platform
```

This repository is suitable today for:

- AI governance research;
- enterprise-side internal validation;
- customer-service quality inspection experiments;
- local audit trail prototyping;
- protocol-compatible simulation tests.

---

## Test status

Current local verification baseline:

```text
125 passed, 1 warning
```

The remaining warning comes from FastAPI / Starlette test dependency behavior and is not currently treated as a blocker for this alpha preview.

---

## License

Dual license:

- Mulan PSL v2
- Apache License 2.0

See [LICENSE](LICENSE).

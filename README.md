# Full Spectrum Engine

[English](README.md) · [简体中文](README.zh-CN.md)

[![Three entries and three core components](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/architecture/three-entry-three-core-components-zh-v10.png?raw=1)](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/docs/three-entry-three-core-components.md)

> Local-first governance runtime for reproducible AI inspection, risk visibility, audit trace, and explainable simulation.

[![License](https://img.shields.io/badge/License-Mulan%20PSL%20v2%20%2F%20Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-v1.5.0-enterprise_pilot_candidate-success)](#)
[![Tests](https://img.shields.io/badge/Tests-285%20passed%20%2B%203%20subtests-brightgreen)](#)

Full Spectrum Engine is the runnable engine layer in the Full Spectrum ecosystem. It turns AI behavior, knowledge-source conflicts, structured metrics, and synthetic scenarios into reproducible outputs such as `RiskVector`, `Runestone`, local audit records, and optional ESS-lite path suggestions.

## Release truth

| Line | GitHub status | Meaning |
| --- | --- | --- |
| [`v1.4.0`](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.4.0) | **Latest stable release** | Replay and audit hardening baseline. |
| [`v1.5.0`](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.5.0) | **Pre-release** | Enterprise-pilot candidate; additive controls over v1.4. |
| [`v1.0.0`](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.0.0) | Stable historical baseline | First stable local-first contract release. |

`v1.5.0` already exists on both public release tracks. Its pre-release label is intentional and must not be interpreted as a production-complete enterprise platform.

This repository is for **local internal validation first**:

- runnable on a local machine
- reproducible with fixed seeds
- auditable at sample level
- explainable through structured outputs
- usable without joining an external protocol network

It does **not** upload enterprise data by default, does **not** execute final business actions on behalf of an enterprise, and does **not** claim production governance completeness.

## 中文一句话

这是全频谱体系里的企业内部治理引擎：v1.5 在本地可复现计算、Profile、回放与审计基础上，增加受控企业试点所需的配置/秘密分离、最小 RBAC、脱敏、人工复核、韧性、可观测性、备份回滚和默认关闭写回的 Connector 契约。

## v1.5 enterprise pilot candidate

`v1.5.0` is an additive enterprise-pilot release over the sealed v1.4 replay/audit baseline:

- configuration contains secret references, not embedded credentials;
- authentication is limited to local operator/service reference tokens and never treats an ObservedSubject as a login identity;
- field minimization, masking, hashing and tokenization support controlled trials;
- human review records bind to real v1.4 evaluation events and remain append-only;
- retry, observable timeout, health, metrics, backup and rollback primitives are included;
- four Connector output contracts are available with writeback disabled by default;
- protected engine directories remain byte-identical to the frozen v1.2 baseline.

Release evidence: 285 pytest cases plus 3 subtests, v1.5 black box 13/13, v1.4 regression black box 9/9, red-line verification 9/9, and zero-byte protected-core diff. This is a controlled pilot candidate, not a claim of autonomous business execution or production-complete enterprise governance.

---

## v1.0 at a glance

`v1.0.0` is the first stable local-first contract release:

- **Runnable**: a reviewer can clone and run it locally in minutes
- **Reproducible**: fixed seeds and golden samples make output comparison stable
- **Explainable**: results are exported as structured governance artifacts instead of opaque scores only
- **Bounded**: non-goals and release boundary are explicit

---

## Fast visual entry

If you want the fastest possible overview before reading code, start here:

- [From Ethical Appeal to Engineering Compilation](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/public-intro/from-ethical-appeal-to-engineering-compilation.png)
- [Three Entry Paths and Three Core Components](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/docs/three-entry-three-core-components.md)
- [Why AI Needs a Relationship Protocol](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/protocol-system/why-ai-needs-relationship-protocol.png)
- [Four-Layer Architecture](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/diagrams/architecture/four-layer-architecture-v01.png)
- [Visual Index](https://github.com/full-spectrum-lab/full-spectrum-commons/blob/main/docs/visual-index.md)
- [Synthetic industrial tightening-evidence case](https://github.com/full-spectrum-lab/full-spectrum-enterprise-governance/tree/main/cases/industrial-tightening-evidence-gap)

---

## What this engine does

- models a three-dimensional governance state `S(t) = [Survival, Coordination, Meaning]`
- computes FSHI (Full Spectrum Health Index)
- generates structured `RiskVector` and `Runestone` outputs
- records local audit results through persistent decision and runestone storage
- supports deterministic simulation with `--seed`
- provides industry-adapter experiments, including e-commerce and logistics samples
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

### v1.1 subject-aware governance chain

```bash
python -m src.governance_chain generate \
  --input examples/governance_chain/raw-input.ecommerce.json \
  --subject-file examples/subjects/subject-declaration.customer-service.compatible.json \
  --out out/governance-chain
```

The declaration is validated locally, assigned a canonical SHA-256 digest and
propagated as `subject_ref`. External identity and credential references are
retained only; the Observer does not certify, authorize or execute an action.

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt

# Run a simulation
python simulate.py --config examples/scenario_refund_conflict.json

# Reproducible output
python simulate.py --config examples/scenario_refund_conflict.json --seed 42

# Validate public release surface
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1

# Run full test suite
python -m pytest tests -v

# Start local API
pip install -e ".[api]"
python -m src.api.server
```

---

## Governance Chain CLI (ten-minute runnable)

The engine now ships a CLI that turns a raw business input into the **full
Full Spectrum governance object chain** — the same chain previously documented
only as a static example in
[`full-spectrum-protocol/examples/cases/ecommerce_chain/`](https://github.com/full-spectrum-lab/full-spectrum-protocol/tree/main/examples/cases/ecommerce_chain).

No extra install is needed (standard library only, no numpy / network):

```bash
# 1) generate the chain
python -m src.governance_chain generate \
    --input examples/governance_chain/raw-input.ecommerce.json \
    --out out/governance_chain

# 2) validate the generated artifacts against the vendored protocol schemas
python -m src.governance_chain validate out/governance_chain
```

This produces `governance-event`, `canonical-context`, `cell-manifest`,
`output-envelope`, `enterprise-writeback` (all schema-valid) and a `report.md`.
The output is **byte-for-byte reproducible** against the committed example;
`tests/test_governance_chain.py` asserts that.

After `pip install -e .` the same command is also available as `fsengine-govchain`.

Full walkthrough: [examples/governance_chain/README.md](examples/governance_chain/README.md).

Local API docs:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Recommended reading order

1. [API quick contract](docs/api-quick-contract-v1.0.md)
2. [5-minute quick start](docs/getting-started-5min.md)
3. [Local-first engine note](docs/local-first-engine.md)
4. [REST examples (curl / PowerShell / Python)](docs/rest-examples-v1.0.md)
5. [API quick reference](docs/api-reference-v1.0.md)
6. [OpenAPI export](docs/openapi/README.md)
7. [API fields and error codes](docs/api-fields-and-errors-v1.0.md)
8. [Explainability walkthrough](docs/explainability-walkthrough-v1.0.md)
9. [Warning governance](docs/warning-governance-v1.0.md)
10. [Troubleshooting](docs/troubleshooting.md)
11. [Examples overview](examples/README.md)
12. [Test records and golden samples](test-records/README.md)
13. [API sample pack](examples/api-samples/README.md)
14. [v1.0 gate criteria](docs/v1.0-gate-criteria.md)
15. [v1.0 gate review](docs/v1.0-gate-review-v1.0.0.md)
16. [v1.0 release checklist](docs/v1.0-release-checklist.md)
17. [v1.0 release notes](docs/release-v1.0.0.md)
18. [GitHub release body draft](docs/github-release-v1.0.0.md)

---

## Current release boundary

Current public target:

```text
Runnable locally
Reproducible with fixed seeds
Auditable at sample level
Useful for synthetic scenario validation
Stable as a local-first governance engine contract
Not a production governance platform
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
141 passed, 1 warning
```

The remaining warning comes from FastAPI / Starlette dependency behavior and is not currently treated as a blocker for the `v1.0.0` local-first contract release.

---

## License

Dual license:

- Mulan PSL v2
- Apache License 2.0

See [LICENSE](LICENSE).

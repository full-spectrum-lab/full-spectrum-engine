# Full Spectrum Engine

> **v0.8.0-beta (Public Beta)** — 全频谱协议的本地优先可运行仿真引擎

[![License](https://img.shields.io/badge/License-Mulan%20PSL%20v2%20%2F%20Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-v0.8%20Public%20Beta-blue)](#)
[![Tests](https://img.shields.io/badge/Tests-127%20passed-brightgreen)](#)

Full Spectrum Engine 是全频谱协议的本地优先可运行仿真引擎，用于将 AI 行为、知识源冲突、风险显影、审计留痕与 ESS-lite 路径推演转化为可测试、可复现、可解释、可导出的结构化记录。

引擎默认不上传数据、不连接协议网络、不收集企业内容，也不替企业执行最终业务决策。

---

## English Summary

**Full Spectrum Engine** is a local-first, offline-capable simulation engine for the Full Spectrum Protocol. It converts AI behavior, knowledge-source conflicts, risk signals, audit traces, and optional ESS-lite path simulations into reproducible, testable, explainable, and exportable records.

It is designed for internal AI governance, customer-service risk inspection, auditable decision trails, and protocol-compatible simulation. By default, it does not upload data, does not connect to any protocol network, and does not execute final business decisions on behalf of an enterprise.

### What It Does

- **Civilization State Modeling**: Three-dimensional state vector `S(t) = [Survival, Coordination, Meaning]`
- **FSHI (Full Spectrum Health Index)**: Weighted health score with risk grading (EXCELLENT / NORMAL / WARNING / CRISIS / CRITICAL)
- **RiskAlert / RiskVector**: Structured risk detection and 8-dimensional semantic risk vector
- **Runestone**: Auditable decision token for simulation and traceability
- **AuditTrace / Causal Chain Report**: Structured audit trail and human-readable report
- **MetricAdapter (v0.4)**: Industry-specific metric mapping, currently including e-commerce customer service
- **REST API (v0.5)**: Local HTTP API layer powered by FastAPI
- **SQLite Persistence (v0.6)**: Local audit storage for decisions and runestones, with query, TTL cleanup, and capacity management
- **ESS-lite (Optional)**: Internal path-simulation module for non-binding treatment suggestions; it does not replace enterprise final decisions

### Public Beta Promise

v0.8.0-beta aims to be the first public package that is:

- **Runnable** in a few minutes on a local machine
- **Reproducible** with stable seeded outputs and golden samples
- **Explainable** through RiskVector, Runestone, and causal-chain outputs
- **Bounded** by clear non-goals and local-first data discipline

### Quick Start

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt

# Run a simulation
python simulate.py --config examples/scenario_refund_conflict.json

# Reproducible output with seed
python simulate.py --config examples/scenario_refund_conflict.json --seed 42

# Validate public beta contract surface
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1

# Run tests
python -m pytest tests -v

# Start REST API server (local-first, v0.8.0-beta)
pip install -e ".[api]"
python -m src.api.server
# API docs at http://127.0.0.1:8000/docs
```

### Current Release Boundary

v0.8.0-beta is a public beta closure over the v0.7.x alpha line. It keeps the current L2 / organ-level engine scope stable, upgrades seeded reproducibility into golden-sample validation, and tightens the first-run public experience.

It does **not** add the full four-layer recursive architecture yet. Cell Manifest, organization-level aggregation, protocol-network interoperability, complete DreamBrain, and Frequency Economy settlement remain planned future work.

### Design Principles

- **Local-First**: No data upload, no network dependency, no enterprise content collection
- **Offline-Capable**: All simulation, validation, and report generation work fully offline
- **Verifiable**: Every decision path has a complete causal chain record and Runestone audit token
- **Non-Execution System**: The engine outputs risk signals, audit records, reports, and ESS-lite suggestions only; it does not execute refunds, compensations, penalties, bans, or final rulings on behalf of an enterprise
- **ESS-lite Optional**: Enterprises may use only risk detection and audit capabilities, or enable ESS-lite for path-simulation suggestions

### Repository Ecosystem

| Repository | Role | Platform |
|------------|------|----------|
| `full-spectrum-protocol` | Protocol specification (RFC, Schema, examples) | [GitHub](https://github.com/full-spectrum-lab/full-spectrum-protocol) |
| **`full-spectrum-engine`** | **Runnable engine (this repo)** | [GitHub](https://github.com/full-spectrum-lab/full-spectrum-engine) / [Gitee](https://gitee.com/full-spectrum/full-spectrum-engine) |
| `full-spectrum-commons` | Commons, ecosystem notes, cross-repo public context | [GitHub](https://github.com/full-spectrum-lab/full-spectrum-commons) |
| `qpp` | Project control center (Wiki, roadmap, requirements) | [Gitee Wiki](https://gitee.com/full-spectrum/qpp/wikis/Home) |

### Public Beta Reading Path

If you are evaluating the engine for the first time, read in this order:

1. [5-minute quick start](docs/getting-started-5min.md)
2. [Examples overview](examples/README.md)
3. [Public preview boundary](docs/public-preview-boundary.md)
4. [v0.8 public beta gap list](docs/v0.8-public-beta-gap-list.md)
5. [Release notes: v0.8.0-beta](docs/release-v0.8.0-beta.md)
6. [Test records and golden samples](test-records/README.md)

### License

Dual license: Mulan PSL v2 (China) + Apache License 2.0 (International). See [LICENSE](LICENSE).

---

## 中文文档

## 设计承诺

- **本地优先**：引擎默认不上传数据、不连接协议网络、不收集企业内容
- **可断网运行**：所有仿真、验证、报告生成均可在完全离线环境下完成
- **可验证**：每个决策路径都有完整的因果链记录和符石审计令牌
- **非执行系统**：引擎只输出风险、审计记录、报告与 ESS-lite 推演建议，不替企业执行退款、赔付、处罚、封禁或最终裁决
- **ESS-lite 可选**：企业可以只使用风险检测与审计能力，也可以启用 ESS-lite 获得路径推演建议

## Engine 与 ESS-lite 的关系

Full Spectrum Engine 是一个本地优先的风险显影、审计留痕与仿真推演引擎。它默认负责将 AI 对话、Agent 行为、知识源冲突和业务事件转化为 RiskAlert、RiskVector、Runestone、AuditTrace 与人类可读报告。

ESS-lite 是 Engine 内部的可选路径推演模块，用于在风险已经被显影之后，对不同处理路径进行非强制性后果推演。例如：立即执行、严格拒绝、人工复核、暂缓处理等路径各自会带来什么收益、代价和责任变化。

企业可以只使用 Engine 的风险检测与审计能力，也可以启用 ESS-lite 获得路径推演建议。无论是否启用 ESS-lite，系统都不替代企业、人工主管、客服、法务或业务系统作出最终裁决。

## 与协议规范的关系

| 仓库 | 定位 | 平台 |
|------|------|------|
| `full-spectrum-protocol` | 公开协议规范层（RFC、Schema、示例） | [GitHub](https://github.com/full-spectrum-lab/full-spectrum-protocol) |
| **`full-spectrum-engine`** | **可运行引擎层（本仓库）** | [GitHub](https://github.com/full-spectrum-lab/full-spectrum-engine) / [Gitee](https://gitee.com/full-spectrum/full-spectrum-engine) |
| `full-spectrum-commons` | 公开说明层（生态介绍、公共边界、跨仓库入口） | [GitHub](https://github.com/full-spectrum-lab/full-spectrum-commons) |
| `qpp` | 项目总控台（Wiki、路线图、需求草稿） | [Gitee Wiki](https://gitee.com/full-spectrum/qpp/wikis/Home) |

protocol 仓库定义“协议应该是什么样”，engine 仓库实现“协议跑起来是什么样”。

## 快速开始

### 安装

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt
```

### 运行仿真

```bash
# 通过场景配置文件运行
python simulate.py --config examples/scenario_refund_conflict.json

# 生成可复现输出，用于 golden sample / CI
python simulate.py --config examples/scenario_refund_conflict.json --seed 42

# 一键校验 public beta 收口面
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1

# 直接运行单元测试
python -m pytest tests -v

# 如果不想安装 pytest，也可以使用 Python 内置 unittest
python -m unittest tests.test_bomb -v
python -m unittest tests.test_simulate_determinism -v

# 运行实验脚本（A-H）
python experiments/experiment_A_baseline.py
```

### 5 分钟体验

```python
from src.core.state import CivilizationState
from src.core.fshi import compute_fshi, FSHIConfig, fshi_risk_level
from src.engine.ess import ESS, ESSConfig

# 1. 定义当前文明状态
S = CivilizationState(survival=0.72, coordination=0.65, meaning=0.58)

# 2. 运行 ESS-lite 推演
ess = ESS(ESSConfig(horizon=5, num_candidates=10))
W, result = ess.select_strategy_with_result(S)

# 3. 计算 FSHI 频段健康指数
fshi = compute_fshi(S, FSHIConfig())
print(f"FSHI = {fshi:.1f} ({fshi_risk_level(fshi)})")
print(f"Selected strategy: {result.selected_option}")
for p in result.paths:
    print(f"  {p.option}: pain={p.total_pain:.3f} {'<-- selected' if p.selected else ''}")
```

更完整的新手说明：

- [5 分钟跑通 full-spectrum-engine](docs/getting-started-5min.md)
- [Local-First Engine：企业内部引擎层说明](docs/local-first-engine.md)
- [Examples 说明](examples/README.md)
- [Public Preview Boundary](docs/public-preview-boundary.md)
- [v0.8 Public Beta Gap List](docs/v0.8-public-beta-gap-list.md)
- [v0.8 Release Notes](docs/release-v0.8.0-beta.md)
- [Test Records 说明](test-records/README.md)

## 模块架构

### Core Modules

| 模块 | 路径 | 功能 |
|------|------|------|
| **Core** | `src/core/` | 文明状态向量 `S(t) = [S_l, S_m, S_h]^T` + FSHI 频段健康指数计算 |
| **Bridge** | `src/bridge/` | 符石审计令牌（Runestone）+ 八维语义风险向量（RiskVector） |
| **Adapters** | `src/adapters/` | 行业指标适配器 MetricAdapter（v0.4：电商客服 CASE005） |
| **Storage** | `src/storage/` | SQLite 本地持久化后端，保存 decision / runestone 审计记录，支持查询、TTL 清理与容量管理 |
| **API** | `src/api/` | REST API 薄封装层（v0.6：FastAPI + SQLite 持久化 + 审计查询） |
| **Report** | `src/report_generator.py` | 因果链报告生成器 |

### Optional / Simulation Modules

| 模块 | 路径 | 功能 |
|------|------|------|
| **Engine / ESS-lite** | `src/engine/` | 多路径推演、痛苦比较、非强制性路径建议 |
| **Observation** | `src/observation/` | L0 现实锚定层（复合观测算子、压缩映射、多源融合） |
| **Safety** | `src/safety/` | 紧急制动系统 BSRM（FSHI 崩溃检测、生存危机熔断、守庙人多签复位） |

### Research / Experimental Modules

| 模块 | 路径 | 功能 |
|------|------|------|
| **Guardian** | `src/guardian/` | 守庙人网络（2/3 多签投票、提案治理）+ Lyapunov 调节器 |
| **Governance** | `src/governance/` | 梦蝶四层校验器 + 觉性炸弹引擎 |
| **Experiments** | `experiments/` | A-H 研究实验脚本 |

### 核心概念

**文明状态向量** `S(t) = [S_l, S_m, S_h]^T`
- `S_l` 生存层 (Survival) — 底层生存保障 [0,1]
- `S_m` 协调层 (Coordination) — 信任与协作 [0,1]
- `S_h` 意义层 (Meaning) — 意义与方向 [0,1]

**FSHI 频段健康指数** `FSHI = w_l*S_l + w_m*S_m + w_h*S_h - Penalty`
- 默认权重: `w_l=0.40, w_m=0.35, w_h=0.25`
- 风险分级: EXCELLENT(80+) / NORMAL(60+) / WARNING(40+) / CRISIS(20+) / CRITICAL(<20)

**悲悯约束集** `C = { S in [0,1]^3 | S_l >= 0.3, S_m <= 0.8, S_h >= 0.2 }`
- 觉性炸弹将越界状态投影回可行域

## 实验脚本

| 实验 | 脚本 | 目的 |
|------|------|------|
| A | `experiment_A_baseline.py` | 基线验证：FSHI 计算 + 状态约束 |
| B | `experiment_B_ess.py` | ESS 推演：多路径策略选择 + 痛苦比较 |
| C | `experiment_C_l0_ess.py` | L0+ESS 联动：观测层驱动推演 |
| D | `experiment_D_guardian_short.py` | 守庙人短期：提案 + 投票 + 裁决 |
| E | `experiment_E_guardian_long.py` | 守庙人长期：多轮治理 + 信任衰减 |
| F | `experiment_F_frequency.py` | 频率经济：三频干预效果 |
| G | `experiment_G_threshold.py` | 阈值扫描：约束边界行为 |
| H | `experiment_H_stress.py` | 压力测试：极端状态 + 连续触发 |

## 测试

```bash
# 单元测试
python -m pytest tests -v

# 可复现性测试
python -m unittest tests.test_simulate_determinism -v

# 测试记录
ls test-records/2026-07-04-v0.3-candidate/
```

测试记录存放在 `test-records/` 目录下，按日期和版本归档。

## 依赖

- Python >= 3.10
- numpy >= 1.24.0
- pytest >= 8.0.0（用于运行测试；CI 会自动安装）

详见 `requirements.txt`。

## 路线图

- [x] v0.3.0-alpha — 候选包：7 模块 + 8 实验 + 单元测试 + 因果链报告
- [x] v0.3.1-alpha — 确定性仿真：`--seed` + golden sample + determinism test
- [x] Schema 文档 — scenario-input / simulation-output / risk-vector / runestone
- [x] v0.4.0-alpha — MetricAdapter + 电商客服适配器（CASE005）+ penalty + golden sample + MiniHub 两轮测试通过
- [x] v0.5.0-alpha — REST API 薄封装，FastAPI，本地优先
- [x] v0.6.0-alpha — SQLite 持久化 + 审计查询 API + retention / cleanup 机制
- [x] v0.7.0-alpha — 行业 CASE 包与验证套件：物流适配器 + 4 主 CASE（电商质检/物流质检/电商审计/物流审计）+ RiskVector 方案B + MiniHub 三轮测试通过
- [x] v0.7.2-alpha — 发布质量清理：版本元信息统一、API 422 弃用常量修复、测试 125 passed、README 边界说明
- [ ] v1.0-beta — 可公开推荐试用版

v0.7 已完成四个主 CASE 的第一阶段验证：
- CASE002：电商 AI 客服质检与系统优化样例
- CASE005：电商 AI 客服知识源冲突审计样例
- CASE006：物流 AI 客服知识源冲突审计样例
- CASE007：物流 AI 客服质检与系统优化样例

完整路线图参见 [QPP Wiki](https://gitee.com/full-spectrum/qpp/wikis/Home)。

### Schema 文档

| Schema | 文件 |
|--------|------|
| Scenario Input | [docs/schema/scenario-input-schema.md](docs/schema/scenario-input-schema.md) |
| Simulation Output | [docs/schema/simulation-output-schema.md](docs/schema/simulation-output-schema.md) |
| RiskVector | [docs/schema/risk-vector-schema.md](docs/schema/risk-vector-schema.md) |
| Runestone | [docs/schema/runestone-schema.md](docs/schema/runestone-schema.md) |

### MetricAdapter（v0.4）

```python
from src.adapters.ecommerce_adapter import EcommerceCustomerServiceAdapter
from simulate import run_simulation

adapter = EcommerceCustomerServiceAdapter()
metrics = {
    "refund_rate": 0.15,
    "complaint_rate": 0.12,
    "promise_conflict_rate": 0.22,
    "knowledge_source_conflict_rate": 0.18,
    "manual_handoff_rate": 0.28,
    "appeal_success_rate": 0.25,
    "resolution_satisfaction": 0.48,
    "response_time_score": 0.62,
    "policy_clarity_score": 0.45,
}
scenario = adapter.to_scenario(metrics, simulation_id="CASE005_DEMO")
result = run_simulation(scenario, seed=42)
```

### REST API（local-first, v0.7.2-alpha）

v0.7.2-alpha 沿用 v0.6 引入的 REST API、SQLite 持久化与审计查询能力。本版本只做发布质量清理与公开预览边界说明，API 仍然是本地优先开发接口，不是生产服务。

```bash
# 安装 API 依赖
pip install -e ".[api]"

# 启动服务（默认 127.0.0.1:8000）
python -m src.api.server

# API 文档
# http://127.0.0.1:8000/docs
```

当前主要端点：

```text
GET    /api/v1/health
POST   /api/v1/evaluate
POST   /api/v1/runestone
GET    /api/v1/decisions/{decision_id}
GET    /api/v1/audit/decisions
GET    /api/v1/audit/runestones
GET    /api/v1/audit/runestones/{runestone_id}
DELETE /api/v1/audit/decisions
```

```bash
# 健康检查
curl http://127.0.0.1:8000/api/v1/health

# 仿真评估 — 直接模式
curl -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"scenario": <scenario.json content>, "seed": 42}'

# 仿真评估 — 适配器模式
curl -X POST http://127.0.0.1:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"industry": "ecommerce_customer_service", "metrics": {...}, "seed": 42}'

# 符石生成
curl -X POST http://127.0.0.1:8000/api/v1/runestone \
  -H "Content-Type: application/json" \
  -d '{"decision": "W3", "reason": {"enterprise_id": "test", "rule_version": "v0.3"}, "risk_vector": {...}, "seed": 42}'

# 决策查询
curl http://127.0.0.1:8000/api/v1/decisions/{decision_id}

# 审计查询 — 决策列表
curl http://127.0.0.1:8000/api/v1/audit/decisions

# 审计查询 — 符石列表
curl http://127.0.0.1:8000/api/v1/audit/runestones

# 审计查询 — 单个符石
curl http://127.0.0.1:8000/api/v1/audit/runestones/{runestone_id}

# 数据清理（带安全阀：confirm=true + before=<UTC ISO> 或 all=true）
curl -X DELETE "http://127.0.0.1:8000/api/v1/audit/decisions?confirm=true&all=true"
```

**已知限制 (Known Limitations)：**

- 本地开发接口，不是生产级服务；
- 默认绑定 127.0.0.1；
- SQLite 为单进程本地持久化，不建议多 worker 并发写同一个 DB；
- 不做认证授权；
- 不上传企业数据；
- 不连接协议网络；
- 清理接口必须带安全确认参数（confirm + before/all）。

更多示例见 [examples/api_curl_examples.sh](examples/api_curl_examples.sh)。

## 许可证

双协议开源许可：木兰宽松许可证第2版 (Mulan PSL v2) + Apache License 2.0。详见 [LICENSE](LICENSE)。

## 相关仓库

- [full-spectrum-ethics](https://github.com/blackswan-ai-immunity/full-spectrum-ethics) — 公开协议规范层
- [QPP Wiki](https://gitee.com/full-spectrum/qpp/wikis/Home) — 项目总控台

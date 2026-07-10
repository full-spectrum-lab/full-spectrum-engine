# Schema: Scenario Input

> 版本：v0.7（语义修订）
> 作者：workbuddy
> 日期：2026-07-07
> 对应代码：`simulate.py` → `run_simulation(scenario: dict)`

---

## 1. 概述

Scenario Input 是 `simulate.py` 的输入配置文件（JSON 格式），描述一次仿真场景的初始条件。

```
scenario.json → simulate.py → simulation_output.json
```

---

## 2. 字段定义

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `simulation_id` | string | 否 | `SIM-{timestamp}` | 仿真唯一标识，用于输出追踪 |
| `input_query` | string | 否 | `""` | 场景的自然语言描述 |
| `sensitivity_level` | string | 否 | `"medium"` | 敏感度等级：`low` / `medium` / `high` |
| `enterprise_id` | string | 否 | `"default"` | 企业标识，用于 ReasonField `ESS-{enterprise_id}-{rule_version}` |
| `rule_version` | string | 否 | `"v0.3"` | 规则版本号 |
| `timestamp` | string | 否 | 自动生成 | ISO 8601 时间戳（输出用） |
| `timestamp_unix` | float | 否 | 自动生成 | Unix 时间戳（Runestone 用） |
| `initial_state` | object | 否 | 见下 | 文明状态初始值 |
| `agents` | array | 否 | 内置默认 | Agent 配置列表 |
| `weights` | object | 否 | 见下 | FSHI 权重配置 |
| `ess_horizon` | int | 否 | `5` | ESS 推演时间步 |
| `ess_candidates` | int | 否 | `10` | ESS 候选路径数 |
| `conflict_density` | float | 否 | `0.0` | 冲突密度 [0,1]，用于紧急制动 |
| `reversibility` | float | 否 | `0.5` | **不可逆风险强度** [0,1]，用于 RiskVector。字段名保留 `reversibility` 以兼容协议规范，但语义为 **irreversibility**（值越高 = 决策后果越不可逆/越难撤销）。代码层支持 `irreversibility` 和 `reversibility` 双字段兼容 |
| `diffusivity` | float | 否 | `0.3` | 扩散性 [0,1]，用于 RiskVector |

---

## 3. 子对象定义

### 3.1 initial_state

| 字段 | 类型 | 范围 | 默认值 | 说明 |
|------|------|------|--------|------|
| `survival` | float | [0, 1] | 0.7 | S_l 生存层 |
| `coordination` | float | [0, 1] | 0.6 | S_m 协调层 |
| `meaning` | float | [0, 1] | 0.5 | S_h 意义层 |

### 3.2 agents[]

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | Agent 类型：`AI` / `Human` / `Regulator` / `Enterprise` |
| `weight` | float | 权重 [0,1]，所有 agent 权重之和应为 1.0 |

> 注意：当前版本 `simulate.py` 使用内置默认 Agent（`create_default_agents()`），`agents` 字段仅用于记录配置，不影响实际 Agent 创建。

### 3.3 weights

| 字段 | 类型 | 范围 | 默认值 | 说明 |
|------|------|------|--------|------|
| `survival` | float | [0, 1] | 0.40 | w_l 生存权重 |
| `coordination` | float | [0, 1] | 0.35 | w_m 协调权重 |
| `meaning` | float | [0, 1] | 0.25 | w_h 意义权重 |

> 约束：`survival + coordination + meaning = 1.0`

---

## 4. 完整示例

```json
{
  "simulation_id": "CASE001_REFUND_CONFLICT",
  "input_query": "用户申请退款，但商家以'已拆封'为由拒绝，平台需要裁决是否强制退款",
  "sensitivity_level": "high",
  "enterprise_id": "ecommerce-platform",
  "rule_version": "v0.3",
  "initial_state": {
    "survival": 0.72,
    "coordination": 0.45,
    "meaning": 0.55
  },
  "agents": [
    {"type": "AI", "weight": 0.40},
    {"type": "Human", "weight": 0.20},
    {"type": "Regulator", "weight": 0.25},
    {"type": "Enterprise", "weight": 0.15}
  ],
  "weights": {
    "survival": 0.40,
    "coordination": 0.35,
    "meaning": 0.25
  },
  "ess_horizon": 5,
  "ess_candidates": 10,
  "conflict_density": 0.6,
  "reversibility": 0.57,
  "diffusivity": 0.5
}
```

---

## 5. 校验规则

| 规则 | 检查方式 |
|------|---------|
| `initial_state.*` 在 [0,1] 区间 | `CivilizationState.__post_init__` 自动 clamp |
| `weights` 三项之和 = 1.0 | `FSHIConfig.validate()` 校验 |
| `sensitivity_level` 在枚举内 | 建议校验（当前未强制） |
| `agents` 权重之和 = 1.0 | 建议校验（当前未强制） |
| `reversibility` / `irreversibility` 在 [0,1] | 建议校验（当前未强制）。注意：语义为不可逆程度，值越高越不可逆。代码层支持双字段兼容：`scenario.get("irreversibility", scenario.get("reversibility", 0.5))` |

---

## 6. 与协议仓的关系

Scenario Input 是引擎内部格式，不直接进入协议仓（`full-spectrum-ethics`）。

协议仓的 CASE 样例（`CASE001-005`）是业务层描述，需要通过 MetricAdapter（v0.4+）映射为 Scenario Input。

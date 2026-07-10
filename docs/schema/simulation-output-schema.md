# Schema: Simulation Output

> 版本：v0.3.1
> 作者：workbuddy
> 日期：2026-07-04
> 对应代码：`simulate.py` → `run_simulation()` 返回值

---

## 1. 概述

Simulation Output 是 `simulate.py` 的完整输出（JSON 格式），包含一次仿真的全部结构化结果。

---

## 2. 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `simulation_id` | string | 仿真唯一标识（透传输入） |
| `timestamp` | string | ISO 8601 时间戳 |
| `input_query` | string | 场景描述（透传输入） |
| `sensitivity_level` | string | 敏感度等级（透传输入） |
| `initial_state` | object | 初始文明状态 |
| `final_state` | object | 仿真后文明状态 |
| `fshi` | object | FSHI 频段健康指数 |
| `ess` | object | ESS 伦理觉性模拟器结果 |
| `validation` | object | 校验结果（梦蝶 + 觉性炸弹 + 紧急制动） |
| `risk_vector` | object | 八维语义风险向量（引擎内部格式） |
| `runestone` | object | 符石审计令牌 |
| `causal_chain` | object | 因果链报告 |

---

## 3. 子对象定义

### 3.1 initial_state / final_state

```json
{
  "survival": 0.7287,
  "coordination": 0.4588,
  "meaning": 0.5565
}
```

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `survival` | float | [0, 1] | S_l 生存层 |
| `coordination` | float | [0, 1] | S_m 协调层 |
| `meaning` | float | [0, 1] | S_h 意义层 |

### 3.2 fshi

```json
{
  "value": 59.12,
  "risk_level": "WARNING",
  "weights": {
    "survival": 0.40,
    "coordination": 0.35,
    "meaning": 0.25
  }
}
```

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `value` | float | [0, 100] | FSHI = w_l·S_l + w_m·S_m + w_h·S_h) × 100 |
| `risk_level` | string | 枚举 | `EXCELLENT` ≥80 / `NORMAL` ≥60 / `WARNING` ≥40 / `CRISIS` ≥20 / `CRITICAL` <20 |
| `weights` | object | — | 使用的权重配置 |

### 3.3 ess

```json
{
  "selected_option": "PATH-001",
  "horizon": 5,
  "paths": [
    {
      "option": "PATH-001",
      "selected": true,
      "total_pain": 6.2881,
      "low_freq": 0.479,
      "mid_freq": 0.3384,
      "high_freq": 0.2765
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `selected_option` | string | 选中的路径 ID |
| `horizon` | int | 推演时间步 |
| `paths[]` | array | 候选路径列表 |
| `paths[].option` | string | 路径 ID |
| `paths[].selected` | bool | 是否被选中 |
| `paths[].total_pain` | float | 总痛苦值 |
| `paths[].low_freq` | float | 低频（生存）影响 |
| `paths[].mid_freq` | float | 中频（信任）影响 |
| `paths[].high_freq` | float | 高频（意义）影响 |

### 3.4 validation

```json
{
  "dream_butterfly_passed": true,
  "dream_butterfly_reason": "OK",
  "bomb_triggered": false,
  "bomb_reason": "",
  "brake_state": "NORMAL"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `dream_butterfly_passed` | bool | 梦蝶校验是否通过 |
| `dream_butterfly_reason` | string | 校验原因说明 |
| `bomb_triggered` | bool | 觉性炸弹是否触发 |
| `bomb_reason` | string | 触发原因（未触发则为空） |
| `brake_state` | string | 紧急制动状态：`NORMAL` / `WARNING` / `BRAKE` |

### 3.5 risk_vector

见 [RiskVector Schema](risk-vector-schema.md)。

### 3.6 runestone

见 [Runestone Schema](runestone-schema.md)。

### 3.7 causal_chain

```json
{
  "causal_chain_id": "CC-20260704-a1b2c3d4",
  "timestamp": "2026-07-04T00:00:00Z",
  "version": "1.0",
  "system_state": {
    "current_state": "WARNING",
    "judgment_basis": ["FSHI=59.12 (WARNING)", "..."],
    "spectrum_priority": "coordination"
  },
  "ess_decision_context": {
    "candidate_options": ["PATH-001", "PATH-002", "PATH-003"],
    "selected_option": "PATH-001",
    "horizon": 5
  },
  "causal_paths": [
    {
      "path_id": "PATH-001",
      "option": "PATH-001",
      "selected": true,
      "frequency_impacts": {
        "低频": {"seed_type": "生存保障", "intensity": 0.479, "description": "..."},
        "中频": {"seed_type": "信任修复", "intensity": 0.338, "description": "..."},
        "高频": {"seed_type": "意义守护", "intensity": 0.277, "description": "..."}
      },
      "total_pain": 6.2881,
      "chain_visual": "低频(0.48) → 中频(0.34) → 高频(0.28)"
    }
  ],
  "dream_butterfly_validation": {
    "passed": true,
    "reason": "OK",
    "bomb_triggered": false,
    "bomb_reason": ""
  },
  "soul_account": {
    "initial_balance": 100,
    "debits": [...],
    "credits": [...],
    "balance": 80,
    "health_status": "亚健康"
  },
  "who_hurts": {
    "低频": {"pain_bearer": "基层开发者", "description": "..."},
    "中频": {"pain_bearer": "合作伙伴", "description": "..."},
    "高频": {"pain_bearer": "决策者", "description": "..."}
  },
  "frequency_plan": {
    "recommendation": "优先修复中频信任...",
    "priority": "coordination",
    "interventions": [...]
  },
  "full_chain_narrative": "本次决策推演识别到..."
}
```

---

## 4. 确定性输出

当 `--seed` 参数提供时：

| 字段 | 确定性来源 |
|------|-----------|
| `timestamp` | 固定为 `2026-07-04T00:00:00Z`（或 `--fixed-time`） |
| `runestone.runestone_id` | 基于 seed + sim_id + selected_option + risk_vector 的 SHA256 |
| `runestone.timestamp` | 固定为 `1783123200.0 + seed` |
| `causal_chain.causal_chain_id` | 基于 seed + sim_id + selected_option + timestamp 的 SHA256 |
| `ess.paths` | np.random.seed(seed) 固定 ESS 随机路径 |

不带 `--seed` 时，以上字段每次运行都会变化。

---

## 5. 与协议仓的关系

Simulation Output 是引擎内部格式。未来通过桥接层（v0.5+）可导出为：

- `CrossEnterpriseAuditRecord`（协议仓 RFC 0006）
- `RiskVector`（协议仓 FSP_RiskVector，见 RiskVector Schema 映射表）

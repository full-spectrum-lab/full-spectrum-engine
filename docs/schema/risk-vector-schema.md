# Schema: RiskVector（八维语义风险向量）

> 版本：v0.7（语义修订）
> 作者：workbuddy
> 日期：2026-07-07
> 对应代码：`src/bridge/runestone.py` → `RiskVector` dataclass
> 协议仓对应：`FSP_RiskVector_v0.1_内部草案`

---

## 1. 概述

RiskVector 是引擎内部的风险评估结构，描述一次仿真决策在八个语义维度上的风险分布。

```
CivilizationState + Scenario 配置 → RiskVector(8 维) → 嵌入 Runestone
```

---

## 2. 八维字段定义

| 序号 | 字段名 | 类型 | 范围 | 语义含义 |
|------|--------|------|------|---------|
| 1 | `survival_impact` | float | [0, 1] | 生存层冲击：值越高表示生存受到的威胁越大 |
| 2 | `trust_impact` | float | [0, 1] | 信任层冲击：值越高表示协调/信任受损越严重 |
| 3 | `meaning_impact` | float | [0, 1] | 意义层冲击：值越高表示意义方向越模糊 |
| 4 | `reversibility` | float | [0, 1] | **不可逆风险强度**（字段名保留 `reversibility` 以兼容协议规范，但语义为 **irreversibility / rollback_difficulty**）：值越高表示决策后果越难撤销、越不可逆。后续协议版本可能重命名为 `rollback_difficulty` |
| 5 | `explainability` | float | [0, 1] | 可解释性：值越高表示决策过程越透明可审计 |
| 6 | `diffusivity` | float | [0, 1] | 扩散性：值越高表示风险越容易扩散到其他系统/企业 |
| 7 | `urgency` | float | [0, 1] | 紧急度：值越高表示需要越快响应 |
| 8 | `uncertainty` | float | [0, 1] | 不确定性：值越高表示预测可靠度越低 |

> ⚠️ **reversibility 语义说明**：该字段名保留 `reversibility` 是为了兼容协议规范（full-spectrum-ethics），但其语义为 **irreversibility**（不可逆程度）。值越高 = 决策后果越不可逆、越难撤销。例如：
> - 冷链物流 `irreversibility=0.85`（最高，物理不可逆）
> - 国际件 `irreversibility=0.80`（跨境流程不可逆）
> - 电商客服 `irreversibility=0.57`（退款流程部分可逆）
> - 普快物流 `irreversibility=0.50`
> - 面单打印 `irreversibility=0.45`（最可逆）

---

## 3. 引擎中的计算方式

在 `simulate.py` 中，RiskVector 由仿真结果动态构造：

```python
risk_vector = RiskVector(
    survival_impact=1.0 - S_new.survival,       # 生存越低，冲击越大
    trust_impact=1.0 - S_new.coordination,       # 协调越低，信任冲击越大
    meaning_impact=1.0 - S_new.meaning,          # 意义越低，意义冲击越大
    reversibility=scenario.get("irreversibility", scenario.get("reversibility", 0.5)),  # 语义为 irreversibility：值越高越不可逆
    explainability=0.8,                           # 固定值（v0.4 将由 MetricAdapter 提供）
    diffusivity=scenario.get("diffusivity", 0.3), # 来自场景配置
    urgency=0.1 if risk_level in ("EXCELLENT", "NORMAL") else 0.5,  # FSHI 驱动
    uncertainty=0.2,                              # 固定值（v0.4 将由 L0 观测层提供）
)
```

| 字段 | 当前来源 | v0.4+ 来源 |
|------|---------|-----------|
| `survival_impact` | `1.0 - S_l`（引擎计算） | MetricAdapter 映射 |
| `trust_impact` | `1.0 - S_m`（引擎计算） | MetricAdapter 映射 |
| `meaning_impact` | `1.0 - S_h`（引擎计算） | MetricAdapter 映射 |
| `reversibility` | scenario 配置（语义为 irreversibility） | 行业 CASE 模板（irreversibility 值） |
| `explainability` | 固定 0.8 | 企业系统审计接口 |
| `diffusivity` | scenario 配置 | 行业 CASE 模板 |
| `urgency` | FSHI risk_level 驱动 | L0 实时观测 |
| `uncertainty` | 固定 0.2 | L0 观测层置信度 |

---

## 4. 约束行为

`RiskVector.__post_init__` 会对所有 8 个字段执行 clamp：

```python
for k, v in self.__dict__.items():
    setattr(self, k, max(0.0, min(1.0, v)))
```

- 值 < 0 → 强制为 0.0
- 值 > 1 → 强制为 1.0
- 确保所有维度严格落在 [0, 1] 区间

---

## 5. JSON 序列化

`RiskVector.to_dict()` 输出：

```json
{
  "survival_impact": 0.2713,
  "trust_impact": 0.5412,
  "meaning_impact": 0.4435,
  "reversibility": 0.57,
  "explainability": 0.8,
  "diffusivity": 0.5,
  "urgency": 0.5,
  "uncertainty": 0.2
}
```

> 注意：`reversibility` 字段语义为 **irreversibility**（不可逆程度），值越高 = 越不可逆。上面示例值 0.57 表示电商客服场景的不可逆程度（部分可逆）。

在 Simulation Output 中，该对象位于顶层 `risk_vector` 字段，同时嵌入 `runestone.risk_vector`。

---

## 6. 与协议仓的映射

引擎内部 RiskVector（8 维）与协议仓 `FSP_RiskVector`（草案）的映射关系：

| 引擎字段 | 协议仓 FSP_RiskVector 字段 | 说明 |
|---------|---------------------------|------|
| `survival_impact` | `survival_impact` | 直接对应 |
| `trust_impact` | `trust_impact` | 直接对应 |
| `meaning_impact` | `meaning_impact` | 直接对应 |
| `reversibility` | `reversibility` | 字段名相同，引擎语义为 irreversibility（值越高越不可逆） |
| `explainability` | `explainability` | 直接对应 |
| `diffusivity` | `diffusivity` | 直接对应 |
| `urgency` | `urgency` | 直接对应 |
| `uncertainty` | `uncertainty` | 直接对应 |

> 当前引擎版本与协议仓草案字段完全对齐。协议仓的评分口径（`RiskVector评分口径_v0.1`）定义了如何将 8 维向量聚合成一个综合风险分，引擎暂不实现聚合逻辑。

---

## 7. CASE 样例

协议仓 CASE002 的 RiskVector 样例（供参考）：

```json
{
  "case_id": "CASE002",
  "scenario": "平台强制执行退款",
  "risk_vector": {
    "survival_impact": 0.30,
    "trust_impact": 0.65,
    "meaning_impact": 0.45,
    "reversibility": 0.57,
    "explainability": 0.75,
    "diffusivity": 0.55,
    "urgency": 0.60,
    "uncertainty": 0.25
  }
}
```

CASE005（电商客服，v0.4 MetricAdapter 目标）的预期 RiskVector：

```json
{
  "case_id": "CASE005",
  "scenario": "电商客服自动化决策",
  "risk_vector": {
    "survival_impact": 0.15,
    "trust_impact": 0.40,
    "meaning_impact": 0.30,
    "reversibility": 0.57,
    "explainability": 0.70,
    "diffusivity": 0.35,
    "urgency": 0.25,
    "uncertainty": 0.30
  }
}
```

CASE006（物流客服，v0.7 新增）的预期 RiskVector（冷链场景，irreversibility 最高）：

```json
{
  "case_id": "CASE006",
  "scenario": "冷链物流知识源冲突",
  "risk_vector": {
    "survival_impact": 0.30,
    "trust_impact": 0.45,
    "meaning_impact": 0.35,
    "reversibility": 0.85,
    "explainability": 0.60,
    "diffusivity": 0.65,
    "urgency": 0.50,
    "uncertainty": 0.40
  }
}
```

> 注意：所有 CASE 样例中 `reversibility` 字段语义为 **irreversibility**（不可逆程度），值越高 = 越不可逆。CASE006 冷链场景 `reversibility=0.85` 是当前最高不可逆值。

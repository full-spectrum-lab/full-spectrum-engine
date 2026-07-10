# Schema: Runestone（符石审计令牌）

> 版本：v0.3.1
> 作者：workbuddy
> 日期：2026-07-04
> 对应代码：`src/bridge/runestone.py` → `Runestone` dataclass
> 协议仓对应：`CrossEnterpriseAuditRecord`（RFC 0006，未来桥接）

---

## 1. 概述

Runestone（符石）是引擎产出的不可篡改审计令牌，记录一次完整决策的上下文、风险向量、ESS 快照和因果链引用。它是跨企业审计记录（协议层）的引擎内部前身。

```
ESS 决策 + RiskVector + Agent Trail → Runestone.create() → 嵌入 Simulation Output
```

---

## 2. 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `runestone_id` | string | 是 | 符石唯一标识。默认 `RS_{uuid4.hex[:16]}`；seed 模式下为 `RS_{sha256[:16]}` |
| `timestamp` | float | 是 | Unix 时间戳。默认 `time.time()`；seed 模式下为 `1783123200.0 + seed` |
| `decision` | string | 是 | 决策标识，即 ESS 选中的路径 ID（如 `PATH-001`） |
| `reason` | string | 是 | 决策来源标识，格式 `ESS-{enterprise_id}-{rule_version}` |
| `risk_vector` | object | 是 | 八维语义风险向量，见 [RiskVector Schema](risk-vector-schema.md) |
| `parent_runestone` | string\|null | 否 | 父符石 ID，用于链式验证（当前版本不使用） |
| `agent_trail` | array[string] | 否 | 参与决策的 Agent 名称列表 |
| `ess_snapshot` | object | 否 | ESS 推演快照 |
| `causal_chain` | object\|null | 否 | 因果链报告引用（当前版本在 output 顶层单独输出） |
| `signature` | string\|null | 否 | 签名（当前版本为 null，v0.6+ 持久化层实现） |

---

## 3. ess_snapshot 子对象

```json
{
  "horizon": 5,
  "num_paths": 10,
  "selected_pain": 6.2881
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `horizon` | int | ESS 推演时间步 |
| `num_paths` | int | 候选路径总数 |
| `selected_pain` | float | 选中路径的总痛苦值 |

---

## 4. Reason 字段格式

`reason` 字段遵循 `ReasonField` 协议：

```
ESS-{enterprise_id}-{rule_version}
```

示例：
- `ESS-ecommerce-platform-v0.3`
- `ESS-default-v0.3`

`ReasonField.parse()` 可反向解析：

```python
rf = ReasonField.parse("ESS-ecommerce-platform-v0.3")
# rf.enterprise_id = "ecommerce-platform"
# rf.rule_version = "v0.3"
```

---

## 5. 创建方式

### 5.1 随机模式（默认）

```python
runestone = Runestone.create(
    decision=ess_result.selected_option,
    reason=str(reason_field),
    risk_vector=risk_vector,
    agents=[a.get_name() for a in agents],
    ess_data={...},
)
# runestone_id = "RS_a1b2c3d4e5f67890" (随机 UUID)
# timestamp = 1754567890.123 (当前时间)
```

### 5.2 确定性模式（seed）

```python
runestone = Runestone.create(
    decision=ess_result.selected_option,
    reason=str(reason_field),
    risk_vector=risk_vector,
    agents=[...],
    ess_data={...},
    runestone_id=stable_id,  # 基于 seed + payload 的 SHA256
    timestamp=fixed_ts,      # 1783123200.0 + seed
)
# runestone_id = "RS_9f8e7d6c5b4a3928" (确定性)
# timestamp = 1783123242.0 (确定性)
```

确定性 ID 的计算 payload：

```python
deterministic_payload = {
    "seed": seed,
    "simulation_id": sim_id,
    "selected_option": ess_result.selected_option,
    "reason": str(reason_field),
    "risk_vector": risk_vector.to_dict(),
    "ess": {
        "horizon": ess_result.horizon,
        "num_paths": len(ess_result.paths),
        "selected_pain": ess_result.paths[0].total_pain,
    },
}
runestone_id = "RS_" + sha256(json.dumps(payload, sort_keys=True))[:16]
```

---

## 6. 链式验证

`compute_hash()` 和 `verify_chain()` 支持符石链验证：

```python
# 计算哈希（排除 signature 字段）
hash_val = runestone.compute_hash()

# 验证父子链
is_valid = child.verify_chain(parent)
# 检查 child.parent_runestone == parent.runestone_id
# 且 child.compute_hash() != parent.compute_hash()
```

> 当前版本未使用链式验证（`parent_runestone` 始终为 null）。v0.6 SQLite 持久化层将启用。

---

## 7. JSON 序列化

`Runestone.to_dict()` 输出：

```json
{
  "runestone_id": "RS_9f8e7d6c5b4a3928",
  "timestamp": 1783123242.0,
  "decision": "PATH-001",
  "reason": "ESS-ecommerce-platform-v0.3",
  "risk_vector": {
    "survival_impact": 0.2713,
    "trust_impact": 0.5412,
    "meaning_impact": 0.4435,
    "reversibility": 0.4,
    "explainability": 0.8,
    "diffusivity": 0.5,
    "urgency": 0.5,
    "uncertainty": 0.2
  },
  "parent_runestone": null,
  "agent_trail": ["AI-Agent", "Human-Agent", "Regulator-Agent", "Enterprise-Agent"],
  "ess_snapshot": {
    "horizon": 5,
    "num_paths": 10,
    "selected_pain": 6.2881
  },
  "causal_chain": null,
  "signature": null
}
```

在 Simulation Output 中，该对象位于顶层 `runestone` 字段。

---

## 8. 与协议仓的关系

Runestone 是引擎内部格式，未来通过桥接层（v0.5+）可导出为协议仓的 `CrossEnterpriseAuditRecord`（RFC 0006）。

映射关系：

| Runestone 字段 | CrossEnterpriseAuditRecord 字段 | 说明 |
|---------------|-------------------------------|------|
| `runestone_id` | `record_id` | 直接映射 |
| `timestamp` | `created_at` | Unix → ISO 8601 转换 |
| `decision` | `decision_summary` | 路径 ID → 决策摘要 |
| `reason` | `rule_ref` | ESS 格式 → 协议引用 |
| `risk_vector` | `risk_vector` | 直接映射 |
| `parent_runestone` | `parent_record_id` | 直接映射 |
| `agent_trail` | `participants` | 名称 → 参与者标识 |
| `ess_snapshot` | `evidence_bundle` | 快照 → 证据包 |
| `signature` | `signature` | 签名机制对齐 |

> 协议层增加了 `enterprise_signature`、`guardian_endorsements` 等多签字段，引擎层暂不实现。

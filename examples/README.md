# Examples

本目录存放 full-spectrum-engine 的最小运行样例。

当前样例均为合成数据，不代表任何真实企业、真实用户或真实业务系统。

v0.8 public beta 要求所有核心样例都满足三件事：

1. 能直接运行；
2. 能通过 `--seed` 复现；
3. 能和 golden sample 做结构对比。

---

## 1. 电商退款冲突

文件：

```text
examples/scenario_refund_conflict.json
```

运行：

```bash
python simulate.py --config examples/scenario_refund_conflict.json
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

用途：

- 模拟用户退款、商家规则、平台裁决之间的冲突；
- 观察 FSHI、ESS、RiskVector、Runestone、CausalChain 的完整输出；
- 作为 FSHI 电商适配的早期样例。

---

## 2. 企业知识源冲突

文件：

```text
examples/scenario_knowledge_conflict.json
```

运行：

```bash
python simulate.py --config examples/scenario_knowledge_conflict.json
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42
```

用途：

- 模拟 AI 助手与企业知识库对同一问题给出矛盾答案；
- 展示知识源冲突如何进入风险显影；
- 为后续“平台规则、商家规则、商品知识、订单状态、客服话术”适配提供锚点。

---

## 3. 样例设计原则

所有公开样例应遵守：

1. 不使用真实企业数据；
2. 不使用真实用户隐私；
3. 不暗示已有真实客户部署；
4. 不把推演结果描述为法律或合规裁决；
5. 保留“人类/企业最终复核”的边界。

---

## 4. v0.8 public beta golden sample

当前 public beta 对外保留两组固定样例：

```text
test-records/v0.8-public-beta/golden_refund_seed42.json
test-records/v0.8-public-beta/golden_knowledge_seed42.json
```

推荐验证命令：

```bash
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1
```

---

## 5. 后续样例方向

建议逐步补充：

- `scenario_customer_service_escalation.json`：客服情绪升级；
- `scenario_multi_agent_permission_conflict.json`：多 Agent 权限冲突；
- `scenario_cross_enterprise_audit.json`：跨企业审计记录；
- `scenario_cell_boundary.json`：细胞协议边界声明；
- `scenario_logistics_customer_service.json`：物流客服质检；
- `scenario_ecommerce_product_knowledge.json`：电商商品知识冲突。


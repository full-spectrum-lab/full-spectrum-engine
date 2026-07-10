# 5 分钟跑通 full-spectrum-engine

> 目标：让第一次进入仓库的人，在不理解全频谱全部理论的情况下，也能本地跑通一次完整推演。

---

## 1. 前提

- Python 3.10+
- 可访问 Gitee
- 本地不需要数据库
- 本地不需要外部 API Key
- 本地不需要接入全频谱协议网络

---

## 2. 安装

```bash
git clone https://gitee.com/full-spectrum/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt
```

---

## 3. 运行第一个样例

```bash
python simulate.py --config examples/scenario_refund_conflict.json
```

你会看到一段 JSON 输出，里面包含：

- `fshi`：当前状态的全频谱健康指数；
- `ess`：ESS 推演选择了哪条路径；
- `validation`：梦蝶校验、觉性炸弹、紧急制动状态；
- `risk_vector`：风险向量；
- `runestone`：符石审计令牌；
- `causal_chain`：因果链报告。

---

## 3.1 生成可复现输出

如果你希望每次运行得到完全一致的输出，可以指定随机种子：

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

`--seed` 会固定 ESS 推演随机路径、符石 ID、符石时间戳与因果链 ID。这样生成的结果可以作为 golden sample，用于 CI 或版本升级前后的回归比较。

如需指定展示时间戳，可额外传入：

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --fixed-time 2026-07-04T00:00:00Z
```

---

## 4. 把结果写入文件

```bash
python simulate.py --config examples/scenario_refund_conflict.json --output output/refund-result.json
```

如果 `output/` 不存在，请先创建：

```bash
mkdir output
```

---

## 5. 运行第二个样例

```bash
python simulate.py --config examples/scenario_knowledge_conflict.json
```

这个样例模拟的是“AI 助手与企业知识库对同一问题给出矛盾答案”的情况。

---

## 6. 运行单元测试

```bash
python -m pytest tests -v
```

如果你不想使用 pytest，也可以运行 Python 内置 unittest：

```bash
python -m unittest tests.test_bomb -v
python -m unittest tests.test_simulate_determinism -v
```

---

## 7. 运行实验脚本

```bash
python experiments/experiment_A_baseline.py
python experiments/experiment_B_ess.py
python experiments/experiment_C_l0_ess.py
```

完整实验 A-H 位于：

```text
experiments/
```

---

## 8. 你应该如何理解输出

### FSHI

FSHI 是三频健康指数，用于描述当前系统状态：

- 低频：生存与基本安全；
- 中频：信任、协作与关系；
- 高频：意义、方向与长期演化。

### ESS

ESS 是推演器。它不替代企业、人类或组织做最终决定，而是把不同路径的后果显影出来。

### RiskVector

RiskVector 是风险压缩格式。它把复杂冲突压缩为几个可比较的维度，例如信任影响、意义影响、可逆性、可解释性等。

### Runestone

Runestone 是符石审计令牌，用于记录“这次判断从哪里来、依据什么、留下什么审计线索”。

---

## 9. 当前阶段边界

当前版本是：

```text
v0.3 alpha / experimental engine
```

它可以用于：

- 本地实验；
- 推演样例；
- 协议验证；
- 内部方法论演示；
- 早期开发者理解全频谱引擎结构。

它暂不应被描述为：

- 成熟生产系统；
- 已被企业大规模部署的系统；
- 法律、监管或合规裁决工具；
- 能直接替代人类决策的自动裁决系统。

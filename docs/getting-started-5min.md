# 5 分钟跑通 full-spectrum-engine

> 目标：第一次进入仓库的人，在不了解完整理论背景的前提下，也能本地跑通一次完整推演。

---

## 1. 前提

- Python 3.10+
- 可访问 GitHub 或 Gitee
- 本地不需要外部数据库
- 本地不需要外部 API Key
- 本地不需要加入全频谱协议网络

---

## 2. 安装

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt
```

如使用 Gitee：

```bash
git clone https://gitee.com/full-spectrum/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt
```

---

## 3. 跑第一个样例

```bash
python simulate.py --config examples/scenario_refund_conflict.json
```

你会看到一段 JSON 输出，核心字段包括：

- `fshi`：当前状态的全频谱健康指数
- `ess`：ESS-lite 给出的建议路径
- `validation`：边界校验、炸弹校验、紧急制动状态
- `risk_vector`：压缩后的风险向量
- `runestone`：审计令牌
- `causal_chain`：因果链说明

---

## 4. 跑可复现输出

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

`--seed` 会固定：

- ESS-lite 路径选择
- `Runestone` ID
- 因果链 ID
- 输出时间戳

如需进一步固定展示时间：

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --fixed-time 2026-07-04T00:00:00Z
```

---

## 5. 将结果写入文件

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --output output/refund-result.json
```

如果 `output/` 不存在，请先创建：

```bash
mkdir output
```

---

## 6. 跑第二个样例

```bash
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42
```

这个样例模拟的是：

> AI 助手与企业知识源对同一问题给出冲突判断，需要把冲突显影为可复核的治理输出。

---

## 7. 跑 public beta 验证脚本

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1
```

这个脚本会顺序执行：

1. deterministic tests
2. golden sample regression
3. 重新生成临时样本并与仓库内 golden sample 对比
4. 完整 `pytest`

---

## 8. 跑测试

```bash
python -m pytest tests -v
```

如果你只想先验证可复现性：

```bash
python -m unittest tests.test_simulate_determinism -v
python -m unittest tests.test_golden_samples -v
```

---

## 9. 启动本地 API

```bash
pip install -e ".[api]"
python -m src.api.server
```

启动后访问：

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 10. 如何理解当前阶段

当前版本是：

```text
v0.8.0-beta / local-first public beta
```

它适合用于：

- 本地实验
- 样例推演
- 协议输出验证
- 内部方法论演示
- 早期开源评审

它暂时不应用于：

- 高后果生产自动裁决
- 法律/监管替代判断
- 跨组织在线治理
- 无人工复核的企业自动执行

---

## 11. 下一步看什么

建议按这个顺序继续：

1. [docs/local-first-engine.md](local-first-engine.md)
2. [docs/api-reference-v0.8.md](api-reference-v0.8.md)
3. [docs/troubleshooting.md](troubleshooting.md)
4. [examples/README.md](../examples/README.md)
5. [test-records/README.md](../test-records/README.md)

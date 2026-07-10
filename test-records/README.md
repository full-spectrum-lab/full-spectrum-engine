# Test Records

本目录用于保存 full-spectrum-engine 的本地验证留痕。

它不是正式测试框架的一部分，而是项目早期为了可追溯而保留的运行证据。

---

## 1. 当前记录

```text
test-records/2026-07-04-v0.3-candidate/
test-records/v0.8-public-beta/
```

包含：

- Python 编译检查；
- 单元测试输出；
- 实验 A-H 输出；
- CLI 样例输出。
- 固定随机种子的 golden sample。

其中：

```text
golden_refund_seed42.json
golden_knowledge_seed42.json
```

是通过 `--seed 42` 生成的可复现输出，用于检查后续版本是否破坏主输出结构。

v0.8 public beta 额外要求：

- 固定场景 + 固定 seed 产出必须稳定；
- golden sample 必须可以被自动脚本校验；
- 测试记录既能给人看，也能给 CI / 镜像同步看。

---

## 2. 为什么保留这些文件

全频谱项目强调：

> 不只说“能跑”，还要留下“怎么跑、跑出了什么、谁验证过”的痕迹。

因此早期版本会保留文本化测试输出，方便：

- AI 接力；
- 人类复核；
- 版本回溯；
- 后续 release note 编写；
- 对比不同版本的行为变化。

---

## 3. 如何重新生成

```bash
python -m compileall .
python -m unittest tests.test_bomb -v
python experiments/experiment_A_baseline.py
python experiments/experiment_B_ess.py
python experiments/experiment_C_l0_ess.py
python experiments/experiment_D_guardian_short.py
python experiments/experiment_E_guardian_long.py
python experiments/experiment_F_frequency.py
python experiments/experiment_G_threshold.py
python experiments/experiment_H_stress.py
python simulate.py --config examples/scenario_refund_conflict.json --output test-records/2026-07-04-v0.3-candidate/simulate_refund_conflict.json
python simulate.py --config examples/scenario_knowledge_conflict.json --output test-records/2026-07-04-v0.3-candidate/simulate_knowledge_conflict.json
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --output test-records/2026-07-04-v0.3-candidate/golden_refund_seed42.json
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42 --output test-records/2026-07-04-v0.3-candidate/golden_knowledge_seed42.json

# v0.8 public beta
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --output test-records/v0.8-public-beta/golden_refund_seed42.json
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42 --output test-records/v0.8-public-beta/golden_knowledge_seed42.json
powershell -ExecutionPolicy Bypass -File scripts/validate-public-beta.ps1
```

---

## 4. 后续建议

当项目进入更稳定阶段后，应逐步减少大体积静态输出文件，改为：

- CI artifact；
- 结构化 snapshot；
- 固定随机种子的 golden sample；
- schema 校验；
- release 附件。

当前保留完整输出，是为了早期协作和断联接力。

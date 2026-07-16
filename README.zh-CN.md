# Full Spectrum Engine

[English](README.md) · [简体中文](README.zh-CN.md)

> 用于可复现 AI 检查、风险可见性、审计追踪和可解释仿真的本地优先治理运行时。

[![CI](https://github.com/full-spectrum-lab/full-spectrum-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/full-spectrum-lab/full-spectrum-engine/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Mulan%20PSL%20v2%20%2F%20Apache%202.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/Status-v1.5.0--enterprise__pilot__candidate-success)](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.5.0)

## 版本真相

| 版本 | GitHub 状态 | 准确含义 |
|---|---|---|
| [`v1.4.0`](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.4.0) | **最新正式版** | Replay 与 Audit 加固基线 |
| [`v1.5.0`](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.5.0) | **预发布** | 企业试点候选，在 v1.4 上增加受控企业能力 |
| [`v1.0.0`](https://github.com/full-spectrum-lab/full-spectrum-engine/releases/tag/v1.0.0) | 历史正式基线 | 首个稳定的本地优先合同版本 |

`v1.5.0` 已在 Gitee 和 GitHub 建立 Release；其 pre-release 标记是有意保留的边界，不代表生产级企业治理平台已经完成。

## 能做什么

- 本地运行确定性治理仿真；
- 生成 RiskVector、Runestone、AuditTrace 和结构化报告；
- 固定随机种子和 golden fixture 后复现输出；
- 通过本地 REST API 或 CLI 调用；
- 使用治理链 CLI 将业务输入转换为 Governance Event、Canonical Context、Cell Manifest、Output Envelope、Enterprise Writeback 与报告；
- v1.5 增加配置/秘密分离、最小 RBAC、脱敏、人工复核、韧性、可观测性、备份回滚和默认关闭写回的 Connector 合同。

## 不做什么

- 不替代法律、合规或企业责任人；
- 不自动执行退款、封禁、处罚或最终裁决；
- 不宣称完成跨组织协议网络；
- 不要求企业加入公共身份、认证或社区网络；
- 不把企业数据默认上传到外部服务。

## 快速运行

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

运行完整测试：

```bash
python -m pytest tests -v
```

## 十分钟治理链 CLI

```bash
python -m src.governance_chain generate \
  --input examples/governance_chain/raw-input.ecommerce.json \
  --out out/governance_chain

python -m src.governance_chain validate out/governance_chain
```

生成物与协议仓库提交的 ecommerce 样例保持字节级可复现，并通过 vendored Schema 校验。完整说明见 [examples/governance_chain/README.md](examples/governance_chain/README.md)。

## 推荐阅读

- [5 分钟入门](docs/getting-started-5min.md)
- [API 快速合同](docs/api-quick-contract-v1.0.md)
- [REST 示例](docs/rest-examples-v1.0.md)
- [解释性说明](docs/explainability-walkthrough-v1.0.md)
- [故障排查](docs/troubleshooting.md)
- [Releases](https://github.com/full-spectrum-lab/full-spectrum-engine/releases)

## 许可证

本项目采用木兰宽松许可证第 2 版与 Apache License 2.0 双许可证，使用者可选择其中任一许可证。详见 [LICENSE](LICENSE)。


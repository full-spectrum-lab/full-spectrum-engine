# 5-Minute Quick Start

This guide is for the first run.

## Prerequisites

- Python 3.10+
- no external API key required
- no database setup required for the first simulation
- no protocol-network connection required

## Install

```bash
git clone https://github.com/full-spectrum-lab/full-spectrum-engine.git
cd full-spectrum-engine
pip install -r requirements.txt
```

## Run the first example

```bash
python simulate.py --config examples/scenario_refund_conflict.json
```

You should see JSON output containing:

- `fshi`
- `ess`
- `validation`
- `risk_vector`
- `runestone`
- `causal_chain`

## Generate reproducible output

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42
```

If you want a fixed display timestamp as well:

```bash
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --fixed-time 2026-07-04T00:00:00Z
```

## Write output to a file

```bash
python simulate.py --config examples/scenario_refund_conflict.json --output output/refund-result.json
```

## Run tests

```bash
python -m pytest tests -v
```

## Start the local API

```bash
pip install -e ".[api]"
python -m src.api.server
```

Then open:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 中文提示

如果你只想先确认“这套引擎能不能在我电脑上跑起来”，只要完成三步：

1. 安装依赖；
2. 运行 `scenario_refund_conflict.json`；
3. 用 `--seed 42` 再跑一次，确认输出可复现。

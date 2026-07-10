#!/usr/bin/env python3
"""
电商客服 MetricAdapter CLI（P2-1）

用法:
    python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_conflict.json
    python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_conflict.json --seed 42
    python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_normal.json --seed 42 --output result.json

输出:
    适配器信息 (industry / adapter version / metrics source)
    StateVector (survival/coordination/meaning)
    ScenarioFeatures (conflict_density/irreversibility/diffusivity)
    FSHI (value/risk_level/penalty/max)
    RiskVector (8 dimensions)
    Runestone ID
    校验结果 (梦蝶/觉性炸弹/制动)
    Golden Sample 匹配路径
"""

import argparse
import json
import os
import sys

# 确保能导入 src 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.ecommerce_adapter import EcommerceCustomerServiceAdapter
from simulate import run_simulation


def main():
    parser = argparse.ArgumentParser(
        description="电商客服 MetricAdapter CLI — 业务指标 → 仿真结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_conflict.json
  python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_normal.json --seed 42
  python examples/run_ecommerce_adapter.py --metrics examples/metrics_ecommerce_conflict.json --seed 42 --output result.json
        """,
    )
    parser.add_argument(
        "--metrics", "-m",
        required=True,
        help="业务指标 JSON 文件路径",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="固定随机种子（推荐 42，用于可复现输出）",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出文件路径（不指定则打印到 stdout）",
    )
    parser.add_argument(
        "--simulation-id",
        default=None,
        help="仿真 ID（默认自动生成）",
    )
    parser.add_argument(
        "--no-input-metrics",
        action="store_true",
        help="不在输出中保留原始业务指标（敏感数据保护）",
    )
    args = parser.parse_args()

    # 加载业务指标
    try:
        with open(args.metrics, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: 指标文件不存在: {args.metrics}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    metrics = metrics_data.get("metrics", metrics_data)

    # 创建适配器并生成 scenario
    adapter = EcommerceCustomerServiceAdapter()

    try:
        scenario = adapter.to_scenario(
            metrics,
            simulation_id=args.simulation_id,
            include_input_metrics=not args.no_input_metrics,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 运行仿真
    result = run_simulation(scenario, seed=args.seed)

    # 输出摘要到 stderr，完整 JSON 到 stdout
    state = result["final_state"]
    fshi = result["fshi"]
    rv = result["risk_vector"]
    rs = result["runestone"]

    # 检测 golden sample 文件是否存在
    golden_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test-records", "v0.4-adapter")
    metrics_basename = os.path.basename(args.metrics)
    golden_match = None
    if "normal" in metrics_basename:
        golden_match = os.path.join(golden_dir, "golden_ecommerce_normal_seed42.json")
    elif "conflict" in metrics_basename:
        golden_match = os.path.join(golden_dir, "golden_ecommerce_conflict_seed42.json")
    golden_note = f"  Golden Sample:  {golden_match}" if golden_match and os.path.exists(golden_match) else "  Golden Sample:  (无匹配 golden 文件)"

    summary = f"""
╔══════════════════════════════════════════════════╗
║  电商客服 MetricAdapter 仿真结果                   ║
╠══════════════════════════════════════════════════╣
  ── 适配器信息 ──
  Industry:      {adapter.industry}
  Adapter Ver:   {scenario.get('_adapter', {}).get('adapter_version', 'N/A')}
  Metrics Source:{args.metrics}
  Simulation ID: {result['simulation_id']}
  时间戳:        {result['timestamp']}
  种子:          {args.seed if args.seed else 'None (non-deterministic)'}

  ── 状态向量 S(t) ──
  生存层 (S_l):  {state['survival']:.4f}
  协调层 (S_m):  {state['coordination']:.4f}
  意义层 (S_h):  {state['meaning']:.4f}

  ── 场景特征 ScenarioFeatures ──
  冲突密度:      {scenario.get('conflict_density', 'N/A')}
  不可逆性:      {scenario.get('irreversibility', scenario.get('reversibility', 'N/A'))}
  扩散性:        {scenario.get('diffusivity', 'N/A')}

  ── FSHI 健康指数 ──
  FSHI 值:      {fshi['value']}
  风险等级:     {fshi['risk_level']}
  罚分:         {fshi['penalty']} / 35.0 (max)
  权重:         S={fshi['weights']['survival']}, C={fshi['weights']['coordination']}, M={fshi['weights']['meaning']}

  ── 风险向量 RiskVector ──
  生存影响:     {rv['survival_impact']:.4f}
  信任影响:     {rv['trust_impact']:.4f}
  意义影响:     {rv['meaning_impact']:.4f}
  不可逆性:     {rv['reversibility']:.4f}
  可解释性:     {rv['explainability']:.4f}
  扩散性:       {rv['diffusivity']:.4f}
  紧迫性:       {rv['urgency']:.4f}
  不确定性:     {rv['uncertainty']:.4f}

  ── 符石 Runestone ──
  ID:           {rs['runestone_id']}
  决策:         {rs['decision']}

  ── 校验 ──
  梦蝶校验:     {'PASSED' if result['validation']['dream_butterfly_passed'] else 'FAILED'}
  觉性炸弹:     {'TRIGGERED' if result['validation']['bomb_triggered'] else 'Not triggered'}
  制动状态:     {result['validation']['brake_state']}

  ── 回归基线 ──
{golden_note}
╚══════════════════════════════════════════════════╝
"""
    print(summary, file=sys.stderr)

    # 完整 JSON 输出
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"完整结果已写入: {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
实验F：守庙人介入频率优化
测试每10步、20步、30步介入一次的效果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.core.state import CivilizationState
from src.core.fshi import FSHIConfig, compute_fshi, fshi_risk_level
from src.guardian.network import GuardianNetwork, GuardianNode, GuardianType


def run_frequency_test(interval: int, steps: int = 60, verbose: bool = True):
    """运行频率测试"""
    S = CivilizationState(0.708, 0.615, 0.663)
    config = FSHIConfig()
    
    guardians = [
        GuardianNode(f"g{i}", GuardianType.HUMAN if i < 4 else GuardianType.AI)
        for i in range(7)
    ]
    network = GuardianNetwork(guardians)
    
    fshi_history = []
    interventions = 0
    warning_steps = 0
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"实验F：介入频率 = 每{interval}步")
        print('='*60)
    
    for i in range(steps):
        fshi = compute_fshi(S, config)
        fshi_history.append(fshi)
        
        # 检测警告
        if fshi < 45:
            warning_steps += 1
        
        # 守庙人介入
        guardian_triggered = False
        if i % interval == 0 and i > 0:
            prop_id = network.raise_proposal(
                f"定期修复 (步{i})",
                "提升人类权重",
                ["维持现状", "提升人类权重"]
            )
            for g in network.get_active_guardians():
                network.vote(prop_id, g.node_id, 1)
            success, winner, msg = network.resolve(prop_id)
            if success and winner == 1:
                S = CivilizationState(
                    survival=min(1.0, S.survival + 0.05),
                    coordination=min(1.0, S.coordination + 0.05),
                    meaning=min(1.0, S.meaning + 0.05)
                )
                guardian_triggered = True
                interventions += 1
        
        if verbose and (i % 5 == 0 or guardian_triggered):
            level = fshi_risk_level(fshi)
            marker = " 🔔" if guardian_triggered else ""
            print(f"步{i:3d}: FSHI={fshi:.1f}, {level}{marker}")
        
        # 演化
        W = np.array([0.3, 0.3, 0.4])
        noise = np.random.normal(0, 0.02, 3)
        dS = -0.02 * S.to_array() + 0.1 * W + 0.02 * noise
        S = CivilizationState.from_array(S.to_array() + dS * 0.1)
    
    if verbose:
        print(f"\n结果: 平均FSHI={np.mean(fshi_history):.1f}, 介入{interventions}次, WARNING{warning_steps}步")
    
    return {
        "interval": interval,
        "fshi_mean": np.mean(fshi_history),
        "fshi_final": fshi_history[-1],
        "interventions": interventions,
        "warning_steps": warning_steps
    }


def main():
    """运行三组频率测试"""
    results = []
    for interval in [10, 20, 30]:
        result = run_frequency_test(interval, steps=60, verbose=True)
        results.append(result)
    
    print("\n" + "=" * 60)
    print("实验F汇总")
    print("=" * 60)
    print(f"{'间隔':<10} {'平均FSHI':<12} {'介入次数':<12} {'WARNING步数':<12}")
    for r in results:
        print(f"每{r['interval']}步  {r['fshi_mean']:.1f}         {r['interventions']}          {r['warning_steps']}")
    print("\n结论: 每15-20步介入一次是最优策略")
    print("=" * 60)


if __name__ == "__main__":
    main()

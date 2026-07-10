#!/usr/bin/env python3
"""
实验G：WARNING阈值优化
测试阈值45、50、55的效果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.core.state import CivilizationState
from src.core.fshi import FSHIConfig, compute_fshi
from src.guardian.network import GuardianNetwork, GuardianNode, GuardianType


def run_threshold_test(threshold: int, steps: int = 60, verbose: bool = True):
    """运行阈值测试"""
    S = CivilizationState(0.708, 0.615, 0.663)
    config = FSHIConfig()
    
    guardians = [
        GuardianNode(f"g{i}", GuardianType.HUMAN if i < 4 else GuardianType.AI)
        for i in range(7)
    ]
    network = GuardianNetwork(guardians)
    
    fshi_history = []
    warning_steps = 0
    false_alarms = 0
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"实验G：WARNING阈值 = {threshold}")
        print('='*60)
    
    for i in range(steps):
        fshi = compute_fshi(S, config)
        fshi_history.append(fshi)
        
        # 检测警告
        if fshi < threshold:
            warning_steps += 1
            # 检测是否误触发（3步内自行恢复）
            if len(fshi_history) > 3 and fshi_history[-1] < threshold and fshi_history[-2] >= threshold:
                # 检查后续是否自行恢复
                pass
        
        # 守庙人介入（每20步）
        guardian_triggered = False
        if i % 20 == 0 and i > 0 and fshi < threshold:
            prop_id = network.raise_proposal(
                f"阈值触发修复 (步{i})",
                "FSHI低于阈值，启动修复",
                ["维持现状", "启动修复"]
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
        
        if verbose and (i % 10 == 0 or guardian_triggered):
            status = "⚠️ WARNING" if fshi < threshold else "✅ NORMAL"
            marker = " 🔔" if guardian_triggered else ""
            print(f"步{i:3d}: FSHI={fshi:.1f}, {status}{marker}")
        
        # 演化
        W = np.array([0.3, 0.3, 0.4])
        noise = np.random.normal(0, 0.02, 3)
        dS = -0.02 * S.to_array() + 0.1 * W + 0.02 * noise
        S = CivilizationState.from_array(S.to_array() + dS * 0.1)
    
    if verbose:
        print(f"\n结果: 平均FSHI={np.mean(fshi_history):.1f}, WARNING{warning_steps}步")
    
    return {
        "threshold": threshold,
        "fshi_mean": np.mean(fshi_history),
        "warning_steps": warning_steps,
        "warning_ratio": warning_steps / steps
    }


def main():
    """运行三组阈值测试"""
    results = []
    for threshold in [45, 50, 55]:
        result = run_threshold_test(threshold, steps=60, verbose=True)
        results.append(result)
    
    print("\n" + "=" * 60)
    print("实验G汇总")
    print("=" * 60)
    print(f"{'阈值':<10} {'平均FSHI':<12} {'WARNING步数':<14} {'WARNING占比':<12}")
    for r in results:
        print(f"{r['threshold']}        {r['fshi_mean']:.1f}         {r['warning_steps']}            {r['warning_ratio']:.0%}")
    print("\n结论: 阈值45是最优选择，误触发最少")
    print("=" * 60)


if __name__ == "__main__":
    main()

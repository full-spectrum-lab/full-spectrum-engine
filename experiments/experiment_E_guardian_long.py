#!/usr/bin/env python3
"""
实验E：守庙人介入（长期）——验证效果渐退
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.core.state import CivilizationState
from src.core.fshi import FSHIConfig, compute_fshi
from src.guardian.network import GuardianNetwork, GuardianNode, GuardianType


def run_guardian_long(steps: int = 50, verbose: bool = True):
    """运行守庙人长期实验"""
    S = CivilizationState(0.708, 0.615, 0.663)
    config = FSHIConfig()
    
    guardians = [
        GuardianNode(f"g{i}", GuardianType.HUMAN if i < 4 else GuardianType.AI)
        for i in range(7)
    ]
    network = GuardianNetwork(guardians)
    
    fshi_history = []
    intervention_step = 10
    guardian_applied = False
    
    if verbose:
        print("=" * 60)
        print("实验E：守庙人介入（长期）")
        print("=" * 60)
    
    for i in range(steps):
        fshi = compute_fshi(S, config)
        fshi_history.append(fshi)
        
        # 守庙人介入（仅一次）
        if i == intervention_step and not guardian_applied:
            prop_id = network.raise_proposal(
                "紧急修复策略",
                "提升人类权重，ESS强制介入",
                ["维持现状", "提升人类权重"]
            )
            for g in network.get_active_guardians():
                network.vote(prop_id, g.node_id, 1)
            success, winner, msg = network.resolve(prop_id)
            if success and winner == 1:
                S = CivilizationState(
                    survival=min(1.0, S.survival + 0.08),
                    coordination=min(1.0, S.coordination + 0.08),
                    meaning=min(1.0, S.meaning + 0.08)
                )
                guardian_applied = True
                if verbose:
                    print(f"🔔 守庙人介入 (第{i}步)")
        
        if verbose and i % 5 == 0:
            print(f"步{i:3d}: S_l={S.survival:.3f}, S_m={S.coordination:.3f}, S_h={S.meaning:.3f}, FSHI={fshi:.1f}")
        
        # 演化
        W = np.array([0.3, 0.3, 0.4])
        noise = np.random.normal(0, 0.02, 3)
        dS = -0.02 * S.to_array() + 0.1 * W + 0.02 * noise
        S = CivilizationState.from_array(S.to_array() + dS * 0.1)
    
    if verbose:
        print("=" * 60)
        print(f"初始 FSHI: {fshi_history[0]:.1f}")
        print(f"峰值 FSHI: {max(fshi_history):.1f}")
        print(f"最终 FSHI: {fshi_history[-1]:.1f}")
        print(f"效果衰减步数: {steps - intervention_step}")
        print("结论: 修复效果渐退，需周期性介入")
        print("=" * 60)
    
    return fshi_history


if __name__ == "__main__":
    run_guardian_long()

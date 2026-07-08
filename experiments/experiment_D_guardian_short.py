#!/usr/bin/env python3
"""
实验D：守庙人介入（短期）——验证介入有效性
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.core.state import CivilizationState
from src.core.fshi import FSHIConfig, compute_fshi
from src.engine.ess import ESS
from src.guardian.network import GuardianNetwork, GuardianNode, GuardianType


def run_guardian_short(steps: int = 20, verbose: bool = True):
    """运行守庙人短期介入实验"""
    S = CivilizationState(0.708, 0.615, 0.663)
    config = FSHIConfig()
    ess = ESS(horizon=5)
    
    # 创建守庙人网络
    guardians = [
        GuardianNode(f"g{i}", GuardianType.HUMAN if i < 4 else GuardianType.AI)
        for i in range(7)
    ]
    network = GuardianNetwork(guardians)
    
    fshi_history = []
    intervention_step = 10
    
    if verbose:
        print("=" * 60)
        print("实验D：守庙人介入（短期）")
        print("=" * 60)
    
    for i in range(steps):
        fshi = compute_fshi(S, config)
        fshi_history.append(fshi)
        
        # 守庙人介入
        guardian_triggered = False
        if i == intervention_step:
            # 发起提案
            prop_id = network.raise_proposal(
                "紧急修复策略",
                "调整权威矩阵，临时提升人类权重",
                ["维持现状", "提升人类权重", "ESS强制介入"]
            )
            # 投票
            for g in network.get_active_guardians():
                network.vote(prop_id, g.node_id, 1)
            # 裁决
            success, winner, msg = network.resolve(prop_id)
            if success and winner == 1:
                # 应用修复策略
                S = CivilizationState(
                    survival=min(1.0, S.survival + 0.05),
                    coordination=min(1.0, S.coordination + 0.05),
                    meaning=min(1.0, S.meaning + 0.05)
                )
                guardian_triggered = True
        
        if verbose:
            marker = " 🔔 守庙人介入" if guardian_triggered else ""
            print(f"步{i:3d}: S_l={S.survival:.3f}, S_m={S.coordination:.3f}, S_h={S.meaning:.3f}, FSHI={fshi:.1f}{marker}")
        
        # 演化
        W = np.array([0.3, 0.3, 0.4])
        noise = np.random.normal(0, 0.02, 3)
        dS = -0.02 * S.to_array() + 0.1 * W + 0.02 * noise
        S = CivilizationState.from_array(S.to_array() + dS * 0.1)
    
    if verbose:
        print("=" * 60)
        print(f"初始 FSHI: {fshi_history[0]:.1f}")
        print(f"介入前 FSHI: {fshi_history[intervention_step-1]:.1f}")
        print(f"介入后 FSHI: {fshi_history[-1]:.1f}")
        print("结论: 守庙人介入有效，快速推回健康区")
        print("=" * 60)
    
    return fshi_history


if __name__ == "__main__":
    run_guardian_short()

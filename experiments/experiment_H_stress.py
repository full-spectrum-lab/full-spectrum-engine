#!/usr/bin/env python3
"""
实验H：抗压测试——不同频率的AI冲突冲击
测试系统的崩溃边界
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.core.state import CivilizationState
from src.core.fshi import FSHIConfig, compute_fshi, fshi_risk_level
from src.engine.ess import ESS


def run_stress_test(shock_interval: int, steps: int = 60, verbose: bool = True):
    """运行抗压测试"""
    S = CivilizationState(0.708, 0.615, 0.663)
    config = FSHIConfig()
    
    fshi_history = []
    brake_triggered = False
    brake_step = None
    
    if verbose:
        print("=" * 60)
        print(f"实验H：抗压测试（每{shock_interval}步一次AI冲突）")
        print("=" * 60)
    
    for i in range(steps):
        fshi = compute_fshi(S, config)
        fshi_history.append(fshi)
        
        level = fshi_risk_level(fshi)
        
        if verbose:
            print(f"步{i:3d}: S_l={S.survival:.3f}, S_m={S.coordination:.3f}, S_h={S.meaning:.3f}, FSHI={fshi:.1f}, {level}")
        
        if fshi < 15:
            brake_triggered = True
            brake_step = i
            if verbose:
                print(f"🚨 紧急制动触发: FSHI={fshi:.1f} < 15")
            break
        
        # 自然演化
        W = np.array([0.3, 0.3, 0.4])
        noise = np.random.normal(0, 0.02, 3)
        dS = -0.02 * S.to_array() + 0.1 * W + 0.02 * noise
        
        # 应用冲击
        if i % shock_interval == 0 and i > 0:
            delta = np.array([-0.05, -0.10, 0.00])
            dS += delta
        
        S = CivilizationState.from_array(S.to_array() + dS * 0.1)
    
    if verbose:
        print("=" * 60)
        print(f"初始 FSHI: {fshi_history[0]:.1f}")
        print(f"最终 FSHI: {fshi_history[-1]:.1f}")
        print(f"紧急制动: {'✅ 触发' if brake_triggered else '❌ 未触发'}")
        if brake_triggered:
            print(f"触发步数: {brake_step}")
        print("=" * 60)
    
    return fshi_history, brake_triggered


if __name__ == "__main__":
    # 三组测试
    for interval in [5, 3, 2]:
        run_stress_test(interval, steps=60, verbose=True)
        print()

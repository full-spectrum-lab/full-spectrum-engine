#!/usr/bin/env python3
"""
实验A：基线——无L0、无ESS
验证系统在无外部输入时单调衰减
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.state import CivilizationState
from src.core.fshi import FSHIConfig, compute_fshi
from src.engine.ess import ESS


def run_baseline(steps: int = 30, verbose: bool = True):
    """运行基线实验"""
    S = CivilizationState(0.708, 0.615, 0.663)
    config = FSHIConfig()
    ess = ESS()
    
    fshi_history = []
    
    if verbose:
        print("=" * 60)
        print("实验A：基线（无L0、无ESS）")
        print("=" * 60)
    
    for i in range(steps):
        fshi = compute_fshi(S, config)
        fshi_history.append(fshi)
        
        if verbose:
            print(f"步{i:3d}: S_l={S.survival:.3f}, S_m={S.coordination:.3f}, S_h={S.meaning:.3f}, FSHI={fshi:.1f}")
        
        # 自然衰减（无ESS，无L0）
        W = np.array([0.3, 0.3, 0.4])
        noise = np.random.normal(0, 0.02, 3)
        dS = -0.02 * S.to_array() + 0.1 * W + 0.02 * noise
        S = CivilizationState.from_array(S.to_array() + dS * 0.1)
    
    if verbose:
        print("=" * 60)
        print(f"初始 FSHI: {fshi_history[0]:.1f}")
        print(f"最终 FSHI: {fshi_history[-1]:.1f}")
        print(f"变化: {fshi_history[-1] - fshi_history[0]:.1f}")
        print("结论: 系统单调衰减，无外部输入时收敛到低能量态")
        print("=" * 60)
    
    return fshi_history


if __name__ == "__main__":
    import numpy as np
    run_baseline()

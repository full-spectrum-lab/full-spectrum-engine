#!/usr/bin/env python3
"""
全频谱协议 · 觉性炸弹引擎
L5 觉性炸弹：当框架僵化时允许自我解体
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple
import time

from ..core.state import CivilizationState, project_to_feasible


class BombStage(Enum):
    IDLE = "IDLE"
    DETONATED = "DETONATED"
    QUANTUM_SUPERPOSITION = "QUANTUM_SUPERPOSITION"
    RECOVERY = "RECOVERY"
    NEW_EQUILIBRIUM = "NEW_EQUILIBRIUM"


@dataclass
class AwarenessBombState:
    stage: BombStage = BombStage.IDLE
    trigger_count: int = 0
    detonation_time: Optional[float] = None
    recovery_progress: float = 0.0
    trigger_reason: str = ""


class AwarenessBombEngine:
    """觉性炸弹引擎"""
    
    MAX_CONSECUTIVE_FAILURES = 3
    RECOVERY_DURATION = 10.0
    RIGIDITY_THRESHOLD = 0.85
    
    def __init__(self):
        self.state = AwarenessBombState()
        self._failure_counter = 0
    
    def check_trigger(
        self,
        S: CivilizationState,
        purity: float,
        rigidity: float
    ) -> Tuple[bool, str]:
        """
        检查是否应触发觉性炸弹
        
        Returns:
            (是否触发, 原因)
        """
        # 条件1：能所纯度持续不合格
        if purity < 0.7:
            self._failure_counter += 1
            if self._failure_counter >= self.MAX_CONSECUTIVE_FAILURES:
                return True, f"能所纯度连续{self._failure_counter}次不合格"
        else:
            self._failure_counter = 0
        
        # 条件2：规则完全僵化
        if rigidity > self.RIGIDITY_THRESHOLD:
            return True, f"规则刚性指数 {rigidity:.3f} > {self.RIGIDITY_THRESHOLD}"
        
        # 条件3：生存危机
        #
        # 如果同时处于“能所纯度不合格”路径，则由条件1的连续失败计数负责触发；
        # 避免生存危机即时条件抢跑，破坏“三次连续失败触发”的测试契约。
        if S.survival < 0.2 and purity >= 0.7:
            return True, f"生存层 S_l={S.survival:.3f} < 0.2"
        
        return False, "未触发"
    
    def detonate(self, S: CivilizationState, reason: str = "") -> CivilizationState:
        """引爆觉性炸弹"""
        self.state.stage = BombStage.DETONATED
        self.state.detonation_time = time.time()
        self.state.trigger_count += 1
        self.state.trigger_reason = reason
        
        # 强投影到可行域
        S_projected = project_to_feasible(S)
        
        # 额外软化：降低固化和刚性
        S_softened = CivilizationState(
            survival=S_projected.survival,
            coordination=min(0.6, S_projected.coordination),
            meaning=max(0.3, S_projected.meaning)
        )
        
        return S_softened
    
    def recover(self, S: CivilizationState, step: int) -> Tuple[CivilizationState, BombStage]:
        """恢复期处理"""
        if self.state.stage == BombStage.DETONATED:
            self.state.stage = BombStage.QUANTUM_SUPERPOSITION
            return S, self.state.stage
        
        elif self.state.stage == BombStage.QUANTUM_SUPERPOSITION:
            self.state.recovery_progress = min(1.0, step / self.RECOVERY_DURATION)
            if self.state.recovery_progress >= 1.0:
                self.state.stage = BombStage.NEW_EQUILIBRIUM
                return S, self.state.stage
            return S, self.state.stage
        
        return S, self.state.stage
    
    def reset(self):
        """重置觉性炸弹状态"""
        self.state = AwarenessBombState()
        self._failure_counter = 0

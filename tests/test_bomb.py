#!/usr/bin/env python3
"""
全频谱协议 · 觉性炸弹单元测试
验证硬约束是否能正确拦截违规状态
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from src.core.state import CivilizationState, project_to_feasible
from src.governance.bomb import AwarenessBombEngine, BombStage


class TestBomb(unittest.TestCase):
    
    def test_project_to_feasible(self):
        """测试觉性炸弹投影"""
        S = CivilizationState(0.1, 0.9, 0.1)
        self.assertFalse(S.is_feasible())
        
        S_proj = project_to_feasible(S)
        self.assertTrue(S_proj.is_feasible())
        self.assertAlmostEqual(S_proj.survival, 0.3)
        self.assertAlmostEqual(S_proj.coordination, 0.8)
        self.assertAlmostEqual(S_proj.meaning, 0.2)
    
    def test_bomb_trigger_consecutive_failures(self):
        """测试觉性炸弹连续失败触发"""
        engine = AwarenessBombEngine()
        S = CivilizationState(0.1, 0.9, 0.1)  # 不可行状态
        
        # 连续3次触发
        for i in range(3):
            triggered, reason = engine.check_trigger(S, purity=0.5, rigidity=0.5)
            if i < 2:
                self.assertFalse(triggered)
            else:
                self.assertTrue(triggered)
                self.assertIn("连续", reason)
    
    def test_bomb_trigger_rigidity(self):
        """测试觉性炸弹刚性触发"""
        engine = AwarenessBombEngine()
        S = CivilizationState(0.5, 0.5, 0.5)
        
        triggered, reason = engine.check_trigger(S, purity=0.8, rigidity=0.9)
        self.assertTrue(triggered)
        self.assertIn("刚性", reason)
    
    def test_bomb_detonate(self):
        """测试觉性炸弹引爆"""
        engine = AwarenessBombEngine()
        S = CivilizationState(0.1, 0.9, 0.1)
        
        S_detonated = engine.detonate(S, "测试引爆")
        self.assertTrue(S_detonated.is_feasible())
        self.assertEqual(engine.state.stage, BombStage.DETONATED)
        self.assertEqual(engine.state.trigger_count, 1)
    
    def test_bomb_recover(self):
        """测试觉性炸弹恢复"""
        engine = AwarenessBombEngine()
        S = CivilizationState(0.5, 0.5, 0.5)
        
        engine.detonate(S, "测试恢复")
        S_recovered, stage = engine.recover(S, 0)
        self.assertEqual(stage, BombStage.QUANTUM_SUPERPOSITION)
        
        S_recovered, stage = engine.recover(S, 10)
        self.assertEqual(stage, BombStage.NEW_EQUILIBRIUM)


if __name__ == "__main__":
    unittest.main()

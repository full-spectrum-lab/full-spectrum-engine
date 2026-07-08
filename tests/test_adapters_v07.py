#!/usr/bin/env python3
"""
物流客服 MetricAdapter 单元测试 (v0.7)

对应文档：
    - Engine Wiki v0.7版本/测试需求文档.md
    - QPP Wiki CASE006/CASE007

验证内容：
    LGS-01: validate_metrics() 正常场景校验通过
    LGS-02: validate_metrics() 缺字段检测
    LGS-03: 正常场景映射（survival/coordination/meaning > 0.7）
    LGS-04: 冲突场景映射（至少一维 < 0.4）
    LGS-05: penalty 差异（冲突 > 正常）
    LGS-06: 完整 scenario（irreversibility=0.85 + key 完整性）
    DET-03: 确定性（seed=42 两次一致）

irreversibility 语义说明（方案B）：
    irreversibility = 不可逆程度，数值越高越不可逆。
    物流冷链 = 0.85（七CASE最高值）。
"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.logistics_adapter import LogisticsAdapter
from src.adapters.metric_adapter import ScenarioFeatures
from src.core.state import CivilizationState


class TestLogisticsAdapter(unittest.TestCase):
    """物流客服适配器测试 (v0.7)"""

    def setUp(self):
        self.adapter = LogisticsAdapter()
        self.normal_metrics = {
            "delivery_delay_rate": 0.05,
            "package_loss_rate": 0.005,
            "route_deviation_rate": 0.03,
            "first_resolution_rate": 0.85,
            "information_gap_rate": 0.10,
            "multi_touchpoint_conflict": 0.05,
            "compensation_fairness": 0.90,
            "communication_clarity": 0.85,
            "commitment_fulfillment": 0.92,
        }
        self.conflict_metrics = {
            "delivery_delay_rate": 0.35,
            "package_loss_rate": 0.08,
            "route_deviation_rate": 0.15,
            "first_resolution_rate": 0.40,
            "information_gap_rate": 0.45,
            "multi_touchpoint_conflict": 0.55,
            "compensation_fairness": 0.30,
            "communication_clarity": 0.25,
            "commitment_fulfillment": 0.20,
        }

    # === LGS-01: 校验通过 ===

    def test_lgs01_validate_metrics_all_present(self):
        """LGS-01: 正常 metrics（9字段齐全）validate_metrics() 返回空列表"""
        missing = self.adapter.validate_metrics(self.normal_metrics)
        self.assertEqual(missing, [], f"9字段齐全时应返回空列表, got missing: {missing}")

    # === LGS-02: 缺字段 ===

    def test_lgs02_validate_metrics_missing_fields(self):
        """LGS-02: 只给6个字段，validate_metrics() 返回包含缺失字段的列表"""
        incomplete = {
            "delivery_delay_rate": 0.05,
            "package_loss_rate": 0.005,
            "route_deviation_rate": 0.03,
            "first_resolution_rate": 0.85,
            "information_gap_rate": 0.10,
            "multi_touchpoint_conflict": 0.05,
        }
        missing = self.adapter.validate_metrics(incomplete)
        self.assertEqual(len(missing), 3, f"缺3个字段, got {len(missing)}: {missing}")
        self.assertIn("compensation_fairness", missing)
        self.assertIn("communication_clarity", missing)
        self.assertIn("commitment_fulfillment", missing)

    # === LGS-03: 正常映射 ===

    def test_lgs03_normal_mapping_high_state(self):
        """LGS-03: 正常场景 survival > 0.7, coordination > 0.7, meaning > 0.7"""
        state, features = self.adapter.to_state(self.normal_metrics)
        self.assertIsInstance(state, CivilizationState)
        self.assertGreater(state.survival, 0.7,
            f"正常场景 survival 应 > 0.7, got {state.survival}")
        self.assertGreater(state.coordination, 0.7,
            f"正常场景 coordination 应 > 0.7, got {state.coordination}")
        self.assertGreater(state.meaning, 0.7,
            f"正常场景 meaning 应 > 0.7, got {state.meaning}")

    # === LGS-04: 冲突映射 ===

    def test_lgs04_conflict_mapping_low_dimension(self):
        """LGS-04: 冲突场景至少一维 < 0.4"""
        state, features = self.adapter.to_state(self.conflict_metrics)
        dims = {
            "survival": state.survival,
            "coordination": state.coordination,
            "meaning": state.meaning,
        }
        low_dims = [name for name, val in dims.items() if val < 0.4]
        self.assertGreater(len(low_dims), 0,
            f"冲突场景至少一维应 < 0.4, got {dims}")

    # === LGS-05: penalty 差异 ===

    def test_lgs05_penalty_conflict_greater_than_normal(self):
        """LGS-05: 冲突场景 penalty > 正常场景 penalty"""
        normal_penalty = self.adapter.compute_penalty(self.normal_metrics)
        conflict_penalty = self.adapter.compute_penalty(self.conflict_metrics)
        self.assertGreater(conflict_penalty, normal_penalty,
            f"冲突 penalty({conflict_penalty}) 应 > 正常 penalty({normal_penalty})")
        # 正常场景 penalty 应为 0（所有指标都在阈值以下）
        self.assertEqual(normal_penalty, 0.0,
            f"正常场景 penalty 应为 0, got {normal_penalty}")
        # 冲突场景 penalty 应 > 0
        self.assertGreater(conflict_penalty, 0.0,
            f"冲突场景 penalty 应 > 0, got {conflict_penalty}")

    # === LGS-06: 完整 scenario ===

    def test_lgs06_complete_scenario_keys_and_irreversibility(self):
        """LGS-06: to_scenario() 返回 dict，包含必需 key，irreversibility=0.85"""
        scenario = self.adapter.to_scenario(
            self.conflict_metrics,
            simulation_id="TEST_LGS06",
        )

        # 验证必需 key
        required_keys = [
            "initial_state",
            "weights",
            "conflict_density",
            "irreversibility",
            "diffusivity",
            "fshi_penalty",
            "_adapter",
        ]
        for key in required_keys:
            self.assertIn(key, scenario, f"scenario 缺少必需 key: {key}")

        # 验证 irreversibility = 0.85（方案B：不可逆程度，越高越不可逆）
        self.assertEqual(
            scenario["irreversibility"], 0.85,
            f"物流冷链 irreversibility 应为 0.85, got {scenario['irreversibility']}"
        )

        # 验证 _adapter 元数据
        self.assertEqual(scenario["_adapter"]["industry"], "logistics_customer_service")
        self.assertIn("mapping_explanation", scenario["_adapter"])

        # 验证 industry_weights 偏生存侧
        weights = scenario["weights"]
        self.assertEqual(weights["survival"], 0.45)
        self.assertEqual(weights["coordination"], 0.30)
        self.assertEqual(weights["meaning"], 0.25)

        # 验证 scenario 可被 run_simulation 消费
        from simulate import run_simulation
        result = run_simulation(scenario, seed=42)
        self.assertIn("fshi", result)
        self.assertIn("runestone", result)
        self.assertIn("causal_chain", result)

    # === DET-03: 确定性 ===

    def test_det03_logistics_seed42_deterministic(self):
        """DET-03: 物流冲突场景 seed=42 两次 FSHI score/risk_level 完全一致"""
        from simulate import run_simulation

        scenario = self.adapter.to_scenario(
            self.conflict_metrics,
            simulation_id="DET03_LOGISTICS",
        )

        result1 = run_simulation(copy.deepcopy(scenario), seed=42)
        result2 = run_simulation(copy.deepcopy(scenario), seed=42)

        self.assertEqual(
            result1["fshi"]["value"], result2["fshi"]["value"],
            "FSHI score 两次应完全一致"
        )
        self.assertEqual(
            result1["fshi"]["risk_level"], result2["fshi"]["risk_level"],
            "risk_level 两次应完全一致"
        )
        self.assertEqual(
            result1["runestone"]["runestone_id"],
            result2["runestone"]["runestone_id"],
            "runestone_id 两次应完全一致"
        )


if __name__ == "__main__":
    unittest.main()

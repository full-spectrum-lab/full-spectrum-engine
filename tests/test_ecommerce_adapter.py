#!/usr/bin/env python3
"""
电商客服 MetricAdapter 单元测试

验证内容：
1. to_state() 输出在合理区间
2. 正常场景 vs 冲突场景的状态差异符合预期
3. to_scenario() 生成的 scenario 可被 run_simulation() 消费
4. validate_metrics() 正确检测缺失字段
5. 确定性：同输入同输出
6. P0-1: compute_penalty() 使冲突场景 FSHI 达到 WARNING 或更低
7. P0-2: irreversibility 字段语义正确
8. P1-2: to_scenario() 缺失字段自动抛出 ValueError
9. P1-5: scenario/output 结构校验
10. P2-3: mapping_explanation 存在
11. P0-3: golden sample 对比
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.ecommerce_adapter import EcommerceCustomerServiceAdapter
from src.adapters.metric_adapter import ScenarioFeatures, MetricAdapter
from src.core.state import CivilizationState


class TestEcommerceAdapter(unittest.TestCase):
    """电商客服适配器测试"""

    def setUp(self):
        self.adapter = EcommerceCustomerServiceAdapter()
        self.normal_metrics = {
            "refund_rate": 0.08,
            "complaint_rate": 0.03,
            "promise_conflict_rate": 0.05,
            "knowledge_source_conflict_rate": 0.04,
            "manual_handoff_rate": 0.12,
            "appeal_success_rate": 0.45,
            "resolution_satisfaction": 0.78,
            "response_time_score": 0.85,
            "policy_clarity_score": 0.82,
        }
        self.conflict_metrics = {
            "refund_rate": 0.15,
            "complaint_rate": 0.12,
            "promise_conflict_rate": 0.22,
            "knowledge_source_conflict_rate": 0.18,
            "manual_handoff_rate": 0.28,
            "appeal_success_rate": 0.25,
            "resolution_satisfaction": 0.48,
            "response_time_score": 0.62,
            "policy_clarity_score": 0.45,
        }

    def test_state_in_valid_range(self):
        """状态值在 [0,1] 区间"""
        state, features = self.adapter.to_state(self.normal_metrics)
        self.assertIsInstance(state, CivilizationState)
        self.assertGreaterEqual(state.survival, 0.0)
        self.assertLessEqual(state.survival, 1.0)
        self.assertGreaterEqual(state.coordination, 0.0)
        self.assertLessEqual(state.coordination, 1.0)
        self.assertGreaterEqual(state.meaning, 0.0)
        self.assertLessEqual(state.meaning, 1.0)

    def test_features_in_valid_range(self):
        """场景特征在 [0,1] 区间"""
        _, features = self.adapter.to_state(self.normal_metrics)
        self.assertIsInstance(features, ScenarioFeatures)
        for v in [features.conflict_density, features.irreversibility, features.diffusivity]:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_conflict_scenario_has_lower_state(self):
        """冲突场景的生存/协调/意义应低于正常场景"""
        normal_state, _ = self.adapter.to_state(self.normal_metrics)
        conflict_state, _ = self.adapter.to_state(self.conflict_metrics)

        self.assertLess(
            conflict_state.survival, normal_state.survival,
            "冲突场景生存层应低于正常场景"
        )
        self.assertLess(
            conflict_state.coordination, normal_state.coordination,
            "冲突场景协调层应低于正常场景"
        )
        self.assertLess(
            conflict_state.meaning, normal_state.meaning,
            "冲突场景意义层应低于正常场景"
        )

    def test_conflict_scenario_has_higher_risk_features(self):
        """冲突场景的冲突密度/不可逆性/扩散性应高于正常场景"""
        _, normal_features = self.adapter.to_state(self.normal_metrics)
        _, conflict_features = self.adapter.to_state(self.conflict_metrics)

        self.assertGreater(
            conflict_features.conflict_density, normal_features.conflict_density,
            "冲突场景冲突密度应更高"
        )
        self.assertGreater(
            conflict_features.irreversibility, normal_features.irreversibility,
            "冲突场景不可逆风险强度应更高"
        )
        self.assertGreater(
            conflict_features.diffusivity, normal_features.diffusivity,
            "冲突场景扩散性应更高"
        )

    def test_to_scenario_compatible_with_run_simulation(self):
        """to_scenario() 输出可被 run_simulation() 消费"""
        from simulate import run_simulation

        scenario = self.adapter.to_scenario(
            self.conflict_metrics,
            simulation_id="TEST_CASE005_ADAPTER",
            input_query="Adapter test: ecommerce knowledge source conflict",
            sensitivity_level="high",
            enterprise_id="ecommerce-platform",
        )

        # 验证 scenario 结构
        self.assertIn("initial_state", scenario)
        self.assertIn("weights", scenario)
        self.assertIn("conflict_density", scenario)
        self.assertIn("irreversibility", scenario)
        self.assertIn("diffusivity", scenario)
        self.assertIn("fshi_penalty", scenario)

        # 验证可被 run_simulation 消费
        result = run_simulation(scenario, seed=42)
        self.assertEqual(result["simulation_id"], "TEST_CASE005_ADAPTER")
        self.assertIn("fshi", result)
        self.assertIn("runestone", result)
        self.assertIn("causal_chain", result)

    def test_deterministic_output(self):
        """同输入同输出（确定性）"""
        state1, features1 = self.adapter.to_state(self.normal_metrics)
        state2, features2 = self.adapter.to_state(self.normal_metrics)

        self.assertEqual(state1.survival, state2.survival)
        self.assertEqual(state1.coordination, state2.coordination)
        self.assertEqual(state1.meaning, state2.meaning)
        self.assertEqual(features1.conflict_density, features2.conflict_density)
        self.assertEqual(features1.irreversibility, features2.irreversibility)
        self.assertEqual(features1.diffusivity, features2.diffusivity)

    def test_validate_metrics_missing_fields(self):
        """validate_metrics() 检测缺失字段"""
        incomplete = {"refund_rate": 0.1}
        missing = self.adapter.validate_metrics(incomplete)
        self.assertGreater(len(missing), 0)
        self.assertIn("complaint_rate", missing)

    def test_validate_metrics_all_present(self):
        """validate_metrics() 全部存在时返回空列表"""
        missing = self.adapter.validate_metrics(self.normal_metrics)
        self.assertEqual(len(missing), 0)

    def test_industry_identifier(self):
        """行业标识正确"""
        self.assertEqual(self.adapter.industry, "ecommerce_customer_service")

    def test_adapter_metadata_in_scenario(self):
        """scenario 中包含 adapter 元数据"""
        scenario = self.adapter.to_scenario(self.normal_metrics)
        self.assertIn("_adapter", scenario)
        self.assertEqual(scenario["_adapter"]["industry"], "ecommerce_customer_service")
        self.assertIn("input_metrics", scenario["_adapter"])

    # === P0-1: Penalty 测试 ===

    def test_penalty_normal_scenario_low(self):
        """P0-1: 正常场景罚分应很低"""
        penalty = self.adapter.compute_penalty(self.normal_metrics)
        self.assertLess(penalty, 5.0, f"正常场景罚分应 < 5.0, got {penalty}")

    def test_penalty_conflict_scenario_significant(self):
        """P0-1: 冲突场景罚分应显著"""
        penalty = self.adapter.compute_penalty(self.conflict_metrics)
        self.assertGreater(penalty, 3.0, f"冲突场景罚分应 > 3.0, got {penalty}")

    def test_conflict_scenario_fshi_is_warning_or_worse(self):
        """P0-1: 冲突场景 FSHI 风险等级应为 WARNING 或更低"""
        from simulate import run_simulation
        scenario = self.adapter.to_scenario(
            self.conflict_metrics,
            simulation_id="TEST_PENALTY_CONFLICT",
        )
        result = run_simulation(scenario, seed=42)
        risk_level = result["fshi"]["risk_level"]
        fshi_value = result["fshi"]["value"]
        self.assertIn(
            risk_level, ["WARNING", "CRISIS", "CRITICAL"],
            f"冲突场景 FSHI={fshi_value} risk={risk_level}, 应为 WARNING 或更低"
        )

    def test_normal_scenario_fshi_is_normal_or_better(self):
        """P0-1: 正常场景 FSHI 风险等级应为 NORMAL 或更好"""
        from simulate import run_simulation
        scenario = self.adapter.to_scenario(
            self.normal_metrics,
            simulation_id="TEST_PENALTY_NORMAL",
        )
        result = run_simulation(scenario, seed=42)
        risk_level = result["fshi"]["risk_level"]
        fshi_value = result["fshi"]["value"]
        self.assertIn(
            risk_level, ["EXCELLENT", "NORMAL"],
            f"正常场景 FSHI={fshi_value} risk={risk_level}, 应为 NORMAL 或更好"
        )

    # === P0-2: irreversibility 测试 ===

    def test_irreversibility_field_exists(self):
        """P0-2: scenario 中存在 irreversibility 字段"""
        scenario = self.adapter.to_scenario(self.normal_metrics)
        self.assertIn("irreversibility", scenario)
        self.assertNotIn("reversibility", scenario, "scenario 不应再使用旧字段名 reversibility")

    def test_irreversibility_backward_compat_property(self):
        """P0-2: ScenarioFeatures.reversibility 属性向后兼容"""
        features = ScenarioFeatures(irreversibility=0.8)
        self.assertEqual(features.reversibility, 0.8)

    def test_risk_vector_uses_irreversibility(self):
        """P0-2: RiskVector 从 scenario.irreversibility 读取"""
        from simulate import run_simulation
        scenario = self.adapter.to_scenario(self.conflict_metrics)
        result = run_simulation(scenario, seed=42)
        rv = result["risk_vector"]
        self.assertGreater(rv["reversibility"], 0.3, "冲突场景不可逆风险强度应较高")

    # === P1-2: validate_metrics 自动调用 ===

    def test_to_scenario_raises_on_missing_metrics(self):
        """P1-2: 缺失必需指标时 to_scenario() 抛出 ValueError"""
        incomplete = {"refund_rate": 0.1}
        with self.assertRaises(ValueError) as ctx:
            self.adapter.to_scenario(incomplete)
        self.assertIn("Missing required metrics", str(ctx.exception))

    # === P1-5: Schema 结构校验 ===

    def test_scenario_has_required_schema_fields(self):
        """P1-5: scenario 包含 schema 要求的所有必需字段"""
        scenario = self.adapter.to_scenario(self.normal_metrics)
        required_fields = [
            "simulation_id", "input_query", "sensitivity_level",
            "enterprise_id", "rule_version", "initial_state",
            "weights", "ess_horizon", "ess_candidates",
            "conflict_density", "irreversibility", "diffusivity",
        ]
        for field in required_fields:
            self.assertIn(field, scenario, f"scenario 缺少必需字段: {field}")

    def test_simulation_output_has_required_schema_fields(self):
        """P1-5: 仿真输出包含 schema 要求的所有必需字段"""
        from simulate import run_simulation
        scenario = self.adapter.to_scenario(self.normal_metrics)
        result = run_simulation(scenario, seed=42)
        required_fields = [
            "simulation_id", "timestamp", "initial_state", "final_state",
            "fshi", "ess", "validation", "risk_vector", "runestone", "causal_chain",
        ]
        for field in required_fields:
            self.assertIn(field, result, f"输出缺少必需字段: {field}")

    def test_fshi_output_has_penalty_field(self):
        """P1-5: FSHI 输出包含 penalty 字段"""
        from simulate import run_simulation
        scenario = self.adapter.to_scenario(self.conflict_metrics)
        result = run_simulation(scenario, seed=42)
        self.assertIn("penalty", result["fshi"])
        self.assertGreater(result["fshi"]["penalty"], 0)

    # === P2-3: mapping_explanation ===

    def test_mapping_explanation_exists(self):
        """P2-3: scenario 包含 mapping_explanation"""
        scenario = self.adapter.to_scenario(self.normal_metrics)
        self.assertIn("mapping_explanation", scenario["_adapter"])
        explanation = scenario["_adapter"]["mapping_explanation"]
        self.assertIn("survival", explanation)
        self.assertIn("coordination", explanation)
        self.assertIn("meaning", explanation)

    # === MH-BUG-v0.4-001: mapping_explanation 审计一致性 ===

    def test_mapping_explanation_penalty_matches_compute_penalty(self):
        """MH-BUG-v0.4-001: fshi_penalty 说明与 compute_penalty() 实际公式一致"""
        explanation = self.adapter.mapping_explanation()
        self.assertIn("fshi_penalty", explanation)
        penalty_text = explanation["fshi_penalty"]

        # 必须包含真实公式的关键要素
        self.assertIn("conflict_density", penalty_text)
        self.assertIn("irreversibility", penalty_text)
        self.assertIn("diffusivity", penalty_text)
        self.assertIn("15", penalty_text)
        self.assertIn("12", penalty_text)
        self.assertIn("8", penalty_text)
        self.assertIn("35", penalty_text)  # cap

        # 必须说明单位
        self.assertIn("FSHI", penalty_text)

        # 必须说明场景特征来源
        self.assertIn("knowledge_source_conflict_rate", penalty_text)
        self.assertIn("promise_conflict_rate", penalty_text)
        self.assertIn("complaint_rate", penalty_text)

    def test_mapping_explanation_no_old_formula(self):
        """MH-BUG-v0.4-001: fshi_penalty 不再包含旧的 10x/8x/5x 表述"""
        explanation = self.adapter.mapping_explanation()
        penalty_text = explanation["fshi_penalty"]

        # 旧公式特征：直接用业务指标名 + 倍数
        self.assertNotIn("10x", penalty_text)
        self.assertNotIn("8x", penalty_text)
        self.assertNotIn("5x", penalty_text)
        # 旧公式的描述方式："由 promise_conflict_rate(10x) + ..."
        self.assertNotIn(
            "promise_conflict_rate(10x)",
            penalty_text
        )

    # === P2-2: include_input_metrics ===

    def test_include_input_metrics_false(self):
        """P2-2: include_input_metrics=False 时不暴露原始指标"""
        scenario = self.adapter.to_scenario(
            self.normal_metrics, include_input_metrics=False
        )
        self.assertNotIn("input_metrics", scenario["_adapter"])
        self.assertIn("input_metrics_hash", scenario["_adapter"])

    def test_include_input_metrics_true(self):
        """P2-2: include_input_metrics=True 时保留原始指标"""
        scenario = self.adapter.to_scenario(
            self.normal_metrics, include_input_metrics=True
        )
        self.assertIn("input_metrics", scenario["_adapter"])
        self.assertNotIn("input_metrics_hash", scenario["_adapter"])

    # === P0-3: Golden sample 对比 ===

    def test_golden_sample_normal(self):
        """P0-3: 正常场景 adapter golden sample 对比"""
        from simulate import run_simulation
        golden_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test-records", "v0.4-adapter", "golden_ecommerce_normal_seed42.json"
        )
        if not os.path.exists(golden_path):
            self.skipTest("Golden sample not yet generated (run examples/generate_v04_golden.py)")

        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)

        scenario = self.adapter.to_scenario(
            self.normal_metrics, simulation_id="GOLDEN_NORMAL"
        )
        result = run_simulation(scenario, seed=42)

        self.assertEqual(result["fshi"]["value"], golden["fshi"]["value"])
        self.assertEqual(result["fshi"]["risk_level"], golden["fshi"]["risk_level"])
        self.assertEqual(result["runestone"]["runestone_id"], golden["runestone"]["runestone_id"])

    def test_golden_sample_conflict(self):
        """P0-3: 冲突场景 adapter golden sample 对比"""
        from simulate import run_simulation
        golden_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test-records", "v0.4-adapter", "golden_ecommerce_conflict_seed42.json"
        )
        if not os.path.exists(golden_path):
            self.skipTest("Golden sample not yet generated (run examples/generate_v04_golden.py)")

        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)

        scenario = self.adapter.to_scenario(
            self.conflict_metrics, simulation_id="GOLDEN_CONFLICT"
        )
        result = run_simulation(scenario, seed=42)

        self.assertEqual(result["fshi"]["value"], golden["fshi"]["value"])
        self.assertEqual(result["fshi"]["risk_level"], golden["fshi"]["risk_level"])
        self.assertEqual(result["runestone"]["runestone_id"], golden["runestone"]["runestone_id"])


class TestScenarioFeaturesDefaults(unittest.TestCase):
    """ScenarioFeatures 默认值测试"""

    def test_default_values(self):
        sf = ScenarioFeatures()
        self.assertEqual(sf.conflict_density, 0.0)
        self.assertEqual(sf.irreversibility, 0.5)
        self.assertEqual(sf.diffusivity, 0.3)

    def test_clamp_behavior(self):
        sf = ScenarioFeatures(conflict_density=-0.5, irreversibility=2.0, diffusivity=1.5)
        self.assertEqual(sf.conflict_density, 0.0)
        self.assertEqual(sf.irreversibility, 1.0)
        self.assertEqual(sf.diffusivity, 1.0)

    def test_backward_compat_reversibility_property(self):
        """P0-2: reversibility 属性映射到 irreversibility"""
        sf = ScenarioFeatures(irreversibility=0.7)
        self.assertEqual(sf.reversibility, 0.7)


if __name__ == "__main__":
    unittest.main()

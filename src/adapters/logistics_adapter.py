#!/usr/bin/env python3
"""
全频谱协议 · 物流客服 MetricAdapter
对应 CASE006：物流 AI 客服知识源冲突审计样例
对应 CASE007：物流 AI 客服质检与系统优化样例

将物流客服业务指标映射为引擎可用的 CivilizationState + ScenarioFeatures。

映射逻辑参考 CASE006/CASE007 的全频谱解释层：
    - 生存层 (S_l)：配送延误率、包裹丢失率、路线偏差率 — 物理交付稳定性
    - 协调层 (S_m)：首次解决率、信息差率、多触点冲突率 — 信任与协作
    - 意义层 (S_h)：赔付公平性、沟通清晰度、承诺兑现率 — 公平性与方向感

权重说明：偏生存侧（survival=0.45），因为物流场景的物理不可逆性
（冷链断裂、包裹丢失）直接影响生存层。

irreversibility 语义说明（方案B）：
    irreversibility = 不可逆程度，数值越高越不可逆。
    物流冷链 irreversibility = 0.85（七个CASE最高值），
    远高于电商 0.57（退款可逆）。
    字段名不变，数值语义已翻转（v0.7评审修改）。

引擎定位说明：
    引擎是观察者，不操作业务。所有推荐操作使用 recommend_human_review。
    人工复核策略：required_by_policy / recommended / not_required。
"""

from typing import Dict, Tuple

from .metric_adapter import MetricAdapter, ScenarioFeatures
from ..core.state import CivilizationState


class LogisticsAdapter(MetricAdapter):
    """
    物流客服 MetricAdapter（冷链场景优先）。

    锚点：CASE006（物流 AI 客服知识源冲突审计）
          CASE007（物流 AI 客服质检与系统优化）
    定位：不接真实企业数据，使用合成业务指标验证映射逻辑。

    用法：
        adapter = LogisticsAdapter()
        metrics = {
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
        state, features = adapter.to_state(metrics)
        scenario = adapter.to_scenario(metrics, simulation_id="CASE006_DEMO")
        result = run_simulation(scenario, seed=42)
    """

    @property
    def industry(self) -> str:
        return "logistics_customer_service"

    @property
    def required_metrics(self) -> list:
        return [
            "delivery_delay_rate",
            "package_loss_rate",
            "route_deviation_rate",
            "first_resolution_rate",
            "information_gap_rate",
            "multi_touchpoint_conflict",
            "compensation_fairness",
            "communication_clarity",
            "commitment_fulfillment",
        ]

    @property
    def optional_metrics(self) -> list:
        return [
            "temperature_violation_rate",
            "return_rate",
        ]

    def to_state(self, metrics: Dict[str, float]) -> Tuple[CivilizationState, ScenarioFeatures]:
        """
        将物流客服业务指标映射为引擎状态。

        所有输入指标应为 [0,1] 归一化值：
        - 比率类指标（如 delivery_delay_rate）：原始比率，越高越差
        - 评分类指标（如 compensation_fairness）：[0,1] 评分，越高越好

        映射方向：
        - 高 delivery_delay_rate / package_loss_rate / route_deviation_rate → 低 survival
        - 高 information_gap_rate / multi_touchpoint_conflict → 低 coordination
        - 高 compensation_fairness / communication_clarity / commitment_fulfillment → 高 meaning
        """
        # === 生存层 S_l ===
        # 配送延误率、包裹丢失率、路线偏差率越高，生存层越低
        survival = 1.0 - (
            self._clamp(metrics.get("delivery_delay_rate", 0.05)) * 0.40 +
            self._clamp(metrics.get("package_loss_rate", 0.005)) * 0.35 +
            self._clamp(metrics.get("route_deviation_rate", 0.03)) * 0.25
        )

        # === 协调层 S_m ===
        # 首次解决率越高，协调层越高
        # 信息差率越高，协调层越低（信息不一致导致信任下降）
        # 多触点冲突越高，协调层越低
        coordination = (
            self._clamp(metrics.get("first_resolution_rate", 0.80)) * 0.35 +
            (1.0 - self._clamp(metrics.get("information_gap_rate", 0.10))) * 0.35 +
            (1.0 - self._clamp(metrics.get("multi_touchpoint_conflict", 0.05))) * 0.30
        )

        # === 意义层 S_h ===
        # 赔付公平性、沟通清晰度、承诺兑现率越高，意义层越高
        meaning = (
            self._clamp(metrics.get("compensation_fairness", 0.85)) * 0.35 +
            self._clamp(metrics.get("communication_clarity", 0.80)) * 0.35 +
            self._clamp(metrics.get("commitment_fulfillment", 0.88)) * 0.30
        )

        # === 场景特征 ===
        # 冲突密度：延误率 + 多触点冲突
        conflict_density = min(1.0,
            self._clamp(metrics.get("delivery_delay_rate", 0.05)) * 0.5 +
            self._clamp(metrics.get("multi_touchpoint_conflict", 0.05)) * 0.5
        )

        # 不可逆风险强度：物流冷链固定 0.85（物理不可逆，七CASE最高值）
        # 方案B：字段名不变，数值语义翻转（越高越不可逆）
        irreversibility = 0.85

        # 扩散性：信息差率越高，风险扩散越快
        diffusivity = min(1.0,
            self._clamp(metrics.get("information_gap_rate", 0.10))
        )

        state = CivilizationState(
            survival=survival,
            coordination=coordination,
            meaning=meaning,
        )

        features = ScenarioFeatures(
            conflict_density=conflict_density,
            irreversibility=irreversibility,
            diffusivity=diffusivity,
        )

        return state, features

    def compute_penalty(self, metrics: Dict[str, float]) -> float:
        """
        计算物流客服场景的 FSHI 罚分。

        罚分基于业务指标阈值触发，直接从 FSHI 总分中扣除。

        罚分规则：
            - delivery_delay_rate > 0.15 → +10
            - package_loss_rate > 0.02 → +12
            - multi_touchpoint_conflict > 0.20 → +8

        cap = 35（基于电商适配器 penalty 最大值 30 + 物流场景物理不可逆特性的额外 5 分余量）

        典型值：
        - 正常场景：delay=0.05, loss=0.005, conflict=0.05 → 0 罚分
        - 冲突场景：delay=0.35, loss=0.08, conflict=0.55 → 10+12+8=30 罚分

        Returns:
            罚分值（0-35 之间，cap=35.0 防止异常输入导致超限扣分）
        """
        penalty = 0.0

        delay = self._clamp(metrics.get("delivery_delay_rate", 0.0))
        if delay > 0.15:
            penalty += 10.0

        loss = self._clamp(metrics.get("package_loss_rate", 0.0))
        if loss > 0.02:
            penalty += 12.0

        conflict = self._clamp(metrics.get("multi_touchpoint_conflict", 0.0))
        if conflict > 0.20:
            penalty += 8.0

        return min(35.0, penalty)

    def industry_weights(self) -> Dict[str, float]:
        """
        物流客服场景默认权重。
        偏生存侧（survival=0.45），因为物理不可逆性直接影响交付稳定性。
        """
        return {"survival": 0.45, "coordination": 0.30, "meaning": 0.25}

    def mapping_explanation(self) -> Dict[str, str]:
        """
        返回映射说明字典，用于审计追溯。
        """
        return {
            "survival": "由 delivery_delay_rate(0.40) + package_loss_rate(0.35) + route_deviation_rate(0.25) 计算",
            "coordination": "由 first_resolution_rate(0.35) + (1-information_gap_rate)(0.35) + (1-multi_touchpoint_conflict)(0.30) 计算",
            "meaning": "由 compensation_fairness(0.35) + communication_clarity(0.35) + commitment_fulfillment(0.30) 计算",
            "penalty": "delay>0.15(+10) | loss>0.02(+12) | touchpoint_conflict>0.20(+8) | cap 35. 基于电商适配器penalty最大值30+物流场景物理不可逆特性的额外5分余量",
            "irreversibility": "0.85 (物流冷链物理不可逆，七CASE最高值。方案B：字段名不变，数值语义翻转)",
            "diffusivity": "由 information_gap_rate 直接映射（信息差越高，风险扩散越快）",
            "weights_note": "偏生存侧(survival=0.45)，因为物流场景物理不可逆性直接影响交付稳定性。CASE006/007 启发式权重，尚未基于真实企业数据校准",
            "engine_role": "引擎是观察者，不操作业务。所有推荐操作使用 recommend_human_review",
        }

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """将值限制在 [lo, hi] 区间"""
        return max(lo, min(hi, float(value)))


# 便捷函数
def adapt_logistics_metrics(metrics: Dict[str, float]) -> dict:
    """
    快捷函数：物流指标 → scenario dict

    >>> from src.adapters.logistics_adapter import adapt_logistics_metrics
    >>> scenario = adapt_logistics_metrics({"delivery_delay_rate": 0.05, ...})
    >>> from simulate import run_simulation
    >>> result = run_simulation(scenario, seed=42)
    """
    adapter = LogisticsAdapter()
    return adapter.to_scenario(metrics)

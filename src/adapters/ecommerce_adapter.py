#!/usr/bin/env python3
"""
全频谱协议 · 电商客服 MetricAdapter
对应 CASE005：电商 AI 客服知识源冲突样例

将电商客服业务指标映射为引擎可用的 CivilizationState + ScenarioFeatures。

映射逻辑参考 CASE005 的全频谱解释层：
    - 生存层 (S_l)：退款率、投诉率、响应时间 — 基本运营稳定性
    - 协调层 (S_m)：承诺冲突率、知识源冲突率、人工转接率 — 信任与协作
    - 意义层 (S_h)：申诉成功率、解决满意度、规则清晰度 — 公平性与方向感

⚠️ 权重说明：当前所有权重均为 CASE005 启发式权重，尚未基于真实企业数据校准。

语义说明（P1-3/P1-4 修复）：
    - manual_handoff_rate：v0.4 中暂作为协调压力指标，不直接等同于负面服务质量。
      高风险场景中 AI 主动转人工是边界意识的表现，非协调失败。
      后续版本将改为复合指标（handoff + satisfaction 联合判断）。
    - appeal_success_rate：v0.4 中表示纠错机制有效性，不表示初始错误率。
      申诉成功率高 = 纠错机制有效（正面）；但未来需结合 appeal_rate 联合判断。
"""

from typing import Dict, Tuple
from .metric_adapter import MetricAdapter, ScenarioFeatures
from ..core.state import CivilizationState


class EcommerceCustomerServiceAdapter(MetricAdapter):
    """
    电商客服 MetricAdapter。

    锚点：CASE005（电商 AI 客服知识源冲突）
    定位：不接真实企业数据，使用合成业务指标验证映射逻辑。

    用法：
        adapter = EcommerceCustomerServiceAdapter()
        metrics = {
            "refund_rate": 0.12,
            "complaint_rate": 0.08,
            "promise_conflict_rate": 0.18,
            "knowledge_source_conflict_rate": 0.15,
            "manual_handoff_rate": 0.22,
            "appeal_success_rate": 0.31,
            "resolution_satisfaction": 0.65,
            "response_time_score": 0.80,
            "policy_clarity_score": 0.72,
        }
        state, features = adapter.to_state(metrics)
        scenario = adapter.to_scenario(metrics, simulation_id="CASE005_DEMO")
        result = run_simulation(scenario, seed=42)
    """

    @property
    def industry(self) -> str:
        return "ecommerce_customer_service"

    @property
    def required_metrics(self) -> list:
        return [
            "refund_rate",
            "complaint_rate",
            "promise_conflict_rate",
            "knowledge_source_conflict_rate",
            "manual_handoff_rate",
            "appeal_success_rate",
            "resolution_satisfaction",
            "response_time_score",
            "policy_clarity_score",
        ]

    @property
    def optional_metrics(self) -> list:
        return [
            "repeat_complaint_rate",
            "ai_error_rate",
            "escalation_rate",
        ]

    def to_state(self, metrics: Dict[str, float]) -> Tuple[CivilizationState, ScenarioFeatures]:
        """
        将电商客服业务指标映射为引擎状态。

        所有输入指标应为 [0,1] 归一化值：
        - 比率类指标（如 refund_rate）：原始比率，越高越差
        - 评分类指标（如 resolution_satisfaction）：[0,1] 评分，越高越好

        映射方向：
        - 高 refund_rate / complaint_rate → 低 survival
        - 高 promise_conflict_rate / knowledge_source_conflict_rate → 低 coordination
        - 高 appeal_success_rate / resolution_satisfaction → 高 meaning
        """
        # === 生存层 S_l ===
        # 退款率和投诉率越高，生存层越低
        # 响应时间评分越高（响应快），生存层越高
        survival = 1.0 - (
            self._clamp(metrics.get("refund_rate", 0.10)) * 0.35 +
            self._clamp(metrics.get("complaint_rate", 0.05)) * 0.40 +
            (1.0 - self._clamp(metrics.get("response_time_score", 0.80))) * 0.25
        )

        # === 协调层 S_m ===
        # 承诺冲突和知识源冲突越高，协调层越低
        # 人工转接率越高，说明 AI 自主协调能力越弱
        # 注意：manual_handoff_rate 在某些场景下是边界意识表现（P1-3）
        coordination = 1.0 - (
            self._clamp(metrics.get("promise_conflict_rate", 0.10)) * 0.45 +
            self._clamp(metrics.get("knowledge_source_conflict_rate", 0.10)) * 0.35 +
            self._clamp(metrics.get("manual_handoff_rate", 0.15)) * 0.20
        )

        # === 意义层 S_h ===
        # 申诉成功率（纠错机制有效性，P1-4）、解决满意度、规则清晰度越高，意义层越高
        meaning = (
            self._clamp(metrics.get("appeal_success_rate", 0.30)) * 0.30 +
            self._clamp(metrics.get("resolution_satisfaction", 0.60)) * 0.35 +
            self._clamp(metrics.get("policy_clarity_score", 0.70)) * 0.35
        )

        # === 场景特征 ===
        # 冲突密度：知识源冲突 + 承诺冲突
        conflict_density = min(1.0,
            self._clamp(metrics.get("knowledge_source_conflict_rate", 0.10)) +
            self._clamp(metrics.get("promise_conflict_rate", 0.10))
        )

        # 不可逆风险强度（P0-2 修复：原 reversibility 重命名）
        # 承诺冲突越高，AI 已做出的承诺越难撤回
        # （用户已经期待退款+优惠券，撤回承诺会导致信任崩溃）
        irreversibility = min(1.0,
            self._clamp(metrics.get("promise_conflict_rate", 0.10)) * 2.0
        )

        # 扩散性：投诉率越高，负面口碑扩散越快
        # 乘以放大系数 3.0 模拟社交媒体传播效应
        diffusivity = min(1.0,
            self._clamp(metrics.get("complaint_rate", 0.05)) * 3.0
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
        P0-1 修复：计算电商客服场景的 FSHI 罚分。

        罚分基于场景特征（冲突密度/不可逆性/扩散性），直接从 FSHI 总分中扣除，
        使知识源冲突场景不会误判为 NORMAL。

        罚分公式：
            penalty = conflict_density * 15
                    + irreversibility * 12
                    + diffusivity * 8

        ⚠️ 单位说明：
            系数 15/12/8 是 FSHI 百分制扣分权重（0-100 scale），
            不是 0-1 归一化权重。因为三个特征值均在 [0,1] 区间，
            理论最大扣分为 15+12+8 = 35 FSHI points。
            Penalty is measured in FSHI points on a 0-100 scale.
            Maximum adapter penalty is 35 FSHI points.

        典型值：
        - 正常场景：0.09*15 + 0.10*12 + 0.09*8 ≈ 3.3 → FSHI 几乎不变
        - 冲突场景：0.40*15 + 0.44*12 + 0.36*8 ≈ 14.2 → FSHI 降约 14 分（70→56, NORMAL→WARNING）

        Returns:
            罚分值（0-35 之间，cap=35.0 防止异常输入导致超限扣分）
        """
        state, features = self.to_state(metrics)
        penalty = (
            features.conflict_density * 15.0 +
            features.irreversibility * 12.0 +
            features.diffusivity * 8.0
        )
        # 防御性 cap：三个特征均在 [0,1]，理论最大值 = 15+12+8 = 35
        # 即使未来特征范围被修改，也不会导致 penalty 无限扩大
        return min(35.0, penalty)

    def industry_weights(self) -> Dict[str, float]:
        """
        电商客服场景默认权重。
        注意：此为行业特定权重，全局 FSHI 默认权重仍为 0.40/0.35/0.25（FSHIConfig）。
        """
        return {"survival": 0.40, "coordination": 0.35, "meaning": 0.25}

    def mapping_explanation(self) -> Dict[str, str]:
        """
        P2-3 修复（rc3 审计一致性修正）：返回映射说明，便于审计追溯。

        ⚠️ 审计一致性要求：
            fshi_penalty 说明必须与 compute_penalty() 实际公式完全一致。
            MiniHub MH-BUG-v0.4-001 已修复旧版不一致问题。
        """
        return {
            "survival": "由 refund_rate(0.35) + complaint_rate(0.40) + response_time_score(0.25) 计算",
            "coordination": "由 promise_conflict_rate(0.45) + knowledge_source_conflict_rate(0.35) + manual_handoff_rate(0.20) 计算",
            "meaning": "由 appeal_success_rate(0.30) + resolution_satisfaction(0.35) + policy_clarity_score(0.35) 计算",
            "fshi_penalty": (
                "penalty = min(35.0, conflict_density*15 + irreversibility*12 + diffusivity*8). "
                "单位为 FSHI 百分制扣分(0-100 scale)，最大扣分 35.0. "
                "场景特征来源: conflict_density = min(1.0, knowledge_source_conflict_rate + promise_conflict_rate); "
                "irreversibility = min(1.0, promise_conflict_rate * 2.0); "
                "diffusivity = min(1.0, complaint_rate * 3.0)"
            ),
            "irreversibility": "由 promise_conflict_rate * 2.0 计算（承诺越冲突越难撤回）",
            "diffusivity": "由 complaint_rate * 3.0 计算（社交媒体放大效应）",
            "weights_note": "CASE005 启发式权重，尚未基于真实企业数据校准",
        }

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """将值限制在 [lo, hi] 区间"""
        return max(lo, min(hi, float(value)))


# 便捷函数
def adapt_ecommerce_metrics(metrics: Dict[str, float]) -> dict:
    """
    快捷函数：电商指标 → scenario dict

    >>> from src.adapters.ecommerce_adapter import adapt_ecommerce_metrics
    >>> scenario = adapt_ecommerce_metrics({"refund_rate": 0.12, ...})
    >>> from simulate import run_simulation
    >>> result = run_simulation(scenario, seed=42)
    """
    adapter = EcommerceCustomerServiceAdapter()
    return adapter.to_scenario(metrics)

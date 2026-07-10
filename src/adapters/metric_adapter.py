#!/usr/bin/env python3
"""
全频谱协议 · MetricAdapter 基类
业务指标 → 文明状态 + 场景特征

v0.4 核心问题：
    survival / coordination / meaning / conflict_density / irreversibility / diffusivity
    这些值从真实业务系统哪里来？如何清洗？如何映射到三频状态向量？

MetricAdapter 回答这个问题：
    输入：行业业务指标（合成或真实）
    输出：CivilizationState + ScenarioFeatures，可直接进入 run_simulation()

v0.4 MetricAdapter 优化（P0 修复）：
    - 引入 compute_penalty() 机制，使冲突场景 FSHI 更合理地反映风险等级
    - reversibility 重命名为 irreversibility，消除语义歧义
    - to_scenario() 自动调用 validate_metrics()，缺失字段抛出 ValueError
    - 新增 mapping_explanation 输出，便于审计追溯
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from ..core.state import CivilizationState


@dataclass
class ScenarioFeatures:
    """
    场景级特征，由业务指标推导，用于补充 simulate.py 的 scenario 配置。

    这些字段对应 Scenario Input Schema 中的同名字段：
    - conflict_density: 冲突密度 [0,1]，值越高表示冲突越密集
    - irreversibility: 不可逆风险强度 [0,1]，值越高表示决策后果越难撤销（P0-2 修复：原 reversibility 重命名）
    - diffusivity: 扩散性 [0,1]，值越高表示风险越容易扩散
    """
    conflict_density: float = 0.0
    irreversibility: float = 0.5
    diffusivity: float = 0.3

    def __post_init__(self):
        self.conflict_density = max(0.0, min(1.0, self.conflict_density))
        self.irreversibility = max(0.0, min(1.0, self.irreversibility))
        self.diffusivity = max(0.0, min(1.0, self.diffusivity))

    @property
    def reversibility(self) -> float:
        """向后兼容：reversibility 属性映射到 irreversibility"""
        return self.irreversibility


class MetricAdapter(ABC):
    """
    行业指标适配器基类。

    子类需要实现以下方法：
    - to_state(): 将行业业务指标映射为 (CivilizationState, ScenarioFeatures)
    - compute_penalty(): 计算场景级 FSHI 罚分（v0.4 新增，用于使冲突场景 FSHI 更合理）

    可选覆盖：
    - industry_weights(): 返回该行业的默认 FSHI 权重
    - mapping_explanation(): 返回映射说明字典，用于审计

    用法：
        adapter = EcommerceCustomerServiceAdapter()
        state, features = adapter.to_state(metrics)
        scenario = adapter.to_scenario(metrics, simulation_id="CASE005_DEMO")
        result = run_simulation(scenario, seed=42)

    ⚠️ 权重说明：当前所有权重均为 CASE005 启发式权重，尚未基于真实企业数据校准。
    """

    @property
    @abstractmethod
    def industry(self) -> str:
        """行业标识，如 'ecommerce_customer_service'"""
        pass

    @property
    @abstractmethod
    def required_metrics(self) -> list:
        """必需的指标键名列表"""
        pass

    @property
    def optional_metrics(self) -> list:
        """可选的指标键名列表"""
        return []

    @abstractmethod
    def to_state(self, metrics: Dict[str, float]) -> tuple:
        """
        将业务指标映射为 (CivilizationState, ScenarioFeatures)。

        Args:
            metrics: 业务指标字典，键为指标名，值为 [0,1] 归一化值

        Returns:
            (CivilizationState, ScenarioFeatures)
        """
        pass

    def compute_penalty(self, metrics: Dict[str, float]) -> float:
        """
        计算场景级 FSHI 罚分。

        罚分直接从 FSHI 总分中扣除，用于使冲突场景的风险等级更合理。
        例如：冲突场景不加罚分时 FSHI=70(NORMAL)，加罚分后 FSHI=58(WARNING)。

        子类应覆盖此方法以实现行业特定的罚分逻辑。
        基类默认返回 0.0（无罚分）。

        Args:
            metrics: 业务指标字典

        Returns:
            罚分值（0-35 之间，0 表示无罚分）
        """
        return 0.0

    def industry_weights(self) -> Dict[str, float]:
        """
        返回该行业的默认 FSHI 权重。
        基类返回全局默认权重 0.40/0.35/0.25。
        子类可覆盖以提供行业特定权重。

        注意：全局 FSHI 默认权重（FSHIConfig）为 0.40/0.35/0.25。
        """
        return {"survival": 0.40, "coordination": 0.35, "meaning": 0.25}

    def mapping_explanation(self) -> Dict[str, str]:
        """
        返回映射说明字典，用于审计追溯。
        子类应覆盖此方法以提供具体的映射说明。
        """
        return {}

    def to_scenario(
        self,
        metrics: Dict[str, float],
        simulation_id: Optional[str] = None,
        input_query: Optional[str] = None,
        sensitivity_level: str = "medium",
        enterprise_id: str = "default",
        rule_version: str = "v0.3",
        weights: Optional[Dict[str, float]] = None,
        ess_horizon: int = 5,
        ess_candidates: int = 10,
        include_input_metrics: bool = True,
    ) -> dict:
        """
        将业务指标转换为完整的 scenario dict，可直接传入 run_simulation()。

        P1-2 修复：自动调用 validate_metrics()，缺失必需字段时抛出 ValueError。
        P0-1 修复：输出 fshi_penalty，使冲突场景 FSHI 风险等级更合理。
        P0-2 修复：输出 irreversibility（原 reversibility）。
        P2-3 修复：输出 mapping_explanation 便于审计。
        P2-2 修复：支持 include_input_metrics 参数控制敏感数据暴露。

        Args:
            metrics: 业务指标字典
            simulation_id: 仿真 ID
            input_query: 场景描述
            sensitivity_level: 敏感度等级
            enterprise_id: 企业 ID
            rule_version: 规则版本
            weights: FSHI 权重（None 则使用行业默认权重）
            ess_horizon: ESS 推演步数
            ess_candidates: ESS 候选路径数
            include_input_metrics: 是否在 _adapter 中保留原始指标（P2-2）

        Returns:
            scenario dict，兼容 simulate.py 的 run_simulation()

        Raises:
            ValueError: 当缺少必需指标时
        """
        # P1-2: 自动校验必需字段
        missing = self.validate_metrics(metrics)
        if missing:
            raise ValueError(
                f"Missing required metrics for {self.industry}: {missing}. "
                f"Required: {self.required_metrics}"
            )

        state, features = self.to_state(metrics)

        # P0-1: 计算 FSHI 罚分
        fshi_penalty = self.compute_penalty(metrics)

        if weights is None:
            weights = self.industry_weights()

        # P2-2: 控制原始指标暴露
        adapter_meta: Dict[str, Any] = {
            "industry": self.industry,
        }
        if include_input_metrics:
            adapter_meta["input_metrics"] = metrics
        else:
            import hashlib
            import json as _json
            metrics_hash = hashlib.sha256(
                _json.dumps(metrics, sort_keys=True).encode()
            ).hexdigest()[:16]
            adapter_meta["input_metrics_hash"] = f"sha256:{metrics_hash}"

        scenario = {
            "simulation_id": simulation_id or f"SIM-{self.industry.upper()}-ADAPTED",
            "input_query": input_query or f"MetricAdapter({self.industry}) auto-generated scenario",
            "sensitivity_level": sensitivity_level,
            "enterprise_id": enterprise_id,
            "rule_version": rule_version,
            "initial_state": {
                "survival": round(state.survival, 4),
                "coordination": round(state.coordination, 4),
                "meaning": round(state.meaning, 4),
            },
            "weights": weights,
            "ess_horizon": ess_horizon,
            "ess_candidates": ess_candidates,
            "conflict_density": round(features.conflict_density, 4),
            "irreversibility": round(features.irreversibility, 4),
            "diffusivity": round(features.diffusivity, 4),
            "fshi_penalty": round(fshi_penalty, 4),
            # 元数据：记录适配器来源
            "_adapter": adapter_meta,
        }

        # P2-3: 添加映射说明
        explanation = self.mapping_explanation()
        if explanation:
            scenario["_adapter"]["mapping_explanation"] = explanation

        return scenario

    def validate_metrics(self, metrics: Dict[str, float]) -> list:
        """
        校验指标字典是否包含所有必需字段。

        Returns:
            缺失字段列表（空列表表示校验通过）
        """
        missing = []
        for key in self.required_metrics:
            if key not in metrics:
                missing.append(key)
        return missing

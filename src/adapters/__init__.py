"""
全频谱协议 · 行业指标适配器模块
MetricAdapter: 业务指标 → CivilizationState + ScenarioFeatures

v0.4: 电商客服适配器 (EcommerceCustomerServiceAdapter)
v0.7: 物流客服适配器 (LogisticsAdapter)
"""

from .metric_adapter import MetricAdapter, ScenarioFeatures
from .ecommerce_adapter import EcommerceCustomerServiceAdapter
from .logistics_adapter import LogisticsAdapter

ALL_ADAPTERS = {
    "ecommerce_customer_service": EcommerceCustomerServiceAdapter,
    "logistics_customer_service": LogisticsAdapter,
}

__all__ = [
    "MetricAdapter",
    "ScenarioFeatures",
    "EcommerceCustomerServiceAdapter",
    "LogisticsAdapter",
    "ALL_ADAPTERS",
]

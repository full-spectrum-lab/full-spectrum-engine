#!/usr/bin/env python3
"""
Full Spectrum Engine API — 适配器显式注册表

设计原则（P1-4 修复）：
    - 使用显式注册表，不是"自动发现"
    - 已注册 adapter 可被 API 列出和调用
    - 未注册 adapter 返回 422
    - v0.7 再考虑插件式自动发现
    - try-except 防护：单个适配器导入失败不影响整体启动
"""

import logging
from typing import Dict, List, Optional, Type

from ..adapters.metric_adapter import MetricAdapter

logger = logging.getLogger("full-spectrum.api.registry")


class AdapterRegistry:
    """
    适配器显式注册表。

    用法：
        registry = AdapterRegistry()
        registry.register(EcommerceCustomerServiceAdapter)
        adapter = registry.get("ecommerce_customer_service")
        names = registry.list_industries()
    """

    def __init__(self):
        self._adapters: Dict[str, MetricAdapter] = {}

    def register(self, adapter_class: Type[MetricAdapter]) -> None:
        """
        注册一个适配器类。

        使用 try-except 防护：如果实例化失败，记录错误但不影响其他适配器。
        """
        try:
            instance = adapter_class()
            industry = instance.industry
            self._adapters[industry] = instance
            logger.info(f"Registered adapter: {industry}")
        except Exception as e:
            logger.error(f"Failed to register adapter {adapter_class.__name__}: {e}")

    def get(self, industry: str) -> Optional[MetricAdapter]:
        """获取已注册的适配器实例。未注册返回 None。"""
        return self._adapters.get(industry)

    def list_industries(self) -> List[str]:
        """返回所有已注册的行业标识列表。"""
        return list(self._adapters.keys())

    def is_registered(self, industry: str) -> bool:
        """检查行业是否已注册。"""
        return industry in self._adapters


# ============================================================
# 全局注册表实例（显式注册，不是自动发现）
# ============================================================

_registry = AdapterRegistry()


def _init_default_adapters():
    """
    显式注册默认适配器。

    每个适配器用独立的 try-except 包裹，
    防止单个适配器导入失败导致整个 API 服务启动不了。
    """
    try:
        from ..adapters.ecommerce_adapter import EcommerceCustomerServiceAdapter
        _registry.register(EcommerceCustomerServiceAdapter)
    except ImportError as e:
        logger.error(f"Failed to import EcommerceCustomerServiceAdapter: {e}")
    except Exception as e:
        logger.error(f"Failed to register EcommerceCustomerServiceAdapter: {e}")

    try:
        from ..adapters.logistics_adapter import LogisticsAdapter
        _registry.register(LogisticsAdapter)
    except ImportError as e:
        logger.error(f"Failed to import LogisticsAdapter: {e}")
    except Exception as e:
        logger.error(f"Failed to register LogisticsAdapter: {e}")


# 模块加载时自动初始化默认适配器
_init_default_adapters()


def get_registry() -> AdapterRegistry:
    """获取全局注册表实例。"""
    return _registry

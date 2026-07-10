#!/usr/bin/env python3
"""
Full Spectrum Engine API — Explicit adapter registry.

Design principles (P1-4 fix):
    - Uses an explicit registry, not "auto-discovery"
    - Registered adapters can be listed and invoked via API
    - Unregistered adapters return 422
    - Plugin-style auto-discovery deferred to v0.7+
    - try-except guard: a single adapter import failure does not block startup
"""

import logging
from typing import Dict, List, Optional, Type

from ..adapters.metric_adapter import MetricAdapter

logger = logging.getLogger("full-spectrum.api.registry")


class AdapterRegistry:
    """
    Explicit adapter registry.

    Usage:
        registry = AdapterRegistry()
        registry.register(EcommerceCustomerServiceAdapter)
        adapter = registry.get("ecommerce_customer_service")
        names = registry.list_industries()
    """

    def __init__(self):
        self._adapters: Dict[str, MetricAdapter] = {}

    def register(self, adapter_class: Type[MetricAdapter]) -> None:
        """
        Register an adapter class.

        Uses try-except guard: if instantiation fails, the error is logged
        but other adapters are not affected.
        """
        try:
            instance = adapter_class()
            industry = instance.industry
            self._adapters[industry] = instance
            logger.info(f"Registered adapter: {industry}")
        except Exception as e:
            logger.error(f"Failed to register adapter {adapter_class.__name__}: {e}")

    def get(self, industry: str) -> Optional[MetricAdapter]:
        """Get a registered adapter instance. Returns None if not registered."""
        return self._adapters.get(industry)

    def list_industries(self) -> List[str]:
        """Return a list of all registered industry identifiers."""
        return list(self._adapters.keys())

    def is_registered(self, industry: str) -> bool:
        """Check whether an industry is registered."""
        return industry in self._adapters


# ============================================================
# Global registry instance (explicit registration, not auto-discovery)
# ============================================================

_registry = AdapterRegistry()


def _init_default_adapters():
    """
    Explicitly register default adapters.

    Each adapter is wrapped in its own try-except,
    so a single adapter import failure does not prevent the API from starting.
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


# Auto-initialize default adapters on module load
_init_default_adapters()


def get_registry() -> AdapterRegistry:
    """Get the global registry instance."""
    return _registry

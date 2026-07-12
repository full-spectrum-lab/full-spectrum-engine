#!/usr/bin/env python3
"""
ProfileRegistry: a concrete :class:`ObjectRegistry` for the 13 profile types.

Fixtures and the shared schema live under this package so the registry is fully
self-contained and offline (FR-01 / AC-01). A module-level default registry is
lazily loaded so ``run_envelope`` and the CLI/REST share one instance.
"""
import os

from ..registry import ObjectRegistry

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCHEMA = os.path.join(_HERE, "schemas", "profile.schema.json")
_FIXTURES = os.path.join(_HERE, "fixtures")


class ProfileRegistry(ObjectRegistry):
    """Versioned registry for governance Profiles (13 profile_type values)."""

    def __init__(self):
        super().__init__(_SCHEMA, _FIXTURES)

    def get_by_type(self, profile_type, version=None):
        """Return the first loaded profile of ``profile_type`` (optionally pinned)."""
        matches = [
            obj for (_, _v), obj in self._cache.items()
            if obj.get("profile_type") == profile_type
        ]
        if not matches:
            return None
        if version:
            for obj in matches:
                if obj.get("version") == version:
                    return obj
            return None
        return matches[0]


_default = None


def get_default_registry():
    """Return a lazily-loaded, shared :class:`ProfileRegistry` singleton."""
    global _default
    if _default is None:
        _default = ProfileRegistry()
        _default.load()
    return _default

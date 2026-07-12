#!/usr/bin/env python3
"""
RiskVectorComputer: Profile-driven, deterministic risk_vector (FR-05 / FR-06).

================================================================================
【v1.3 确定性占位实现 — 唯一替换点】
--------------------------------------------------------------------------------
此为 v1.3 确定性占位实现（SRS 未定义既定 risk_vector 算法；语义待 domain owner
确认）。当 domain owner 提供既定算法时，**仅替换本文件中的 RiskVectorComputer
类**即可，其余模块（registry / profile / scenario / certification / envelope /
cli / api）一律不变 —— 这是 v1.3 唯一允许的算法替换点。

本实现的公式**仅依赖** `canonical_json(business_data)` + 各源 Profile 的
`version`，无 numpy / 无 random / 无时钟 / 无环境相关量，因此输出完全可复现，
并暴露 `source_profile_versions` 供 v1.4 ReplayBundle 回放。
================================================================================

Per the v1.3 decision log (decision #6), the value of each dimension depends
ONLY on:

    canonical_json(business_data)  +  the ``version`` of each source Profile

There is no numpy, no ``random``, no clock and no environment-dependent input,
so the result is fully reproducible and ready for a v1.4 ReplayBundle. The set
of source profile versions is exposed as ``source_profile_versions``.

纵向递归不平均 (shared knowledge #4): each source profile contributes its own
weights; we merge by summing (clamped to [0,1]) and NEVER average lower-layer
scores into an upper layer.

Zero intrusion: brand-new additive module; it does not modify any v1.2 core.
"""
import hashlib

from .envelope import canonical_json


def _clamp(x, lo=0.0, hi=1.0):
    """Clamp ``x`` into the inclusive range ``[lo, hi]``."""
    return max(lo, min(hi, x))


def _transform(seed_hex):
    """Map 16 hex chars deterministically into ``[0, 1)``."""
    n = int(seed_hex[:16], 16)
    return (n % 1_000_000) / 1_000_000.0


class RiskVectorComputer:
    """Compute a Profile-driven, deterministic ``risk_vector``.

    【v1.3 确定性占位实现 — 唯一替换点】当 domain owner 提供既定算法时，仅替换
    本类即可，其余模块不变。公式仅依赖 ``canonical_json(business_data)`` + 各源
    Profile ``version``，无 numpy/random，输出暴露 ``source_profile_versions``
    供 v1.4 回放。

    Parameters are profile dicts (as loaded from the registry) or ``None``:
      * ``measurement``  — how to compute (measurement spec; carries weights)
      * ``fshi_profile`` — FSHI measurement profile (carries weights)
      * ``risk_profile`` — Risk measurement profile (carries weights)
      * ``evaluation``   — Evaluation policy (metadata; the deterministic formula
                          does not consume its thresholds, per decision #6)
    """

    def __init__(self, measurement, fshi_profile, risk_profile, evaluation):
        self.measurement = measurement or {}
        self.fshi_profile = fshi_profile or {}
        self.risk_profile = risk_profile or {}
        self.evaluation = evaluation or {}

    def _collect_weights(self):
        """Merge weights from all source profiles (sum + clamp, no averaging)."""
        weights = {}
        for prof in (self.measurement, self.fshi_profile, self.risk_profile):
            params = (prof.get("domain") or {}).get("parameters") or {}
            for dim, wt in (params.get("weights") or {}).items():
                weights[dim] = _clamp(weights.get(dim, 0.0) + float(wt))
        return weights

    def _source_versions(self):
        """Return the sorted, de-duplicated ``id@version`` list of source profiles."""
        versions = []
        for prof in (self.measurement, self.fshi_profile, self.risk_profile, self.evaluation):
            pid = prof.get("id")
            ver = prof.get("version")
            if pid and ver:
                versions.append(f"{pid}@{ver}")
        return sorted(set(versions))

    def compute(self, business_data):
        """Return the extended ``risk_vector`` dict for ``business_data``."""
        business_canon = canonical_json(business_data)
        weights = self._collect_weights()
        dims = sorted(weights.keys())
        src_versions = self._source_versions()
        values = []
        for dim in dims:
            seed_input = business_canon + "|" + "|".join(src_versions) + "|" + dim
            seed = hashlib.sha256(seed_input.encode("utf-8")).hexdigest()
            value = _clamp(weights[dim] * _transform(seed))
            values.append(value)
        return {
            "dimensions": dims,
            "values": values,
            "profile_driven": True,
            "computation": "profile_driven_v1.3",
            "source_profile_versions": src_versions,
            "deterministic": True,
            "note": "v1.3 Profile-driven; reproducible from (business_data, profile versions)",
        }

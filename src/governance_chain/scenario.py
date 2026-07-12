#!/usr/bin/env python3
"""
Scenario Profile (FR-03): governance scenarios decoupled from Adapters.

Three scenario types are supported — Overcommitment, CustomerServiceAudit and
KnowledgeConflict. A Scenario DECLARES governance conditions (notably
``hard_forbidden_conditions``); it does **not** carry a rule engine. The actual
rule evaluation lives in the Policy/Scenario layer, never inside an Adapter
(AC-03 / R-01). The existing ``knowledge_conflict`` / ``ecommerce`` / ``logistics``
Adapters are untouched (zero intrusion).

A :class:`ScenarioRegistry` loads, validates and digests scenarios exactly like
the :class:`ProfileRegistry` (shared :class:`ObjectRegistry`).
"""
import os

from .registry import ObjectRegistry

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCHEMA = os.path.join(_HERE, "scenarios", "schemas", "scenario.schema.json")
_FIXTURES = os.path.join(_HERE, "scenarios", "fixtures")

SCENARIO_TYPES = ("Overcommitment", "CustomerServiceAudit", "KnowledgeConflict")


def _get_path(context, dotted):
    """Resolve a dot-path (e.g. ``business_data.refund_authority``) in ``context``."""
    cur = context
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _condition_hit(cond, context):
    """Return True when the forbidden state described by ``cond`` is present."""
    field = cond.get("field")
    op = cond.get("op", "equals")
    expected = cond.get("value")
    actual = _get_path(context, field) if field else None
    if op == "equals":
        return actual == expected
    if op == "not_equals":
        return actual != expected
    if op == "is_true":
        return actual is True
    if op == "is_false":
        return actual is False
    if op == "present":
        return actual is not None
    if op == "absent":
        return actual is None
    return False


class ScenarioProfile:
    """Thin wrapper around a scenario dict; evaluates ``hard_forbidden_conditions``."""

    def __init__(self, obj):
        self.obj = obj

    @property
    def scenario_type(self):
        return self.obj.get("scenario_type")

    @property
    def hard_forbidden_conditions(self):
        return (self.obj.get("domain") or {}).get("hard_forbidden_conditions", [])

    def evaluate(self, context):
        """Return the list of hard-forbidden conditions that are HIT in ``context``.

        ``context`` is typically the Input Envelope (so ``business_data`` and any
        top-level field are addressable). A condition is HIT when its forbidden
        state is present.
        """
        hits = []
        for cond in self.hard_forbidden_conditions:
            if _condition_hit(cond, context):
                hits.append({
                    "scenario_id": self.obj.get("id"),
                    "scenario_type": self.scenario_type,
                    "condition_id": cond.get("id"),
                    "description": cond.get("description"),
                    "field": cond.get("field"),
                })
        return hits


class OvercommitmentScenario(ScenarioProfile):
    scenario_type = "Overcommitment"


class CustomerServiceAuditScenario(ScenarioProfile):
    scenario_type = "CustomerServiceAudit"


class KnowledgeConflictScenario(ScenarioProfile):
    scenario_type = "KnowledgeConflict"


_TYPE_MAP = {
    "Overcommitment": OvercommitmentScenario,
    "CustomerServiceAudit": CustomerServiceAuditScenario,
    "KnowledgeConflict": KnowledgeConflictScenario,
}


class ScenarioRegistry(ObjectRegistry):
    """Versioned registry for Scenario Profiles."""

    def __init__(self):
        super().__init__(_SCHEMA, _FIXTURES)

    def get_scenario(self, scenario_id, version=None):
        obj = self.get(scenario_id, version)
        cls = _TYPE_MAP.get(obj.get("scenario_type"), ScenarioProfile)
        return cls(obj)


_default = None


def get_default_registry():
    """Return a lazily-loaded, shared :class:`ScenarioRegistry` singleton."""
    global _default
    if _default is None:
        _default = ScenarioRegistry()
        _default.load()
    return _default

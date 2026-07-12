#!/usr/bin/env python3
"""
v1.3 Profile / Policy / Scenario / determinism test suite (FR-01/02/03/05/06).

Covers:
  FR-01  13 profile types load + validate + version binding + digest
  FR-02  Policy layer (Enterprise Authorization is declarative only, not executed)
  FR-03  Scenario profiles load (Overcommitment/CustomerServiceAudit/KnowledgeConflict)
  FR-05  Profile-driven risk_vector is deterministic (same input + version => same digest)
  FR-06  UNKNOWN / hard-forbidden are explicitly surfaced and not masked by the score
"""
import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import envelope as env_mod  # noqa: E402
from src.governance_chain.profiles.registry import get_default_registry  # noqa: E402
from src.governance_chain.scenario import get_default_registry as get_scenario_registry  # noqa: E402
from src.governance_chain.policy import (  # noqa: E402
    MeasurementProfile,
    EvaluationPolicy,
    EnterpriseAuthorizationPolicy,
    ForbiddenError,
)

PROFILE_TYPES = [
    "LayerProfile", "FSHIProfile", "RiskProfile", "ESSProfile", "ValidationProfile",
    "HumanReviewProfile", "AggregationProfile", "ReportTemplate", "TrustDomainProfile",
    "InteropProfile", "CertificationRequirementProfile", "AuthorizationGateProfile",
    "ActivationProfile",
]

EXAMPLE = os.path.join(REPO_ROOT, "examples", "envelope", "input-envelope.ecommerce.json")


def _all_objects(reg):
    for pid in reg.list_ids():
        for ver in reg.all_versions(pid):
            yield reg.get(pid, ver)


class TestProfileSchemaLoad(unittest.TestCase):
    def test_thirteen_types_present(self):
        reg = get_default_registry()
        loaded_types = {p.get("profile_type") for p in _all_objects(reg)}
        for t in PROFILE_TYPES:
            self.assertIn(t, loaded_types, f"profile_type {t} missing from registry")

    def test_all_profiles_validate_and_digest(self):
        reg = get_default_registry()
        for obj in _all_objects(reg):
            ok, errors = reg.validate(obj)
            self.assertTrue(ok, msg=f"{obj.get('id')} invalid: {errors}")
            # declared digest must equal the recomputed canonical digest
            self.assertEqual(reg.compute_digest(obj), obj.get("digest"),
                             msg=f"{obj.get('id')} digest mismatch")

    def test_version_binding(self):
        reg = get_default_registry()
        obj = reg.get("prof_fshi_ecom_001", "1.0.0")
        self.assertEqual(obj["version"], "1.0.0")
        self.assertEqual(obj["id"], "prof_fshi_ecom_001")
        self.assertEqual(obj["profile_type"], "FSHIProfile")

    def test_scenarios_load(self):
        reg = get_scenario_registry()
        self.assertEqual(len(reg.list_ids()), 3)
        for sid in ("scn_overcommitment_001", "scn_customer_service_audit_001",
                    "scn_knowledge_conflict_001"):
            self.assertIn(sid, reg.list_ids())


class TestPolicyLayer(unittest.TestCase):
    def test_enterprise_auth_not_executed(self):
        pol = EnterpriseAuthorizationPolicy()
        self.assertRaises(ForbiddenError, pol.execute)
        self.assertIsInstance(pol.describe(), dict)

    def test_measurement_evaluation_wrappers(self):
        reg = get_default_registry()
        m = MeasurementProfile(reg.get("prof_fshi_ecom_001", "1.0.0"))
        self.assertIn("weights", m.compute_spec())
        e = EvaluationPolicy(reg.get("prof_validation_ecom_001", "1.0.0"))
        # thresholds() returns the inner threshold mapping extracted from
        # domain.parameters ({"thresholds": {...}}); the keys are dimension names.
        self.assertIn("commitment_risk", e.thresholds())
        self.assertEqual(e.thresholds()["commitment_risk"], 0.6)


class TestDeterminism(unittest.TestCase):
    def _aug_input(self, business_data=None):
        base = json.load(open(EXAMPLE, encoding="utf-8-sig"))
        aug = dict(base)
        aug["profile_refs"] = ["prof_layer_ecom_001@1.0.0"]
        aug["business_data"] = business_data or {"industry": "ecommerce_customer_service", "order_id": "X"}
        return aug

    def test_profile_driven_risk_vector(self):
        out = env_mod.run_envelope(self._aug_input())
        rv = out["risk_vector"]
        self.assertTrue(rv["profile_driven"])
        self.assertTrue(rv["deterministic"])
        self.assertTrue(rv["source_profile_versions"])
        self.assertGreater(len(rv["dimensions"]), 0)
        self.assertEqual(len(rv["dimensions"]), len(rv["values"]))

    def test_deterministic_same_input_same_version(self):
        a = env_mod.run_envelope(self._aug_input())
        b = env_mod.run_envelope(self._aug_input())
        self.assertEqual(a["content_digest"], b["content_digest"])
        self.assertEqual(a["risk_vector"]["values"], b["risk_vector"]["values"])

    def test_version_change_alters_digest(self):
        # different business data -> different digest (proves dependency on inputs)
        a = env_mod.run_envelope(self._aug_input({"industry": "ecommerce", "order_id": "A"}))
        b = env_mod.run_envelope(self._aug_input({"industry": "ecommerce", "order_id": "B"}))
        self.assertNotEqual(a["content_digest"], b["content_digest"])

    def test_output_validates(self):
        out = env_mod.run_envelope(self._aug_input())
        ok, errors = env_mod.validate_output_envelope(out)
        self.assertTrue(ok, msg=errors)


class TestUnknownHardForbidden(unittest.TestCase):
    def test_hard_forbidden_explicit(self):
        base = json.load(open(EXAMPLE, encoding="utf-8-sig"))
        aug = dict(base)
        aug["profile_refs"] = ["prof_layer_ecom_001@1.0.0"]
        aug["scenario_refs"] = ["scn_overcommitment_001@1.0.0"]
        aug["business_data"] = {"industry": "ecommerce_customer_service", "refund_authority": False}
        out = env_mod.run_envelope(aug)
        self.assertTrue(out["hard_forbidden"], "hard_forbidden must be surfaced")
        self.assertTrue(out["human_review_recommendation"]["required"])
        self.assertIn("HARD_FORBIDDEN", out["explanation"]["basis"])
        self.assertIn("hard_forbidden_condition", out["human_review_recommendation"]["reason"])

    def test_unknown_flags_surfaced(self):
        base = json.load(open(EXAMPLE, encoding="utf-8-sig"))
        aug = dict(base)
        aug["profile_refs"] = ["prof_layer_ecom_001@1.0.0"]
        aug["unknowns"] = {"missing_receipt": True}
        out = env_mod.run_envelope(aug)
        self.assertIn("unknown_flags", out)
        self.assertTrue(out["unknown_flags"])

    def test_broken_profile_link_raises(self):
        base = json.load(open(EXAMPLE, encoding="utf-8-sig"))
        aug = dict(base)
        aug["profile_refs"] = ["prof_ghost_999@1.0.0"]
        self.assertRaises(env_mod.InputEnvelopeError, lambda: env_mod.run_envelope(aug))


if __name__ == "__main__":
    unittest.main(verbosity=2)

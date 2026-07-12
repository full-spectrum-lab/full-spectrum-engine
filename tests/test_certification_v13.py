#!/usr/bin/env python3
"""
v1.3 Certification combination engine test suite (FR-07).

Covers the five combination logics (ALL_OF / ANY_OF / AT_LEAST_N / ONE_OF /
NOT_REQUIRED), judging by issuer / scope / validity window / revocation status /
trust domain, and the hard invariant that:
  * only CANDIDATE state is emitted (never "certified" / "authorized");
  * multi trust-domain results are kept as a dict and NEVER merged to one bool.
"""
import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.governance_chain.certification import CertificationEngine  # noqa: E402

CERT = os.path.join(REPO_ROOT, "tests", "fixtures", "certification")


def _load(name):
    return json.load(open(os.path.join(CERT, name + ".json"), encoding="utf-8-sig"))


class TestFiveLogics(unittest.TestCase):
    def setUp(self):
        self.eng = CertificationEngine()

    def test_all_of_satisfied(self):
        res = self.eng.evaluate(_load("requirement_allof"), _load("attestations_external"))
        self.assertTrue(res["requirements_satisfied"])
        self.assertEqual(res["eligibility_candidate"], "CANDIDATE")

    def test_all_of_not_satisfied(self):
        res = self.eng.evaluate(_load("requirement_allof"), _load("attestations_internal"))
        self.assertFalse(res["requirements_satisfied"])
        self.assertEqual(res["eligibility_candidate"], "NOT_CANDIDATE")

    def test_any_of(self):
        res = self.eng.evaluate(_load("requirement_anyof"), _load("attestations_internal"))
        self.assertTrue(res["requirements_satisfied"])

    def test_at_least_n(self):
        req = _load("requirement_atleast_n")  # n = 2
        res_low = self.eng.evaluate(req, _load("attestations_internal"))  # 1 satisfied
        self.assertFalse(res_low["requirements_satisfied"])
        res_ok = self.eng.evaluate(req, _load("attestations_external"))  # 2 satisfied
        self.assertTrue(res_ok["requirements_satisfied"])

    def test_one_of(self):
        req = _load("requirement_oneof")
        res_two = self.eng.evaluate(req, _load("attestations_external"))  # 2 satisfied -> fail
        self.assertFalse(res_two["requirements_satisfied"])
        res_one = self.eng.evaluate(req, _load("attestations_internal"))  # 1 satisfied -> pass
        self.assertTrue(res_one["requirements_satisfied"])

    def test_not_required(self):
        res = self.eng.evaluate(_load("requirement_not_required"), [])
        self.assertTrue(res["requirements_satisfied"])
        self.assertEqual(res["eligibility_candidate"], "CANDIDATE")

    def test_revoked_attestation_not_satisfied(self):
        res = self.eng.evaluate(_load("requirement_allof"), _load("attestations_revoked"))
        self.assertFalse(res["requirements_satisfied"])


class TestMultiTrustDomain(unittest.TestCase):
    def test_trust_domain_results_not_merged(self):
        eng = CertificationEngine()
        res = eng.evaluate(_load("requirement_allof"), _load("attestations_internal"))
        tdr = res["trust_domain_results"]
        self.assertIn("example.enterprise.internal", tdr)
        self.assertIn("external.ca.org", tdr)
        self.assertTrue(tdr["example.enterprise.internal"])
        self.assertFalse(tdr["external.ca.org"])
        self.assertIsInstance(tdr, dict)  # never collapsed to a single boolean

    def test_external_auth_required_flag(self):
        eng = CertificationEngine()
        res = eng.evaluate(_load("requirement_allof"), _load("attestations_external"))
        self.assertTrue(res["external_auth_required"])


class TestCandidateOnly(unittest.TestCase):
    def test_no_certified_or_authorized_conclusion(self):
        eng = CertificationEngine()
        res = eng.evaluate(_load("requirement_allof"), _load("attestations_external"))
        for forbidden in ("certified", "authorized", "active", "granted"):
            self.assertNotIn(forbidden, res)
        for key in ("eligibility_candidate", "requirements_satisfied",
                    "external_auth_required", "trust_domain_results"):
            self.assertIn(key, res)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
v1.3 Certification UNKNOWN-branch edge tests (FR-07 / NFR-05 / AC-06).

These edge cases PIN the engineer's UNKNOWN handling and the architect's red
line (共享知识 §7.4 / 反模式红线): when there is NO attestation (and no
verification) evidence at all, the first-gen Observer must surface
``UNKNOWN`` rather than silently concluding ``NOT_CANDIDATE`` or ``CANDIDATE``.

They are additive: they cover a branch that ``test_certification_v13.py`` did
not exercise, so the "缺证据时不静默降级为 NOT_CANDIDATE" invariant is now
explicitly locked for >= 2 combination logics.
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


class TestUnknownWhenNoEvidence(unittest.TestCase):
    def setUp(self):
        self.eng = CertificationEngine()

    def test_unknown_all_of_no_attestations(self):
        # ALL_OF with non-empty requirements, but ZERO attestation evidence.
        res = self.eng.evaluate(_load("requirement_allof"), [])
        self.assertEqual(res["eligibility_candidate"], "UNKNOWN")
        self.assertFalse(res["requirements_satisfied"])
        # trust-domain map stays a dict even in UNKNOWN state (never merged / crashed)
        self.assertIsInstance(res["trust_domain_results"], dict)

    def test_unknown_one_of_no_attestations(self):
        # ONE_OF with non-empty requirements, ZERO attestation evidence.
        res = self.eng.evaluate(_load("requirement_oneof"), [])
        # Pin the red line: absence of evidence => UNKNOWN, NEVER a conclusion.
        self.assertEqual(res["eligibility_candidate"], "UNKNOWN")
        self.assertNotEqual(res["eligibility_candidate"], "NOT_CANDIDATE")
        self.assertNotEqual(res["eligibility_candidate"], "CANDIDATE")

    def test_unknown_not_silent_with_empty_verification_results(self):
        # Explicitly empty verification_results must NOT silently flip to a
        # negative conclusion; still UNKNOWN (no evidence at all).
        res = self.eng.evaluate(_load("requirement_allof"), [], verification_results=[])
        self.assertEqual(res["eligibility_candidate"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)

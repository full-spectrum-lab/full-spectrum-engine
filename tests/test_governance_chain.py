#!/usr/bin/env python3
"""
Governance-chain CLI regression test.

Reproduces the documented ecommerce after-sales unauthorized-refund example
with the CLI and asserts the generated artifacts are:
  1. byte-for-byte equal to the committed golden artifacts in the protocol repo
     (so "static example" == "reproducible command"), and
  2. valid against the vendored Full Spectrum Protocol schemas.
"""
import json
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import build_chain, validator  # noqa: E402

EXAMPLE_INPUT = os.path.join(REPO_ROOT, "examples", "governance_chain", "raw-input.ecommerce.json")
EXPECTED_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "expected_ecommerce_chain")

ARTIFACT_KINDS = (
    "governance-event",
    "canonical-context",
    "cell-manifest",
    "output-envelope",
    "enterprise-writeback",
)


class TestGovernanceChain(unittest.TestCase):
    def setUp(self):
        with open(EXAMPLE_INPUT, encoding="utf-8-sig") as f:
            self.raw_doc = json.load(f)
        self.artifacts, self.run_id, self.audit_id = build_chain(self.raw_doc)

    def test_ids_deterministic(self):
        self.assertEqual(self.artifacts["governance-event"]["event_id"], "ge_ecom_refund_001")
        self.assertEqual(self.artifacts["canonical-context"]["canonical_context_id"], "cc_ecom_refund_001")
        self.assertEqual(self.run_id, "run_ecom_001")
        self.assertEqual(self.audit_id, "audit_ecom_001")

    def test_decision_blocks_unauthorized_commitment(self):
        ew = self.artifacts["enterprise-writeback"]
        self.assertEqual(ew["safety_action"], "human_review_required")
        self.assertEqual(ew["risk_level"], "high")
        self.assertEqual(ew["reason_code"], "REFUND_COMMITMENT_WITHOUT_AUTHORITY")
        self.assertFalse(ew["allow_auto_reply"])
        self.assertFalse(ew["allow_commitment"])
        self.assertFalse(ew["allow_auto_execution"])
        self.assertTrue(ew["human_review_required"])
        self.assertEqual(ew["review_role"], "customer_service_supervisor")
        self.assertEqual(ew["review_queue"], "after_sales_review")

    def test_risk_axes(self):
        axes = self.artifacts["canonical-context"]["risk_axes"]
        self.assertEqual(axes["commitment_risk"], 0.9)
        self.assertEqual(axes["authority_risk"], 0.9)
        self.assertEqual(axes["knowledge_conflict_risk"], 0.1)

    def test_matches_committed_example(self):
        for kind in ARTIFACT_KINDS:
            expected_path = os.path.join(EXPECTED_DIR, f"{kind}.ecommerce.json")
            with open(expected_path, encoding="utf-8-sig") as f:
                expected = json.load(f)
            self.assertEqual(
                self.artifacts[kind], expected,
                msg=f"generated {kind} differs from committed golden artifact",
            )

    def test_all_artifacts_schema_valid(self):
        for kind in ARTIFACT_KINDS:
            schema_file = validator.map_schema_for_filename(kind + ".json")
            schema = validator.load_schema(schema_file)
            ok, errors = validator.validate_instance(self.artifacts[kind], schema)
            self.assertTrue(ok, msg=f"{kind} failed schema {schema_file}: {errors}")
        self.assertTrue(self.artifacts["output-envelope"]["conformance"]["schema_valid"])

    def test_write_chain_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            from src.governance_chain import write_chain
            writes, _ = write_chain(tmp, self.raw_doc)
            self.assertTrue(os.path.exists(writes["report"]))
            for kind in ARTIFACT_KINDS:
                self.assertTrue(os.path.exists(writes[kind]))
                with open(writes[kind], encoding="utf-8") as f:
                    json.load(f)  # must be parseable


if __name__ == "__main__":
    unittest.main(verbosity=2)

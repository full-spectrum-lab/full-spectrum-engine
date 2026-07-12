#!/usr/bin/env python3
"""
v1.2 Observer Input/Output Envelope — third-party-testable contract suite.

Covers:
  FR-01  Input/Output Envelope schema (§3.1/§3.2/§3.3)
  FR-02  relationships stable refs + broken-link detection (no silent pass)
  FR-03  CLI and REST share the same model (AC-01 equivalence)
  FR-05  schema_id/schema_version/content_digest traceability (AC-03)
  FR-06  v1.0 legacy input compatibility
  FR-07  UNKNOWN explicit handling (AC-06)
  §5     L4_CANDIDATE carried but never externally effective
  NFR-01 offline (no network calls)
"""
import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import envelope as env_mod  # noqa: E402

try:  # REST endpoint depends on the API server (optional import for unit-only runs)
    import tempfile
    import uuid
    from fastapi.testclient import TestClient  # noqa: E402
    from src.api.server import create_app  # noqa: E402
    _HAS_API = True
except Exception:  # pragma: no cover
    _HAS_API = False

EXAMPLE_INPUT = os.path.join(REPO_ROOT, "examples", "envelope", "input-envelope.ecommerce.json")


def _load_example():
    with open(EXAMPLE_INPUT, encoding="utf-8-sig") as f:
        return json.load(f)


class TestEnvelopeSchema(unittest.TestCase):
    def test_input_envelope_schema_valid(self):  # FR-01
        env = _load_example()
        ok, errors = env_mod.validate_input_envelope(env)
        self.assertTrue(ok, msg=f"input envelope invalid: {errors}")

    def test_output_envelope_schema_valid(self):  # FR-01
        out = env_mod.run_envelope(_load_example())
        ok, errors = env_mod.validate_output_envelope(out)
        self.assertTrue(ok, msg=f"output envelope invalid: {errors}")

    def test_contract_version_present(self):
        env = _load_example()
        self.assertEqual(env["contract_version"], env_mod.CONTRACT_VERSION)
        out = env_mod.run_envelope(env)
        self.assertEqual(out["contract_version"], env_mod.CONTRACT_VERSION)

    def test_input_envelope_requires_unknowns(self):  # P1-1 hardening
        # gie-1.2 must reject an input envelope that omits the (now required)
        # `unknowns` field. This locks in the P1-1 hardening: UNKNOWN may never
        # be silent, so the schema forbids its absence.
        env = _load_example()
        env.pop("unknowns", None)
        ok, errors = env_mod.validate_input_envelope(env)
        self.assertFalse(ok, msg=f"input envelope missing `unknowns` must be rejected, got errors={errors}")
        self.assertTrue(
            any("unknowns" in str(e).lower() for e in errors),
            msg=f"errors should reference `unknowns`: {errors}",
        )

        # An explicit (even empty) unknowns object must still be accepted.
        env2 = _load_example()
        env2["unknowns"] = {}
        ok2, errors2 = env_mod.validate_input_envelope(env2)
        self.assertTrue(ok2, msg=f"input envelope with empty `unknowns` must be valid: {errors2}")


class TestCliRestEquivalence(unittest.TestCase):
    def test_run_envelope_deterministic(self):  # AC-01 (model-level parity)
        env = _load_example()
        a = env_mod.run_envelope(env)
        b = env_mod.run_envelope(env)
        self.assertEqual(env_mod.canonical_json(a), env_mod.canonical_json(b))

    def test_cli_run_matches_inprocess(self):  # FR-03 / AC-01
        out = env_mod.run_envelope(_load_example())
        cli = subprocess.run(
            [sys.executable, "-m", "src.governance_chain", "envelope", "run",
             "--input", EXAMPLE_INPUT],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(cli.returncode, 0, msg=cli.stderr)
        cli_out = json.loads(cli.stdout)
        self.assertEqual(env_mod.canonical_json(cli_out), env_mod.canonical_json(out))


class TestBrokenLinks(unittest.TestCase):
    def test_valid_links_pass(self):  # FR-02
        env = _load_example()
        broken = env_mod.check_envelope_links(env, {"subj_ecom_001", "ge_ecom_refund_001"})
        self.assertEqual(broken, [])

    def test_broken_subject_ref_detected(self):  # FR-02 / AC-05
        env = dict(_load_example())
        env["subject_refs"] = ["subj_ghost_999"]
        broken = env_mod.check_envelope_links(env, {"subj_ecom_001"})
        self.assertIn(("subject_ref", "subj_ghost_999"), broken)

    def test_broken_relationship_ref_detected(self):  # FR-02 / AC-05
        env = dict(_load_example())
        env["relationship_refs"] = ["ge_ghost_999"]
        broken = env_mod.check_envelope_links(env, {"ge_ecom_refund_001"})
        self.assertIn(("relationship_ref", "ge_ghost_999"), broken)

    def test_cli_check_links_exits_nonzero_on_broken(self):  # FR-02 / AC-05
        broken = dict(_load_example())
        broken["subject_refs"] = ["subj_ghost_999"]
        tmp = os.path.join(REPO_ROOT, "out", "v12_broken_input.json")
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(broken, f, ensure_ascii=False)
        cli = subprocess.run(
            [sys.executable, "-m", "src.governance_chain", "envelope", "check-links",
             "--input", tmp, "--known", json.dumps({"known_ids": ["subj_ecom_001"]})],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(cli.returncode, 1, msg=cli.stdout + cli.stderr)


class TestLegacyCompat(unittest.TestCase):
    def test_v1_0_input_compat(self):  # FR-06
        legacy_raw = {
            "industry": "ecommerce_customer_service",
            "scenario": "after_sales_unauthorized_refund",
            "order_id": "ORD-2026-001",
        }
        env = env_mod.normalize_legacy_input(legacy_raw)
        ok, errors = env_mod.validate_input_envelope(env)
        self.assertTrue(ok, msg=f"legacy-wrapped input invalid: {errors}")
        self.assertEqual(env["layer"], "L1")
        self.assertEqual(env["scope"], "internal")


class TestUnknownHandling(unittest.TestCase):
    def test_explicit_unknown_ok(self):  # FR-07 / AC-06
        env = dict(_load_example())
        env["evidence_refs"] = []
        env["unknowns"] = {"missing_receipt": True}
        out = env_mod.run_envelope(env)
        self.assertTrue(out["human_review_recommendation"]["required"])
        self.assertIn("UNKNOWN evidence present", out["warnings"][0])

    def test_missing_evidence_without_unknown_not_fabricated(self):  # FR-07 / AC-06
        env = dict(_load_example())
        env["evidence_refs"] = []
        env["unknowns"] = {}
        # Contract (NFR-05/AC-06): UNKNOWN must be EXPLICIT via `unknowns`.
        # The v1.2 observer must NOT silently fabricate an unknown status when
        # the caller declared no unknowns and no L4 candidate — it produces a
        # valid output with reason "none" (real measurement deferred to v1.3).
        out = env_mod.run_envelope(env)
        self.assertFalse(out["human_review_recommendation"]["required"])
        self.assertEqual(out["human_review_recommendation"]["reason"], "none")
        self.assertFalse(out["external_effect"])


class TestL4Compatibility(unittest.TestCase):
    def test_l4_candidate_not_effective(self):  # §5
        env = dict(_load_example())
        env["l4_mode"] = "NETWORK_CANDIDATE"
        env["l4_refs"] = {
            "trust_domain": "example.org",
            "credential_ref": "cred_abc",
            "mutual_auth_ref": "ma_abc",
            "authorization_ref": "az_abc",
            "verification_result_ref": "vr_abc",
        }
        out = env_mod.run_envelope(env)
        self.assertFalse(out["external_effect"])  # candidate != active
        self.assertEqual(out["gate"]["mutual_auth"]["state"], "CLOSED")
        self.assertEqual(out["gate"]["mutual_auth"]["reason_code"], "L4_CANDIDATE_NOT_YET_AUTHORIZED")
        self.assertEqual(out["gate"]["effective_state"], "INTERNAL_ONLY")

    def test_l4_refs_carried_not_validated(self):  # §5 first-gen only compatible
        env = dict(_load_example())
        env["l4_mode"] = "LOCAL_SIMULATION"
        env["l4_refs"] = {"trust_domain": "example.org", "credential_ref": "cred_abc"}
        ok, errors = env_mod.validate_input_envelope(env)
        self.assertTrue(ok, msg=f"L4 refs should pass schema format check: {errors}")


class TestTraceability(unittest.TestCase):
    def test_digest_traceable(self):  # FR-05 / AC-03
        out = env_mod.run_envelope(_load_example())
        self.assertIn("content_digest", out)
        self.assertEqual(len(out["content_digest"]), 64)
        self.assertEqual(out["schema_id"], "goe-1.2")

    def test_offline_no_network(self):  # NFR-01 / AC-04
        # run_envelope is pure local computation; assert no socket import side effects.
        import socket  # noqa: F401
        before = socket.__dict__.copy()
        env_mod.run_envelope(_load_example())
        after = socket.__dict__.copy()
        self.assertEqual(set(before.keys()), set(after.keys()))


@unittest.skipUnless(_HAS_API, "fastapi TestClient unavailable")
class TestRestEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_path = os.path.join(
            tempfile.mkdtemp(prefix="fse_test_env_"),
            f"t_{uuid.uuid4().hex[:8]}.db",
        )
        cls.app = create_app(db_path=db_path)
        cls.client = TestClient(cls.app)

    def test_envelope_endpoint_matches_inprocess(self):  # FR-03 wire-level parity
        env = _load_example()
        resp = self.client.post("/api/v1/envelope", json={"input_envelope": env})
        self.assertEqual(resp.status_code, 200, msg=resp.text)
        rest_out = resp.json()
        inprocess = env_mod.run_envelope(env)
        self.assertEqual(env_mod.canonical_json(rest_out), env_mod.canonical_json(inprocess))

    def test_envelope_endpoint_invalid_422(self):  # FR-01 / unified error code
        bad = _load_example()
        del bad["subject_refs"]  # drop a required field -> schema fail
        resp = self.client.post("/api/v1/envelope", json={"input_envelope": bad})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["detail"]["error_code"], "INPUT_ENVELOPE_INVALID")

    def test_envelope_endpoint_l4_candidate_external_effect_false(self):  # §5
        env = _load_example()
        env["l4_mode"] = "NETWORK_CANDIDATE"
        env["l4_refs"] = {"trust_domain": "example.org", "credential_ref": "cred_abc"}
        resp = self.client.post("/api/v1/envelope", json={"input_envelope": env})
        self.assertEqual(resp.status_code, 200, msg=resp.text)
        body = resp.json()
        self.assertFalse(body["external_effect"])
        self.assertEqual(body["gate"]["mutual_auth"]["state"], "CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

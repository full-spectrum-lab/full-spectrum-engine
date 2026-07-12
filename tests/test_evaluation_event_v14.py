#!/usr/bin/env python3
"""
v1.4 EvaluationEvent / record_evaluation — third-party-testable contract suite (T10).

Covers:
  FR-01  record_evaluation appends an immutable ORIGINAL EvaluationEvent
  FR-03  audited Output Envelope carries a *real, resolvable* replay_ref (red-line)
  FR-06  append-only: duplicate event_hash rejected; no overwrite of history
  AC-01  output_content_digest stable across original/replay of the same input
  NFR-01 offline (no network calls)
  Schema eve-1.4 validates (additionalProperties:false)

No pre-v1.4 module is touched; this suite imports only the new v1.4 facade and
reuses the unchanged v1.3 run_envelope.
"""
import json
import os
import tempfile

import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys = __import__("sys")
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import evaluation_event as ee_mod  # noqa: E402
from src.governance_chain import envelope as env_mod  # noqa: E402
from src.governance_chain import replay_store as rs_mod  # noqa: E402
from src.governance_chain import replay as replay_mod  # noqa: E402
from src.governance_chain import replay_bundle as rb_mod  # noqa: E402
from src.governance_chain.evaluation_event import EventIntegrityError, GENESIS  # noqa: E402

FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")
CROSS = os.path.join(REPO_ROOT, "tests", "fixtures", "cross_combo", "cross_ecom_knowledge_conflict.json")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _tmp_store():
    fd, path = tempfile.mkstemp(prefix="fse_v14_ev_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return rs_mod.EvaluationEventStore(path)


class TestRecordEvaluation(unittest.TestCase):
    def test_record_creates_original_event(self):  # FR-01
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ev = store.get(out["replay_ref"]["event_id"])
        self.assertIsNotNone(ev)
        self.assertEqual(ev["event_type"], "ORIGINAL")
        self.assertEqual(ev["replay_mode"], None)
        self.assertEqual(ev["source_original_event_id"], None)

    def test_replay_ref_is_real_and_resolvable(self):  # FR-03 red-line
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ref = out["replay_ref"]
        self.assertIsInstance(ref, dict)
        self.assertTrue(ref["event_id"].startswith("evt_"))
        self.assertTrue(ref["bundle_ref"].startswith("bundle_"))
        # The referenced event MUST exist in the store (no forgery).
        resolved = store.get(ref["event_id"])
        self.assertIsNotNone(resolved, "replay_ref.event_id must resolve to a stored event")
        self.assertEqual(resolved["event_id"], ref["event_id"])
        self.assertEqual(resolved["event_hash"], ref["event_digest"])

    def test_replay_ref_not_none_in_audited_output(self):  # FR-03 (anti-pattern inheritance: here it MUST be set)
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        self.assertIsNotNone(out.get("replay_ref"), "audited output must carry replay_ref")

    def test_hash_chain_starts_with_genesis(self):  # FR-06
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ev = store.get(out["replay_ref"]["event_id"])
        self.assertEqual(ev["previous_event_hash"], GENESIS)
        self.assertEqual(len(ev["event_hash"]), 64)
        int(ev["event_hash"], 16)  # must be valid hex

    def test_append_only_rejects_duplicate(self):  # FR-06 red-line
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ev = store.get(out["replay_ref"]["event_id"])
        with self.assertRaises(EventIntegrityError):
            store.append(ev)  # identical event_hash must be rejected

    def test_event_hash_content_addressed(self):  # immutability
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ev = store.get(out["replay_ref"]["event_id"])
        recomputed = ee_mod.compute_event_hash(ev)
        self.assertEqual(recomputed, ev["event_hash"])
        self.assertTrue(ev["event_id"].startswith("evt_"))
        self.assertEqual(ev["event_id"], "evt_" + ev["event_hash"][:16])

    def test_validate_event_schema_ok(self):  # eve-1.4 conforms
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        ev = store.get(out["replay_ref"]["event_id"])
        ok, errors = ee_mod.validate_event(ev)
        self.assertTrue(ok, msg=f"event failed schema validation: {errors}")

    def test_externalize_input_keeps_only_ref(self):  # NFR-03
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store, externalize_input=True)
        ev = store.get(out["replay_ref"]["event_id"])
        self.assertIsNone(ev["input_envelope"], "externalized input must not be inlined")
        self.assertNotEqual(ev["input_ref"]["location"], "inline")
        # The external file must be resolvable (recompute_or_raise enforces it).
        self.assertTrue(os.path.exists(ev["input_ref"]["location"]))

    def test_ac01_output_content_digest_stable_across_replay(self):  # AC-01
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        orig = store.get(out["replay_ref"]["event_id"])
        orig_digest = orig["result_fingerprint"]["output_content_digest"]

        bundle = rb_mod.ReplayBundle.from_event(orig)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle, replay_mode="EXACT")
        replay_digest = new_event["result_fingerprint"]["output_content_digest"]
        self.assertEqual(replay_digest, orig_digest, "AC-01: output_content_digest must be stable")

    def test_compute_canonical_diff_semantic_equal(self):  # FR-04
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        orig = store.get(out["replay_ref"]["event_id"])
        bundle = rb_mod.ReplayBundle.from_event(orig)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle, replay_mode="EXPLANATORY")
        diff = ee_mod.compute_canonical_diff(orig, new_event, mode="EXPLANATORY")
        self.assertTrue(diff["semantic_equal"], msg=diff["narrative"])
        self.assertIn("equivalent", diff["narrative"].lower())


class TestDeterminism(unittest.TestCase):
    def test_record_same_input_deterministic(self):  # NFR-01 determinism
        store = _tmp_store()
        a = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        # record a second event (different event) from the SAME input envelope
        b = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        # The deterministic result is identical (same input -> same output digest).
        base = env_mod.run_envelope(_load(FIXTURE))["content_digest"]
        ev_a = store.get(a["replay_ref"]["event_id"])
        ev_b = store.get(b["replay_ref"]["event_id"])
        self.assertEqual(ev_a["result_fingerprint"]["output_content_digest"], base)
        self.assertEqual(ev_b["result_fingerprint"]["output_content_digest"], base)
        self.assertNotEqual(ev_a["event_id"], ev_b["event_id"])

    def test_cross_combo_deterministic(self):  # mirrors v1.3 BB-05
        store = _tmp_store()
        out1 = ee_mod.record_evaluation(_load(CROSS), store=store)
        out2 = ee_mod.record_evaluation(_load(CROSS), store=store)
        ev1 = store.get(out1["replay_ref"]["event_id"])
        ev2 = store.get(out2["replay_ref"]["event_id"])
        self.assertEqual(
            ev1["result_fingerprint"]["output_content_digest"],
            ev2["result_fingerprint"]["output_content_digest"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
v1.4 ReplayEngine — third-party-testable contract suite (T10).

Covers:
  FR-05  ReplayEngine.replay appends a new REPLAY event; original unchanged
  FR-06  append-only: replay only appends; original event_hash never changes
  NFR-02 missing dependency raises explicit ReplayDependencyError (never guess)
  FR-05  --policy override rewrites the policy binding in the new event
  NFR-01 same-version recompute: replay uses the unchanged run_envelope algorithm

Replay-by-event-id (ReplayBundle.from_event) and replay-by-bundle (from_dict)
are both exercised.
"""
import json
import os
import tempfile

import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys = __import__("sys")
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import evaluation_event as ee_mod  # noqa: E402
from src.governance_chain import replay as replay_mod  # noqa: E402
from src.governance_chain import replay_bundle as rb_mod  # noqa: E402
from src.governance_chain import replay_store as rs_mod  # noqa: E402
from src.governance_chain.replay_bundle import ReplayDependencyError  # noqa: E402

FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _tmp_store():
    fd, path = tempfile.mkstemp(prefix="fse_v14_rep_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return rs_mod.EvaluationEventStore(path)


def _record_and_bundle(store):
    out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
    ev = store.get(out["replay_ref"]["event_id"])
    return ev, rb_mod.ReplayBundle.from_event(ev)


class TestReplay(unittest.TestCase):
    def test_replay_appends_replay_event_original_untouched(self):  # FR-05 / FR-06
        store = _tmp_store()
        orig, bundle = _record_and_bundle(store)
        orig_hash_before = orig["event_hash"]

        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle, replay_mode="EXACT")

        self.assertEqual(new_event["event_type"], "REPLAY")
        self.assertEqual(new_event["replay_mode"], "EXACT")
        self.assertEqual(new_event["source_original_event_id"], orig["event_id"])
        # Original must be byte-identical (no overwrite of history).
        orig_after = store.get(orig["event_id"])
        self.assertEqual(orig_after["event_hash"], orig_hash_before)
        self.assertEqual(orig_after["event_type"], "ORIGINAL")

    def test_replay_by_event_id(self):  # replay-by-event-id
        store = _tmp_store()
        out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
        orig_id = out["replay_ref"]["event_id"]
        ev = store.get(orig_id)
        bundle = rb_mod.ReplayBundle.from_event(ev)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle)
        self.assertEqual(new_event["source_original_event_id"], orig_id)

    def test_replay_by_bundle_dict(self):  # replay-by-bundle
        store = _tmp_store()
        orig, bundle = _record_and_bundle(store)
        bundle_dict = bundle.to_dict()
        rebuilt = rb_mod.ReplayBundle.from_dict(bundle_dict)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(rebuilt)
        self.assertEqual(new_event["version_bindings"]["subject"],
                         orig["version_bindings"]["subject"])

    def test_replay_modes(self):  # EXACT / SEMANTIC / EXPLANATORY
        store = _tmp_store()
        _, bundle = _record_and_bundle(store)
        engine = replay_mod.ReplayEngine(store)
        for mode in ("EXACT", "SEMANTIC", "EXPLANATORY"):
            ev = engine.replay(bundle, replay_mode=mode)
            self.assertEqual(ev["replay_mode"], mode)
            self.assertEqual(ev["event_type"], "REPLAY")

    def test_replay_semantic_equal_digest(self):  # AC-01 / AC-02
        store = _tmp_store()
        orig, bundle = _record_and_bundle(store)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle, replay_mode="EXACT")
        self.assertEqual(
            new_event["result_fingerprint"]["output_content_digest"],
            orig["result_fingerprint"]["output_content_digest"],
        )

    def test_policy_override_rewrites_binding(self):  # FR-05
        store = _tmp_store()
        _, bundle = _record_and_bundle(store)
        engine = replay_mod.ReplayEngine(store)
        new_event = engine.replay(bundle, policy_version="1.0.0")
        self.assertEqual(
            new_event["version_bindings"]["policy"]["ref"].split("@")[-1],
            "1.0.0",
        )

    def test_nfr02_missing_profile_version_raises(self):  # NFR-02 explicit, never guess
        store = _tmp_store()
        # Build a bundle whose source_profile_versions references a non-existent
        # version; recompute_or_raise must raise ReplayDependencyError.
        bad_bundle = rb_mod.ReplayBundle.from_dict({
            "bundle_id": "bundle_bad",
            "bindings": {
                "subject": {"ref": "subj_ecom_001"},
                "schema": {"input": "gie-1.2", "output": "goe-1.2"},
                "adapter": {"ref": "ecommerce_customer_service"},
                "engine": {"observer": "govchain@1.4.0", "computation": "profile_driven_v1.3"},
                "profile": {"refs": ["prof_fshi_ecom_001@9.9.9"],
                            "source_profile_versions": ["prof_fshi_ecom_001@9.9.9"]},
                "policy": {"ref": "gov_rules_default@1.0.0"},
                "knowledge": {"refs": []},
                "model": {"id": "risk_vector/profile_driven_v1.3", "version": "1.3.0"},
                "environment": {"seed": 0, "clock": "2026-01-01T00:00:00Z",
                                "contract_version": "1.2.0", "python": "3.x", "platform": "win32"},
            },
            "input_ref": {"digest": "x", "location": "inline"},
            "input_envelope": _load(FIXTURE),
            "bundle_digest": "x",
            "source_event_id": None,
        })
        engine = replay_mod.ReplayEngine(store)
        with self.assertRaises(ReplayDependencyError):
            engine.replay(bad_bundle)

    def test_unknown_replay_mode_rejected(self):
        store = _tmp_store()
        _, bundle = _record_and_bundle(store)
        engine = replay_mod.ReplayEngine(store)
        with self.assertRaises(ValueError):
            engine.replay(bundle, replay_mode="BOGUS")


if __name__ == "__main__":
    unittest.main(verbosity=2)

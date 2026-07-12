#!/usr/bin/env python3
"""
v1.4 REST endpoints — third-party-testable contract suite (T09 additive API).

Verifies the 6 additive endpoints work end-to-end against a FastAPI TestClient,
reusing the exact same facade functions the CLI uses (so REST == CLI):

    POST /api/v1/evaluation/record
    POST /api/v1/replay
    GET  /api/v1/evaluation/events/{event_id}
    GET  /api/v1/evaluation/events
    POST /api/v1/audit/export
    POST /api/v1/audit/verify

The v1.4 store is redirected to a temp SQLite so nothing persists. No pre-v1.4
endpoint or model is modified.
"""
import json
import os
import tempfile

import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys = __import__("sys")
sys.path.insert(0, REPO_ROOT)

from fastapi.testclient import TestClient  # noqa: E402

from src.api.server import create_app  # noqa: E402
from src.governance_chain import replay_store as rs_mod  # noqa: E402

FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


class TestApiV14(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix="fse_v14_api_", suffix=".sqlite")
        os.close(fd)
        os.remove(path)
        self._store = rs_mod.EvaluationEventStore(path)
        self._orig = rs_mod.get_default_store
        rs_mod.get_default_store = lambda: self._store
        self._client = TestClient(create_app())

    def tearDown(self):
        rs_mod.get_default_store = self._orig
        try:
            os.remove(self._store.db_path)
        except OSError:
            pass

    def test_evaluation_record_endpoint(self):  # FR-01
        resp = self._client.post("/api/v1/evaluation/record",
                                 json={"input_envelope": _load(FIXTURE)})
        self.assertEqual(resp.status_code, 200, msg=resp.text)
        body = resp.json()
        self.assertIsNotNone(body.get("replay_ref"))
        self.assertTrue(body["replay_ref"]["event_id"].startswith("evt_"))
        self.assertIn("X-Evaluation-Event-Id", resp.headers)

    def test_get_event_and_list_endpoints(self):  # FR-09
        rec = self._client.post("/api/v1/evaluation/record",
                                json={"input_envelope": _load(FIXTURE)}).json()
        event_id = rec["replay_ref"]["event_id"]
        g = self._client.get(f"/api/v1/evaluation/events/{event_id}")
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()["event_id"], event_id)

        lst = self._client.get("/api/v1/evaluation/events")
        self.assertEqual(lst.status_code, 200)
        self.assertGreaterEqual(lst.json()["total"], 1)

        # 404 for unknown id
        miss = self._client.get("/api/v1/evaluation/events/evt_doesnotexist")
        self.assertEqual(miss.status_code, 404)

    def test_replay_endpoint(self):  # FR-05 / FR-06
        rec = self._client.post("/api/v1/evaluation/record",
                                json={"input_envelope": _load(FIXTURE)}).json()
        event_id = rec["replay_ref"]["event_id"]
        resp = self._client.post("/api/v1/replay", json={"event_id": event_id,
                                                         "replay_mode": "EXACT"})
        self.assertEqual(resp.status_code, 200, msg=resp.text)
        new_event = resp.json()
        self.assertEqual(new_event["event_type"], "REPLAY")
        self.assertEqual(new_event["source_original_event_id"], event_id)
        # Original must still be intact
        orig = self._client.get(f"/api/v1/evaluation/events/{event_id}").json()
        self.assertEqual(orig["event_type"], "ORIGINAL")

    def test_audit_export_and_verify_endpoints(self):  # FR-09
        self._client.post("/api/v1/evaluation/record",
                          json={"input_envelope": _load(FIXTURE)})
        exp = self._client.post("/api/v1/audit/export", json={"limit": 1000})
        self.assertEqual(exp.status_code, 200)
        exp_body = exp.json()
        self.assertGreaterEqual(exp_body["count"], 1)
        self.assertIn("content", exp_body)

        ver = self._client.post("/api/v1/audit/verify", json={})
        self.assertEqual(ver.status_code, 200)
        self.assertTrue(ver.json()["ok"], msg=ver.json())
        self.assertEqual(ver.json()["tampered"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

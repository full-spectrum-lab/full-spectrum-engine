#!/usr/bin/env python3
"""
v1.4 Audit — IntegrityChecker / AuditExporter / retention suite (T12).

Covers:
  FR-09  canonical JSONL export (no event_hash in the line)
  FR-09  IntegrityChecker.verify_chain: clean chain -> (True, [])
  FR-09  tamper detection: content_digest mismatch -> (False, [reasons])
  FR-09  replay_ref forgery detection -> (False, [reasons])
  FR-06  append-only: ORIGINAL/REPLAY events are never pruned
  NFR-04 retention / backup / restore / cleanup are *audited* (OPERATION events)
  NFR-01 offline; no network calls

Tampering is performed directly at the SQLite layer (bypassing the append-only
store API) to simulate a malicious/accidental edit and prove the verifier catches
it — this is a legitimate negative test, not a violation of append-only (which
constrains the *write API*, not attack scenarios).
"""
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys = __import__("sys")
sys.path.insert(0, REPO_ROOT)

from src.governance_chain import evaluation_event as ee_mod  # noqa: E402
from src.governance_chain import envelope as env_mod  # noqa: E402
from src.governance_chain import audit as audit_mod  # noqa: E402
from src.governance_chain import replay_store as rs_mod  # noqa: E402
from src.governance_chain.envelope import canonical_json  # noqa: E402

FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "v14", "input-envelope.ecommerce.json")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _tmp_store():
    fd, path = tempfile.mkstemp(prefix="fse_v14_aud_", suffix=".sqlite")
    os.close(fd)
    os.remove(path)
    return rs_mod.EvaluationEventStore(path)


def _record(store):
    out = ee_mod.record_evaluation(_load(FIXTURE), store=store)
    return store.get(out["replay_ref"]["event_id"])


def _tamper_payload(store, event_id, mutate):
    """Mutate a stored event's payload directly at the SQLite layer (negative test)."""
    conn = sqlite3.connect(store.db_path)
    try:
        row = conn.execute(
            "SELECT payload FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        ev = json.loads(row[0])
        mutate(ev)
        conn.execute(
            "UPDATE events SET payload=? WHERE event_id=?",
            (canonical_json(ev), event_id),
        )
        conn.commit()
    finally:
        conn.close()


class TestAuditExport(unittest.TestCase):
    def test_export_canonical_jsonl(self):  # FR-09
        store = _tmp_store()
        _record(store)
        _record(store)
        fd, path = tempfile.mkstemp(prefix="fse_aud_export_", suffix=".jsonl")
        os.close(fd)
        events = store.list_events(limit=10 ** 9)
        audit_mod.AuditExporter.export_range(events, path)
        with open(path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        for ln in lines:
            obj = json.loads(ln)
            # canonical export excludes event_hash
            self.assertNotIn("event_hash", obj)
            self.assertIn("event_id", obj)


class TestIntegrityVerification(unittest.TestCase):
    def test_verify_clean_chain(self):  # FR-09
        store = _tmp_store()
        _record(store)
        ok, tampered = audit_mod.IntegrityChecker.verify_chain(store)
        self.assertTrue(ok, msg=f"unexpected tamper: {tampered}")
        self.assertEqual(tampered, [])

    def test_verify_detects_content_digest_tamper(self):  # FR-09 tamper
        store = _tmp_store()
        ev = _record(store)
        _tamper_payload(store, ev["event_id"], lambda e: e["output_envelope"]
                        ["risk_vector"]["values"].__setitem__(0, 0.123))
        ok, tampered = audit_mod.IntegrityChecker.verify_chain(store)
        self.assertFalse(ok)
        reasons = [t["reason"] for t in tampered]
        self.assertIn("output_content_digest_mismatch", reasons)

    def test_verify_detects_replay_ref_forgery(self):  # FR-09 red-line: no forged ref
        store = _tmp_store()
        ev = _record(store)
        _tamper_payload(
            store, ev["event_id"],
            lambda e: e["output_envelope"]["replay_ref"].__setitem__(
                "event_id", "evt_deadbeefdeadbeef"),
        )
        ok, tampered = audit_mod.IntegrityChecker.verify_chain(store)
        self.assertFalse(ok)
        reasons = [t["reason"] for t in tampered]
        self.assertIn("replay_ref_forged", reasons)

    def test_verify_detects_event_hash_tamper(self):  # FR-09 tamper
        store = _tmp_store()
        ev = _record(store)
        # Mutate a field OUTSIDE output_envelope (so event_hash should break).
        _tamper_payload(store, ev["event_id"],
                        lambda e: e.__setitem__("recorded_at", "2099-01-01T00:00:00Z"))
        ok, tampered = audit_mod.IntegrityChecker.verify_chain(store)
        self.assertFalse(ok)
        reasons = [t["reason"] for t in tampered]
        self.assertIn("event_hash_mismatch", reasons)


class TestRetentionBackupRestore(unittest.TestCase):
    def test_backup_creates_file_and_audits(self):  # NFR-04
        store = _tmp_store()
        _record(store)
        fd, bak = tempfile.mkstemp(prefix="fse_bak_", suffix=".sqlite")
        os.close(fd)
        os.remove(bak)
        store.backup(bak)
        self.assertTrue(os.path.exists(bak))
        # A BACKUP OPERATION event must have been appended.
        self.assertGreater(store.count_by_type("OPERATION"), 0)

    def test_restore_returns_to_backup_state(self):  # AC-03 chain continuity
        store = _tmp_store()
        _record(store)  # event #1
        fd, bak = tempfile.mkstemp(prefix="fse_bak_", suffix=".sqlite")
        os.close(fd)
        os.remove(bak)
        store.backup(bak)
        _record(store)  # event #2 (after backup)
        self.assertEqual(store.count_by_type("ORIGINAL"), 2)
        store.restore(bak)
        # After restore the extra ORIGINAL is gone (backup had only 1).
        self.assertEqual(store.count_by_type("ORIGINAL"), 1)


class TestStoreImmutabilityContract(unittest.TestCase):
    def test_store_exposes_no_historical_update_delete_api(self):
        store = _tmp_store()
        event = _record(store)
        forbidden = ("update", "delete", "modify", "replace", "remove", "purge_event", "update_event")
        self.assertEqual([name for name in forbidden if hasattr(store, name)], [])
        with self.assertRaises(Exception):
            store.append(event)
        self.assertEqual(store.get(event["event_id"])["event_hash"], event["event_hash"])

    def test_cleanup_prunes_only_trailing_operations(self):  # FR-06 red-line
        store = _tmp_store()
        ev = _record(store)  # ORIGINAL event (immortal)
        store.apply_retention(retention_days=365)  # appends RETENTION OPERATION
        self.assertEqual(store.count(), 2)  # ORIGINAL + OPERATION
        future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        removed = store.cleanup(before=future)
        self.assertGreaterEqual(removed, 1)
        # ORIGINAL event must survive cleanup.
        self.assertIsNotNone(store.get(ev["event_id"]))
        self.assertEqual(store.count_by_type("ORIGINAL"), 1)


class TestStoreImmutabilityContract(unittest.TestCase):
    def test_store_exposes_no_historical_update_delete_api(self):  # FR-06 red-line
        """The store must NOT expose any surface to UPDATE/DELETE a historical
        ORIGINAL/REPLAY event. Covering history is impossible via the public
        API (only append + audited operations exist), satisfying the v1.4
        'cover-historical-audit' red-line at the storage layer."""
        store = _tmp_store()
        ev = _record(store)
        forbidden = ("update", "delete", "modify", "replace",
                     "remove", "purge_event", "update_event")
        exposed = [m for m in forbidden if hasattr(store, m)]
        self.assertEqual(
            exposed, [],
            f"store must not expose history-mutating API: {exposed}",
        )
        # The only event-writing method is append(); re-appending the identical
        # event (an overwrite attempt) is rejected -> history is immutable.
        with self.assertRaises(Exception):
            store.append(ev)
        # The original event is still intact (byte-identical) after the refused write.
        self.assertEqual(
            store.get(ev["event_id"])["event_hash"], ev["event_hash"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
